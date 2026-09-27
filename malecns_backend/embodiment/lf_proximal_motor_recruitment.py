"""Fail-closed runner for the frozen LF proximal recruitment assay.

Importing this module performs no I/O and constructs no neural runtime.  The
ordinary CLI is also inert: provenance checking and scientific execution each
require a distinct explicit flag.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

import numpy as np

from .motor import MotorActivityObserver
from .sensory import LegSensoryFrame, SensoryEncoder
from .six_tibia import LEG_ORDER, load_six_tibia_interfaces

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SPEC_DIR = HERE / "interface_output/lf_proximal_motor_recruitment"
REPLAY_DIR = HERE / "interface_output/lf_proximal_motor_recruitment_sensory_replay"

PREREGISTRATION = SPEC_DIR / "lf_proximal_motor_recruitment_preregistration.json"
CLARIFICATION = SPEC_DIR / "lf_proximal_motor_recruitment_crn_clarification.json"
ADDENDUM = SPEC_DIR / "lf_proximal_motor_recruitment_pre_extraction_addendum.json"
REPLAY = REPLAY_DIR / "lf_proximal_motor_recruitment_sensory_replay.npy"
MANIFEST = REPLAY_DIR / "lf_proximal_motor_recruitment_sensory_replay_manifest.json"
EXTRACTION_REPORT = REPLAY_DIR / "LF_PROXIMAL_MOTOR_RECRUITMENT_SENSORY_REPLAY_REPORT.md"

EXPECTED = {
    "preregistration": "994789847840cc53287b1bcbfff34e86fdc880f7b4d00c7cbc00f54f68ed812c",
    "clarification": "3c5cc199480903f3942ca476b808e19533ab1a0397dba88429102e598cabf057",
    "addendum": "2dbfff3e8db3ea26a57a028dc0b50b24d186cedfb51f95e4fcc5fbde319b1588",
    "replay": "0515c8df205b613c84d2d727fec3cdd1914aa44b66ff0db35b37431f71cf131b",
    "manifest": "21dc70c74e10f913cad20d15f6fc48e0695df945ab6b612c1ddaacf60bde26f3",
    "report": "b9d931dcad1ccd533dcdae5864b545c313eaeb6e70fc183d0619ef86ae206c1a",
    "source_m8": "4e39bb83dd4455d56a4d88f717615530602317efaf83a6ed241b13af89dc2a5b",
}
# These identities were frozen from Git's canonical LF blob bytes.  A checkout
# may represent each LF as CRLF, but no other byte transformation is allowed.
CANONICAL_LF_ARTIFACTS = frozenset({"preregistration", "clarification", "addendum"})
CHANNELS = ("joint_LFTibia", "joint_LMTibia", "joint_LHTibia",
            "joint_RFTibia", "joint_RMTibia", "joint_RHTibia")
CONDITIONS = ("CONTROL_REPLAY", "LF_MIN_BOUND", "LF_MAX_BOUND")
SEEDS = (1, 2, 3)


class RecruitmentFailure(RuntimeError):
    """Fail-closed protocol or implementation error."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_lf_sha256(path: Path) -> str:
    """Hash canonical Git text bytes, tolerating only checkout CRLF expansion."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _verified_identity(path: Path, expected: str, *, canonical_lf: bool) -> str:
    """Return the frozen identity after applying the artifact's declared policy."""
    actual = canonical_lf_sha256(path) if canonical_lf else sha256_file(path)
    _require(actual == expected, "SHA-256 mismatch")
    return actual


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RecruitmentFailure(message)


