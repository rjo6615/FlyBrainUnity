"""Guarded executor contract for the frozen three-candidate observation.

Import, ``--help``, and ``--preflight`` never construct a neural or physics
runtime.  ``--diagnose-identity`` may construct runtimes but cannot advance
them, apply commands, write results, or classify a candidate.  The only
scientific execution boundary is the explicit ``--execute`` option; the
Windows adapter reuses the authoritative scientific transition kernel.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREREGISTRATION_PATH = HERE / "interface_output" / "candidate_motor_channel_future_preregistration.json"
PREREGISTRATION_SHA256 = "16cf491729aae39b8552a79b67993feef5661ee2240317d37c2d385e9e21893d"
OUTPUT_DIR = HERE / "interface_output" / "candidate_motor_channel_experiment"
OUTPUTS = ("execution_manifest.json", "candidate_motor_channel_raw.npz",
           "candidate_motor_channel_report.json", "final_manifest.json")
CANDIDATES = (("joint_RFFemur", 24, -1), ("joint_LFTarsus1", 6, -1),
              ("joint_RFTarsus1", 27, -1))
CONDITIONS = ("ENABLED", "ZEROED")
CURRENT_11_INDICES = (5, 12, 19, 26, 33, 40, 3, 10, 17, 31, 38)
DURATION_MS, SEED = 1000, 1
PHYSICS_DT_MS, NEURAL_DT_MS = 0.1, 0.5
INITIALIZATION_FIELDS = ("initial_qpos", "initial_qvel", "initial_ctrl", "malecns_state_digest",
                         "sensory_state", "decoder_state", "seed", "physics_model_identity",
                         "timestep_configuration")
CLASSIFICATIONS = ("SUPPORTED_AND_ACTIVE", "SUPPORTED_BUT_SILENT",
                   "DECODER_CANCELLATION", "SUPPORTED_LOW_ACTIVITY")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_array_identity(value: Any) -> dict[str, Any]:
    """Describe a numeric array without encoding its owning Python object."""
    import numpy as np

    array = np.asarray(value)
    # MuJoCo model scalars/arrays are native endian.  Normalizing byte order
    # makes an identity portable without changing any represented values.
    dtype = array.dtype.newbyteorder("<")
    canonical = np.ascontiguousarray(array.astype(dtype, copy=False))
    return {"dtype": dtype.str, "shape": list(canonical.shape),
            "sha256": sha256_bytes(canonical.tobytes(order="C"))}


def physics_model_identity(model: Any, data: Any) -> dict[str, Any]:
    """Return a deterministic identity for a compiled model and initial state.

    Only value-bearing numeric MuJoCo fields and compiled names are included.
    In particular, wrapper reprs, ``ptr``, object IDs, attachment-instance
    namespaces, paths, temporary filenames, and MuJoCo's derived ``names_map``
    name-lookup hash table never enter the identity.  Scientifically meaningful
    names and ordering are represented by the normalized inventories below.
    """
    import numpy as np
    from .m8_contact_kinematics import compiled_name, namespace_component

    dimensions = {}
    for name in dir(model):
        if name.startswith("n"):
            try:
                value = getattr(model, name)
            except (AttributeError, RuntimeError, TypeError, ValueError):
                continue
            if isinstance(value, (int, np.integer)):
                dimensions[name] = int(value)

    arrays = {}
    for name in dir(model):
        # The compiled name buffer and its byte offsets encode dm_control's
        # per-instance attachment prefix.  Names are represented separately
        # below after removing only that irrelevant namespace.
        if (name.startswith("_") or name == "ptr" or name in ("names", "names_map")
                or name.endswith("_nameadr")):
            continue
        try:
            value = getattr(model, name)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            continue
        if isinstance(value, np.ndarray) and value.dtype.kind in "biufc":
            arrays[name] = _canonical_array_identity(value)

    inventories = {}
    for kind, count_name in (("body", "nbody"), ("joint", "njnt"),
                             ("geom", "ngeom"), ("actuator", "nu"),
                             ("sensor", "nsensor"), ("site", "nsite")):
        count = int(getattr(model, count_name, 0))
        inventories[kind] = [namespace_component(compiled_name(model, kind, index))
                             for index in range(count)]

    option = getattr(model, "opt", None)
    options = {}
    if option is not None:
        for name in dir(option):
            if name.startswith("_"):
                continue
            try:
                value = getattr(option, name)
            except (AttributeError, RuntimeError, TypeError, ValueError):
                continue
            if isinstance(value, (bool, int, float, np.bool_, np.integer, np.floating)):
                options[name] = value.item() if isinstance(value, np.generic) else value
            elif isinstance(value, np.ndarray) and value.dtype.kind in "biufc":
                options[name] = _canonical_array_identity(value)

    state = {}
    for name in ("qpos", "qvel", "act", "ctrl"):
        if hasattr(data, name):
            state[name] = _canonical_array_identity(getattr(data, name))
    components = {"schema": "MUJOCO-SCIENTIFIC-PHYSICS-IDENTITY.1",
                  "dimensions": dimensions, "options": options,
                  "inventories": inventories, "model_arrays": arrays,
                  "initial_state": state}
    canonical = json.dumps(components, sort_keys=True, separators=(",", ":"),
                           allow_nan=False).encode()
    return {"schema": components["schema"], "sha256": sha256_bytes(canonical),
            "components": components}


def physics_model_diagnostic_snapshot(model: Any, data: Any) -> dict[str, Any]:
    """Capture values needed to explain an identity mismatch.

    This is deliberately separate from :func:`physics_model_identity`: it is
    diagnostic data, not a revised scientific identity.  Callers must keep it
    in memory and must not place it in a canonical experiment result.
    """
    import numpy as np
    from .m8_contact_kinematics import compiled_name, namespace_component

    dimensions, arrays = {}, {}
    for name in dir(model):
        try:
            value = getattr(model, name)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            continue
        if name.startswith("n") and isinstance(value, (int, np.integer)):
            dimensions[name] = int(value)
        if (not name.startswith("_") and name != "ptr" and name != "names"
                and not name.endswith("_nameadr") and isinstance(value, np.ndarray)
                and value.dtype.kind in "biufc"):
            arrays[name] = np.array(value, copy=True)
    inventories = {}
    for kind, count_name in (("body", "nbody"), ("joint", "njnt"),
                             ("geom", "ngeom"), ("actuator", "nu"),
                             ("sensor", "nsensor"), ("site", "nsite")):
        inventories[kind] = [namespace_component(compiled_name(model, kind, index))
                             for index in range(int(getattr(model, count_name, 0)))]
    options = {}
    option = getattr(model, "opt", None)
    if option is not None:
        for name in dir(option):
            if name.startswith("_"):
                continue
            try:
                value = getattr(option, name)
            except (AttributeError, RuntimeError, TypeError, ValueError):
                continue
            if isinstance(value, (bool, int, float, np.bool_, np.integer, np.floating)):
                options[name] = value.item() if isinstance(value, np.generic) else value
            elif isinstance(value, np.ndarray) and value.dtype.kind in "biufc":
                options[name] = np.array(value, copy=True)
    state = {name: np.array(getattr(data, name), copy=True)
             for name in ("qpos", "qvel", "act", "ctrl") if hasattr(data, name)}
    return {"dimensions": dimensions, "model_arrays": arrays, "options": options,
            "inventories": inventories, "initial_state": state,
            "aggregate_identity": physics_model_identity(model, data)}


def compare_physics_model_snapshots(left: Mapping[str, Any], right: Mapping[str, Any],
                                    sample_limit: int = 8) -> dict[str, Any]:
    """Return a JSON-safe, component-level, exact comparison of snapshots."""
    import numpy as np

    def scalar(value: Any) -> Any:
        value = value.item() if isinstance(value, np.generic) else value
        if isinstance(value, float) and not math.isfinite(value):
            return {"nonfinite": str(value)}
        if isinstance(value, complex):
            return {"real": scalar(value.real), "imag": scalar(value.imag)}
        return value

    def array_report(a: Any, b: Any) -> dict[str, Any]:
        a, b = np.asarray(a), np.asarray(b)
        ai, bi = _canonical_array_identity(a), _canonical_array_identity(b)
        report = {"enabled_dtype": ai["dtype"], "zeroed_dtype": bi["dtype"],
                  "enabled_shape": ai["shape"], "zeroed_shape": bi["shape"],
                  "enabled_sha256": ai["sha256"], "zeroed_sha256": bi["sha256"],
                  "bit_identical": bool(a.dtype == b.dtype and a.shape == b.shape
                                        and a.tobytes() == b.tobytes())}
        if a.dtype != b.dtype or a.shape != b.shape:
            report.update(differing_element_count=None, first_differences=[],
                          maximum_absolute_difference=None)
            return report
        item_bytes = max(1, a.dtype.itemsize)
        av = np.ascontiguousarray(a).view(np.uint8).reshape(-1, item_bytes)
        bv = np.ascontiguousarray(b).view(np.uint8).reshape(-1, item_bytes)
        differing = np.flatnonzero(np.any(av != bv, axis=1))
        samples = []
        flat_a, flat_b = a.reshape(-1), b.reshape(-1)
        for flat_index in differing[:sample_limit]:
            index = list(np.unravel_index(int(flat_index), a.shape))
            samples.append({"index": index, "enabled": scalar(flat_a[flat_index]),
                            "zeroed": scalar(flat_b[flat_index])})
        report["differing_element_count"] = int(differing.size)
        report["first_differences"] = samples
        try:
            finite = np.isfinite(a) & np.isfinite(b)
            report["maximum_absolute_difference"] = (float(np.max(np.abs(a[finite] - b[finite])))
                                                       if np.any(finite) else None)
        except (TypeError, ValueError, OverflowError):
            report["maximum_absolute_difference"] = None
        return report

    differing = []
    for section in ("model_arrays", "initial_state"):
        for name in sorted(set(left[section]) | set(right[section])):
            # Keep the raw lookup table in the recursive snapshot for audit,
            # but compare the same scientifically relevant components as the
            # aggregate identity.  This is the sole model-array exclusion.
            if section == "model_arrays" and name == "names_map":
                continue
            if name not in left[section] or name not in right[section]:
                differing.append({"component": f"{section}.{name}", "missing_from":
                                  "ENABLED" if name not in left[section] else "ZEROED"})
                continue
            detail = array_report(left[section][name], right[section][name])
            if not detail["bit_identical"]:
                differing.append({"component": f"{section}.{name}", **detail})
    for name in sorted(set(left["options"]) | set(right["options"])):
        if name not in left["options"] or name not in right["options"]:
            differing.append({"component": f"options.{name}", "missing_from":
                              "ENABLED" if name not in left["options"] else "ZEROED"})
        elif isinstance(left["options"][name], np.ndarray) or isinstance(right["options"][name], np.ndarray):
            detail = array_report(left["options"][name], right["options"][name])
            if not detail["bit_identical"]:
                differing.append({"component": f"options.{name}", **detail})
        elif left["options"][name] != right["options"][name]:
            differing.append({"component": f"options.{name}",
                              "enabled": scalar(left["options"][name]),
                              "zeroed": scalar(right["options"][name])})
    for section in ("dimensions", "inventories"):
        for name in sorted(set(left[section]) | set(right[section])):
            a, b = left[section].get(name), right[section].get(name)
            if a != b:
                row = {"component": f"{section}.{name}", "enabled": a, "zeroed": b}
                if section == "inventories" and isinstance(a, list) and isinstance(b, list):
                    row["differing_indices"] = [{"index": i,
                        "enabled": a[i] if i < len(a) else None,
                        "zeroed": b[i] if i < len(b) else None}
                        for i in range(max(len(a), len(b)))
                        if i >= len(a) or i >= len(b) or a[i] != b[i]]
                differing.append(row)
    left_sha = left["aggregate_identity"]["sha256"]
    right_sha = right["aggregate_identity"]["sha256"]
    return {"identical": not differing and left_sha == right_sha,
            "enabled_aggregate_sha256": left_sha, "zeroed_aggregate_sha256": right_sha,
            "aggregate_sha_identical": left_sha == right_sha, "differences": differing}


def diagnostic_json_value(value: Any) -> Any:
    """Recursively copy a diagnostic value into JSON-native containers/scalars."""
    import numpy as np

    if isinstance(value, np.ndarray):
        return diagnostic_json_value(value.tolist())
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, dict):
        return {key: diagnostic_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [diagnostic_json_value(item) for item in value]
    return value


def verify_preregistration_bytes(raw: bytes, expected_sha256: str = PREREGISTRATION_SHA256) -> str:
    actual = sha256_bytes(raw)
    if actual != expected_sha256:
        raise RuntimeError(f"fail closed: preregistration SHA-256 mismatch: {actual}")
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("fail closed: preregistration is not valid JSON") from exc
    if value.get("status") != "NOT_RUN":
        raise RuntimeError("fail closed: preregistration status is not NOT_RUN")
    if (value.get("duration_ms"), value.get("seed"), tuple(value.get("conditions", ()))) != (
            DURATION_MS, SEED, CONDITIONS):
        raise RuntimeError("fail closed: frozen duration, seed, or conditions differ")
    frozen = tuple((row.get("joint"), row.get("action_index"), row.get("coordinate_sign"))
                   for row in value.get("candidates", ()))
    if frozen != CANDIDATES:
        raise RuntimeError("fail closed: frozen candidate inventory differs")
    return actual


def verify_preregistration(path: Path = PREREGISTRATION_PATH) -> str:
    path = Path(path)
    if not path.is_file():
        raise RuntimeError("fail closed: preregistration is absent")
    return verify_preregistration_bytes(path.read_bytes())


def authorize_contribution(action_index: int, contribution: float,
                           condition: str) -> tuple[tuple[float, ...], float, float]:
    """Apply the sole intervention and return the complete physical vector."""
    if action_index not in {row[1] for row in CANDIDATES} or condition not in CONDITIONS:
        raise ValueError("exact candidate and condition required")
    before = float(contribution)
    if not math.isfinite(before):
        raise ValueError("candidate contribution must be finite")
    after = before if condition == "ENABLED" else 0.0
    vector = [0.0] * 42
    vector[action_index] = after
    nonzero = tuple(index for index, value in enumerate(vector) if value != 0.0)
    if nonzero not in ((), (action_index,)) or any(vector[index] != 0.0 for index in CURRENT_11_INDICES):
        raise RuntimeError("unauthorized neural motor contribution")
    return tuple(vector), before, after


def require_matched_initialization(enabled: Mapping[str, Any], zeroed: Mapping[str, Any]) -> bool:
    for field in INITIALIZATION_FIELDS:
        if field not in enabled or field not in zeroed:
            raise RuntimeError(f"matched initialization field absent: {field}")
        left = json.dumps(enabled[field], sort_keys=True, separators=(",", ":"), default=str)
        right = json.dumps(zeroed[field], sort_keys=True, separators=(",", ":"), default=str)
        if left != right:
            raise RuntimeError(f"matched initialization differs: {field}")
    return True


def transition_counts(duration_ms: float, physics_dt_ms: float,
                      neural_dt_ms: float) -> tuple[int, int]:
    if duration_ms != DURATION_MS or physics_dt_ms != PHYSICS_DT_MS or neural_dt_ms != NEURAL_DT_MS:
        raise ValueError("only the frozen 1000-ms timestep configuration is permitted")
    physics = int(round(duration_ms / physics_dt_ms))
    neural = int(round(duration_ms / neural_dt_ms))
    if (physics, neural) != (10000, 2000):
        raise RuntimeError("frozen transition accounting mismatch")
    return physics, neural


def require_new_output_directory(path: Path = OUTPUT_DIR) -> Path:
    path = Path(path).resolve()
    prereg = PREREGISTRATION_PATH.resolve()
    if path == prereg or prereg in path.parents or path in prereg.parents:
        raise ValueError("output path may not overlap the preregistration")
    if path.exists() and any(path.iterdir()):
        raise FileExistsError("experiment output directory is occupied; overwrite forbidden")
    return path


def next_attempt_directory(path: Path = OUTPUT_DIR) -> tuple[Path, int, list[dict[str, Any]]]:
    """Select a fresh attempt without touching legacy aborted-start evidence."""
    root = Path(path).resolve()
    prereg = PREREGISTRATION_PATH.resolve()
    if root == prereg or prereg in root.parents or root in prereg.parents:
        raise ValueError("output path may not overlap the preregistration")
    prior: list[dict[str, Any]] = []
    occupied_legacy = root.is_dir() and any(
        child.name in OUTPUTS for child in root.iterdir() if child.is_file())
    if occupied_legacy:
        manifest = root / OUTPUTS[0]
        status = "ABORTED_INFRASTRUCTURE_ERROR"
        if manifest.is_file():
            try:
                recorded = json.loads(manifest.read_bytes()).get("status")
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                recorded = None
            if recorded not in (None, "STARTED"):
                status = str(recorded)
        prior.append({"attempt": 1, "directory": ".", "status": status,
                      "reason": "legacy-layout attempt; STARTED without final_manifest is aborted"})
    attempt = 2 if occupied_legacy else 1
    while (root / f"attempt_{attempt:03d}").exists():
        prior.append({"attempt": attempt, "directory": f"attempt_{attempt:03d}",
                      "status": "OCCUPIED_IMMUTABLE"})
        attempt += 1
    return root / f"attempt_{attempt:03d}", attempt, prior


def classify(metrics: Mapping[str, float]) -> str:
    """Apply exact, predeclared activity rules without a movement threshold."""
    spikes = int(metrics["total_spike_increments"])
    rate = float(metrics["peak_filtered_rate_hz"])
    contribution = float(metrics["peak_absolute_contribution"])
    antagonist = float(metrics["peak_absolute_raw_antagonist_signal"])
    positive = float(metrics["positive_peak_hz"])
    negative = float(metrics["negative_peak_hz"])
    if contribution != 0.0:
        return "SUPPORTED_AND_ACTIVE"
    if spikes == 0 and rate == 0.0 and antagonist == 0.0:
        return "SUPPORTED_BUT_SILENT"
    if (spikes > 0 or rate > 0.0) and positive > 0.0 and negative > 0.0 and antagonist == 0.0:
        return "DECODER_CANCELLATION"
    return "SUPPORTED_LOW_ACTIVITY"


def preflight(output_dir: Path = OUTPUT_DIR) -> dict[str, Any]:
    digest = verify_preregistration()
    destination, attempt, prior = next_attempt_directory(output_dir)
    physics, neural = transition_counts(DURATION_MS, PHYSICS_DT_MS, NEURAL_DT_MS)
    return {"status": "PREFLIGHT_PASS", "preregistration_sha256": digest,
            "scientific_conditions_executed": 0, "runtime_constructed": False,
            "output_directory": str(destination), "attempt": attempt, "prior_attempts": prior,
            "physics_transitions_per_condition": physics,
            "neural_transitions_per_condition": neural, "condition_count": 6}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--diagnose-identity", action="store_true")
    mode.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if args.preflight:
        result = preflight()
    elif args.diagnose_identity:
        from . import _windows_candidate_motor_channel_experiment_adapter as adapter
        result = diagnostic_json_value(adapter.diagnose_identity())
    else:
        from . import _windows_candidate_motor_channel_experiment_adapter as adapter
        result = adapter.execute()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
