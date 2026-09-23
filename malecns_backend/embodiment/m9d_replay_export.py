"""Zero-transition exporter for the frozen canonical M9B Unity replay.

This module only reads recorded NPZ arrays.  It intentionally imports neither
the M9B runner nor FlyGym/MuJoCo/MaleCNS runtime code.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
from typing import Mapping, Sequence

import numpy as np

HERE = Path(__file__).resolve().parent
SOURCE_DIR = HERE / "interface_output" / "m9b_external_perturbation"
OUTPUT_DIR = HERE / "interface_output" / "m9d_unity_replay"
RAW_PATH = SOURCE_DIR / "m9b_raw.npz"
MANIFEST_PATH = SOURCE_DIR / "m9b_manifest.json"
PREREGISTRATION_PATH = SOURCE_DIR / "m9b_preregistration.json"
REPORT_PATH = SOURCE_DIR / "m9b_report.json"

SCHEMA = "M9D-CANONICAL-M9B-UNITY-REPLAY.1"
MAGIC = b"M9DRPLY\0"
VERSION = 1
CONDITIONS = ("A_P", "A_C", "B_P", "B_C")
FILES = {condition: f"m9d_{condition.lower()}_replay.bin" for condition in CONDITIONS}
STATE_COUNT = 15001
JOINT_COUNT = 42
JOINT_NAMES = tuple(f"joint_{leg}{part}" for leg in ("LF", "LM", "LH", "RF", "RM", "RH")
                    for part in ("Coxa", "Coxa_roll", "Coxa_yaw", "Femur", "Femur_roll", "Tibia", "Tarsus1"))
FIELDS = (("physics_time_ms", ()), ("physics_body_position", (3,)),
          ("physics_body_orientation", (4,)), ("physics_joint_position", (42,)))
CANONICAL = {
    "m9b_raw.npz": (108063966, "55359880f3f63a5ef2ae2b316737973e73ad4308d499a02d999538f8f19d984f"),
    "m9b_manifest.json": (104660, "1ac6be8338180feccc6af5a9a0d5e5590c6f4d4278d55f5a87218df21b4c1830"),
    "m9b_preregistration.json": (6442, "1c2509317b01950925d7fa29807ab5aec73dbed78a2606da87512b665b7d3c23"),
    # Git stores the frozen JSON with LF.  The M9B manifest records the
    # byte-equivalent Windows CRLF publication (316 bytes, SHA 7299c3...).
    "m9b_report.json": (309, "a76b861a9cc6a846f07a3f2fa7f4115f92bae2a0cd1c6f99304e49478ea64be5"),
}
PUBLISHED_WINDOWS_REPORT = {
    "byte_size": 316,
    "sha256": "7299c349d5824fb9d5ef7713bf7ea5e9794972f3669790502609dfa5a3e8224e",
}
PHYSICS_TRANSITIONS = NEURAL_TRANSITIONS = 0


class EvidenceError(RuntimeError): pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""): digest.update(block)
    return digest.hexdigest()


def _identity(data: bytes) -> dict:
    return {"byte_size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _read_canonical_json(path: Path, canonical: tuple[int, str]) -> tuple[dict, dict]:
    """Read an LF-canonical JSON artifact without changing its physical bytes."""
    physical = path.read_bytes()
    crlf_count = physical.count(b"\r\n")
    without_crlf = physical.replace(b"\r\n", b"")
    if b"\r" in without_crlf:
        raise EvidenceError(f"malformed newline representation: {path.name}")
    if crlf_count and b"\n" in without_crlf:
        raise EvidenceError(f"mixed newline representation: {path.name}")

    canonical_bytes = physical.replace(b"\r\n", b"\n")
    if (len(canonical_bytes), hashlib.sha256(canonical_bytes).hexdigest()) != canonical:
        raise EvidenceError(f"canonical M9B source identity mismatch: {path.name}")
    try:
        value = json.loads(canonical_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"invalid canonical M9B JSON: {path.name}") from exc
    provenance = {
        "identity_semantics": "canonical_lf_after_crlf_normalization",
        "canonical_lf_identity": {"byte_size": canonical[0], "sha256": canonical[1]},
        "working_tree_identity": _identity(physical),
        "working_tree_newlines": "CRLF" if crlf_count else "LF",
    }
    return value, provenance


def validate_source(source_dir: Path = SOURCE_DIR) -> dict:
    raw_path = source_dir / "m9b_raw.npz"
    raw_size, raw_digest = CANONICAL[raw_path.name]
    if (not raw_path.is_file() or raw_path.stat().st_size != raw_size
            or sha256(raw_path) != raw_digest):
        raise EvidenceError(f"canonical M9B source identity mismatch: {raw_path.name}")
    provenance = {
        raw_path.name: {
            "identity_semantics": "exact_bytes",
            "exact_identity": {"byte_size": raw_size, "sha256": raw_digest},
            "working_tree_identity": {"byte_size": raw_size, "sha256": raw_digest},
        }
    }
    values = {}
    for name in ("m9b_manifest.json", "m9b_preregistration.json", "m9b_report.json"):
        path = source_dir / name
        if not path.is_file():
            raise EvidenceError(f"canonical M9B source identity mismatch: {name}")
        values[name], provenance[name] = _read_canonical_json(path, CANONICAL[name])
    manifest = values["m9b_manifest.json"]
    prereg = values["m9b_preregistration.json"]
    report = values["m9b_report.json"]
    if manifest.get("status") != "COMPLETE" or report.get("status") != "COMPLETE_UNCLASSIFIED":
        raise EvidenceError("canonical M9B completion status mismatch")
    if prereg.get("design", {}).get("conditions") != list(CONDITIONS):
        raise EvidenceError("canonical M9B condition order mismatch")
    raw = manifest.get("raw", {})
    if (raw.get("byte_size"), raw.get("sha256")) != CANONICAL["m9b_raw.npz"]:
        raise EvidenceError("M9B manifest raw identity mismatch")
    if manifest.get("report") != PUBLISHED_WINDOWS_REPORT:
        # The explicit check deliberately keeps the published Windows identity
        # separate from the repository's newline-normalized frozen copy.
        raise EvidenceError("M9B manifest report identity mismatch")
    return {"manifest": manifest, "preregistration": prereg, "report": report,
            "source_provenance": provenance}


def validate_arrays(arrays: Mapping[str, np.ndarray]) -> None:
    for condition in CONDITIONS:
        for field, tail in FIELDS:
            key = f"{condition}__{field}"
            if key not in arrays: raise EvidenceError(f"missing replay field: {key}")
            value = arrays[key]
            if value.shape != (STATE_COUNT, *tail) or value.dtype != np.dtype("<f8"):
                raise EvidenceError(f"shape/dtype mismatch: {key}")
            if not np.all(np.isfinite(value)): raise EvidenceError(f"nonfinite replay value: {key}")
        time = arrays[f"{condition}__physics_time_ms"]
        if not np.allclose(time, np.arange(STATE_COUNT) * .1, rtol=0, atol=2e-7):
            raise EvidenceError(f"physical clock/count mismatch: {condition}")
    first = arrays[f"{CONDITIONS[0]}__physics_time_ms"]
    if any(not np.array_equal(first, arrays[f"{c}__physics_time_ms"]) for c in CONDITIONS[1:]):
        raise EvidenceError("four-condition physical clocks disagree")


def load_arrays(raw_path: Path) -> dict[str, np.ndarray]:
    required = {f"{c}__{field}" for c in CONDITIONS for field, _ in FIELDS}
    try:
        with np.load(raw_path, allow_pickle=False) as archive:
            if not required.issubset(archive.files): raise EvidenceError("M9B archive lacks replay fields")
            arrays = {key: archive[key].copy() for key in required}
    except (OSError, ValueError) as exc: raise EvidenceError(f"cannot read M9B NPZ: {exc}") from exc
    validate_arrays(arrays)
    return arrays


def serialize_condition(arrays: Mapping[str, np.ndarray], condition: str) -> bytes:
    if condition not in CONDITIONS: raise EvidenceError("unknown M9D condition")
    chunks = [struct.pack("<8sIII", MAGIC, VERSION, STATE_COUNT, JOINT_COUNT)]
    for field, _ in FIELDS: chunks.append(arrays[f"{condition}__{field}"].astype("<f8", copy=False).tobytes())
    return b"".join(chunks)


def parse_replay(data: bytes) -> dict[str, np.ndarray]:
    header = struct.calcsize("<8sIII")
    if len(data) < header: raise EvidenceError("truncated M9D header")
    magic, version, count, joints = struct.unpack_from("<8sIII", data)
    if magic != MAGIC or version != VERSION or count != STATE_COUNT or joints != JOINT_COUNT:
        raise EvidenceError("M9D binary header mismatch")
    offset = header; result = {}
    for field, tail in FIELDS:
        shape = (count, *tail); size = int(np.prod(shape)) * 8
        if offset + size > len(data): raise EvidenceError(f"truncated M9D field: {field}")
        result[field] = np.frombuffer(data, "<f8", int(np.prod(shape)), offset).reshape(shape).copy()
        offset += size
    if offset != len(data): raise EvidenceError("M9D binary has trailing bytes")
    return result


def flygym_to_unity(value):
    value = np.asarray(value, dtype=np.float64)
    if value.shape[-1:] != (3,) or not np.all(np.isfinite(value)): raise ValueError("finite XYZ required")
    return value[..., (0, 2, 1)] * .1


def _commit():
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=HERE, check=True,
                          text=True, capture_output=True).stdout.strip()


def build_manifest(paths: Sequence[Path], source_provenance: Mapping | None = None) -> dict:
    if source_provenance is None:
        source_provenance = {
            name: {"identity_semantics": "exact_bytes" if name.endswith(".npz") else
                   "canonical_lf_after_crlf_normalization",
                   "canonical_lf_identity" if name.endswith(".json") else "exact_identity":
                   {"byte_size": size, "sha256": digest}}
            for name, (size, digest) in CANONICAL.items()
        }
    return {"schema": SCHEMA, "status": "COMPLETE", "exporter_source_commit": _commit(),
            "canonical_m9b_sources": dict(source_provenance),
            "published_m9b_report_identity": {
                "identity_semantics": "exact_bytes_of_m9b_windows_publication",
                **PUBLISHED_WINDOWS_REPORT,
            },
            "conditions": [{"id": c, "artifact": FILES[c], "state_count": STATE_COUNT,
                            "neural_motor_enabled": c.startswith("A_"), "perturbation_present": c.endswith("_P")}
                           for c in CONDITIONS],
            "joint_count": JOINT_COUNT, "joint_names": list(JOINT_NAMES),
            "artifacts": [{"path": p.name, "byte_size": p.stat().st_size, "sha256": sha256(p)} for p in paths],
            "force": {"magnitude_native": 1.024, "world_direction_source_xyz": [0, 1, 0],
                      "unity_direction_xyz": [0, 0, 1], "target": "authoritative Thorax center of mass",
                      "torque_source_xyz": [0, 0, 0], "start_ms_inclusive": 500.0,
                      "stop_ms_exclusive": 520.0, "transition_start_inclusive": 5000,
                      "transition_stop_exclusive": 5200, "first_potentially_affected_state_ms": 500.1},
            "coordinate_conversion": {"mapping": "[x,y,z] -> [x,z,y]", "presentation_scale": .1,
                                      "stored_coordinates": "unconverted authoritative source values"},
            "presentation_interpolation_default": False, "unity_physics_authoritative": False,
            "physics_transitions": 0, "neural_transitions": 0}


def export(source_dir: Path = SOURCE_DIR, output_dir: Path = OUTPUT_DIR) -> dict:
    if output_dir.exists(): raise FileExistsError(f"conflicting M9D output exists: {output_dir}")
    source = validate_source(source_dir); arrays = load_arrays(source_dir / "m9b_raw.npz")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".m9d.tmp-", dir=output_dir.parent))
    try:
        paths = []
        for condition in CONDITIONS:
            path = staging / FILES[condition]; path.write_bytes(serialize_condition(arrays, condition)); paths.append(path)
            replay = parse_replay(path.read_bytes())
            for field, _ in FIELDS:
                if not np.array_equal(replay[field], arrays[f"{condition}__{field}"]): raise EvidenceError("replay endpoint equality failure")
        (staging / "m9d_replay_manifest.json").write_text(
            json.dumps(build_manifest(paths, source["source_provenance"]), indent=2, sort_keys=True) + "\n")
        staging.rename(output_dir)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True); raise
    return json.loads((output_dir / "m9d_replay_manifest.json").read_text())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--export-windows", action="store_true", required=True)
    parser.parse_args(argv); export(); print("M9D EXPORT COMPLETE — PHYSICS TRANSITIONS = 0 — NEURAL TRANSITIONS = 0")
    return 0


if __name__ == "__main__": raise SystemExit(main())
