"""Read-only validation for the addendum-authorized M8 replay slice.

This module never imports a simulator or the neural runtime and never creates a
replay.  The archive byte gate is completed before NumPy is imported or an NPZ
member is opened.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
RAW = HERE / "interface_output/m8_extended_spontaneous/m8_raw.npz"
ADDENDUM = HERE / "interface_output/lf_proximal_motor_recruitment/lf_proximal_motor_recruitment_pre_extraction_addendum.json"
PREREG = HERE / "interface_output/lf_proximal_motor_recruitment/lf_proximal_motor_recruitment_preregistration.json"
JOINT_SOURCE = HERE / "m7e_postrun_analysis.py"
LOOP_SOURCE = HERE / "_windows_m8_live_condition.py"
SIX_MAP = HERE / "six_leg_map.json"

EXPECTED_RAW_SIZE = 345_584_215
EXPECTED_RAW_SHA256 = "4e39bb83dd4455d56a4d88f717615530602317efaf83a6ed241b13af89dc2a5b"
EXPECTED_ADDENDUM_LF_SHA256 = "2dbfff3e8db3ea26a57a028dc0b50b24d186cedfb51f95e4fcc5fbde319b1588"
EXPECTED_PREREG_SHA256 = "994789847840cc53287b1bcbfff34e86fdc880f7b4d00c7cbc00f54f68ed812c"
CONDITION = "CORRECTED_SPONTANEOUS_NEURAL_EMBODIMENT"
JOINTS = tuple(f"joint_{leg}Tibia" for leg in ("LF", "LM", "LH", "RF", "RM", "RH"))
COLUMNS = (5, 12, 19, 26, 33, 40)
ROWS = tuple(range(0, 10_000, 10))


class ValidationFailure(RuntimeError):
    """A fail-closed validation failure with a public result category."""

    def __init__(self, status: str, message: str, evidence: dict[str, Any] | None = None):
        super().__init__(message)
        self.status = status
        self.evidence = evidence or {}


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_lf(data: bytes) -> bytes:
    """Normalize CRLF and legacy CR without changing any other byte."""
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValidationFailure("ADDENDUM_FAILURE", f"expected JSON object: {path}")
    return value


def _verify_addendum() -> tuple[dict[str, Any], dict[str, Any]]:
    raw = ADDENDUM.read_bytes()
    identities = {
        "path": str(ADDENDUM.relative_to(REPO)),
        "raw_worktree_sha256": _sha_bytes(raw),
        "canonical_lf_sha256": _sha_bytes(_canonical_lf(raw)),
        "expected_canonical_lf_sha256": EXPECTED_ADDENDUM_LF_SHA256,
    }
    if identities["canonical_lf_sha256"] != EXPECTED_ADDENDUM_LF_SHA256:
        raise ValidationFailure("ADDENDUM_FAILURE", "canonical-LF addendum SHA-256 mismatch")
    addendum = _load_object(ADDENDUM)
    source = addendum.get("authoritative_source_identity_required_for_future_extraction", {})
    payload = addendum.get("replay_payload", {})
    selection = addendum.get("frozen_source_selection", {})
    required = (
        addendum.get("status") == "FROZEN_BEFORE_EXTRACTION_NOT_EXECUTED",
        source.get("byte_size") == EXPECTED_RAW_SIZE,
        source.get("sha256") == EXPECTED_RAW_SHA256,
        selection.get("condition") == CONDITION,
        selection.get("intended_interval_ms") == {"start_inclusive": 0.0, "stop_exclusive": 1000.0},
        payload.get("units") == "radians",
        tuple(payload.get("channel_order", ())) == JOINTS,
        tuple(payload.get("source_columns_zero_based", ())) == COLUMNS,
        payload.get("source_physics_cadence_ms") == 0.1,
        payload.get("target_replay_cadence_ms") == 1.0,
        payload.get("sample_count") == 1000,
        payload.get("output_shape") == [1000, 6],
        payload.get("source_row_indices") == "0, 10, ..., 9990",
    )
    if not all(required):
        raise ValidationFailure("ADDENDUM_FAILURE", "frozen addendum semantics mismatch")
    if _sha_bytes(_canonical_lf(PREREG.read_bytes())) != EXPECTED_PREREG_SHA256:
        raise ValidationFailure("ADDENDUM_FAILURE", "parent preregistration canonical-LF identity mismatch")
    return addendum, identities


def _verify_archive_bytes(path: Path) -> dict[str, Any]:
    """Complete both binary gates before any scientific-array dependency."""
    size = path.stat().st_size
    digest = _sha_file(path)
    result = {"path": str(path.relative_to(REPO)), "byte_size": size,
              "expected_byte_size": EXPECTED_RAW_SIZE, "sha256": digest,
              "expected_sha256": EXPECTED_RAW_SHA256}
    if size != EXPECTED_RAW_SIZE or digest != EXPECTED_RAW_SHA256:
        raise ValidationFailure(
            "PROVENANCE_FAILURE",
            f"M8 binary identity mismatch before array access (size={size}, sha256={digest})",
            {"source_identity": result},
        )
    return result


def _accumulation_bound(expected: Any, dt_ms: float, np: Any) -> Any:
    """Forward-error bound for sequential binary64 additions.

    Each correctly rounded addition contributes at most half an ULP at that
    step.  One reference ULP covers rounding of the vectorized ``index * dt``.
    This bound is derived before observing archive residuals.
    """
    ulp = np.spacing(np.maximum(np.abs(expected), abs(dt_ms)))
    return 0.5 * np.cumsum(ulp) + ulp


def _time_report(time: Any, *, count: int, dt_ms: float, first_index: int,
                 np: Any) -> tuple[dict[str, Any], bool, Any]:
    def finite_max_or_none(values: Any) -> float | None:
        finite_values = values[np.isfinite(values)]
        return float(finite_values.max()) if finite_values.size else None

    expected = np.arange(first_index, first_index + count, dtype=np.float64) * dt_ms
    structural = (time.dtype == np.dtype("float64") and time.shape == (count,)
                  and bool(np.all(np.isfinite(time))) and bool(np.all(np.diff(time) > 0)))
    error = np.abs(time - expected) if time.shape == expected.shape else np.array([np.inf])
    bound = _accumulation_bound(expected, dt_ms, np)
    accumulated_ok = bool(error.shape == bound.shape and np.all(error <= bound))
    if time.shape == expected.shape and count > 1:
        scale = np.maximum(np.abs(time[:-1]), np.abs(time[1:]))
        delta_bound = 2 * np.spacing(np.maximum(scale, abs(dt_ms))) + np.spacing(dt_ms)
        cadence_error = np.abs(np.diff(time) - dt_ms)
        cadence_ok = bool(np.all(cadence_error <= delta_bound))
        max_cadence_error = finite_max_or_none(cadence_error)
    else:
        cadence_ok, max_cadence_error = False, None
    report = {
        "dtype": str(time.dtype), "count": int(time.size),
        "first_timestamp_ms": float(time[0]) if time.size else None,
        "last_timestamp_ms": float(time[-1]) if time.size else None,
        "finite": bool(np.all(np.isfinite(time))),
        "strictly_increasing": bool(time.size > 0 and np.all(np.diff(time) > 0)),
        "nominal_cadence_ms": dt_ms,
        "max_grid_error_ms": finite_max_or_none(error),
        "maximum_derived_accumulation_bound_ms": float(bound.max()),
        "max_per_step_cadence_error_ms": max_cadence_error,
        "integer_sample_index_correspondence": accumulated_ok,
        "cadence_within_adjacent_float64_bound": cadence_ok,
        "valid": bool(structural and accumulated_ok and cadence_ok),
    }
    return report, report["valid"], expected


def _neural_time_report(neural_time: Any, *, physics_time: Any,
                        physics_valid: bool, np: Any) -> tuple[dict[str, Any], bool]:
    """Validate the neural timestamps as an exact sampled view of physics time.

    The nominal-grid calculations remain useful diagnostics, but are not
    acceptance criteria: the generator does not maintain an independent
    0.5-ms accumulator.
    """
    report, hypothetical_accumulator_ok, _ = _time_report(
        neural_time, count=20_000, dt_ms=0.5, first_index=1, np=np)
    sampled_physics = physics_time[5::5]
    expected_sample_count_ok = sampled_physics.shape == (20_000,)
    expected_shape = neural_time.shape == (20_000,)
    finite = bool(np.all(np.isfinite(neural_time)))
    increasing = bool(neural_time.size > 0 and np.all(np.diff(neural_time) > 0))
    exact_sampled_identity = bool(
        expected_shape and expected_sample_count_ok
        and np.array_equal(neural_time, sampled_physics))
    valid = bool(
        neural_time.dtype == np.dtype("float64")
        and expected_shape
        and finite
        and increasing
        and physics_valid
        and expected_sample_count_ok
        and exact_sampled_identity)
    report.update({
        "generation_semantics": "copied from physics.data.time at every fifth 0.1-ms transition",
        "acceptance_semantics": (
            "validity is inherited from the validated parent physics clock plus exact "
            "element-wise identity with physics_time[5::5]"),
        "expected_physics_row_rule": "5*(i+1)",
        "expected_physics_row_range": [5, 100000],
        "expected_sampled_count": 20_000,
        "expected_sampled_count_matches": bool(expected_sample_count_ok),
        "parent_physics_time_valid": bool(physics_valid),
        "exact_alignment_to_physics_rows": exact_sampled_identity,
        "hypothetical_independent_0_5ms_accumulator_comparison": {
            "diagnostic_only": True,
            "within_derived_accumulation_and_adjacent_cadence_bounds": bool(
                hypothetical_accumulator_ok),
            "reason_not_acceptance_criterion": (
                "tracked generation source has no independent 0.5-ms accumulator"),
        },
        "nominal_grid_and_cadence_checks_are_diagnostic_only": True,
        "valid": valid,
    })
    return report, valid


def _source_joint_names() -> tuple[str, ...]:
    tree = ast.parse(JOINT_SOURCE.read_text(encoding="utf-8"), filename=str(JOINT_SOURCE))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "JOINT_NAMES" for t in node.targets):
            return tuple(eval(compile(ast.Expression(node.value), str(JOINT_SOURCE), "eval"),
                              {"__builtins__": {"tuple": tuple}}))
    raise ValidationFailure("PROVENANCE_FAILURE", "tracked JOINT_NAMES assignment not found")


def _sensor_member_counts() -> tuple[int, ...]:
    audit = _load_object(SIX_MAP)
    result = []
    order = []
    for leg in audit.get("legs", []):
        sensors = [j for j in leg["joints"] if j["actuator"]["anatomical_joint"] == "tibia"]
        if len(sensors) != 1 or len(sensors[0]["sensory"]["populations"]) != 1:
            raise ValidationFailure("PROVENANCE_FAILURE", "non-unique tibial sensor mapping")
        order.append(leg["leg"])
        result.append(len(sensors[0]["sensory"]["populations"][0]["body_ids"]))
    if tuple(order) != ("LF", "LM", "LH", "RF", "RM", "RH"):
        raise ValidationFailure("PROVENANCE_FAILURE", "sensory leg order mismatch")
    return tuple(result)


def _encoded_peak(q: Any, n: int, np: Any) -> Any:
    x = (q - (-1.35)) / (1.30 - (-1.35))
    preferred = (np.arange(n, dtype=np.float64) + 0.5) / n
    rates = 120.0 * np.exp(-((x[:, None] - preferred) ** 2) / (2 * 0.25 ** 2))
    rates[rates <= 5.0] = 0.0
    return np.clip(rates, 0.0, 120.0).max(axis=1)


def assess(raw_path: Path = RAW) -> dict[str, Any]:
    addendum, addendum_identity = _verify_addendum()
    source_identity = _verify_archive_bytes(raw_path)

    # Import only after the complete binary identity gate above.
    import numpy as np

    names = _source_joint_names()
    columns = tuple(names.index(name) for name in JOINTS)
    if columns != COLUMNS:
        raise ValidationFailure("PROVENANCE_FAILURE", f"tracked joint ordering mismatch: {columns}")
    prefix = CONDITION + "__"
    with np.load(raw_path, allow_pickle=False) as archive:
        physics_time = archive[prefix + "physics_time_ms"].copy()
        positions = archive[prefix + "physics_joint_position"].copy()
        neural_time = archive[prefix + "neural_time_ms"].copy()
        frozen_encoded = archive[prefix + "neural_sensory_encoded"].copy()

    physics_report, physics_ok, _ = _time_report(
        physics_time, count=100_001, dt_ms=0.1, first_index=0, np=np)
    neural_report, neural_ok = _neural_time_report(
        neural_time, physics_time=physics_time, physics_valid=physics_ok, np=np)

    row_index = np.asarray(ROWS, dtype=np.int64)
    selected_view = positions[row_index[:, None], np.asarray(COLUMNS)[None, :]]
    selected_copy = selected_view.copy()
    selected_times = physics_time[row_index]
    nominal_times = np.arange(1000, dtype=np.float64)
    selected_error = np.abs(selected_times - nominal_times)
    selected_bounds = _accumulation_bound(nominal_times, 1.0, np)
    # The source clock advances in 0.1-ms steps, so use its corresponding bound,
    # not the tighter hypothetical bound for a separately accumulated 1-ms clock.
    source_bounds = _accumulation_bound(np.arange(100_001, dtype=np.float64) * 0.1, 0.1, np)[row_index]
    slice_ok = bool(positions.shape == (100_001, 42) and selected_copy.shape == (1000, 6)
                    and np.all(np.isfinite(selected_copy))
                    and np.array_equal(selected_copy, selected_view, equal_nan=True)
                    and np.all(selected_error <= source_bounds))

    aligned_rows = np.arange(5, 100_001, 5)
    all_tibiae = positions[:, COLUMNS]
    reconstructed = np.column_stack([
        _encoded_peak(all_tibiae[aligned_rows, channel], count, np)
        for channel, count in enumerate(_sensor_member_counts())
    ])
    residual = np.abs(reconstructed - frozen_encoded)
    encoder_ok = bool(frozen_encoded.shape == (20_000, 6)
                      and np.all(np.isfinite(frozen_encoded))
                      and np.array_equal(reconstructed, frozen_encoded))
    valid = physics_ok and neural_ok and slice_ok and encoder_ok
    return {
        "schema": "M8-LF-PROXIMAL-PRE-EXTRACTION-VALIDATION.1",
        "final_status": "READY_FOR_AUTHORIZED_REPLAY_EXTRACTION" if valid else "NUMERICAL_VALIDATION_FAILURE",
        "scientific_execution": {"simulation_steps": 0, "physics_steps": 0, "neural_steps": 0,
                                 "replay_extracted": False},
        "addendum_identity": addendum_identity,
        "source_identity": source_identity,
        "tracked_generation_semantics": {
            "physics": "physics.data.time * 1000 sampled initially and after repeated 0.1-ms MuJoCo transitions",
            "neural": "the same now_ms value recorded at transition indices divisible by five",
            "loop_source_path": str(LOOP_SOURCE.relative_to(REPO)),
            "loop_source_canonical_lf_sha256": _sha_bytes(_canonical_lf(LOOP_SOURCE.read_bytes())),
            "conclusion": "bounded deterministic IEEE-754 accumulation, not cadence/state mismatch" if valid else "validation did not establish ordinary accumulation",
        },
        "verification": {
            "physics_time": physics_report,
            "neural_time": neural_report,
            "authorized_source_slice": {
                "source_rows": "0,10,...,9990", "source_columns": list(COLUMNS),
                "channel_order": list(JOINTS), "units": "radians",
                "shape": list(selected_copy.shape), "finite": bool(np.all(np.isfinite(selected_copy))),
                "exact_source_copy": bool(np.array_equal(selected_copy, selected_view, equal_nan=True)),
                "nominal_first_timestamp_ms": 0.0, "nominal_last_timestamp_ms": 999.0,
                "actual_first_timestamp_ms": float(selected_times[0]),
                "actual_last_timestamp_ms": float(selected_times[-1]),
                "max_timestamp_deviation_ms": float(selected_error.max()),
                "maximum_source_clock_bound_ms": float(source_bounds.max()),
                "hypothetical_1ms_accumulator_bound_not_used_ms": float(selected_bounds.max()),
                "valid": slice_ok,
            },
            "encoder_consistency": {
                "comparison": "all 20000x6 modeled per-interface encoded-rate peaks",
                "exact_float64_equal_count": int(np.count_nonzero(reconstructed == frozen_encoded)),
                "value_count": int(frozen_encoded.size),
                "max_absolute_error_hz": float(residual.max()), "valid": encoder_ok,
                "scope": "modeled encoder consistency only; not biological validation",
            },
        },
        "authorization": addendum["authorization"],
        "interpretation_boundaries": {
            "angles": "FlyGym/MuJoCo measured joint coordinates",
            "transduction": "modeled",
            "biological_claim": "none",
            "active_physical_motor_interface_channel_count": 11,
            "new_decoder_or_sign_assignment": False,
        },
        "next_action_if_ready": (
            "In a separate change, implement and run a deterministic extractor that first repeats both identity gates, "
            "then writes only physics_joint_position[np.arange(0,10000,10)[:,None],[5,12,19,26,33,40]]."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=RAW)
    parser.add_argument("--output", type=Path, help="new report path; existing files are never overwritten")
    args = parser.parse_args()
    try:
        report = assess(args.raw)
    except ValidationFailure as exc:
        report = {"schema": "M8-LF-PROXIMAL-PRE-EXTRACTION-VALIDATION.1",
                  "final_status": exc.status, "failure": str(exc),
                  "scientific_execution": {"simulation_steps": 0, "physics_steps": 0,
                                             "neural_steps": 0, "replay_extracted": False}}
        report.update(exc.evidence)
        # A source-byte failure happens after the addendum gate.  Retain both
        # requested newline-sensitive identities in that fail-closed report.
        if exc.status == "PROVENANCE_FAILURE":
            try:
                _, report["addendum_identity"] = _verify_addendum()
            except ValidationFailure:
                pass
    rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(rendered)
    else:
        print(rendered, end="")
    return 0 if report["final_status"] == "READY_FOR_AUTHORIZED_REPLAY_EXTRACTION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
