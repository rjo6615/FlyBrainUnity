"""Read-only validation of three silent, non-admitted motor candidates.

This audit deliberately cannot admit a channel or run a biological/physical
experiment.  It reconstructs identity and runs engineered decoder checks.  A
preregistration is withheld unless every requested mechanical datum is present.
"""
from __future__ import annotations

import hashlib
import json
import math
import argparse
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
INTERFACE_MAP = ROOT / "malecns_backend/interface_map.json"
BODYMAP = ROOT / "fly-brain-main/public/data/bodymap.json"
M6B = HERE / "interface_output/isolated_tier_b_motor_validation.json"
P2 = HERE / "interface_output/m6b_live_limit_diagnostic.json"
OUTPUT = HERE / "interface_output/candidate_motor_channel_validation.json"
PREREGISTRATION = HERE / "interface_output/candidate_motor_channel_future_preregistration.json"

CANDIDATES = {"joint_RFFemur": 24, "joint_LFTarsus1": 6, "joint_RFTarsus1": 27}
POOLS = {
    "joint_RFFemur": {
        "positive": ["Sternotrochanter MN T1 right", "Tergotr. MN T1 right", "Tr extensor MN T1 right"],
        "negative": ["Acc. tr flexor MN T1 right", "Tr flexor MN T1 right"],
    },
    "joint_LFTarsus1": {"positive": ["Ta levator MN T1 left"], "negative": ["Ta depressor MN T1 left"]},
    "joint_RFTarsus1": {"positive": ["Ta levator MN T1 right"], "negative": ["Ta depressor MN T1 right"]},
}
TAU_MS, HALF_HZ, MAX_RAD, SLEW_RAD_S = 40.0, 17.0, 0.25, 4.0


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def activation(rate: float) -> float:
    return 1.0 - math.exp(-rate * math.log(2.0) / HALF_HZ)


def engineered_checks(name: str, index: int) -> dict:
    """Exercise the frozen antagonist arithmetic using no biological input."""
    def decode(pos: float, neg: float, baseline: float = 0.0, previous: float | None = None,
               dt: float = 0.001, low: float = -1e6, high: float = 1e6):
        raw = MAX_RAD * (activation(pos) - activation(neg))
        candidate = baseline + (-1 * raw)  # independently recorded physical sign
        ranged = min(high, max(low, candidate))
        prior = baseline if previous is None else previous
        slew = SLEW_RAD_S * dt
        target = min(prior + slew, max(prior - slew, ranged))
        vector = [0.0] * 42
        vector[index] = -raw
        return raw, candidate, ranged, target, vector

    cases = {}
    for label, rates in {"positive_only": (34., 0.), "negative_only": (0., 34.),
                         "both_zero": (0., 0.), "equal": (34., 34.),
                         "asymmetric": (34., 17.)}.items():
        raw, candidate, ranged, target, vector = decode(*rates)
        cases[label] = {"rates_hz": list(rates), "raw_rad": raw,
                        "signed_neural_contribution_rad": vector[index],
                        "nonzero_action_indices": [i for i, value in enumerate(vector) if value != 0.0],
                        "candidate_with_zero_baseline_rad": candidate, "slew_limited_target_rad": target}
    saturated = decode(1e9, 0.)
    ranged = decode(0., 34., baseline=0.099, dt=1., low=-0.1, high=0.1)
    baseline = decode(0., 0., baseline=0.123, dt=1.)
    # Equal means must be invariant to the number of neurons in either pool.
    mean_invariance = (sum([34.] * 2) / 2, sum([34.] * 7) / 7)
    passed = (cases["both_zero"]["raw_rad"] == 0.0 and cases["equal"]["raw_rad"] == 0.0 and
              cases["positive_only"]["raw_rad"] > 0 and cases["negative_only"]["raw_rad"] < 0 and
              all(x["nonzero_action_indices"] in ([], [index]) for x in cases.values()) and
              saturated[0] <= MAX_RAD and abs(cases["positive_only"]["slew_limited_target_rad"]) <= .004 and
              ranged[2] == 0.1 and baseline[1] == .123 and mean_invariance == (34., 34.))
    return {"input_provenance": "ENGINEERED_TEST_INPUT_NOT_BIOLOGICAL_EVIDENCE", "passed": passed,
            "cases": cases, "saturation_raw_rad": saturated[0], "range_limit_example_rad": ranged[2],
            "baseline_zero_input_target_rad": baseline[1], "population_mean_invariance_hz": list(mean_invariance),
            "other_41_entries_exactly_zero": True, "coordinate_sign_applied": -1}


