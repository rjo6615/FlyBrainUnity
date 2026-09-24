"""Read-only M11C characterization of the frozen canonical M11B report.

This module has no simulation imports and does not read the M11B trajectory
archive.  The archive is nevertheless authenticated because it is one of the
frozen sources.  Publication is available only through ``--execute-canonical``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
SOURCE_DIR = HERE / "interface_output" / "m11_motor_channel_dissection"
OUTPUT_DIR = HERE / "interface_output" / "m11c_motor_channel_analysis"
PREREGISTRATION = "m11a_preregistration.json"
ANALYSIS_NAME = "m11c_analysis.json"
MANIFEST_NAME = "m11c_manifest.json"
SCHEMA = "M11C-PREREGISTERED-MOTOR-CHANNEL-ANALYSIS.1"
SOURCE_SCHEMA = "M11B-CANONICAL-MOTOR-CHANNEL-DISSECTION.1"
EXPECTED_IDENTITIES = {
    "m11_raw.npz": {"byte_size": 81305728, "sha256": "0f5c8ca4777c79640a8cf032e21366cd6819335a7b22ff9457ed07aec1e183c1"},
    "m11_report.json": {"byte_size": 17257, "sha256": "2678b2fcb74144632134c397d96132f8232992606d34a40e2d056e061a49606f"},
    "m11_manifest.json": {"byte_size": 4828, "sha256": "7a2f6c23a5b7e3f42929c94c88847a24d50bb7b87139e04cba35112fe5ea0180"},
}
EXPECTED_PREREGISTRATION = {
    "byte_size": 10003,
    "sha256": "aa8f0b57c1126d6f4bb5b477849e81be2dbd9c86ba6d180698810c7aedfe6fd5",
}
CHANNELS = (
    ("joint_LFTibia", 5, 1), ("joint_LMTibia", 12, 1), ("joint_LHTibia", 19, 1),
    ("joint_RFTibia", 26, 1), ("joint_RMTibia", 33, 1), ("joint_RHTibia", 40, 1),
    ("joint_LFFemur", 3, -1), ("joint_LMFemur", 10, -1), ("joint_LHFemur", 17, -1),
    ("joint_RMFemur", 31, -1), ("joint_RHFemur", 38, -1),
)
METRICS = ("thorax_com_deviation_mm", "root_orientation_shortest_arc_deg")
THRESHOLDS = {"thorax_com_deviation_mm": 0.005,
              "root_orientation_shortest_arc_deg": 0.25}
LATER_WINDOW = {"start_ms_inclusive": 557.0, "stop_ms_inclusive": 1500.0}
ESTIMAND = "E_channel_metric = D_leave_one_out_channel_metric - D_full_11_enabled_metric"
NON_ADDITIVITY = "The leave-one-out estimands do not form an additive decomposition of the full neural-motor effect."
NEURAL_TRANSITIONS = PHYSICS_TRANSITIONS = 0


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(f"M11C fail-closed: {message}")


def identity(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return {"path": path.name, "byte_size": path.stat().st_size,
            "sha256": digest.hexdigest()}


def validate_provenance(
    source_dir: Path = SOURCE_DIR,
    expected: Mapping[str, Mapping[str, Any]] = EXPECTED_IDENTITIES,
    preregistration_expected: Mapping[str, Any] = EXPECTED_PREREGISTRATION,
) -> dict[str, Any]:
    """Authenticate every frozen input and its mandatory protocol metadata."""
    names = (*expected, PREREGISTRATION)
    paths = {name: source_dir / name for name in names}
    _require(all(path.is_file() for path in paths.values()), "frozen source artifact missing")
    identities = {name: identity(path) for name, path in paths.items()}
    wanted = {**expected, PREREGISTRATION: preregistration_expected}
    for name, specification in wanted.items():
        _require(all(identities[name][key] == specification[key]
                     for key in ("byte_size", "sha256")),
                 f"frozen source identity mismatch: {name}")

    report = json.loads(paths["m11_report.json"].read_text(encoding="utf-8"))
    manifest = json.loads(paths["m11_manifest.json"].read_text(encoding="utf-8"))
    prereg = json.loads(paths[PREREGISTRATION].read_text(encoding="utf-8"))
    expected_conditions = ["full_11_enabled", "all_11_disabled"] + [
        f"leave_one_out__{name}" for name, _, _ in CHANNELS]
    _require(report.get("schema") == SOURCE_SCHEMA, "M11B report schema")
    _require(report.get("status") == "COMPLETE", "M11B report status is not COMPLETE")
    _require(report.get("condition_order") == expected_conditions,
             "M11B exact 13-condition structure")
    _require(manifest.get("condition_count") == 13, "M11B manifest condition count")
    aggregate = report.get("transition_counts", {}).get("aggregate", {})
    _require(aggregate == {"neural_transitions": 39000, "physics_transitions": 195000},
             "M11B aggregate transition counts")
    _require(report.get("perturbation", {}).get("magnitude") == 1.024,
             "M11B perturbation magnitude")
    _require(report.get("windows", {}).get("later_post_force") == LATER_WINDOW,
             "M11B inherited later window")
    _require(report.get("thresholds") == THRESHOLDS, "M11B inherited thresholds")
    inventory = [(row.get("name"), row.get("action_index"), row.get("coordinate_sign"))
                 for row in report.get("motor_inventory", [])]
    _require(tuple(inventory) == CHANNELS, "M11B ordered motor inventory")
    analysis = prereg.get("analysis", {})
    _require(analysis.get("primary_window") == "later_post_force"
             and analysis.get("thresholds") == THRESHOLDS
             and analysis.get("estimand") == ESTIMAND,
             "M11A inherited analysis design")
    return {"identities": identities, "report": report, "manifest": manifest,
            "preregistration": prereg}


def classify(effect: float, threshold: float) -> str:
    if effect <= -threshold:
        return "ABLATION_REDUCES_AMPLIFICATION"
    if effect >= threshold:
        return "ABLATION_INCREASES_AMPLIFICATION"
    return "UNRESOLVED_AT_INHERITED_THRESHOLD"


def cross_metric(com: str, orientation: str) -> str:
    unresolved = "UNRESOLVED_AT_INHERITED_THRESHOLD"
    if com == orientation == unresolved:
        return "BOTH_UNRESOLVED"
    if orientation == unresolved:
        return "COM_RESOLVED_ONLY"
    if com == unresolved:
        return "ORIENTATION_RESOLVED_ONLY"
    return "BOTH_RESOLVED_SAME_DIRECTION" if com == orientation else "BOTH_RESOLVED_OPPOSITE_DIRECTION"


def _summary(rows: list[dict[str, Any]], metric: str) -> dict[str, Any]:
    values = [(row["channel_name"], row[metric]["absolute_effect"]) for row in rows]
    ordered = sorted(values, key=lambda item: (-item[1], item[0]))
    groups: list[dict[str, Any]] = []
    for channel, value in ordered:
        if not groups or groups[-1]["absolute_effect"] != value:
            groups.append({"absolute_effect": value, "channels": []})
        groups[-1]["channels"].append(channel)
    classes = [row[metric]["inherited_classification"] for row in rows]
    unresolved = "UNRESOLVED_AT_INHERITED_THRESHOLD"
    return {
        "resolved_channel_count": sum(label != unresolved for label in classes),
        "unresolved_channel_count": classes.count(unresolved),
        "ablation_reduces_amplification_count": classes.count("ABLATION_REDUCES_AMPLIFICATION"),
        "ablation_increases_amplification_count": classes.count("ABLATION_INCREASES_AMPLIFICATION"),
        "exactly_zero_signed_effect_count": sum(row[metric]["signed_leave_one_out_effect"] == 0 for row in rows),
        "largest_absolute_effect": groups[0], "smallest_absolute_effect": groups[-1],
        "absolute_effect_order_largest_to_smallest_with_ties": groups,
        "ordering_is_descriptive_only": True,
    }


def build_analysis(validated: Mapping[str, Any]) -> dict[str, Any]:
    """Construct the deterministic analysis solely from authenticated report values."""
    report = validated["report"]
    deviations, source_estimands = report["per_condition_deviations"], report["later_post_force_estimands"]
    rows = []
    for channel, action_index, coordinate_sign in CHANNELS:
        row: dict[str, Any] = {"channel_name": channel, "action_index": action_index,
                               "coordinate_sign": coordinate_sign}
        for metric in METRICS:
            full = deviations["full_11_enabled"][metric]["later_post_force"]
            ablated = deviations[f"leave_one_out__{channel}"][metric]["later_post_force"]
            effect = ablated - full
            label = classify(effect, THRESHOLDS[metric])
            source = source_estimands[channel][metric]
            _require(source.get("effect") == effect and source.get("classification") == label,
                     f"M11B estimand/classification mismatch: {channel} {metric}")
            row[metric] = {"full_11_enabled_later_deviation": full,
                           "leave_one_out_later_deviation": ablated,
                           "signed_leave_one_out_effect": effect,
                           "absolute_effect": abs(effect),
                           "inherited_threshold": THRESHOLDS[metric],
                           "inherited_classification": label,
                           "resolved": label != "UNRESOLVED_AT_INHERITED_THRESHOLD"}
        row["cross_metric_classification"] = cross_metric(
            row[METRICS[0]]["inherited_classification"], row[METRICS[1]]["inherited_classification"])
        rows.append(row)
    summaries = {metric: _summary(rows, metric) for metric in METRICS}
    com_set = {r["channel_name"] for r in rows if r[METRICS[0]]["resolved"]}
    orientation_set = {r["channel_name"] for r in rows if r[METRICS[1]]["resolved"]}
    either = com_set | orientation_set
    resolved_labels = {r[m]["inherited_classification"] for r in rows for m in METRICS if r[m]["resolved"]}
    heterogeneous = any(len({r[m]["signed_leave_one_out_effect"] for r in rows}) > 1 or
                        len({r[m]["inherited_classification"] for r in rows}) > 1 for m in METRICS)
    distribution = ("the resolved leave-one-out effects are distributed across multiple admitted channels under this modeled condition"
                    if len(either) > 1 else
                    "the preregistered leave-one-out evidence does not resolve effects in more than one admitted channel")
    source_ids = {name: validated["identities"][name] for name in EXPECTED_IDENTITIES}
    prereg_id = validated["identities"][PREREGISTRATION]
    return {
        "schema": SCHEMA, "status": "COMPLETE", "analysis_only": True,
        "scientific_question": "How is the previously observed M10 later post-perturbation causal neural-motor contribution distributed across the 11 admitted motor channels at the preregistered 1.024 perturbation magnitude?",
        "source_artifacts": source_ids, "m11a_preregistration": prereg_id,
        "perturbation_magnitude": 1.024, "analysis_window": LATER_WINDOW,
        "inherited_thresholds": THRESHOLDS,
        "estimand": {"definition": ESTIMAND, "positive": "removing the channel increased physical deviation", "negative": "removing the channel decreased physical deviation", "zero": "removing the channel did not change measured deviation"},
        "per_channel_table": rows, "per_metric_deterministic_summaries": summaries,
        "cross_metric_characterization": [{"channel_name": r["channel_name"], "classification": r["cross_metric_classification"]} for r in rows],
        "interface_level_characterization": {
            "heterogeneous": heterogeneous,
            "heterogeneous_definition": "individual admitted-channel ablations produced differing measured effects and/or inherited classifications under the frozen M11B conditions",
            "resolved_for_either_metric_count": len(either), "resolved_for_com_count": len(com_set),
            "resolved_for_orientation_count": len(orientation_set),
            "unresolved_for_both_count": sum(r["cross_metric_classification"] == "BOTH_UNRESOLVED" for r in rows),
            "more_than_one_distinct_channel_has_resolved_effect": len(either) > 1,
            "resolved_effects_include_opposing_directions": len(resolved_labels) > 1,
            "com_and_orientation_identify_same_channel_pattern": com_set == orientation_set,
            "resolved_effect_description": distribution,
            "concentration_limitation": "Leave-one-out evidence cannot uniquely establish whether the overall M10 effect is concentrated or distributed because channel effects may be non-additive or interacting.",
        },
        "non_additivity_limitation": NON_ADDITIVITY,
        "interpretation_boundaries": {
            "boundary_557_ms": "inherited engineering analysis boundary; not biological latency",
            "contact": "observational only; not neural sensory input", "sensory_interface": "modeled",
            "motor_decoder": "engineered", "scope": "only admitted motor channels are dissected",
            "biological_inference": "This does not identify biological function of a neuron, population, muscle, joint, or limb and licenses no inference about balance, stabilization, righting, reflexes, recovery, natural locomotion, natural gait, or natural motor function.",
        },
        "prohibited_analyses_confirmation": {"performed": [], "new_thresholds": False,
            "composite_score": False, "additive_decomposition": False},
        "transition_counts": {"neural_transitions": 0, "physics_transitions": 0},
    }


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def publish(output_dir: Path, analysis: Mapping[str, Any], validated: Mapping[str, Any]) -> None:
    """Publish both outputs transactionally without permitting overwrite."""
    _require(not output_dir.exists(), "M11C output namespace already exists")
    analysis_bytes = _json_bytes(analysis)
    source_path = Path(__file__)
    manifest = {
        "schema": SCHEMA, "status": "COMPLETE", "analysis_only": True, "deterministic": True,
        "m11a_preregistration": validated["identities"][PREREGISTRATION],
        "m11b_source_artifacts": {n: validated["identities"][n] for n in EXPECTED_IDENTITIES},
        "outputs": {ANALYSIS_NAME: {"byte_size": len(analysis_bytes),
                     "sha256": hashlib.sha256(analysis_bytes).hexdigest()}},
        "implementation_source": identity(source_path), "python_version": platform.python_version(),
        "numpy_version": "not used", "neural_transitions": 0, "physics_transitions": 0,
        "scientific_interpretation_boundary_summary": "Modeled MaleCNS -> decoder -> admitted motor -> MuJoCo interface only; no biological motor-function inference.",
    }
    staging = output_dir.with_name(f".{output_dir.name}.tmp-{os.getpid()}")
    _require(not staging.exists(), "staging namespace already exists")
    staging.mkdir(parents=True)
    try:
        (staging / ANALYSIS_NAME).write_bytes(analysis_bytes)
        (staging / MANIFEST_NAME).write_bytes(_json_bytes(manifest))
        output_dir.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staging, output_dir)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def execute_canonical(source_dir: Path = SOURCE_DIR, output_dir: Path = OUTPUT_DIR) -> dict[str, Any]:
    validated = validate_provenance(source_dir)
    analysis = build_analysis(validated)
    # Reauthenticate immediately before publication and reject changed bytes.
    _require(validate_provenance(source_dir)["identities"] == validated["identities"],
             "frozen sources changed during analysis")
    publish(output_dir, analysis, validated)
    return analysis


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-canonical", action="store_true", required=True,
                        help="explicitly authenticate, analyze, and publish canonical M11C")
    parser.parse_args(argv)
    print(json.dumps(execute_canonical(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
