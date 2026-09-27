"""Read-only, fail-closed assessment of M8 for the LF recruitment replay.

This utility imports only the standard library and NumPy.  It never imports a
runner, FlyGym, MuJoCo, or the neural runtime, and it never writes a replay.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
RAW = HERE / "interface_output/m8_extended_spontaneous/m8_raw.npz"
PREREG = HERE / "interface_output/lf_proximal_motor_recruitment/lf_proximal_motor_recruitment_preregistration.json"
JOINT_SOURCE = HERE / "m7e_postrun_analysis.py"
LOOP_SOURCE = HERE / "_windows_m8_live_condition.py"
ENCODER_SOURCE = HERE / "sensory.py"
TELEMETRY_SOURCE = HERE / "m7_telemetry.py"
SIX_MAP = HERE / "six_leg_map.json"
EXPECTED_RAW_SHA256 = "4e39bb83dd4455d56a4d88f717615530602317efaf83a6ed241b13af89dc2a5b"
CONDITION = "CORRECTED_SPONTANEOUS_NEURAL_EMBODIMENT"
JOINTS = tuple(f"joint_{leg}Tibia" for leg in ("LF", "LM", "LH", "RF", "RM", "RH"))
EXPECTED_COLUMNS = (5, 12, 19, 26, 33, 40)
TIME_ATOL_MS = 1e-9
ENCODER_ATOL_HZ = 1e-12


class ProvenanceFailure(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ProvenanceFailure(f"expected JSON object: {path}")
    return value


def source_joint_names() -> tuple[str, ...]:
    """Evaluate only the literal JOINT_NAMES comprehension from tracked source."""
    tree = ast.parse(JOINT_SOURCE.read_text(encoding="utf-8"), filename=str(JOINT_SOURCE))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "JOINT_NAMES" for t in node.targets):
            value = eval(compile(ast.Expression(node.value), str(JOINT_SOURCE), "eval"), {"__builtins__": {"tuple": tuple}})
            return tuple(value)
    raise ProvenanceFailure("tracked JOINT_NAMES assignment not found")


def sensor_member_counts() -> tuple[int, ...]:
    audit = load_json(SIX_MAP)
    counts = []
    order = []
    for leg in audit.get("legs", []):
        tibiae = [j for j in leg["joints"] if j["actuator"]["anatomical_joint"] == "tibia"]
        if len(tibiae) != 1 or len(tibiae[0]["sensory"]["populations"]) != 1:
            raise ProvenanceFailure("six_leg_map does not contain one unique tibial sensor per leg")
        order.append(leg["leg"])
        counts.append(len(tibiae[0]["sensory"]["populations"][0]["body_ids"]))
    if tuple(order) != ("LF", "LM", "LH", "RF", "RM", "RH"):
        raise ProvenanceFailure(f"unexpected sensory leg order: {order}")
    return tuple(counts)


def encoded_peak(q: Any, n: int) -> Any:
    x = (q - (-1.35)) / (1.30 - (-1.35))
    preferred = (np.arange(n, dtype=np.float64) + 0.5) / n
    rates = 120.0 * np.exp(-((x[:, None] - preferred) ** 2) / (2 * 0.25 ** 2))
    rates[rates <= 5.0] = 0.0
    return np.clip(rates, 0.0, 120.0).max(axis=1)


def assess() -> dict[str, Any]:
    # The byte digest is deliberately computed before np.load touches scientific data.
    observed_sha = sha256(RAW)
    if observed_sha != EXPECTED_RAW_SHA256:
        raise ProvenanceFailure(f"M8 SHA-256 mismatch: expected {EXPECTED_RAW_SHA256}, observed {observed_sha}")

    # Delay the scientific-data dependency until after the authoritative byte
    # check.  A pointer, truncated file, or altered archive therefore fails
    # without NumPy opening or interpreting any archive content.
    global np
    import numpy as np

    prereg = load_json(PREREG)  # read in full; requirements below are checked by exact path
    protocol = prereg["numerical_protocol"]
    precondition = prereg["implementation_precondition_fail_closed"]
    pathway = prereg["sensory_pathway_implementation_audit"]
    if protocol["runtime_ms"] != 1000.0 or protocol["sensory_sample_ms"] != 1.0:
        raise ProvenanceFailure("preregistered replay duration/cadence changed")
    if pathway["physically_measured_variables"]["neural_input_sources"] != (
        "Six FlyGym tibia joint positions in radians, ordered LF, LM, LH, RF, RM, RH and observed once per 1.0-ms control sample."):
        raise ProvenanceFailure("preregistered physical input definition changed")

    names = source_joint_names()
    columns = tuple(names.index(name) for name in JOINTS)
    if columns != EXPECTED_COLUMNS:
        raise ProvenanceFailure(f"tracked joint ordering mismatch: {columns}")

    prefix = CONDITION + "__"
    with np.load(RAW, allow_pickle=False) as archive:
        t = archive[prefix + "physics_time_ms"].copy()
        positions = archive[prefix + "physics_joint_position"].copy()
        nt = archive[prefix + "neural_time_ms"].copy()
        frozen_encoded = archive[prefix + "neural_sensory_encoded"].copy()
    selected = positions[:, columns].copy()
    source_selection_unchanged = np.array_equal(selected, positions[:, columns], equal_nan=True)

    expected_t = np.arange(100001, dtype=np.float64) * 0.1
    time_ok = (t.shape == (100001,) and np.all(np.isfinite(t)) and np.all(np.diff(t) > 0)
               and np.allclose(t, expected_t, rtol=0.0, atol=TIME_ATOL_MS))
    trajectory_ok = positions.shape == (100001, 42) and selected.shape == (100001, 6) and np.all(np.isfinite(selected))
    neural_time_ok = (nt.shape == (20000,) and np.all(np.isfinite(nt)) and
                      np.allclose(nt, np.arange(1, 20001) * 0.5, rtol=0.0, atol=TIME_ATOL_MS))

    # Loop source samples current measured state at steps 5,10,..., then stores a
    # per-population peak.  Compare all 20,000 frozen observations analytically.
    aligned_rows = np.arange(5, 100001, 5)
    reconstructed = np.column_stack([
        encoded_peak(selected[aligned_rows, channel], count)
        for channel, count in enumerate(sensor_member_counts())
    ])
    residual = np.abs(reconstructed - frozen_encoded)
    encoder_ok = (frozen_encoded.shape == (20000, 6) and np.all(np.isfinite(frozen_encoded))
                  and np.allclose(reconstructed, frozen_encoded, rtol=0.0, atol=ENCODER_ATOL_HZ))

    return {
        "schema": "M8-LF-PROXIMAL-REPLAY-ASSESSMENT.1",
        "final_status": "M8_COMPATIBLE_ADDENDUM_REQUIRED_BEFORE_EXTRACTION",
        "scientific_execution": {"simulation_steps": 0, "physics_steps": 0, "neural_steps": 0},
        "source": {"path": str(RAW.relative_to(REPO)), "sha256": observed_sha, "condition": CONDITION,
                   "field": "physics_joint_position", "seed": 1},
        "preregistered_requirements": {
            "duration_ms": protocol["runtime_ms"], "sample_cadence_ms": protocol["sensory_sample_ms"],
            "channel_order": list(JOINTS), "units": "radians", "replay_count": 1,
            "replay_seed_use": "one unchanged frozen replay shared by seeds 1, 2, and 3",
            "encoder": pathway["modeled_sensory_transduction"],
            "state_requirement": prereg["pairing_and_state_copy"],
            "interval_selection_rule": None,
            "fail_closed_requirement": precondition,
        },
        "source_code_provenance": {str(p.relative_to(REPO)): sha256(p) for p in
            (PREREG, JOINT_SOURCE, LOOP_SOURCE, ENCODER_SOURCE, TELEMETRY_SOURCE, SIX_MAP)},
        "verification": {
            "joint_columns": list(columns), "joint_names": list(JOINTS),
            "physics_time": {"shape": list(t.shape), "finite": bool(np.all(np.isfinite(t))),
                "strictly_increasing": bool(np.all(np.diff(t) > 0)), "start_ms": float(t[0]),
                "end_ms": float(t[-1]), "expected_cadence_ms": 0.1, "absolute_tolerance_ms": TIME_ATOL_MS,
                "max_grid_error_ms": float(np.max(np.abs(t - expected_t))), "valid": bool(time_ok)},
            "tibial_trajectories": {"shape": list(selected.shape), "finite": bool(np.all(np.isfinite(selected))),
                "pure_copy_comparison_unchanged": bool(source_selection_unchanged), "valid": bool(trajectory_ok)},
            "temporal_alignment": {"rule": "neural row i uses physics row 5*(i+1) at time (i+1)*0.5 ms",
                "physics_rows": [5, 100000], "neural_time_valid": bool(neural_time_ok)},
            "encoder_consistency": {"comparison": "all 20000x6 per-interface peak rates",
                "absolute_tolerance_hz": ENCODER_ATOL_HZ, "max_absolute_error_hz": float(residual.max()),
                "exact_float64_equal_count": int(np.count_nonzero(reconstructed == frozen_encoded)),
                "value_count": int(frozen_encoded.size), "valid": bool(encoder_ok),
                "rng_or_hidden_state_needed": False,
                "scope": "deterministic encoded-rate peaks only; stochastic external events are not reconstructed"},
        },
        "compatibility": {
            "m8_can_supply_required_physical_variables": bool(time_ok and trajectory_ok and neural_time_ok and encoder_ok),
            "blocked_reason": "The preregistration requires a frozen replay but specifies no outcome-independent source interval.",
            "decision": "Do not extract until a preregistration addendum freezes an interval-selection rule.",
            "no_replay_artifact_created": True,
        },
        "interpretation_boundary": "Angles are FlyGym/MuJoCo measured joint coordinates; encoding is modeled proprioceptive transduction, not biological proprioception."
    }


def main() -> None:
    print(json.dumps(assess(), indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