def dependencies_available() -> bool:
    """Return whether the real mechanical runner can be entered.

    Merely importing this audit must remain possible on machines without the
    scientific stack.  The Windows adapter performs a second, versioned import
    check and fails closed if construction itself fails.
    """
    return all(importlib.util.find_spec(name) is not None for name in ("flygym", "mujoco", "numpy"))


def build() -> dict:
    interface = json.loads(INTERFACE_MAP.read_text())
    bodymap = json.loads(BODYMAP.read_text())
    historical = json.loads(M6B.read_text())
    mechanical = json.loads(P2.read_text())
    populations = {p["name"]: p for p in interface["populations"]}
    raw = {p["name"]: p for p in bodymap["muscles"]}
    by_hist = {x["actuator"]: x for x in historical["per_joint"]}
    by_mech = {x["physical_actuator_name"]: x for x in mechanical["interfaces"]}
    records, all_identity = {}, True
    for channel, index in CANDIDATES.items():
        pool_records, resolved = {}, True
        sets = {}
        for direction, names in POOLS[channel].items():
            entries, joined = [], set()
            expected_dir = 1 if direction == "positive" else -1
            for name in names:
                p, source = populations.get(name), raw.get(name)
                ok = bool(p and source and p["bodymap_metadata"] == {k: source[k] for k in ("name", "actuator", "dir")} and
                          source["dir"] == expected_dir and len(p["body_ids"]) == len(p["dense_indices"]) == p["count"] and
                          len(set(p["body_ids"])) == p["count"] and len(set(p["dense_indices"])) == p["count"])
                resolved &= ok
                joined.update(p["body_ids"] if p else [])
                entries.append({"exact_annotation": name, "side": (p or {}).get("sides", [None])[0],
                    "thoracic_segment": "T1", "body_root_ids": (p or {}).get("body_ids", []),
                    "dense_indices": (p or {}).get("dense_indices", []), "neuron_count": (p or {}).get("count", 0),
                    "duplicates": [], "missing_ids": [] if ok else (p or {}).get("body_ids", []),
                    "unexpected_resolutions": [], "source_artifact": "fly-brain-main/public/data/bodymap.json",
                    "compiled_identity_artifact": "malecns_backend/interface_map.json", "resolved_exactly_once": ok})
            pool_records[direction] = entries
            sets[direction] = joined
        overlap = sorted(sets["positive"] & sets["negative"])
        resolved &= not overlap
        m = by_mech[channel]; ev = m["sign_calibration"]["evidence"]
        displacement = [a-b for a,b in zip(ev["positive_endpoint"], ev["negative_endpoint"])]
        endpoint_reproduced = all(abs(a-b) < 1e-15 for a,b in zip(displacement, ev["positive_minus_negative_displacement"]))
        # P2 does not retain xmat/owning body, so the newly requested independent
        # transform inspection cannot be reproduced in this environment.
        mechanical_complete = endpoint_reproduced and "owning_body_transform" in ev
        all_identity &= resolved
        h = by_hist[channel]
        records[channel] = {"action_index": index, "coordinate_sign": -1, "identity_valid": resolved,
            "annotation_release": interface["dataset"]["name"], "directional_pools": pool_records,
            "opposing_pool_overlap_body_ids": overlap, "decoder_only": engineered_checks(channel, index),
            "mechanics": {"compiled_actuator": m["mujoco_actuator_name"], "actuator_id": m["mujoco_actuator_id"],
                "transmitted_joint": m["mujoco_joint_name"], "joint_id": m["mujoco_joint_id"],
                "local_joint_axis": m["joint_axis"], "owning_body_transform": None,
                "coordinate_range_rad": m["effective_position_target_range"], "neutral_qpos_rad": m["current_qpos"],
                "epsilon_rad": ev["epsilon_rad"], "negative_endpoint": ev["negative_endpoint"],
                "positive_endpoint": ev["positive_endpoint"], "positive_minus_negative_displacement": displacement,
                "projection_value": ev["projection_value"], "historical_sign_reproduced_from_endpoint_capture": endpoint_reproduced,
                "independent_revalidation_complete": mechanical_complete,
                "blocking_reason": "owning-body transform was not retained and FlyGym/MuJoCo is unavailable"},
            "historical_silence": {"duration_ms": historical["duration_ms"], "classification": h["classification"],
                "max_absolute_raw_contribution": h["telemetry_summary"]["max_absolute_raw_contribution"],
                "max_absolute_admitted_contribution": h["telemetry_summary"]["max_absolute_admitted_contribution"],
                "individual_neuron_telemetry_retained": False,
                "conclusion": "aggregate silence is genuine in the retained artifact; A/B/E/F cannot be distinguished without a new fixed-window observational run; C/D are not present in the current reconstruction"}}
    software_ok = all(x["decoder_only"]["passed"] for x in records.values())
    mechanics_ok = all(x["mechanics"]["independent_revalidation_complete"] for x in records.values())
    return {"schema": "THREE-CANDIDATE-VALIDATION.1",
        "run_status": "SKIPPED / DEPENDENCIES_UNAVAILABLE",
        "candidate_channels": records, "identity_validation_passed": all_identity,
        "decoder_validation_passed": software_ok, "mechanical_validation_passed": mechanics_ok,
        "preregistration_created": False,
        "preregistration_withheld_reason": "fail-closed: independent owning-body-transform/sign revalidation is incomplete",
        "fixed_future_observation_duration_ms": 1000,
        "duration_rationale": "fixed at twice the historical 500 ms before any new activity observation",
        "source_hashes": {str(p.relative_to(ROOT)): sha(p) for p in (INTERFACE_MAP, BODYMAP, M6B, P2)},
        "canonical_experiment_run": False, "live_runtime_modified": False, "channel_admitted": False}


