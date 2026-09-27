"""Fail-closed, deterministic extraction of the authorized M8 replay.

This program only copies frozen array elements.  It does not import or invoke
any simulator, physics implementation, neural runtime, or recruitment code.
In particular, NumPy is deliberately imported inside :func:`extract`, after
both immutable byte-identity gates and the existing validation have passed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SOURCE = HERE / "interface_output/m8_extended_spontaneous/m8_raw.npz"
ADDENDUM = HERE / "interface_output/lf_proximal_motor_recruitment/lf_proximal_motor_recruitment_pre_extraction_addendum.json"
OUTPUT_DIR = HERE / "interface_output/lf_proximal_motor_recruitment_sensory_replay"
REPLAY_NAME = "lf_proximal_motor_recruitment_sensory_replay.npy"
MANIFEST_NAME = "lf_proximal_motor_recruitment_sensory_replay_manifest.json"
REPORT_NAME = "LF_PROXIMAL_MOTOR_RECRUITMENT_SENSORY_REPLAY_REPORT.md"

SOURCE_SIZE = 345_584_215
SOURCE_SHA256 = "4e39bb83dd4455d56a4d88f717615530602317efaf83a6ed241b13af89dc2a5b"
ADDENDUM_CANONICAL_SHA256 = "2dbfff3e8db3ea26a57a028dc0b50b24d186cedfb51f95e4fcc5fbde319b1588"
CONDITION = "CORRECTED_SPONTANEOUS_NEURAL_EMBODIMENT"
FIELD = "physics_joint_position"
ROWS = tuple(range(0, 10_000, 10))
COLUMNS = (5, 12, 19, 26, 33, 40)
CHANNELS = ("joint_LFTibia", "joint_LMTibia", "joint_LHTibia",
            "joint_RFTibia", "joint_RMTibia", "joint_RHTibia")


class ExtractionFailure(RuntimeError):
    """A failure whose status is safe to expose in the final JSON result."""

    def __init__(self, status: str, message: str, evidence: dict[str, Any] | None = None):
        super().__init__(message)
        self.status = status
        self.evidence = evidence or {}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_lf(data: bytes) -> bytes:
    """Canonicalize newlines for identity checking, and for nothing else."""
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def identity_gates(source: Path = SOURCE, addendum: Path = ADDENDUM) -> dict[str, Any]:
    """Verify both byte identities without importing NumPy or opening an NPZ."""
    try:
        size = source.stat().st_size
        source_sha = sha256_file(source)
    except OSError as exc:
        raise ExtractionFailure("PROVENANCE_FAILURE", f"cannot read source: {exc}") from exc
    source_identity = {"path": str(source), "size": size, "sha256": source_sha}
    if size != SOURCE_SIZE or source_sha != SOURCE_SHA256:
        raise ExtractionFailure("PROVENANCE_FAILURE", "authoritative source identity mismatch",
                                {"source_identity": source_identity})

    try:
        raw_addendum = addendum.read_bytes()
    except OSError as exc:
        raise ExtractionFailure("PROVENANCE_FAILURE", f"cannot read addendum: {exc}",
                                {"source_identity": source_identity}) from exc
    raw_sha = hashlib.sha256(raw_addendum).hexdigest()
    canonical_sha = hashlib.sha256(canonical_lf(raw_addendum)).hexdigest()
    addendum_identity = {"path": str(addendum), "raw_worktree_sha256": raw_sha,
                         "canonical_lf_sha256": canonical_sha}
    if canonical_sha != ADDENDUM_CANONICAL_SHA256:
        raise ExtractionFailure("PROVENANCE_FAILURE", "canonical-LF addendum identity mismatch",
                                {"source_identity": source_identity,
                                 "addendum_identity": addendum_identity})
    return {"source_identity": source_identity, "addendum_identity": addendum_identity}


def select_exact(source_array: Any, np: Any) -> Any:
    """Perform the sole authorized direct NumPy selection, without conversion."""
    return source_array[np.arange(0, 10_000, 10)[:, None], [5, 12, 19, 26, 33, 40]]


def validate_selected(selected: Any, source_dtype: Any, np: Any) -> None:
    if selected.shape != (1000, 6):
        raise ExtractionFailure("VALIDATION_FAILURE", f"selected shape is {selected.shape}, not (1000, 6)")
    if selected.dtype != source_dtype:
        raise ExtractionFailure("VALIDATION_FAILURE", "selection changed source dtype")
    if not bool(np.isfinite(selected).all()):
        raise ExtractionFailure("VALIDATION_FAILURE", "selection contains nonfinite values")


def validate_round_trip(replay: Any, source_array: Any, np: Any) -> None:
    expected = select_exact(source_array, np)
    validate_selected(replay, expected.dtype, np)
    if not bool(np.array_equal(replay, expected)):
        raise ExtractionFailure("VALIDATION_FAILURE", "reopened replay is not an exact source copy")


def _json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def extract(source: Path = SOURCE, addendum: Path = ADDENDUM,
            output_dir: Path = OUTPUT_DIR) -> dict[str, Any]:
    identities = identity_gates(source, addendum)

    # Import validation and then NumPy only after BOTH cheap byte gates pass.
    from malecns_backend.embodiment import m8_lf_proximal_pre_extraction_validation as prevalidation
    try:
        validation = prevalidation.assess(source)
    except prevalidation.ValidationFailure as exc:
        raise ExtractionFailure("VALIDATION_FAILURE", str(exc)) from exc
    if validation.get("final_status") != "READY_FOR_AUTHORIZED_REPLAY_EXTRACTION":
        raise ExtractionFailure("VALIDATION_FAILURE", "pre-extraction validation did not authorize extraction")

    import numpy as np

    replay_path = output_dir / REPLAY_NAME
    manifest_path = output_dir / MANIFEST_NAME
    report_path = output_dir / REPORT_NAME
    targets = (replay_path, manifest_path, report_path)
    if any(path.exists() for path in targets):
        raise ExtractionFailure("VALIDATION_FAILURE", "refusing to overwrite an extraction artifact")

    prefix = CONDITION + "__"
    with np.load(source, allow_pickle=False) as archive:
        positions = archive[prefix + FIELD]
        physics_time = archive[prefix + "physics_time_ms"]
        selected = select_exact(positions, np)
        validate_selected(selected, positions.dtype, np)
        selected_times = physics_time[np.arange(0, 10_000, 10)]
        nominal_times = np.arange(1000, dtype=np.float64)
        if selected_times.shape != (1000,) or not bool(np.isfinite(selected_times).all()):
            raise ExtractionFailure("VALIDATION_FAILURE", "selected source timestamps are invalid")
        max_deviation = float(np.max(np.abs(selected_times - nominal_times)))
        source_dtype = positions.dtype

        output_dir.mkdir(parents=True, exist_ok=True)
        created: list[Path] = []
        try:
            with replay_path.open("xb") as stream:
                np.save(stream, selected, allow_pickle=False)
            created.append(replay_path)
            with replay_path.open("rb") as stream:
                reopened = np.load(stream, allow_pickle=False)
            validate_round_trip(reopened, positions, np)

            source_sha_after = sha256_file(source)
            if source_sha_after != SOURCE_SHA256:
                raise ExtractionFailure("PROVENANCE_FAILURE", "source changed during extraction")
            replay_sha = sha256_file(replay_path)
            code_sha = sha256_file(Path(__file__).resolve())
            validation_provenance = {
                "schema": validation.get("schema"),
                "final_status": validation.get("final_status"),
                "logic_path": str(Path(prevalidation.__file__).resolve().relative_to(REPO)),
                "logic_sha256": sha256_file(Path(prevalidation.__file__).resolve()),
            }
            manifest = {
                "schema": "LF-PROXIMAL-MOTOR-RECRUITMENT-SENSORY-REPLAY.1",
                "source": {"path": str(source.resolve().relative_to(REPO)), "size": SOURCE_SIZE,
                           "sha256": source_sha_after},
                "condition": CONDITION, "field": FIELD, "rows": list(ROWS),
                "columns": list(COLUMNS), "channel_names_order": list(CHANNELS),
                "units": "radians", "interval_ms": {"start_inclusive": 0, "stop_exclusive": 1000},
                "replay_cadence_ms": 1, "sample_count": 1000, "shape": [1000, 6],
                "dtype": str(source_dtype), "nominal_timestamps_ms": nominal_times.tolist(),
                "actual_source_timestamps_ms": {"first": float(selected_times[0]),
                                                 "last": float(selected_times[-1])},
                "maximum_nominal_timestamp_deviation_ms": max_deviation,
                "exact_copy_policy": "direct NumPy advanced indexing only; no numerical transformation",
                "addendum_raw_worktree_sha256": identities["addendum_identity"]["raw_worktree_sha256"],
                "addendum_canonical_lf_sha256": identities["addendum_identity"]["canonical_lf_sha256"],
                "validation_provenance": validation_provenance,
                "replay": {"path": REPLAY_NAME, "size": replay_path.stat().st_size,
                           "sha256": replay_sha},
                "extraction_code_sha256": code_sha,
                "zero_execution_ledger": {"simulation_steps": 0, "physics_steps": 0,
                                           "neural_runtime_steps": 0, "m8_reruns": 0,
                                           "recruitment_executions": 0},
            }
            with manifest_path.open("xb") as stream:
                stream.write(_json_bytes(manifest))
            created.append(manifest_path)
            manifest_sha = sha256_file(manifest_path)
            report = (
                "# LF proximal motor recruitment sensory replay extraction\n\n"
                "**Status:** REPLAY_EXTRACTION_COMPLETE\n\n"
                "The replay is an exact, direct selection of the authorized physical-angle source rows "
                "and columns. No simulation, physics, neural runtime, M8 rerun, or recruitment was executed.\n\n"
                f"- Replay SHA-256: `{replay_sha}`\n- Manifest SHA-256: `{manifest_sha}`\n"
                f"- Source SHA-256 after extraction: `{source_sha_after}`\n"
            )
            with report_path.open("xb") as stream:
                stream.write(report.encode("utf-8"))
            created.append(report_path)
            report_sha = sha256_file(report_path)
        except Exception:
            for path in reversed(created):
                path.unlink(missing_ok=True)
            raise

    return {"final_status": "REPLAY_EXTRACTION_COMPLETE", "replay_path": str(replay_path),
            "replay_shape": [1000, 6], "replay_dtype": str(source_dtype),
            "replay_sha256": replay_sha, "manifest_sha256": manifest_sha,
            "report_sha256": report_sha, "source_sha256": source_sha_after,
            "canonical_addendum_sha256": identities["addendum_identity"]["canonical_lf_sha256"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--addendum", type=Path, default=ADDENDUM)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    try:
        summary = extract(args.source, args.addendum, args.output_dir)
    except ExtractionFailure as exc:
        summary = {"final_status": exc.status, "failure": str(exc), **exc.evidence}
    except Exception as exc:
        summary = {"final_status": "VALIDATION_FAILURE", "failure": str(exc)}
    print(json.dumps(summary, sort_keys=True, allow_nan=False))
    return 0 if summary["final_status"] == "REPLAY_EXTRACTION_COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
