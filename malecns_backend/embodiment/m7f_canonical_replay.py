"""Read-only M7D canonical replay exporter.

This module imports no FlyGym, MuJoCo, MaleCNS, or experiment runner.  It
serializes recorded arrays; it cannot advance either scientific clock.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from typing import Any, Mapping, Sequence

import numpy as np

HERE = Path(__file__).resolve().parent
M7D_DIR = HERE / "interface_output" / "m7d_corrected_spontaneous"
M7E_DIR = HERE / "interface_output" / "m7e_postrun_analysis"
OUTPUT_DIR = HERE / "interface_output" / "m7f_replay"
RAW_PATH = M7D_DIR / "m7d_raw.npz"
M7D_MANIFEST_PATH = M7D_DIR / "m7d_manifest.json"
M7D_SUMMARY_PATH = M7D_DIR / "m7d_summary.json"
M7E_MANIFEST_PATH = M7E_DIR / "m7e_manifest.json"
M7E_ANALYSIS_PATH = M7E_DIR / "m7e_analysis.json"
MANIFEST_PATH = OUTPUT_DIR / "m7f_manifest.json"
CONTACT_PATH = OUTPUT_DIR / "m7f_contact_mapping.json"

SCHEMA = "M7F-CANONICAL-REPLAY.1"
BINARY_SCHEMA = 1
MAGIC = b"M7FRPLY\0"
CANONICAL_SIZE = 16_737_088
CANONICAL_SHA256 = "92b5c645a88fe74e5d6aa0988478c374e8fde3a0e923d42cc13974a3e60d8444"
CONDITIONS = ("CORRECTED_SPONTANEOUS_NEURAL_EMBODIMENT", "CORRECTED_ALL_NEURAL_MOTOR_DISABLED")
FILE_NAMES = ("m7f_enabled_replay.bin", "m7f_disabled_replay.bin")
PHYSICS_COUNT, NEURAL_COUNT = 5001, 1000
JOINT_NAMES = tuple(f"joint_{leg}{part}" for leg in ("LF", "LM", "LH", "RF", "RM", "RH")
                    for part in ("Coxa", "Coxa_roll", "Coxa_yaw", "Femur", "Femur_roll", "Tibia", "Tarsus1"))
MOTOR_NAMES = ("joint_LFTibia", "joint_LMTibia", "joint_LHTibia", "joint_RFTibia",
               "joint_RMTibia", "joint_RHTibia", "joint_LFFemur", "joint_LMFemur",
               "joint_LHFemur", "joint_RMFemur", "joint_RHFemur")
SENSORY_NAMES = tuple(f"joint_{leg}Tibia" for leg in ("LF", "LM", "LH", "RF", "RM", "RH"))
FIELDS = (
    ("physics_time_ms", "<f8", ()), ("physics_body_position", "<f8", (3,)),
    ("physics_body_orientation", "<f8", (4,)), ("physics_joint_position", "<f8", (42,)),
    ("neural_time_ms", "<f8", ()), ("neural_observer_outputs", "<f8", (11,)),
    ("neural_decoder_outputs", "<f8", (11,)), ("neural_admitted_contributions", "<f8", (11,)),
    ("neural_sensory_encoded", "<f8", (6,)), ("neural_delivered_drive_count", "<i8", ()),
    ("neural_aggregate_spikes", "<i8", ()),
)


class EvidenceError(RuntimeError):
    """Immutable evidence or replay schema failed a required invariant."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"cannot read JSON evidence {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceError(f"JSON evidence is not an object: {path}")
    return value


def _git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=HERE, check=True,
                              capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def validate_m7e(manifest_path: Path = M7E_MANIFEST_PATH,
                 analysis_path: Path = M7E_ANALYSIS_PATH) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest, analysis = read_json(manifest_path), read_json(analysis_path)
    if manifest.get("status") != "COMPLETE" or manifest.get("schema") != "M7E-POSTRUN-ANALYSIS.1":
        raise EvidenceError("M7E manifest status/schema mismatch")
    spec = manifest.get("analysis", {})
    if spec.get("sha256") != sha256(analysis_path) or spec.get("byte_size") != analysis_path.stat().st_size:
        raise EvidenceError("M7E analysis identity mismatch")
    if manifest.get("source", {}).get("input_sha256") != CANONICAL_SHA256:
        raise EvidenceError("M7E does not annotate the canonical M7D archive")
    if manifest.get("physics_transitions") != 0 or manifest.get("neural_transitions") != 0:
        raise EvidenceError("M7E zero-transition declaration mismatch")
    if analysis.get("status") != "COMPLETE":
        raise EvidenceError("M7E analysis status is not COMPLETE")
    return manifest, analysis


def validate_m7d(raw_path: Path = RAW_PATH, manifest_path: Path = M7D_MANIFEST_PATH,
                 summary_path: Path = M7D_SUMMARY_PATH, *, expected_sha: str = CANONICAL_SHA256,
                 expected_size: int = CANONICAL_SIZE, physics_count: int = PHYSICS_COUNT,
                 neural_count: int = NEURAL_COUNT) -> tuple[dict[str, np.ndarray], dict[str, Any], dict[str, Any]]:
    if not raw_path.is_file():
        raise EvidenceError(f"canonical M7D raw evidence is absent: {raw_path}")
    if raw_path.stat().st_size != expected_size:
        raise EvidenceError(f"raw byte-size mismatch: expected {expected_size}, observed {raw_path.stat().st_size}")
    digest = sha256(raw_path)
    if digest != expected_sha:
        raise EvidenceError(f"raw SHA-256 mismatch: expected {expected_sha}, observed {digest}")
    manifest, summary = read_json(manifest_path), read_json(summary_path)
    if manifest.get("status") != "COMPLETE" or summary.get("status") != "COMPLETE":
        raise EvidenceError("M7D summary and manifest must both have status COMPLETE")
    if manifest.get("schema") != "M7D-CORRECTED-SPONTANEOUS.1" or summary.get("schema") != "M7D-CORRECTED-SPONTANEOUS.1":
        raise EvidenceError("M7D schema mismatch")
    if manifest.get("raw", {}).get("sha256") != digest or manifest.get("raw", {}).get("byte_size") != expected_size:
        raise EvidenceError("M7D manifest raw identity mismatch")
    if summary.get("raw_telemetry", {}).get("sha256") != digest:
        raise EvidenceError("M7D summary raw identity mismatch")
    required = {f"{condition}__{field}" for condition in CONDITIONS for field, _, _ in FIELDS}
    declared = manifest.get("arrays")
    if not isinstance(declared, dict) or not required.issubset(declared):
        raise EvidenceError("M7D manifest lacks required replay arrays")
    try:
        with np.load(raw_path, allow_pickle=False) as archive:
            if not required.issubset(archive.files):
                raise EvidenceError("M7D archive lacks required replay arrays")
            arrays = {name: archive[name].copy() for name in required}
    except (OSError, TypeError, ValueError) as exc:
        raise EvidenceError(f"M7D cannot be loaded with allow_pickle=False: {exc}") from exc
    for condition in CONDITIONS:
        for field, dtype, tail in FIELDS:
            key = f"{condition}__{field}"; value = arrays[key]
            count = physics_count if field.startswith("physics_") else neural_count
            if value.shape != (count, *tail) or value.dtype != np.dtype(dtype):
                raise EvidenceError(f"shape/dtype mismatch: {key}")
            if not np.all(np.isfinite(value)):
                raise EvidenceError(f"nonfinite value forbidden: {key}")
            spec = declared[key]
            if spec.get("shape") != list(value.shape) or np.dtype(spec.get("dtype")) != value.dtype:
                raise EvidenceError(f"manifest array declaration mismatch: {key}")
        pt, nt = arrays[f"{condition}__physics_time_ms"], arrays[f"{condition}__neural_time_ms"]
        if not np.all(np.diff(pt) > 0) or not np.allclose(np.diff(pt), .1, rtol=0, atol=1e-10):
            raise EvidenceError(f"physics clock mismatch: {condition}")
        if not np.array_equal(nt, pt[5::5]):
            raise EvidenceError(f"neural/physics alignment mismatch: {condition}")
    for field in ("physics_time_ms", "neural_time_ms"):
        if not np.array_equal(arrays[f"{CONDITIONS[0]}__{field}"], arrays[f"{CONDITIONS[1]}__{field}"]):
            raise EvidenceError(f"condition clock mismatch: {field}")
    return arrays, manifest, summary


def flygym_to_unity(position: Sequence[float]) -> np.ndarray:
    """Validated presentation transform: [x,y,z] mm -> [x,z,y] * 0.1."""
    value = np.asarray(position, dtype=np.float64)
    if value.shape[-1:] != (3,) or not np.all(np.isfinite(value)):
        raise ValueError("position must have a finite final dimension of three")
    return value[..., (0, 2, 1)] * .1


def contact_audit() -> dict[str, Any]:
    """Fail closed: frozen telemetry preserves vectors, but not sensor identity."""
    channels = [{"channel_index": i, "exact_source_identity": None, "geom_name": None,
                 "body_name": None, "associated_leg": "UNKNOWN",
                 "evidence_source": "M7D numeric archive and recorder array shape only",
                 "derivation_method": "No identity-bearing model metadata was preserved; no behavioral inference permitted.",
                 "confidence": "UNRESOLVED"} for i in range(36)]
    recorder = HERE / "_windows_m7d_corrected_spontaneous_adapter.py"
    source_hashes = {"frozen_m7d_windows_recorder": sha256(recorder)} if recorder.is_file() else {}
    return {"schema": "M7F-CONTACT-IDENTITY-AUDIT.1", "status": "COMPLETE",
            "classification": "CONTACT_IDENTITY_MAPPING_UNRESOLVED", "flygym_version": "1.2.1",
            "mujoco_version": "3.2.7", "source_m7d_sha256": CANONICAL_SHA256,
            "relevant_source_hashes": source_hashes, "exact_channel_ordering": channels,
            "unresolved_channels": list(range(36)), "contacts_available": False,
            "mapping_derivation": "Fail-closed static audit. Resolution requires the exact frozen sensor declaration/order plus compiled model geom/body IDs and names.",
            "metadata_dependencies": ["ordered Fly.contact_sensor_placements used by M7D",
                "FlyGym 1.2.1 contact-force observation construction source",
                "MuJoCo 3.2.7 compiled model geom IDs/names and body IDs/names"],
            "forbidden_derivations": ["force magnitude", "timing", "gait expectation", "symmetry", "leg motion", "visual appearance"],
            "physics_transitions": 0, "neural_transitions": 0,
            "zero_transition_declaration": "Metadata audit performs no env.step, physics.step, mj_step, Brain.step, or neural runtime step."}


def _layout(physics_count: int, neural_count: int) -> list[dict[str, Any]]:
    offset = struct.calcsize("<8sIIII")
    result = []
    for name, dtype, tail in FIELDS:
        shape = (physics_count if name.startswith("physics_") else neural_count, *tail)
        size = int(np.prod(shape, dtype=np.int64)) * np.dtype(dtype).itemsize
        result.append({"name": name, "dtype": dtype, "shape": list(shape), "offset_bytes": offset, "size_bytes": size})
        offset += size
    return result


def serialize_condition(arrays: Mapping[str, np.ndarray], condition: str) -> bytes:
    p = len(arrays[f"{condition}__physics_time_ms"]); n = len(arrays[f"{condition}__neural_time_ms"])
    chunks = [struct.pack("<8sIIII", MAGIC, BINARY_SCHEMA, p, n, len(FIELDS))]
    for field, dtype, tail in FIELDS:
        value = np.asarray(arrays[f"{condition}__{field}"], dtype=np.dtype(dtype), order="C")
        expected = (p if field.startswith("physics_") else n, *tail)
        if value.shape != expected or not np.all(np.isfinite(value)):
            raise EvidenceError(f"cannot serialize malformed field: {field}")
        chunks.append(value.tobytes(order="C"))
    return b"".join(chunks)


def parse_replay(data: bytes) -> dict[str, np.ndarray]:
    header_size = struct.calcsize("<8sIIII")
    if len(data) < header_size:
        raise EvidenceError("truncated replay header")
    magic, version, p, n, fields = struct.unpack_from("<8sIIII", data)
    if magic != MAGIC or version != BINARY_SCHEMA or fields != len(FIELDS):
        raise EvidenceError("binary replay header mismatch")
    result: dict[str, np.ndarray] = {}; offset = header_size
    for spec in _layout(p, n):
        end = offset + spec["size_bytes"]
        if end > len(data): raise EvidenceError(f"truncated replay field: {spec['name']}")
        result[spec["name"]] = np.frombuffer(data, dtype=spec["dtype"],
                                               count=int(np.prod(spec["shape"])), offset=offset).reshape(spec["shape"]).copy()
        offset = end
    if offset != len(data): raise EvidenceError("unexpected trailing replay bytes")
    return result


def ensure_output_available(output_dir: Path = OUTPUT_DIR) -> None:
    manifest = output_dir / "m7f_manifest.json"
    if manifest.exists() and read_json(manifest).get("status") == "CANONICAL_REPLAY_EXPORT_COMPLETE":
        raise FileExistsError("refusing to overwrite COMPLETE M7F export")
    if any((output_dir / name).exists() for name in FILE_NAMES):
        raise FileExistsError("refusing to overwrite existing replay binary")


def build_manifest(arrays: Mapping[str, np.ndarray], summary: Mapping[str, Any],
                   m7e_manifest: Mapping[str, Any], artifacts: Sequence[Path],
                   contact: Mapping[str, Any]) -> dict[str, Any]:
    milestones = summary.get("causal_milestones")
    if not isinstance(milestones, dict) or not all(f"D{i}" in " ".join(milestones) for i in (1, 3, 4, 5, 6, 7, 8, 9, 10)):
        raise EvidenceError("canonical M7D milestones missing")
    return {"schema": SCHEMA, "status": "CANONICAL_REPLAY_EXPORT_COMPLETE",
            "classifications": ["CANONICAL_REPLAY_EXPORT_COMPLETE", contact["classification"], "UNITY_REPLAY_VIEWER_READY"],
            "canonical_m7d_sha256": CANONICAL_SHA256,
            "canonical_m7e_analysis_sha256": m7e_manifest["analysis"]["sha256"],
            "exporter_source_commit": _git_commit(), "frame_counts": {"physics": len(arrays[f"{CONDITIONS[0]}__physics_time_ms"]), "neural": len(arrays[f"{CONDITIONS[0]}__neural_time_ms"])},
            "cadence_ms": {"physics": .1, "neural": .5}, "condition_labels": {CONDITIONS[0]: "NEURAL MOTOR ENABLED", CONDITIONS[1]: "MATCHED MOTOR-DISABLED CONTROL"},
            "coordinate_conversion": {"source": "FlyGym right-handed Z-up millimetres", "unity": "left-handed Y-up", "mapping": "[x,y,z] -> [x,z,y]", "scale": .1, "stored_coordinates": "unconverted scientific source values"},
            "binary": {"magic_ascii": "M7FRPLY\\0", "endianness": "little", "header": "8-byte magic, uint32 schema, physics count, neural count, field count", "layout": _layout(len(arrays[f"{CONDITIONS[0]}__physics_time_ms"]), len(arrays[f"{CONDITIONS[0]}__neural_time_ms"]))},
            "joint_names": list(JOINT_NAMES), "motor_channel_names": list(MOTOR_NAMES), "sensory_channel_names": list(SENSORY_NAMES),
            "milestones": milestones, "milestone_provenance": "canonical M7D summary; consistency annotated by completed M7E",
            "bookmarks": [{"time_ms": x, "label": label, "classification": "NAVIGATION_ONLY"} for x, label in ((0., "initial state"),(54., "first mapped motor contribution / physical divergence begins"),(78.5,"altered sensory drive and downstream CNS divergence"),(121.,"near RH tibia maximum A/B divergence"),(157.,"later mapped motor-state divergence"),(250.,"strong RM/RH divergence region"),(398.,"later large joint divergence region start"),(425.,"later large joint divergence region end"))],
            "contact_mapping_classification": contact["classification"], "contacts_available": contact["contacts_available"],
            "artifacts": [{"path": p.name, "byte_size": p.stat().st_size, "sha256": sha256(p)} for p in artifacts],
            "presentation_interpolation": {"default": False, "scientific_evidence": False},
            "physics_transitions": 0, "neural_transitions": 0, "walking_classification": None, "gait_classification": None}


def export(*, raw_path: Path = RAW_PATH, m7d_manifest: Path = M7D_MANIFEST_PATH,
           m7d_summary: Path = M7D_SUMMARY_PATH, m7e_manifest_path: Path = M7E_MANIFEST_PATH,
           m7e_analysis_path: Path = M7E_ANALYSIS_PATH, output_dir: Path = OUTPUT_DIR,
           expected_sha: str = CANONICAL_SHA256, expected_size: int = CANONICAL_SIZE,
           physics_count: int = PHYSICS_COUNT, neural_count: int = NEURAL_COUNT) -> dict[str, Any]:
    ensure_output_available(output_dir)
    arrays, _, summary = validate_m7d(raw_path, m7d_manifest, m7d_summary,
        expected_sha=expected_sha, expected_size=expected_size, physics_count=physics_count, neural_count=neural_count)
    m7e_manifest_value, _ = validate_m7e(m7e_manifest_path, m7e_analysis_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    contact = contact_audit(); contact_path = output_dir / CONTACT_PATH.name
    previous_contact = contact_path.read_bytes() if contact_path.exists() else None
    contact_path.write_text(json.dumps(contact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifacts = []
    try:
        for condition, filename in zip(CONDITIONS, FILE_NAMES):
            path = output_dir / filename; path.write_bytes(serialize_condition(arrays, condition)); artifacts.append(path)
        manifest = build_manifest(arrays, summary, m7e_manifest_value, artifacts, contact)
        (output_dir / MANIFEST_PATH.name).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception:
        for path in artifacts: path.unlink(missing_ok=True)
        if previous_contact is None: contact_path.unlink(missing_ok=True)
        else: contact_path.write_bytes(previous_contact)
        raise
    return manifest


def preflight() -> None:
    ensure_output_available(); arrays, _, _ = validate_m7d(); validate_m7e()
    for condition in CONDITIONS: parse_replay(serialize_condition(arrays, condition))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__); modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--windows-preflight", action="store_true"); modes.add_argument("--export-windows", action="store_true")
    args = parser.parse_args(argv)
    if args.windows_preflight:
        preflight()
        print("M7F WINDOWS PREFLIGHT PASS —\nCANONICAL M7D VERIFIED —\nCANONICAL M7E VERIFIED —\nREPLAY SCHEMA VERIFIED —\nZERO PHYSICS TRANSITIONS —\nZERO NEURAL TRANSITIONS —\nEXPORT NOT RUN")
    else:
        export(); print("M7F CANONICAL REPLAY EXPORT COMPLETE — ZERO PHYSICS TRANSITIONS — ZERO NEURAL TRANSITIONS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