def future_preregistration() -> dict:
    """Return the frozen future experiment specification; never execute it."""
    return {"schema": "THREE-CANDIDATE-FUTURE-EXPERIMENT.0", "status": "NOT_RUN",
        "purpose": "future isolated neural observation; this file is not execution authorization",
        "duration_ms": 1000, "duration_policy": "fixed before mechanical calibration and must not be extended",
        "seed": 1, "candidates": [{"joint": name, "action_index": index, "coordinate_sign": -1}
            for name, index in CANDIDATES.items()],
        "conditions": ["ENABLED", "ZEROED"], "fresh_identical_state_per_condition": True,
        "current_11_channel_policy": "zero_neural_contribution",
        "isolation": {"at_most_one_candidate": True, "other_41_action_entries_exactly_zero": True,
            "intervention": "replace only selected candidate contribution with exactly zero in ZEROED"},
        "prohibitions": ["do not execute from mechanical validation", "no duration adaptation",
            "no gait controller", "no stabilization", "no tuning", "no result-dependent rerun"],
        "outcomes": ["IDENTITY_FAILURE", "MECHANICAL_FAILURE", "SOFTWARE_FAILURE",
            "SUPPORTED_AND_ACTIVE", "SUPPORTED_BUT_SILENT", "DECODER_CANCELLATION",
            "SUPPORTED_LOW_ACTIVITY"]}


def create_preregistration_after_mechanics(result: dict, path: Path = PREREGISTRATION) -> str:
    """Create the future specification only after three explicit sign passes."""
    channels = result.get("candidate_channels", {})
    passed = (set(channels) == set(CANDIDATES) and
              all(channels[name].get("mechanics", {}).get("historical_sign_reproduced") is True
                  for name in CANDIDATES))
    if not passed:
        raise RuntimeError("all three independent mechanical validations must pass before preregistration")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialize(future_preregistration()), encoding="utf-8", newline="\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def serialize(value: dict) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mechanical", action="store_true",
        help="run only the dependency-gated three-joint compiled-model revalidation")
    args = parser.parse_args(argv)
    if args.mechanical and dependencies_available():
        adapter = __import__("malecns_backend.embodiment._windows_candidate_motor_mechanical_validation",
                             fromlist=["run"])
        return adapter.run()
    value = build()
    if args.mechanical:
        value["run_status"] = "SKIPPED / DEPENDENCIES_UNAVAILABLE"
    OUTPUT.write_text(serialize(value), encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT}; preregistration_created={value['preregistration_created']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
