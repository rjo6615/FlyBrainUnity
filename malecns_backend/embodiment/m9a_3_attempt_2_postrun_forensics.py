"""Read-only M9A-3 Attempt-2 postrun forensic analysis.

This namespace only parses already-recorded arrays.  It has no simulation or
neural-runtime imports and its sole write is an exclusively-created report in
a directory separate from the frozen Attempt-2 evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
EVIDENCE_DIR = HERE / "interface_output" / "m9a_3_matched_control_calibration_attempt_2"
OUTPUT_DIR = HERE / "interface_output" / "m9a_3_attempt_2_postrun_forensics"
REPORT_PATH = OUTPUT_DIR / "m9a_3_attempt_2_postrun_forensics.json"
MAGNITUDES = (0.256, 0.512, 1.024, 2.048)
CONDITIONS = ("P", "C")
FILES = tuple((m, condition, EVIDENCE_DIR / f"candidate_{m:.6f}_{condition}_raw.npz")
              for m in MAGNITUDES for condition in CONDITIONS)
REQUIRED = ("time_ms", "root_position", "orientation_wxyz", "body_up_z",
            "linear_velocity", "angular_velocity", "ground_contact",
            "distal_tarsus_positions", "applied_force", "fixed_actuator_commands", "finite")
PHYSICAL_FIELDS = ("root_position", "orientation_wxyz", "body_up_z", "linear_velocity",
                   "angular_velocity", "ground_contact", "distal_tarsus_positions")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inventory(files: Sequence[tuple[float, str, Path]] = FILES) -> list[dict[str, Any]]:
    """Fail closed on an incomplete evidence set, then inventory exact bytes."""
    missing = [path.name for _, _, path in files if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing canonical Attempt-2 raw evidence: " + ", ".join(missing))
    return [{"filename": path.name, "byte_size": path.stat().st_size,
             "sha256": _sha256(path)} for _, _, path in files]


def _load(np: Any, path: Path) -> dict[str, Any]:
    with np.load(path, allow_pickle=False) as archive:
        missing = sorted(set(REQUIRED) - set(archive.files))
        if missing:
            raise ValueError(f"{path.name}: missing arrays {missing}")
        return {name: np.array(archive[name], copy=True) for name in archive.files}


def _norm(np: Any, values: Any) -> Any:
    return np.linalg.norm(values.reshape((len(values), -1)), axis=1)


def _maximum(np: Any, values: Any, times: Any) -> dict[str, Any]:
    index = int(np.argmax(values))
    return {"value": float(values[index]), "state_index": index, "timestamp_ms": float(times[index])}


def _condition_audit(np: Any, values: Mapping[str, Any], magnitude: float, condition: str) -> dict[str, Any]:
    times = values["time_ms"]
    expected_times = np.arange(15001, dtype=float) * 0.1
    expected_force = np.zeros((15001, 3), dtype=float)
    if condition == "P":
        expected_force[5000:5200, 1] = magnitude
    commands = values["fixed_actuator_commands"]
    finite = all(np.isfinite(values[key]).all() for key in REQUIRED if key != "ground_contact")
    speed = _norm(np, values["linear_velocity"])
    peak = _maximum(np, speed, times)
    peak["linear_velocity_vector"] = values["linear_velocity"][peak["state_index"]].tolist()
    peak["before_500ms_perturbation"] = bool(peak["timestamp_ms"] < 500.0)
    return {
        "state_count": int(len(times)),
        "timestamp_cadence_matches_index_times_0_1ms": bool(
            len(times) == 15001 and np.all(np.isclose(times, expected_times, rtol=0.0, atol=1e-7))),
        "force_nonzero_indices": np.flatnonzero(np.any(values["applied_force"] != 0, axis=1)).tolist(),
        "force_schedule_exact": bool(values["applied_force"].shape == expected_force.shape
                                     and np.array_equal(values["applied_force"], expected_force)),
        "candidate_force_vector": [0.0, magnitude, 0.0] if condition == "P" else [0.0, 0.0, 0.0],
        "actuator_commands_fixed": bool(len(commands) == 15001 and np.all(commands == commands[0])),
        "finite_telemetry": bool(finite),
        "maximum_absolute_root_linear_speed": peak,
    }


def _pair_forensics(np: Any, p: Mapping[str, Any], c: Mapping[str, Any], magnitude: float,
                    reducer: Any) -> dict[str, Any]:
    """Calculate forensic additions while delegating reducer semantics verbatim."""
    reduced = reducer(np, p, c, magnitude)
    times = p["time_ms"]
    position = _norm(np, p["root_position"] - c["root_position"])
    velocity = _norm(np, p["linear_velocity"] - c["linear_velocity"])
    dots = np.abs(np.sum(p["orientation_wxyz"] * c["orientation_wxyz"], axis=1))
    orientation = np.degrees(2 * np.arccos(np.clip(dots, 0, 1)))
    feet = np.linalg.norm(p["distal_tarsus_positions"] - c["distal_tarsus_positions"], axis=2)
    distal = feet.max(axis=1)
    contact = np.logical_xor(p["ground_contact"], c["ground_contact"])
    differing = np.zeros(len(times), dtype=bool)
    for key in PHYSICAL_FIELDS:
        delta = p[key] != c[key]
        differing |= delta if delta.ndim == 1 else np.any(delta.reshape((len(times), -1)), axis=1)
    divergence_indices = np.flatnonzero(differing)
    early = times <= 750.0
    initial = p["root_position"][0]
    p_displacement = _norm(np, p["root_position"] - initial)
    c_displacement = _norm(np, c["root_position"] - initial)
    p_tilt = np.degrees(np.arccos(np.clip(p["body_up_z"], -1, 1)))
    c_tilt = np.degrees(np.arccos(np.clip(c["body_up_z"], -1, 1)))
    p_speed, c_speed = _norm(np, p["linear_velocity"]), _norm(np, c["linear_velocity"])
    no_fall = not bool(np.any(((p["root_position"][:, 2] <= initial[2] * .5)
                              | (c["root_position"][:, 2] <= initial[2] * .5)) & early))
    no_rollover = not bool(np.any(((p["body_up_z"] <= 0) | (c["body_up_z"] <= 0)) & early))
    predicates = {
        "measurable_continuous_divergence": reduced["max_continuous_divergence"] >= 1e-9,
        "contact_pattern_meaningfulness": bool(reduced["contact_pattern_diverged"]),
        "root_position_meaningfulness_gte_0_005_mm": reduced["max_root_position_divergence_mm"] >= .005,
        "orientation_meaningfulness_gte_0_25_deg": reduced["max_orientation_divergence_deg"] >= .25,
        "distal_tarsus_meaningfulness_gte_0_01_mm": reduced["max_distal_tarsus_divergence_mm"] >= .01,
    }
    predicates["meaningful"] = any(predicates[key] for key in (
        "contact_pattern_meaningfulness", "root_position_meaningfulness_gte_0_005_mm",
        "orientation_meaningfulness_gte_0_25_deg", "distal_tarsus_meaningfulness_gte_0_01_mm"))
    predicates.update({
        "no_fall_through_750ms": no_fall, "no_rollover_through_750ms": no_rollover,
        "p_minus_c_root_position_safety": reduced["max_root_position_divergence_mm"] <= .5,
        "p_minus_c_orientation_safety": reduced["max_orientation_divergence_deg"] <= 30,
        "p_minus_c_linear_velocity_safety": reduced["max_root_linear_velocity_divergence"] <= 5,
        "per_condition_displacement_safety": bool(max(p_displacement.max(), c_displacement.max()) <= 1.5),
        "per_condition_tilt_safety": bool(max(p_tilt.max(), c_tilt.max()) <= 60),
        "per_condition_absolute_linear_speed_safety_lte_10_0": bool(max(p_speed.max(), c_speed.max()) <= 10),
        "catastrophic_through_750ms": bool(reduced["catastrophic_through_750ms"]),
    })
    predicates["qualifies"] = bool(predicates["measurable_continuous_divergence"]
        and predicates["meaningful"] and reduced["finite_both"]
        and not predicates["catastrophic_through_750ms"]
        and all(predicates[key] for key in (
            "p_minus_c_root_position_safety", "p_minus_c_orientation_safety",
            "p_minus_c_linear_velocity_safety", "per_condition_displacement_safety",
            "per_condition_tilt_safety", "per_condition_absolute_linear_speed_safety_lte_10_0"))
        and reduced["post_force_observation_ms"] >= 980)
    contact_rows = np.any(contact, axis=1)
    return {"magnitude_native": magnitude, "reducer_fields": reduced, "predicates": predicates,
        "perturbation_response": {
            "maximum_root_position_divergence": _maximum(np, position, times),
            "maximum_shortest_arc_orientation_divergence": _maximum(np, orientation, times),
            "maximum_distal_tarsus_divergence": _maximum(np, distal, times),
            "maximum_root_linear_velocity_divergence": _maximum(np, velocity, times),
            "contact_xor": {"any": bool(contact.any()), "value_count": int(contact.sum()),
                "state_indices": np.flatnonzero(contact_rows).tolist()},
            "first_physical_divergence_index": None if not divergence_indices.size else int(divergence_indices[0]),
            "first_physical_divergence_ms": None if not divergence_indices.size else float(times[divergence_indices[0]]),
        }}


def _nondecreasing(values: Sequence[float]) -> bool:
    return all(right >= left for left, right in zip(values, values[1:]))


def analyze(files: Sequence[tuple[float, str, Path]] = FILES) -> dict[str, Any]:
    """Analyze raw evidence without constructing or advancing a runtime."""
    before = inventory(files)
    import numpy as np
    from . import _windows_m9a_3_matched_control_adapter as production
    from . import m9a_3_matched_control_calibration as protocol

    loaded = {(m, condition): _load(np, path) for m, condition, path in files}
    pairs, condition_audits = [], {}
    for magnitude in MAGNITUDES:
        p, c = loaded[magnitude, "P"], loaded[magnitude, "C"]
        condition_audits[f"{magnitude:.6f}"] = {
            condition: _condition_audit(np, loaded[magnitude, condition], magnitude, condition)
            for condition in CONDITIONS}
        pc_commands = np.array_equal(p["fixed_actuator_commands"], c["fixed_actuator_commands"])
        pre = np.arange(15001) < 5000
        pre_equal = all(np.array_equal(p[key][pre], c[key][pre]) for key in PHYSICAL_FIELDS)
        pair = _pair_forensics(np, p, c, magnitude, production._reduce_pair)
        pair["protocol_audit"] = {"state_count_exact_both": len(p["time_ms"]) == len(c["time_ms"]) == 15001,
            "p_c_timestamps_exactly_equal": bool(np.array_equal(p["time_ms"], c["time_ms"])),
            "pre_force_physical_equivalence_exact": bool(pre_equal),
            "fixed_actuator_command_equivalence_exact": bool(pc_commands)}
        for condition in CONDITIONS:
            peak = condition_audits[f"{magnitude:.6f}"][condition]["maximum_absolute_root_linear_speed"]
            other = c if condition == "P" else p
            index = peak["state_index"]
            peak["p_c_linear_velocity_exactly_equal_at_state"] = bool(np.array_equal(
                loaded[magnitude, condition]["linear_velocity"][index], other["linear_velocity"][index]))
            peak["p_c_physical_state_exactly_equal_at_state"] = all(np.array_equal(
                loaded[magnitude, condition][key][index], other[key][index]) for key in PHYSICAL_FIELDS)
        pairs.append(pair)

    metric_keys = ("maximum_root_position_divergence", "maximum_shortest_arc_orientation_divergence",
                   "maximum_distal_tarsus_divergence", "maximum_root_linear_velocity_divergence")
    monotonic = {key: _nondecreasing([row["perturbation_response"][key]["value"] for row in pairs])
                 for key in metric_keys}
    monotonic["contact_xor_value_count"] = _nondecreasing([
        row["perturbation_response"]["contact_xor"]["value_count"] for row in pairs])
    peaks = [condition_audits[f"{m:.6f}"][condition]["maximum_absolute_root_linear_speed"]
             for m in MAGNITUDES for condition in CONDITIONS]
    shared = all(peak["before_500ms_perturbation"]
                 and peak["state_index"] == peaks[0]["state_index"]
                 and peak["timestamp_ms"] == peaks[0]["timestamp_ms"]
                 and peak["value"] == peaks[0]["value"]
                 and peak["linear_velocity_vector"] == peaks[0]["linear_velocity_vector"] for peak in peaks)
    hypothesis = bool(shared and peaks[0]["value"] > 10.0
                      and all(peak["p_c_physical_state_exactly_equal_at_state"] for peak in peaks))
    try:
        protocol.choose_candidate([row["reducer_fields"] for row in pairs])
    except RuntimeError as error:
        if str(error) != "no preregistered candidate qualifies":
            raise
        selection = "NO_PREREGISTERED_CANDIDATE_QUALIFIES"
    else:
        raise RuntimeError("forensic evidence unexpectedly produces a selected candidate")
    after = inventory(files)
    if before != after:
        raise RuntimeError("Attempt-2 evidence changed during read-only analysis")
    largest = pairs[-1]["predicates"]
    return {"schema": "M9A-3-ATTEMPT-2-POSTRUN-FORENSICS.1", "status": "COMPLETE",
        "read_only": True, "physics_transitions": 0, "neural_transitions": 0,
        "male_cns_constructed": False, "evidence_before_and_after_identical": True,
        "evidence_inventory": before, "condition_protocol_audits": condition_audits,
        "candidate_analysis": pairs, "perturbation_response_monotonic_non_decreasing": monotonic,
        "absolute_speed_forensics": {"same_preforce_maximum_shared_across_all_four_matched_pairs": shared,
            "hypothesis": "SHARED_PREPERTURBATION_BASELINE_TRANSIENT_EXCEEDS_ABSOLUTE_SPEED_LIMIT",
            "hypothesis_supported": hypothesis},
        "magnitude_2_048_meaningfulness": {"satisfies_one_or_more": bool(largest["meaningful"]),
            "predicate_results": {key: value for key, value in largest.items() if "meaningfulness" in key},
            "not_a_selection": True},
        "production_selection_result": selection,
        "claim_boundary": "Postrun physical telemetry forensics only; no retrospective candidate selection."}


def write_report(report: Mapping[str, Any], path: Path = REPORT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args(argv)
    report = analyze()
    if args.write_report:
        write_report(report)
    else:
        print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