def provenance_gate(*, preregistration=PREREGISTRATION, clarification=CLARIFICATION,
                    addendum=ADDENDUM, replay=REPLAY, manifest=MANIFEST,
                    report=EXTRACTION_REPORT) -> tuple[np.ndarray, dict[str, Any]]:
    """Validate every frozen input before a brain factory may be called."""
    paths = {"preregistration": Path(preregistration), "clarification": Path(clarification),
             "addendum": Path(addendum), "replay": Path(replay),
             "manifest": Path(manifest), "report": Path(report)}
    identities: dict[str, str] = {}
    for name, path in paths.items():
        try:
            identities[name] = _verified_identity(
                path, EXPECTED[name], canonical_lf=name in CANONICAL_LF_ARTIFACTS)
        except OSError as exc:
            raise RecruitmentFailure(f"cannot read required {name}: {exc}") from exc
        except RecruitmentFailure as exc:
            raise RecruitmentFailure(f"{name} {exc}") from exc

    # Verify every unchanged dependency frozen by the parent protocol.  The
    # sole exception is neural.py: its old identity is necessarily superseded
    # by the prospectively authorized CRN implementation in this change.
    try:
        prereg_data = json.loads(paths["preregistration"].read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RecruitmentFailure(f"invalid preregistration: {exc}") from exc
    for dependency in prereg_data.get("frozen_evidence_dependencies", []):
        relative = dependency.get("path")
        if relative == "malecns_backend/neural.py":
            continue
        _require(isinstance(relative, str) and isinstance(dependency.get("sha256"), str),
                 "invalid frozen dependency record")
        dependency_path = REPO / relative
        try:
            # Every dependency named by this frozen preregistration is a
            # Git-tracked text/source artifact whose recorded digest is its
            # canonical repository LF identity.
            actual = canonical_lf_sha256(dependency_path)
        except OSError as exc:
            raise RecruitmentFailure(f"cannot read frozen dependency {relative}: {exc}") from exc
        _require(actual == dependency["sha256"], f"frozen dependency mismatch: {relative}")

    try:
        manifest_data = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RecruitmentFailure(f"invalid replay manifest: {exc}") from exc
    required_manifest = {
        "schema": "LF-PROXIMAL-MOTOR-RECRUITMENT-SENSORY-REPLAY.1",
        "condition": "CORRECTED_SPONTANEOUS_NEURAL_EMBODIMENT",
        "field": "physics_joint_position", "rows": list(range(0, 10_000, 10)),
        "columns": [5, 12, 19, 26, 33, 40], "channel_names_order": list(CHANNELS),
        "units": "radians", "interval_ms": {"start_inclusive": 0, "stop_exclusive": 1000},
        "replay_cadence_ms": 1, "sample_count": 1000, "shape": [1000, 6],
        "dtype": "float64",
        "exact_copy_policy": "direct NumPy advanced indexing only; no numerical transformation",
        "addendum_canonical_lf_sha256": EXPECTED["addendum"],
    }
    for key, expected in required_manifest.items():
        _require(manifest_data.get(key) == expected, f"manifest {key} mismatch")
    source = manifest_data.get("source", {})
    _require(source.get("sha256") == EXPECTED["source_m8"], "manifest source-M8 mismatch")
    _require(source.get("size") == 345_584_215, "manifest source-M8 size mismatch")
    replay_record = manifest_data.get("replay", {})
    _require(replay_record.get("sha256") == EXPECTED["replay"], "manifest replay identity mismatch")
    validation = manifest_data.get("validation_provenance", {})
    _require(validation.get("final_status") == "READY_FOR_AUTHORIZED_REPLAY_EXTRACTION",
             "manifest extraction validation was not ready")
    _require(manifest_data.get("maximum_nominal_timestamp_deviation_ms") == 0.0,
             "manifest timestamps are not exact 1-ms samples")
    nominal = manifest_data.get("nominal_timestamps_ms")
    _require(nominal == [float(i) for i in range(1000)], "manifest timestamp sequence mismatch")
    actual = manifest_data.get("actual_source_timestamps_ms", {})
    _require(actual == {"first": 0.0, "last": 999.0}, "manifest source timestamp bounds mismatch")

    try:
        with paths["replay"].open("rb") as stream:
            values = np.load(stream, allow_pickle=False)
    except Exception as exc:
        raise RecruitmentFailure(f"cannot load frozen replay: {exc}") from exc
    _require(values.shape == (1000, 6), "replay shape mismatch")
    _require(values.dtype == np.dtype("float64"), "replay dtype mismatch")
    _require(bool(np.isfinite(values).all()), "replay contains nonfinite values")
    return values, {"sha256": identities, "manifest": manifest_data}


def frozen_sensory_indices(interfaces) -> np.ndarray:
    indices = np.asarray(sorted(i for leg in LEG_ORDER
                                for i in interfaces[leg].sensor.dense_indices), dtype=np.intp)
    _require(len(indices) == 392 and len(np.unique(indices)) == 392,
             "frozen sensory union is not exactly 392 unique neurons")
    _require(bool(np.all(indices[1:] > indices[:-1])), "sensory indices are not increasing")
    return indices


def _digest(value: Any) -> str:
    digest = hashlib.sha256()
    if isinstance(value, np.ndarray):
        digest.update(value.dtype.str.encode()); digest.update(str(value.shape).encode())
        digest.update(value.tobytes(order="C"))
    else:
        digest.update(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                 default=lambda x: x.tolist() if isinstance(x, np.ndarray) else str(x)).encode())
    return digest.hexdigest()


