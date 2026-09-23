"""Preregistered, read-only analysis of the completed canonical M10B archive.

This module deliberately imports no simulation code.  Importing it performs no
I/O; the only executable operation is the explicit ``--analyze`` CLI.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
from typing import Any, Mapping

import numpy as np

SCHEMA = "M10C-PREREGISTERED-M10B-PERTURBATION-SCALING-ANALYSIS.1"
HERE = Path(__file__).resolve().parent
SOURCE_DIR = HERE / "interface_output/m10b_perturbation_scaling"
OUTPUT_DIR = HERE / "interface_output/m10c_m10b_analysis"
SCIENTIFIC_QUESTION = ("whether the preregistered physical perturbation-response effect attributable "
                       "to neural-motor enablement changes systematically across four frozen magnitudes")
CONDITIONS = (
    (0.0, "A_C", True), (0.0, "B_C", False),
    (0.256, "A_F0256", True), (0.256, "B_F0256", False),
    (1.024, "A_F1024", True), (1.024, "B_F1024", False),
    (2.896309375740099, "A_F2896", True), (2.896309375740099, "B_F2896", False),
    (4.096, "A_F4096", True), (4.096, "B_F4096", False),
)
FORCE_PAIRS = (
    (0.256, "A_F0256", "B_F0256"), (1.024, "A_F1024", "B_F1024"),
    (2.896309375740099, "A_F2896", "B_F2896"), (4.096, "A_F4096", "B_F4096"),
)
WINDOWS = {
    "pre_perturbation": {"start_ms_inclusive": 0.0, "stop_ms_exclusive": 500.0},
    "direct_force": {"start_ms_inclusive": 500.0, "stop_ms_exclusive": 520.0},
    "early_post_force": {"start_ms_inclusive": 520.0, "stop_ms_exclusive": 557.0},
    "later_post_force": {"start_ms_inclusive": 557.0, "stop_ms_inclusive": 1500.0},
}
THRESHOLDS = {"thorax_com_deviation_mm": 0.005,
              "root_orientation_shortest_arc_deg": 0.25}
EXPECTED_IDENTITIES = {
    "m10b_raw.npz": {"sha256": "85e98715ac3d8b219c86ef338187828e787ee8f300bacad9d318809e23208cde", "byte_size": 57652701},
    "m10b_report.json": {"sha256": "fdc3cc8aef9f02a85dc10f671a4ff86d9592354c8ea60d9a5f179b2c0c81acfc", "byte_size": 5785},
    "m10b_manifest.json": {"sha256": "62b1f4a3e5f5773de594a3d965b0227e0dec9cc52fb09658c0a3d92ecc7f0ad7", "byte_size": 26684},
    "m10b_preregistration.json": {"sha256": "a267647093d616f394374761da58ae495f12a6df6fe12e004abbcb1cb1b2d5a9", "byte_size": 10924},
}
PRIMARY_SHAPES = {"physics_time_ms": (15001,), "root_thorax_position": (15001, 3),
                  "root_orientation_wxyz": (15001, 4)}
PHYSICS_TRANSITIONS = NEURAL_TRANSITIONS = 0


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise RuntimeError(f"M10C fail-closed: {message}")


def identity(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return {"path": path.name, "byte_size": path.stat().st_size, "sha256": digest.hexdigest()}


def validate_provenance(source_dir: Path = SOURCE_DIR,
                        expected: Mapping[str, Mapping[str, Any]] = EXPECTED_IDENTITIES) -> dict[str, Any]:
    """Verify immutable bytes and completed protocol metadata before NPZ loading."""
    paths = {name: source_dir / name for name in expected}
    _require(all(path.is_file() for path in paths.values()), "canonical artifact missing")
    identities = {name: identity(path) for name, path in paths.items()}
    for name, wanted in expected.items():
        _require(all(identities[name][key] == wanted[key] for key in ("sha256", "byte_size")),
                 f"canonical artifact identity mismatch: {name}")
    report = json.loads(paths["m10b_report.json"].read_text(encoding="utf-8"))
    manifest = json.loads(paths["m10b_manifest.json"].read_text(encoding="utf-8"))
    prereg = json.loads(paths["m10b_preregistration.json"].read_text(encoding="utf-8"))
    expected_conditions = [{"force_magnitude": f, "fresh_identical_deterministic_initialization": True,
                            "motor_enabled": enabled, "name": name}
                           for f, name, enabled in CONDITIONS]
    _require(report.get("status") == "COMPLETE_UNANALYZED", "report is not COMPLETE_UNANALYZED")
    _require(report.get("canonical_experiment_executed") is True, "experiment execution flag")
    _require(report.get("disabled_motor_integrity", {}).get("passed") is True,
             "disabled-motor integrity failure")
    _require(report.get("force_integrity", {}).get("passed") is True, "force integrity failure")
    _require(manifest.get("disabled_motor_integrity", {}).get("passed") is True,
             "manifest disabled-motor integrity failure")
    _require(manifest.get("force_integrity", {}).get("passed") is True,
             "manifest force integrity failure")
    _require(manifest.get("conditions") == expected_conditions and prereg.get("conditions") == expected_conditions,
             "condition identities, forces, or motor states differ")
    _require(report.get("condition_order") == [x[1] for x in CONDITIONS], "condition order differs")
    _require(prereg.get("scientific_question") == SCIENTIFIC_QUESTION, "scientific question differs")
    _require(prereg.get("analysis_windows") == WINDOWS, "analysis windows differ")
    _require(prereg.get("directional_resolution", {}).get("thresholds") == THRESHOLDS,
             "directional thresholds differ")
    return {"identities": identities, "report": report, "manifest": manifest,
            "preregistration": prereg}


def euclidean_deviation(left: np.ndarray, right: np.ndarray, *, scale: float = 1.0) -> np.ndarray:
    left, right = np.asarray(left, float), np.asarray(right, float)
    _require(left.shape == right.shape and left.ndim == 2 and left.shape[1] == 3,
             "position shape/alignment")
    return np.linalg.norm(left - right, axis=1) * scale


def quaternion_shortest_arc_deg(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    """Sign-invariant, robustly normalized quaternion shortest arc in degrees."""
    left, right = np.asarray(left, float), np.asarray(right, float)
    _require(left.shape == right.shape and left.ndim == 2 and left.shape[1] == 4,
             "quaternion shape/alignment")
    ln, rn = np.linalg.norm(left, axis=1), np.linalg.norm(right, axis=1)
    _require(bool(np.all(np.isfinite(left)) and np.all(np.isfinite(right))), "nonfinite quaternion")
    _require(bool(np.all(ln > 0) and np.all(rn > 0)), "zero quaternion norm")
    dot = np.sum((left / ln[:, None]) * (right / rn[:, None]), axis=1)
    return np.degrees(2.0 * np.arccos(np.clip(np.abs(dot), 0.0, 1.0)))


def window_mask(times: np.ndarray, window: Mapping[str, float]) -> np.ndarray:
    times = np.asarray(times)
    mask = times >= window["start_ms_inclusive"]
    if "stop_ms_exclusive" in window:
        mask &= times < window["stop_ms_exclusive"]
    else:
        mask &= times <= window["stop_ms_inclusive"]
    return mask


def classify_window(effect: float, threshold: float) -> str:
    if effect <= -threshold:
        return "ATTENUATING"
    if effect >= threshold:
        return "AMPLIFYING"
    return "UNRESOLVED"


def classify_overall(early: str, later: str) -> str:
    resolved = [x for x in (early, later) if x != "UNRESOLVED"]
    if not resolved:
        return "NO_RESOLVED_DIRECTIONAL_EFFECT"
    if len(set(resolved)) > 1:
        return "DIRECTIONALLY_MIXED"
    return resolved[0]


def reduce_window(enabled: np.ndarray, disabled: np.ndarray, times: np.ndarray,
                  window: Mapping[str, float], threshold: float) -> dict[str, Any]:
    mask = window_mask(times, window)
    _require(bool(np.any(mask)), "empty analysis window")
    indices = np.flatnonzero(mask)
    ei, di = indices[np.argmax(enabled[mask])], indices[np.argmax(disabled[mask])]
    ev, dv = float(enabled[ei]), float(disabled[di])
    effect = ev - dv
    return {"enabled_maximum_deviation": ev, "disabled_maximum_deviation": dv,
            "directional_effect": effect, "absolute_directional_effect": abs(effect),
            "directional_classification": classify_window(effect, threshold),
            "enabled_maximum_time_ms": float(times[ei]), "disabled_maximum_time_ms": float(times[di])}


def scaling_summary(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    signed = [float(row["directional_effect"]) for row in rows]
    absolute = [abs(x) for x in signed]
    labels = [str(row["directional_classification"]) for row in rows]
    resolved = [x for x in labels if x != "UNRESOLVED"]
    return {"force_order": [x[0] for x in FORCE_PAIRS], "signed_directional_effects": signed,
            "absolute_directional_effects": absolute,
            "adjacent_signed_changes": [b - a for a, b in zip(signed, signed[1:])],
            "adjacent_absolute_effect_changes": [b - a for a, b in zip(absolute, absolute[1:])],
            "resolved_sign_consistency": len(set(resolved)) <= 1,
            "adjacent_resolved_sign_changes": [labels[i] != labels[i + 1]
                if labels[i] != "UNRESOLVED" and labels[i + 1] != "UNRESOLVED" else False
                for i in range(3)],
            "absolute_effect_monotonic_nondecreasing": all(a <= b for a, b in zip(absolute, absolute[1:]))}


def _validate_arrays(arrays: Mapping[str, np.ndarray]) -> np.ndarray:
    expected = {f"{name}__{field}" for _, name, _ in CONDITIONS for field in PRIMARY_SHAPES}
    _require(expected <= set(arrays), "primary array inventory incomplete")
    for _, condition, _ in CONDITIONS:
        for field, shape in PRIMARY_SHAPES.items():
            value = np.asarray(arrays[f"{condition}__{field}"])
            _require(value.shape == shape, f"unexpected shape: {condition} {field}")
        for field in ("root_thorax_position", "root_orientation_wxyz"):
            _require(bool(np.all(np.isfinite(arrays[f"{condition}__{field}"]))),
                     f"nonfinite primary trajectory: {condition} {field}")
        norms = np.linalg.norm(arrays[f"{condition}__root_orientation_wxyz"], axis=1)
        _require(bool(np.all(np.isfinite(norms)) and np.all(norms > 0)),
                 f"invalid quaternion norms: {condition}")
    times = np.asarray(arrays["A_C__physics_time_ms"])
    _require(bool(np.all(np.isfinite(times)) and np.all(np.diff(times) > 0)), "invalid physics times")
    _require(all(np.array_equal(times, arrays[f"{name}__physics_time_ms"])
                 for _, name, _ in CONDITIONS), "physics time vectors do not align exactly")
    # Recorder time is accumulated in binary64, so validate endpoints within a
    # small numerical representation tolerance while window membership always
    # uses the recorded timestamps themselves.
    _require(abs(float(times[0])) <= 1e-12 and abs(float(times[-1]) - 1500.0) <= 1e-9,
             "physics time endpoints")
    return times


def analyze_arrays(arrays: Mapping[str, np.ndarray]) -> tuple[dict[str, Any], dict[str, Any]]:
    times = _validate_arrays(arrays)
    per_force: dict[str, Any] = {}
    scaling: dict[str, dict[str, Any]] = {metric: {} for metric in THRESHOLDS}
    for force, a_force, b_force in FORCE_PAIRS:
        deviations = {
            "thorax_com_deviation_mm": (
                euclidean_deviation(arrays[f"{a_force}__root_thorax_position"], arrays["A_C__root_thorax_position"]),
                euclidean_deviation(arrays[f"{b_force}__root_thorax_position"], arrays["B_C__root_thorax_position"])),
            "root_orientation_shortest_arc_deg": (
                quaternion_shortest_arc_deg(arrays[f"{a_force}__root_orientation_wxyz"], arrays["A_C__root_orientation_wxyz"]),
                quaternion_shortest_arc_deg(arrays[f"{b_force}__root_orientation_wxyz"], arrays["B_C__root_orientation_wxyz"])),
        }
        metrics = {}
        for metric, (enabled, disabled) in deviations.items():
            windows = {name: reduce_window(enabled, disabled, times, rule, THRESHOLDS[metric])
                       for name, rule in WINDOWS.items()}
            metrics[metric] = {"windows": windows, "overall_post_force_directional_classification":
                classify_overall(windows["early_post_force"]["directional_classification"],
                                 windows["later_post_force"]["directional_classification"])}
        per_force[str(force)] = {"force_magnitude": force, "enabled_condition": a_force,
                                 "disabled_condition": b_force, "metrics": metrics}
    for metric in THRESHOLDS:
        for window in WINDOWS:
            rows = [per_force[str(force)]["metrics"][metric]["windows"][window]
                    for force, _, _ in FORCE_PAIRS]
            scaling[metric][window] = scaling_summary(rows)
    return per_force, scaling


def _load(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as archive:
        return {name: archive[name].copy() for name in archive.files}


def _write_outputs(output_dir: Path, analysis: Mapping[str, Any], source_ids: Mapping[str, Any]) -> None:
    _require(not output_dir.exists(), "output namespace already exists")
    staging = output_dir.with_name(f".{output_dir.name}.tmp-{os.getpid()}")
    _require(not staging.exists(), "staging namespace already exists")
    staging.mkdir(parents=True, exist_ok=False)
    try:
        analysis_path = staging / "m10c_analysis.json"
        analysis_path.write_text(json.dumps(analysis, indent=2, sort_keys=True, allow_nan=False) + "\n")
        source_path = Path(__file__).resolve()
        manifest = {"schema": SCHEMA, "status": "COMPLETE", "source_git_commit": analysis["source_git_commit"],
            "analysis_source": identity(source_path), "python_version": platform.python_version(),
            "numpy_version": np.__version__, "canonical_m10b_inputs": source_ids,
            "frozen_preregistration_identity": source_ids["m10b_preregistration.json"],
            "analysis_rules": {"windows": WINDOWS, "thresholds": THRESHOLDS,
                "force_order": [x[0] for x in FORCE_PAIRS], "position_native_unit_to_mm": 1.0,
                "reduction": "maximum timestamp-aligned nonnegative deviation; enabled minus disabled"},
            "timestamp_independent_reproducibility": {"deterministic": True,
                "json_keys_sorted": True, "input_and_source_sha256_recorded": True},
            "outputs": {"m10c_analysis.json": identity(analysis_path)}}
        (staging / "m10c_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n")
        staging.rename(output_dir)
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def analyze(source_dir: Path = SOURCE_DIR, output_dir: Path = OUTPUT_DIR) -> dict[str, Any]:
    """Validate immutable M10B, analyze it, and atomically create only M10C."""
    _require(not output_dir.exists(), "output namespace already exists")
    before = validate_provenance(source_dir)
    arrays = _load(source_dir / "m10b_raw.npz")
    per_force, scaling = analyze_arrays(arrays)
    after = {name: identity(source_dir / name) for name in EXPECTED_IDENTITIES}
    _require(after == before["identities"], "canonical M10B inputs changed during analysis")
    result = {"schema": SCHEMA, "status": "COMPLETE", "analysis_only": True,
        "physics_transitions": 0, "neural_transitions": 0, "scientific_question": SCIENTIFIC_QUESTION,
        "source_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "canonical_input_identities": before["identities"],
        "frozen_preregistration_identity": before["identities"]["m10b_preregistration.json"],
        "condition_mapping": [{"force_magnitude": f, "condition": n, "motor_enabled": e} for f, n, e in CONDITIONS],
        "windows": WINDOWS, "thresholds": THRESHOLDS, "position_native_unit_to_mm": 1.0,
        "per_force": per_force, "scaling_analysis": scaling,
        "supporting_metrics": {name: {"status": "NOT_INFERENTIALLY_REDUCED_DESCRIPTIVE_ONLY",
            "reason": "the frozen preregistration specifies no exact reduction; no post-hoc reduction was introduced"}
            for name in before["preregistration"]["supporting_metrics"]},
        "prohibited_analyses_not_performed": ["correlation", "regression", "curve fitting", "force normalization",
            "response/force ratios", "normalized effect sizes", "post-hoc thresholds", "post-hoc windows"],
        "interpretation_boundaries": ["causal physical perturbation-response within the modeled MaleCNS -> decoder -> admitted motor -> MuJoCo chain",
            "not balance, stabilization, righting, reflex, recovery, natural locomotion, biological function, or biological timing",
            "557 ms is the frozen M9C approximate first admitted-motor boundary, not a biological latency",
            "contact is observation only and is not a neural sensory input"]}
    _write_outputs(output_dir, result, before["identities"])
    final = {name: identity(source_dir / name) for name in EXPECTED_IDENTITIES}
    _require(final == before["identities"], "canonical M10B inputs changed during publication")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analyze", action="store_true", help="run the read-only canonical M10B analysis")
    args = parser.parse_args(argv)
    if not args.analyze:
        parser.error("explicit --analyze is required")
    analyze()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
