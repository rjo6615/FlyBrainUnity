"""Frozen, read-only MaleCNS motor-population activity survey.

Importing this module and ``--preflight`` execute no neural or physics steps.
Only ``--execute`` may run the preregistered one-second observation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

HERE = Path(__file__).resolve().parent
OUTPUT_DIR = HERE / "interface_output" / "motor_population_activity_survey"
INVENTORY_PATH = OUTPUT_DIR / "motor_population_inventory.json"
PREREGISTRATION_PATH = OUTPUT_DIR / "motor_population_activity_survey_preregistration.json"
RAW_PATH = OUTPUT_DIR / "motor_population_activity_survey_raw.npz"
REPORT_PATH = OUTPUT_DIR / "motor_population_activity_survey_report.json"
EXECUTION_MANIFEST_PATH = OUTPUT_DIR / "motor_population_activity_survey_execution_manifest.json"
FINAL_MANIFEST_PATH = OUTPUT_DIR / "motor_population_activity_survey_final_manifest.json"
INVENTORY_SHA256 = "b0fbbe9d7bf5d83ee2b7b6d8d458be92105344c7bef24729e9e2969edaabc5cb"
# Frozen after the preregistration was serialized and reviewed.
PREREGISTRATION_SHA256 = "8cf9e38219316886a69e5970c5d521283cf652e8a747fba77d99cd4ccc0eaff5"
SEED, DURATION_MS, NEURAL_DT_MS, PHYSICS_DT_MS = 1, 1000, 0.5, 0.1
NEURAL_TRANSITIONS, PHYSICS_TRANSITIONS, BIN_WIDTH_MS = 2000, 10000, 25
RATE_TAU_MS = 40.0
RESULT_PATHS = (RAW_PATH, REPORT_PATH, EXECUTION_MANIFEST_PATH, FINAL_MANIFEST_PATH)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def load_inventory(path: Path = INVENTORY_PATH) -> dict[str, Any]:
    if not path.is_file() or sha256(path) != INVENTORY_SHA256:
        raise RuntimeError("frozen motor-population inventory SHA-256 mismatch")
    value = json.loads(path.read_text(encoding="utf-8")); populations = value.get("population_inventory", [])
    indices = [i for p in populations for i in p.get("dense_neural_indices", [])]
    ids = [i for p in populations for i in p.get("neuron_ids", [])]
    checks = (len(populations) == 102, len(indices) == 328, len(set(ids)) == 328,
              len(indices) == len(ids), all(isinstance(i, int) and i >= 0 for i in indices),
              all(len(p["dense_neural_indices"]) == p["neuron_count"] for p in populations),
              len(value.get("admitted_11_inventory", [])) == 11,
              value.get("summary", {}).get("admitted_channel_count") == 11)
    if not all(checks):
        raise RuntimeError("frozen motor-population inventory invariant failure")
    return value


def verify_preregistration(path: Path = PREREGISTRATION_PATH) -> dict[str, Any]:
    if PREREGISTRATION_SHA256 == "TO_BE_FROZEN" or not path.is_file() or sha256(path) != PREREGISTRATION_SHA256:
        raise RuntimeError("frozen survey preregistration SHA-256 mismatch")
    value = json.loads(path.read_text(encoding="utf-8"))
    if (value.get("inventory_sha256") != INVENTORY_SHA256 or value.get("seed") != SEED or
            value.get("duration_ms") != DURATION_MS or value.get("neural_dt_ms") != NEURAL_DT_MS or
            value.get("physics_dt_ms") != PHYSICS_DT_MS or value.get("bin_width_ms") != BIN_WIDTH_MS or
            value.get("expected_neural_transitions") != NEURAL_TRANSITIONS or
            value.get("expected_physics_transitions") != PHYSICS_TRANSITIONS):
        raise RuntimeError("frozen survey preregistration invariant failure")
    return value


def classify(total_spike_increments: int, active_transition_fraction: float) -> str:
    if total_spike_increments == 0: return "OBSERVED_SILENT"
    if active_transition_fraction < 0.01: return "OBSERVED_LOW_ACTIVITY"
    return "OBSERVED_ACTIVE"


class PopulationActivityObserver:
    """Pure accumulator over copies of cumulative counts and physical action."""
    def __init__(self, inventory: Mapping[str, Any]):
        self.populations = tuple(inventory["population_inventory"])
        self.last: np.ndarray | None = None; self.filtered: np.ndarray | None = None
        self.transitions = 0; self.initial_action: np.ndarray | None = None
        self.rows = []
        for p in self.populations:
            n = p["neuron_count"]
            self.rows.append({"total": 0, "per_neuron": np.zeros(n, np.uint64), "peak_increment": 0,
                "rate_sum": 0.0, "peak_rate": 0.0, "first": None, "last": None, "active": 0,
                "bins": [{"total_spike_increments": 0, "active_neuron_indices": set(),
                          "rate_sum": 0.0, "peak_filtered_rate_hz": 0.0, "samples": 0}
                         for _ in range(DURATION_MS // BIN_WIDTH_MS)]})

    def initialize(self, spike_counts: Any) -> None:
        counts = np.asarray(spike_counts)
        if counts.ndim != 1: raise RuntimeError("spike-count state is not dense one-dimensional state")
        maximum = max(i for p in self.populations for i in p["dense_neural_indices"])
        if maximum >= counts.size: raise RuntimeError("inventory dense index exceeds live MaleCNS state")
        self.last = counts.astype(np.uint64, copy=True); self.filtered = np.zeros(counts.size, np.float64)

    def observe(self, *, time_ms: float, spike_counts: Any, physical_action: Any,
                neural_transition_count: int, physics_transition_count: int) -> None:
        current = np.asarray(spike_counts, dtype=np.uint64)
        action = np.asarray(physical_action, dtype=np.float64)
        if self.last is None or self.filtered is None: raise RuntimeError("observer was not initialized")
        if action.shape != (42,): raise RuntimeError("physical action is not exactly 42 entries")
        if neural_transition_count != self.transitions + 1:
            raise RuntimeError("observer cadence differs from authoritative neural transitions")
        if physics_transition_count != neural_transition_count * 5:
            raise RuntimeError("observer cadence differs from authoritative physics transitions")
        before_current, before_action = current.copy(), action.copy()
        increments = current - self.last
        self.filtered += (NEURAL_DT_MS / RATE_TAU_MS) * (increments * (1000 / NEURAL_DT_MS) - self.filtered)
        bin_index = min(int(time_ms // BIN_WIDTH_MS), len(self.rows[0]["bins"]) - 1)
        for p, row in zip(self.populations, self.rows):
            ix = np.asarray(p["dense_neural_indices"], dtype=np.intp); inc = increments[ix]; rates = self.filtered[ix]
            total = int(inc.sum()); row["total"] += total; row["per_neuron"] += inc
            row["peak_increment"] = max(row["peak_increment"], int(inc.max(initial=0)))
            row["rate_sum"] += float(rates.mean()); row["peak_rate"] = max(row["peak_rate"], float(rates.max(initial=0)))
            if total: row["first"] = time_ms if row["first"] is None else row["first"]; row["last"] = time_ms; row["active"] += 1
            b = row["bins"][bin_index]; b["total_spike_increments"] += total
            b["active_neuron_indices"].update(np.flatnonzero(inc).tolist()); b["rate_sum"] += float(rates.mean())
            b["peak_filtered_rate_hz"] = max(b["peak_filtered_rate_hz"], float(rates.max(initial=0))); b["samples"] += 1
        self.last = current.copy(); self.transitions += 1
        if not np.array_equal(current, before_current) or not np.array_equal(action, before_action):
            raise RuntimeError("read-only observer mutated supplied state")

    def finalize(self) -> dict[str, Any]:
        if self.transitions != NEURAL_TRANSITIONS: raise RuntimeError("wrong authoritative neural transition count")
        result = []
        for p, row in zip(self.populations, self.rows):
            active_neurons = int(np.count_nonzero(row["per_neuron"])); count = p["neuron_count"]
            fraction = row["active"] / self.transitions
            bins = [{"total_spike_increments": b["total_spike_increments"],
                     "active_member_neurons": len(b["active_neuron_indices"]),
                     "mean_filtered_rate_hz": b["rate_sum"] / b["samples"],
                     "peak_filtered_rate_hz": b["peak_filtered_rate_hz"]} for b in row["bins"]]
            identity = dict(p)
            result.append({**identity, "activity_classification": classify(row["total"], fraction),
                "total_spike_increments": row["total"], "active_member_neurons": active_neurons,
                "active_member_neuron_fraction": active_neurons / count,
                "mean_spike_increments_per_neuron": row["total"] / count,
                "peak_spike_increments_member_neuron": row["peak_increment"],
                "mean_per_neuron_filtered_rate_hz": row["rate_sum"] / self.transitions,
                "peak_filtered_rate_hz": row["peak_rate"], "first_activity_time_ms": row["first"],
                "last_activity_time_ms": row["last"], "active_neural_transition_count": row["active"],
                "active_neural_transition_fraction": fraction, "directional_activity": None,
                "bins": bins})
        return {"populations": result, "neural_transitions": self.transitions}


def assert_outputs_available() -> None:
    existing = [str(p) for p in RESULT_PATHS if p.exists()]
    if existing: raise FileExistsError("refusing to overwrite survey output: " + ", ".join(existing))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__); mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true"); mode.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv); load_inventory(); verify_preregistration(); assert_outputs_available()
    from . import _windows_motor_population_activity_survey_adapter as adapter
    if args.preflight:
        report = adapter.preflight(); print(canonical_json(report), end="")
    else:
        # Execution always repeats the zero-transition preflight first.
        adapter.preflight(); adapter.execute()
    return 0


if __name__ == "__main__": raise SystemExit(main())