STATE_FIELDS = (
    "v", "g_exc", "g_inh", "refractory", "activity_trace", "adaptation",
    "depression_resource", "bias", "threshold_offset", "spike_counts", "_ring",
    "_head", "time_ms", "_last_spikes", "external_drive_withheld_indices",
    "_last_external_candidates", "_last_external_delivered",
    "_withheld_external_refractory", "external_drive", "transmission_withheld_indices",
    "_last_transmission_withheld", "_external_rng_schedule_indices",
    "_external_rng_expected_state", "_external_rng_step_draws",
    "_last_external_rng_indices", "_last_external_rng_uniforms",
)


def clone_branch(brain, observer: MotorActivityObserver):
    """Copy all frozen mutable brain and observer state; share immutable topology."""
    branch = copy.copy(brain)
    for name in STATE_FIELDS:
        _require(hasattr(brain, name), f"required branch state missing: {name}")
        setattr(branch, name, copy.deepcopy(getattr(brain, name)))
    branch.rng = np.random.Generator(np.random.PCG64())
    branch.rng.bit_generator.state = copy.deepcopy(brain.rng.bit_generator.state)
    # The assay does not attach an event observer; candidate observation is
    # explicit and copied separately at the exact control-sample boundary.
    branch.diagnostic_observer = None
    return branch, copy.deepcopy(observer)


def branch_state_digests(brain, observer, sensory_history: np.ndarray) -> dict[str, str]:
    values = {name: _digest(getattr(brain, name)) for name in STATE_FIELDS}
    values["rng"] = _digest(brain.rng.bit_generator.state)
    values["observer_last_counts"] = _digest(observer.last_counts)
    values["observer_filtered_hz"] = _digest(observer.filtered_hz)
    values["sensory_history"] = _digest(sensory_history)
    return values


def require_identical_branches(branches, sensory_history: np.ndarray) -> dict[str, str]:
    digests = {name: branch_state_digests(*pair, sensory_history)
               for name, pair in branches.items()}
    reference = digests[CONDITIONS[0]]
    _require(all(value == reference for value in digests.values()),
             "pre-intervention branch state mismatch invalidates seed triplet")
    return reference


def _candidate_populations(prereg: dict[str, Any]) -> dict[str, np.ndarray]:
    return {record["name"]: np.asarray(record["dense_neural_indices"], dtype=np.intp)
            for record in prereg["candidate_populations"]}


def _apply_sample(brain, encoders, interfaces, row, time_ms):
    brain.clear_external_drive()
    encoded = {}
    for column, leg in enumerate(LEG_ORDER):
        drive = encoders[leg].encode(LegSensoryFrame(time_ms / 1000.0, float(row[column])))
        _require(tuple(drive.indices) == tuple(interfaces[leg].sensor.dense_indices),
                 "encoder dense-index mapping changed")
        brain.set_external_drive(drive.indices, drive.rates_hz)
        encoded[leg] = drive
    return encoded


def _rng_digest(brain) -> str:
    return _digest(brain.rng.bit_generator.state)


def execute_assay(replay: np.ndarray, provenance: dict[str, Any], *, brain_factory=None,
                  data_loader=None) -> dict[str, Any]:
    """Execute only after ``provenance_gate`` has returned validated bytes."""
    from malecns_backend import MaleCNSBrain, load_malecns
    brain_factory = brain_factory or MaleCNSBrain
    data_loader = data_loader or load_malecns
    prereg = json.loads(PREREGISTRATION.read_text(encoding="utf-8"))
    interfaces = load_six_tibia_interfaces()
    schedule = frozen_sensory_indices(interfaces)
    populations = _candidate_populations(prereg)
    candidate_indices = np.concatenate(tuple(populations.values()))
    _require(not np.intersect1d(candidate_indices, schedule).size,
             "candidate neuron is directly externally driven")
    data = data_loader()
    all_seed_results = []
    for seed in SEEDS:
        brain = brain_factory(data)
        brain.reset(seed)
        brain.configure_external_rng_schedule(schedule)
        encoders = {leg: SensoryEncoder(interfaces[leg]) for leg in LEG_ORDER}
        observer = MotorActivityObserver(populations)
        observer.reset(brain.spike_counts)
        initial_counts = brain.spike_counts[candidate_indices].copy()
        prefix_events = []
        for sample in range(250):
            _apply_sample(brain, encoders, interfaces, replay[sample], sample)
            for _ in range(2):
                fired = brain.step()
                prefix_events.extend((brain.time_ms, int(i)) for i in fired if i in candidate_indices)
            observer.update(brain.spike_counts, 1.0)
        _require(brain.time_ms == 250.0, "branch did not occur exactly at 250.0 ms")
        branches = {condition: clone_branch(brain, observer) for condition in CONDITIONS}
        pre_digests = require_identical_branches(branches, replay[:250])
        start_counts = {condition: branches[condition][0].spike_counts[candidate_indices].copy()
                        for condition in CONDITIONS}
        intervention_end_counts = {}
        events = {condition: list(prefix_events) for condition in CONDITIONS}
        observations = {condition: [] for condition in CONDITIONS}
        rng_trace = {condition: [] for condition in CONDITIONS}
        for sample in range(250, 1000):
            for condition, (branch, branch_observer) in branches.items():
                row = replay[sample].copy()
                if sample < 750:
                    if condition == "LF_MIN_BOUND": row[0] = -1.35
                    elif condition == "LF_MAX_BOUND": row[0] = 1.30
                _apply_sample(branch, encoders, interfaces, row, sample)
                for _ in range(2):
                    fired = branch.step()
                    _require(branch._external_rng_step_draws == 392, "CRN draw-count invariant failed")
                    _require(np.array_equal(branch._last_external_rng_indices, schedule),
                             "CRN slot mapping invariant failed")
                    events[condition].extend((branch.time_ms, int(i)) for i in fired
                                             if i in candidate_indices)
                    rng_trace[condition].append((_rng_digest(branch),
                                                  _digest(branch._last_external_rng_uniforms)))
                observations[condition].append(branch_observer.update(branch.spike_counts, 1.0))
            reference = rng_trace[CONDITIONS[0]][-2:]
            _require(all(rng_trace[c][-2:] == reference for c in CONDITIONS),
                     "corresponding branch RNG state or neuron variates diverged")
            if sample == 749:
                intervention_end_counts = {
                    condition: pair[0].spike_counts[candidate_indices].copy()
                    for condition, pair in branches.items()
                }
        condition_results = {}
        for condition, (branch, _) in branches.items():
            final = branch.spike_counts[candidate_indices]
            baseline = (start_counts[condition] - initial_counts).astype(np.uint32)
            intervention = (intervention_end_counts[condition] -
                            start_counts[condition]).astype(np.uint32)
            post = (final - intervention_end_counts[condition]).astype(np.uint32)
            population_windows = {}
            offset = 0
            for name, indices in populations.items():
                width = len(indices)
                population_windows[name] = {
                    "baseline_increments": [int(x) for x in baseline[offset:offset + width]],
                    "intervention_increments": [int(x) for x in intervention[offset:offset + width]],
                    "post_intervention_increments": [int(x) for x in post[offset:offset + width]],
                }
                offset += width
            condition_results[condition] = {
                "population_windows": population_windows,
                "candidate_events": events[condition],
                "observer_samples": observations[condition],
                "final_rng_digest": _rng_digest(branch),
            }
        all_seed_results.append({"seed": seed, "branch_time_ms": 250.0,
                                 "pre_intervention_state_digests": pre_digests,
                                 "conditions": condition_results})
    # Apply the frozen replicated-count decision rule, without adding any
    # outcome-dependent criterion.  The event/count cross-check is exact here
    # because both records came from the same per-step transition log.
    decisions = {}
    for population in populations:
        decisions[population] = {}
        for perturbation in CONDITIONS[1:]:
            responses = []
            crosschecks = []
            for seed_result in all_seed_results:
                conditions = seed_result["conditions"]
                tested = conditions[perturbation]["population_windows"][population]["intervention_increments"]
                control = conditions["CONTROL_REPLAY"]["population_windows"][population]["intervention_increments"]
                responses.append(sum(tested) >= 2 and sum(tested) >= sum(control) + 1 and
                                 (len(tested) == 1 or any(tested)))
                ids = set(map(int, populations[population]))
                timed = sum(250.0 < time <= 750.0 and neuron in ids
                            for time, neuron in conditions[perturbation]["candidate_events"])
                crosschecks.append(timed == sum(tested))
            positives = sum(responses)
            label = ("RECRUITED_UNDER_TEST_CONDITION" if positives >= 2 and
                     any(ok for ok, response in zip(crosschecks, responses) if response) else
                     "NOT_RECRUITED_UNDER_TEST_CONDITION" if positives <= 1 and all(crosschecks) else
                     "INCONCLUSIVE")
            decisions[population][perturbation] = {"label": label,
                                                    "per_seed_response": responses,
                                                    "event_count_crosscheck": crosschecks}
    return {"schema": "LF-PROXIMAL-MOTOR-RECRUITMENT-RESULT.1", "seeds": list(SEEDS),
            "conditions": list(CONDITIONS), "provenance": provenance,
            "seed_results": all_seed_results, "decisions": decisions}


def check_ready(**paths) -> dict[str, Any]:
    replay, provenance = provenance_gate(**paths)
    interfaces = load_six_tibia_interfaces()
    indices = frozen_sensory_indices(interfaces)
    return {"status": "READY_FOR_SCIENTIFIC_EXECUTION", "replay_shape": list(replay.shape),
            "replay_dtype": str(replay.dtype), "sensory_rng_slots": len(indices),
            "provenance_sha256": provenance["sha256"], "neural_runtime_steps": 0}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--check-ready", action="store_true",
                         help="validate provenance/readiness without creating a brain")
    actions.add_argument("--execute", action="store_true",
                         help="explicitly execute the frozen scientific assay")
    parser.add_argument("--replay-dir", type=Path, default=REPLAY_DIR)
    parser.add_argument("--output", type=Path, help="new result JSON (required with --execute)")
    args = parser.parse_args(argv)
    if not args.check_ready and not args.execute:
        parser.print_usage()
        print("No action selected; zero scientific steps executed.")
        return 0
    paths = {"replay": args.replay_dir / REPLAY.name,
             "manifest": args.replay_dir / MANIFEST.name,
             "report": args.replay_dir / EXTRACTION_REPORT.name}
    try:
        if args.check_ready:
            result = check_ready(**paths)
        else:
            replay, provenance = provenance_gate(**paths)
            _require(args.output is not None, "--output is required with --execute")
            _require(not args.output.exists(), "refusing to overwrite a scientific result")
            result = execute_assay(replay, provenance)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    except (RecruitmentFailure, OSError, ValueError) as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
