"""Fail-closed runner for the frozen post-outcome LF propagation-localization assay.

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
SPEC_DIR = HERE / "interface_output/lf_proximal_propagation_localization"
PARENT_SPEC_DIR = HERE / "interface_output/lf_proximal_motor_recruitment"
REPLAY_DIR = HERE / "interface_output/lf_proximal_motor_recruitment_sensory_replay"

PREREGISTRATION = SPEC_DIR / "lf_proximal_propagation_localization_preregistration.json"
ANALYSIS_CLARIFICATION = SPEC_DIR / "lf_proximal_propagation_localization_analysis_clarification.json"
PARENT_PREREGISTRATION = PARENT_SPEC_DIR / "lf_proximal_motor_recruitment_preregistration.json"
PARENT_RESULT = PARENT_SPEC_DIR / "lf_proximal_motor_recruitment_result.json"
CLARIFICATION = PARENT_SPEC_DIR / "lf_proximal_motor_recruitment_crn_clarification.json"
ADDENDUM = PARENT_SPEC_DIR / "lf_proximal_motor_recruitment_pre_extraction_addendum.json"
REPLAY = REPLAY_DIR / "lf_proximal_motor_recruitment_sensory_replay.npy"
MANIFEST = REPLAY_DIR / "lf_proximal_motor_recruitment_sensory_replay_manifest.json"
EXTRACTION_REPORT = REPLAY_DIR / "LF_PROXIMAL_MOTOR_RECRUITMENT_SENSORY_REPLAY_REPORT.md"
EXECUTION_AUTHORIZATION = SPEC_DIR / "lf_proximal_propagation_localization_execution_authorization.json"

EXPECTED = {
    "preregistration": "5fe860393c5a7ad974b9ca38afefd5ec8970335ffdf9d0cdff902d74fd853fb0",
    "analysis_clarification": "e5b367779a58a53c0dda654b8ba4d63ad3e61942e911e7c506b0ebca8ffe112b",
    "parent_preregistration": "994789847840cc53287b1bcbfff34e86fdc880f7b4d00c7cbc00f54f68ed812c",
    "parent_result": "33165b89c117b6ca2ee9852cf7c64e2da879f2484cdb05fb3db2fa32978e4401",
    "clarification": "3c5cc199480903f3942ca476b808e19533ab1a0397dba88429102e598cabf057",
    "addendum": "2dbfff3e8db3ea26a57a028dc0b50b24d186cedfb51f95e4fcc5fbde319b1588",
    "replay": "0515c8df205b613c84d2d727fec3cdd1914aa44b66ff0db35b37431f71cf131b",
    "manifest": "21dc70c74e10f913cad20d15f6fc48e0695df945ab6b612c1ddaacf60bde26f3",
    "report": "b9d931dcad1ccd533dcdae5864b545c313eaeb6e70fc183d0619ef86ae206c1a",
    "source_m8": "4e39bb83dd4455d56a4d88f717615530602317efaf83a6ed241b13af89dc2a5b",
    "execution_authorization": "3ae8c97725474b03d3b607dd6e10cd359145f8270d83a46fc706617beadd8475",
}
# These identities were frozen from Git's canonical LF blob bytes.  A checkout
# may represent each LF as CRLF, but no other byte transformation is allowed.
CANONICAL_LF_ARTIFACTS = frozenset({"preregistration", "analysis_clarification", "parent_preregistration", "parent_result", "clarification", "addendum"})
CHANNELS = ("joint_LFTibia", "joint_LMTibia", "joint_LHTibia",
            "joint_RFTibia", "joint_RMTibia", "joint_RHTibia")
CONDITIONS = ("CONTROL_REPLAY", "LF_MIN_BOUND", "LF_MAX_BOUND")
SEEDS = (1, 2, 3)
FROZEN_ACTUAL_SOURCE_TIMESTAMPS_MS = {
    "first": 0.0,
    "last": 998.9999999999063,
}
FROZEN_MAXIMUM_NOMINAL_TIMESTAMP_DEVIATION_MS = 9.367795428261161e-11


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


def execution_authorization_gate(
    authorization=EXECUTION_AUTHORIZATION,
) -> dict[str, Any]:
    """Validate the separately frozen authorization before scientific execution."""
    path = Path(authorization)

    try:
        identity = sha256_file(path)
    except OSError as exc:
        raise RecruitmentFailure(
            f"cannot read execution authorization: {exc}"
        ) from exc

    _require(
        identity == EXPECTED["execution_authorization"],
        "execution authorization SHA-256 mismatch",
    )

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RecruitmentFailure(
            f"invalid execution authorization: {exc}"
        ) from exc

    _require(
        data.get("schema")
        == "LF-PROXIMAL-PROPAGATION-LOCALIZATION-EXECUTION-AUTHORIZATION.1",
        "execution authorization schema mismatch",
    )
    _require(
        data.get("status") == "SCIENTIFIC_EXECUTION_AUTHORIZED",
        "scientific execution is not authorized",
    )
    _require(
        data.get("experiment")
        == "lf_proximal_propagation_localization",
        "execution authorization experiment mismatch",
    )

    frozen_chain = data.get("frozen_chain", {})

    followup = frozen_chain.get("followup_preregistration", {})
    _require(
        followup.get("git_commit")
        == "a73ee120ff856ff9586865c435a1d88f9a5a08ed",
        "execution authorization follow-up commit mismatch",
    )
    _require(
        followup.get("canonical_lf_sha256")
        == EXPECTED["preregistration"],
        "execution authorization follow-up identity mismatch",
    )

    analysis = frozen_chain.get("analysis_clarification", {})
    _require(
        analysis.get("git_commit")
        == "741580316f0285290a657511ac254638df6568f7",
        "execution authorization analysis-clarification commit mismatch",
    )
    _require(
        analysis.get("canonical_lf_sha256")
        == EXPECTED["analysis_clarification"],
        "execution authorization analysis-clarification identity mismatch",
    )

    implementation = frozen_chain.get("scientific_implementation", {})
    _require(
        implementation.get("git_commit")
        == "b8f1a2452c311147e797752a74620f3d4b495374",
        "execution authorization implementation commit mismatch",
    )
    _require(
        implementation.get("git_tree")
        == "10b376ec72437a518189413ae650727cd0dcf65d",
        "execution authorization implementation tree mismatch",
    )

    validation = data.get("validation", {})
    _require(
        validation.get("passed") == 60,
        "execution authorization validation pass count mismatch",
    )
    _require(
        validation.get("failed") == 0,
        "execution authorization validation failure count mismatch",
    )
    _require(
        validation.get("result") == "PASS",
        "execution authorization validation result mismatch",
    )

    scope = data.get("execution_scope", {})
    _require(
        scope.get("scientific_execution_authorized") is True,
        "scientific execution is not authorized",
    )
    _require(
        scope.get("authorization_count") == 1,
        "execution authorization count mismatch",
    )

    for field in (
        "protocol_changes_authorized",
        "endpoint_changes_authorized",
        "population_changes_authorized",
        "intervention_changes_authorized",
    ):
        _require(
            scope.get(field) is False,
            f"execution authorization unexpectedly permits {field}",
        )

    runtime = data.get("runtime_state_at_authorization", {})
    for field in (
        "simulation_steps",
        "physics_steps",
        "neural_steps",
    ):
        _require(
            runtime.get(field) == 0,
            f"authorization runtime state is not zero for {field}",
        )

    _require(
        runtime.get("experiment_2_result_observed") is False,
        "execution authorization was created after observing Experiment 2",
    )

    return {
        "identity": identity,
        "authorization": data,
    }

def provenance_gate(*, preregistration=PREREGISTRATION,
                    parent_preregistration=PARENT_PREREGISTRATION,
                    parent_result=PARENT_RESULT,
                    clarification=CLARIFICATION, addendum=ADDENDUM,
                    analysis_clarification=ANALYSIS_CLARIFICATION,
                    replay=REPLAY, manifest=MANIFEST,
                    report=EXTRACTION_REPORT) -> tuple[np.ndarray, dict[str, Any]]:
    """Validate follow-up chronology and every inherited frozen input."""
    paths = {
        "preregistration": Path(preregistration),
        "parent_preregistration": Path(parent_preregistration),
        "parent_result": Path(parent_result),
        "clarification": Path(clarification),
        "addendum": Path(addendum),
        "analysis_clarification": Path(analysis_clarification),
        "replay": Path(replay),
        "manifest": Path(manifest),
        "report": Path(report),
    }

    identities: dict[str, str] = {}
    for name, path in paths.items():
        try:
            identities[name] = _verified_identity(
                path,
                EXPECTED[name],
                canonical_lf=name in CANONICAL_LF_ARTIFACTS,
            )
        except OSError as exc:
            raise RecruitmentFailure(f"cannot read required {name}: {exc}") from exc
        except RecruitmentFailure as exc:
            raise RecruitmentFailure(f"{name} {exc}") from exc

    # Validate the post-outcome follow-up preregistration itself.  These checks
    # bind this runner to the frozen Experiment 2 design and prove that this
    # preregistration did not itself authorize scientific execution.
    try:
        followup_data = json.loads(
            paths["preregistration"].read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RecruitmentFailure(f"invalid follow-up preregistration: {exc}") from exc

    _require(
        followup_data.get("schema")
        == "LF-PROXIMAL-PROPAGATION-LOCALIZATION-PREREGISTRATION.1",
        "follow-up preregistration schema mismatch",
    )
    _require(
        followup_data.get("status")
        == "POST_OUTCOME_FROZEN_BEFORE_IMPLEMENTATION_OR_EXECUTION",
        "follow-up preregistration status mismatch",
    )

    chronology = followup_data.get("chronology", {})
    _require(
        chronology.get("parent_result_observed_before_followup_design") is True,
        "follow-up chronology does not record the parent result as observed",
    )
    _require(
        chronology.get("parent_result_git_commit")
        == "960e693296e7564f291e62abb7365075a22fbce5",
        "parent result Git commit mismatch",
    )
    _require(
        chronology.get("parent_result_raw_sha256")
        == "e48bcaf1673871252284d118831410beccf74895d9bdc950d9f9d6c200cb94b9",
        "frozen parent result raw identity record mismatch",
    )
    _require(
        chronology.get("parent_result_canonical_lf_sha256")
        == EXPECTED["parent_result"],
        "frozen parent result canonical identity record mismatch",
    )

    execution_control = followup_data.get("execution_control", {})
    _require(
        execution_control.get("scientific_execution_authorized_by_this_file") is False,
        "follow-up preregistration unexpectedly authorizes scientific execution",
    )
    _require(
        execution_control.get("implementation_must_be_completed_and_validated_before_execution")
        is True,
        "follow-up implementation-validation requirement mismatch",
    )
    _require(
        execution_control.get("no_endpoint_or_population_changes_after_followup_activity_is_observed")
        is True,
        "follow-up endpoint/population freeze requirement mismatch",
    )
    for field in (
        "simulation_steps_at_freeze",
        "physics_steps_at_freeze",
        "neural_steps_at_freeze",
    ):
        _require(
            execution_control.get(field) == 0,
            f"follow-up preregistration {field} is not zero",
        )

    inherited = followup_data.get("inherited_frozen_protocol", {})
    _require(inherited.get("seeds") == [1, 2, 3], "follow-up seed set mismatch")
    _require(
        inherited.get("conditions") == list(CONDITIONS),
        "follow-up condition set mismatch",
    )
    _require(
        inherited.get("branch_point_ms") == 250.0,
        "follow-up branch point mismatch",
    )
    _require(
        inherited.get("neural_timestep_ms") == 0.5,
        "follow-up neural timestep mismatch",
    )
    _require(
        inherited.get("intervention_window_ms")
        == {"start_inclusive": 250.0, "stop_exclusive": 750.0},
        "follow-up intervention window mismatch",
    )
    _require(
        inherited.get("post_window_ms")
        == {"start_inclusive": 750.0, "stop_exclusive": 1000.0},
        "follow-up post window mismatch",
    )

    populations = followup_data.get(
        "post_outcome_static_observation_population_definition", {}
    )
    _require(
        populations.get("lf_sensory_sources", {}).get("count") == 23,
        "frozen LF sensory-source count mismatch",
    )
    _require(
        populations.get("lf_sensory_sources", {}).get(
            "sorted_dense_indices_uint64_le_sha256"
        )
        == "9978c94e5e79c4d54ef93fa888156f15ba9b321566c30419f78975e79899cc71",
        "frozen LF sensory-source population identity mismatch",
    )
    _require(
        populations.get("complete_anatomical_one_hop_targets", {}).get("count")
        == 477,
        "frozen anatomical one-hop count mismatch",
    )
    _require(
        populations.get("complete_anatomical_one_hop_targets", {}).get(
            "sorted_dense_indices_uint64_le_sha256"
        )
        == "bf4a7b79bd2fd9e155fd05af47f40752e719c052cd6a8af7fb5dda0022d0cd81",
        "frozen anatomical one-hop population identity mismatch",
    )
    _require(
        populations.get("runtime_admitted_one_hop_targets", {}).get("count")
        == 268,
        "frozen runtime-admitted one-hop count mismatch",
    )
    _require(
        populations.get("runtime_admitted_one_hop_targets", {}).get(
            "sorted_dense_indices_uint64_le_sha256"
        )
        == "63e11aa63802817ba4b808a4234ac2eb6ee3d0b4176b552a9a16ac19dfd126de",
        "frozen runtime-admitted one-hop population identity mismatch",
    )
    _require(
        populations.get("runtime_admitted_one_hop_targets", {}).get("min_synapses")
        == 6,
        "frozen runtime-admitted threshold mismatch",
    )
    _require(
        populations.get("runtime_admitted_one_hop_targets", {}).get(
            "confirmed_subset_of_complete_anatomical_one_hop_targets"
        )
        is True,
        "frozen runtime-admitted subset assertion mismatch",
    )

    # Validate the prospectively frozen Experiment 2 analysis clarification.
    # This document was frozen after the follow-up preregistration but before
    # any follow-up neural execution.
    try:
        analysis_data = json.loads(
            paths["analysis_clarification"].read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RecruitmentFailure(
            f"invalid follow-up analysis clarification: {exc}"
        ) from exc

    _require(
        analysis_data.get("schema")
        == "LF-PROXIMAL-PROPAGATION-LOCALIZATION-ANALYSIS-CLARIFICATION.1",
        "follow-up analysis clarification schema mismatch",
    )
    _require(
        analysis_data.get("status")
        == "FROZEN_BEFORE_FOLLOWUP_NEURAL_EXECUTION",
        "follow-up analysis clarification status mismatch",
    )

    analysis_parent = analysis_data.get("parent_preregistration", {})
    _require(
        analysis_parent.get("canonical_lf_sha256")
        == EXPECTED["preregistration"],
        "analysis clarification parent preregistration identity mismatch",
    )
    _require(
        analysis_parent.get("git_commit")
        == "a73ee120ff856ff9586865c435a1d88f9a5a08ed",
        "analysis clarification parent preregistration commit mismatch",
    )

    analysis_execution = analysis_data.get("execution_control", {})
    _require(
        analysis_execution.get(
            "scientific_execution_authorized_by_this_file"
        )
        is False,
        "analysis clarification unexpectedly authorizes scientific execution",
    )
    for field in (
        "simulation_steps_at_freeze",
        "physics_steps_at_freeze",
        "neural_steps_at_freeze",
    ):
        _require(
            analysis_execution.get(field) == 0,
            f"analysis clarification {field} is not zero",
        )

    no_change = analysis_data.get("no_change_assertions", {})
    for field in (
        "candidate_motor_populations_changed",
        "intervention_bounds_changed",
        "model_configuration_changed",
        "neural_dynamics_changed",
        "observation_populations_changed",
        "prespecified_stages_changed",
        "replay_changed",
        "rng_semantics_changed",
        "seeds_changed",
    ):
        _require(
            no_change.get(field) is False,
            f"analysis clarification unexpectedly records {field}",
        )

    stage_semantics = analysis_data.get("stage_semantics", {})
    expected_stage_roles = {
        "encoded LF sensory rates": "MANIPULATION_CHECK",
        "delivered LF external sensory events": "FIRST_PROPAGATION_STAGE",
        "23 LF sensory-neuron neural activity": "NEURAL_PROPAGATION_STAGE",
        "complete 477-neuron anatomical one-hop population":
            "NEURAL_PROPAGATION_STAGE",
        "268-neuron runtime-admitted one-hop population":
            "NEURAL_PROPAGATION_STAGE",
        "previously preregistered candidate motor neurons":
            "NEURAL_PROPAGATION_STAGE",
    }
    _require(
        set(stage_semantics) == set(expected_stage_roles),
        "analysis clarification stage set mismatch",
    )
    for stage_name, expected_role in expected_stage_roles.items():
        _require(
            stage_semantics.get(stage_name, {}).get("role")
            == expected_role,
            f"analysis clarification role mismatch for {stage_name}",
        )

    divergence_rule = analysis_data.get("divergence_rule", {})
    _require(
        divergence_rule.get("conditions")
        == [
            "LF_MIN_BOUND versus paired CONTROL_REPLAY",
            "LF_MAX_BOUND versus paired CONTROL_REPLAY",
        ],
        "analysis clarification paired-condition rule mismatch",
    )
    _require(
        divergence_rule.get("pairing") == "within seed",
        "analysis clarification pairing rule mismatch",
    )
    _require(
        divergence_rule.get("per_neuron_data_preserved") is True,
        "analysis clarification per-neuron preservation mismatch",
    )
    _require(
        divergence_rule.get("per_seed_data_preserved") is True,
        "analysis clarification per-seed preservation mismatch",
    )
    _require(
        divergence_rule.get("statistical_threshold") is None,
        "analysis clarification unexpectedly defines a statistical threshold",
    )
    # The parent preregistration remains authoritative for the inherited
    # Experiment 1 evidence dependencies and exact candidate motor populations.
    try:
        parent_prereg_data = json.loads(
            paths["parent_preregistration"].read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RecruitmentFailure(f"invalid parent preregistration: {exc}") from exc

    dependencies = parent_prereg_data.get("frozen_evidence_dependencies")
    _require(
        isinstance(dependencies, list) and bool(dependencies),
        "parent preregistration has no frozen evidence dependencies",
    )

    # neural.py is the sole historical exception inherited from the parent:
    # its original identity was prospectively superseded by the frozen CRN
    # implementation/clarification before Experiment 1 scientific execution.
    for dependency in dependencies:
        relative = dependency.get("path")
        if relative == "malecns_backend/neural.py":
            continue
        _require(
            isinstance(relative, str) and isinstance(dependency.get("sha256"), str),
            "invalid frozen parent dependency record",
        )
        dependency_path = REPO / relative
        try:
            actual_dependency = canonical_lf_sha256(dependency_path)
        except OSError as exc:
            raise RecruitmentFailure(
                f"cannot read frozen dependency {relative}: {exc}"
            ) from exc
        _require(
            actual_dependency == dependency["sha256"],
            f"frozen dependency mismatch: {relative}",
        )

    try:
        manifest_data = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RecruitmentFailure(f"invalid replay manifest: {exc}") from exc

    required_manifest = {
        "schema": "LF-PROXIMAL-MOTOR-RECRUITMENT-SENSORY-REPLAY.1",
        "condition": "CORRECTED_SPONTANEOUS_NEURAL_EMBODIMENT",
        "field": "physics_joint_position",
        "rows": list(range(0, 10_000, 10)),
        "columns": [5, 12, 19, 26, 33, 40],
        "channel_names_order": list(CHANNELS),
        "units": "radians",
        "interval_ms": {"start_inclusive": 0, "stop_exclusive": 1000},
        "replay_cadence_ms": 1,
        "sample_count": 1000,
        "shape": [1000, 6],
        "dtype": "float64",
        "exact_copy_policy": "direct NumPy advanced indexing only; no numerical transformation",
        "addendum_canonical_lf_sha256": EXPECTED["addendum"],
    }
    for key, expected in required_manifest.items():
        _require(
            manifest_data.get(key) == expected,
            f"manifest {key} mismatch",
        )

    source = manifest_data.get("source", {})
    _require(
        source.get("sha256") == EXPECTED["source_m8"],
        "manifest source-M8 mismatch",
    )
    _require(
        source.get("size") == 345_584_215,
        "manifest source-M8 size mismatch",
    )

    replay_record = manifest_data.get("replay", {})
    _require(
        replay_record.get("sha256") == EXPECTED["replay"],
        "manifest replay identity mismatch",
    )

    validation = manifest_data.get("validation_provenance", {})
    _require(
        validation.get("final_status")
        == "READY_FOR_AUTHORIZED_REPLAY_EXTRACTION",
        "manifest extraction validation was not ready",
    )

    nominal = manifest_data.get("nominal_timestamps_ms")
    _require(
        nominal == [float(i) for i in range(1000)],
        "manifest timestamp sequence mismatch",
    )

    # Nominal replay time and inherited M8 accumulated-clock time are distinct
    # frozen provenance and must not be rounded into an invented ideal clock.
    actual = manifest_data.get("actual_source_timestamps_ms")
    _require(
        actual == FROZEN_ACTUAL_SOURCE_TIMESTAMPS_MS,
        "manifest source timestamp bounds mismatch",
    )
    _require(
        manifest_data.get("maximum_nominal_timestamp_deviation_ms")
        == FROZEN_MAXIMUM_NOMINAL_TIMESTAMP_DEVIATION_MS,
        "manifest maximum timestamp deviation mismatch",
    )

    try:
        with paths["replay"].open("rb") as stream:
            values = np.load(stream, allow_pickle=False)
    except Exception as exc:
        raise RecruitmentFailure(f"cannot load frozen replay: {exc}") from exc

    _require(values.shape == (1000, 6), "replay shape mismatch")
    _require(values.dtype == np.dtype("float64"), "replay dtype mismatch")
    _require(bool(np.isfinite(values).all()), "replay contains nonfinite values")

    return values, {
        "sha256": identities,
        "manifest": manifest_data,
        "followup_preregistration": followup_data,
        "parent_preregistration": parent_prereg_data,
    }

def frozen_sensory_indices(interfaces) -> np.ndarray:
    indices = np.asarray(sorted(i for leg in LEG_ORDER
                                for i in interfaces[leg].sensor.dense_indices), dtype=np.intp)
    _require(len(indices) == 392 and len(np.unique(indices)) == 392,
             "frozen sensory union is not exactly 392 unique neurons")
    _require(bool(np.all(indices[1:] > indices[:-1])), "sensory indices are not increasing")
    return indices


def _population_sha256(indices: np.ndarray) -> str:
    """Hash sorted dense indices as concatenated little-endian uint64 values."""
    values = np.asarray(indices, dtype=np.int64)
    _require(values.ndim == 1, "population indices must be one-dimensional")
    _require(
        bool(np.all(values >= 0)),
        "population indices must be nonnegative",
    )
    values = np.asarray(np.sort(values), dtype="<u8")
    _require(
        len(values) == len(np.unique(values)),
        "population indices must be unique",
    )
    return hashlib.sha256(values.tobytes(order="C")).hexdigest()


def reconstruct_observation_populations(data, interfaces,
                                        followup_preregistration: dict[str, Any]
                                        ) -> dict[str, np.ndarray]:
    """Reconstruct frozen Experiment 2 populations from static graph data only."""
    population_spec = followup_preregistration.get(
        "post_outcome_static_observation_population_definition", {}
    )

    lf = np.asarray(
        sorted(interfaces["LF"].sensor.dense_indices),
        dtype=np.intp,
    )

    lf_spec = population_spec.get("lf_sensory_sources", {})
    _require(len(lf) == lf_spec.get("count"), "LF sensory-source count mismatch")
    _require(
        _population_sha256(lf)
        == lf_spec.get("sorted_dense_indices_uint64_le_sha256"),
        "LF sensory-source hash mismatch",
    )

    row_ptr = data.row_ptr
    target_indices = data.target_indices
    synapse_counts = data.synapse_counts

    anatomical_set: set[int] = set()
    admitted_set: set[int] = set()

    admitted_spec = population_spec.get("runtime_admitted_one_hop_targets", {})
    min_synapses = admitted_spec.get("min_synapses")
    _require(
        isinstance(min_synapses, int) and min_synapses >= 1,
        "invalid frozen runtime-admitted synapse threshold",
    )

    for pre in lf:
        start = int(row_ptr[int(pre)])
        stop = int(row_ptr[int(pre) + 1])
        _require(
            0 <= start <= stop <= len(target_indices),
            f"invalid CSR bounds for LF source {int(pre)}",
        )
        _require(
            stop <= len(synapse_counts),
            f"synapse-count array too short for LF source {int(pre)}",
        )

        for edge in range(start, stop):
            post = int(target_indices[edge])
            anatomical_set.add(post)
            if int(synapse_counts[edge]) >= min_synapses:
                admitted_set.add(post)

    anatomical = np.asarray(sorted(anatomical_set), dtype=np.intp)
    admitted = np.asarray(sorted(admitted_set), dtype=np.intp)

    anatomical_spec = population_spec.get(
        "complete_anatomical_one_hop_targets", {}
    )
    _require(
        len(anatomical) == anatomical_spec.get("count"),
        "anatomical one-hop count mismatch",
    )
    _require(
        _population_sha256(anatomical)
        == anatomical_spec.get("sorted_dense_indices_uint64_le_sha256"),
        "anatomical one-hop hash mismatch",
    )

    _require(
        len(admitted) == admitted_spec.get("count"),
        "runtime-admitted one-hop count mismatch",
    )
    _require(
        _population_sha256(admitted)
        == admitted_spec.get("sorted_dense_indices_uint64_le_sha256"),
        "runtime-admitted one-hop hash mismatch",
    )
    _require(
        bool(np.all(np.isin(admitted, anatomical))),
        "runtime-admitted population is not a subset of anatomical one-hop targets",
    )
    _require(
        admitted_spec.get(
            "confirmed_subset_of_complete_anatomical_one_hop_targets"
        ) is True,
        "frozen admitted-subset assertion mismatch",
    )

    return {
        "lf_sensory_sources": lf,
        "anatomical_one_hop_targets": anatomical,
        "runtime_admitted_one_hop_targets": admitted,
    }

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


def _events_in_population(events, indices: np.ndarray) -> np.ndarray:
    """Return sorted event neuron IDs belonging to a frozen observation population."""
    event_array = np.asarray(events, dtype=np.intp)
    if event_array.size == 0:
        return np.empty(0, dtype=np.intp)

    selected = np.asarray(
        np.sort(event_array[np.isin(event_array, indices)]),
        dtype=np.intp,
    )
    _require(
        selected.size == 0 or np.all(selected[1:] != selected[:-1]),
        "recorded event population contains duplicate neuron IDs",
    )
    return selected

def _record_propagation_step(
    branch,
    fired,
    telemetry: dict[str, list],
    lf_indices: np.ndarray,
    anatomical_one_hop_indices: np.ndarray,
    admitted_one_hop_indices: np.ndarray,
    candidate_indices: np.ndarray,
) -> np.ndarray:
    """Record passive post-step propagation telemetry without modifying brain state."""
    _require(
        np.array_equal(
            branch._last_external_candidates,
            branch._last_external_delivered,
        ),
        "external-event withholding unexpectedly active",
    )

    step_time_ms = float(branch.time_ms)

    delivered_lf = _events_in_population(
        branch._last_external_delivered,
        lf_indices,
    )
    fired_lf = _events_in_population(
        fired,
        lf_indices,
    )
    fired_anatomical = _events_in_population(
        fired,
        anatomical_one_hop_indices,
    )
    fired_admitted = _events_in_population(
        fired,
        admitted_one_hop_indices,
    )
    fired_candidates = _events_in_population(
        fired,
        candidate_indices,
    )

    telemetry["delivered_lf_external_events"].append({
        "time_ms": step_time_ms,
        "neurons": [int(i) for i in delivered_lf],
    })
    telemetry["lf_sensory_neural_events"].append({
        "time_ms": step_time_ms,
        "neurons": [int(i) for i in fired_lf],
    })
    telemetry["anatomical_one_hop_neural_events"].append({
        "time_ms": step_time_ms,
        "neurons": [int(i) for i in fired_anatomical],
    })
    telemetry["runtime_admitted_one_hop_neural_events"].append({
        "time_ms": step_time_ms,
        "neurons": [int(i) for i in fired_admitted],
    })
    telemetry["candidate_motor_neural_events"].append({
        "time_ms": step_time_ms,
        "neurons": [int(i) for i in fired_candidates],
    })

    return fired_candidates

def _compare_recorded_stage(
    control_records,
    perturbation_records,
    stage_name: str,
    lf_indices: np.ndarray,
) -> dict[str, Any]:
    """Apply the frozen exact paired-divergence rule to one recorded stage."""
    _require(
        len(control_records) == len(perturbation_records),
        f"{stage_name} record-count mismatch",
    )

    if stage_name == "encoded_lf_rates":
        for control, perturbation in zip(
            control_records,
            perturbation_records,
        ):
            _require(
                control["sample_time_ms"] == perturbation["sample_time_ms"],
                "encoded LF sample-time mismatch",
            )

            control_rates = np.asarray(
                control["rates_hz"],
                dtype=np.float64,
            )
            perturbation_rates = np.asarray(
                perturbation["rates_hz"],
                dtype=np.float64,
            )

            _require(
                control_rates.shape == (len(lf_indices),),
                "control encoded LF rate-vector shape mismatch",
            )
            _require(
                perturbation_rates.shape == (len(lf_indices),),
                "perturbation encoded LF rate-vector shape mismatch",
            )

            different = np.flatnonzero(
                control_rates != perturbation_rates
            )
            if different.size:
                return {
                    "diverged": True,
                    "first_difference_time_ms": float(
                        control["sample_time_ms"]
                    ),
                    "first_differing_neurons": [
                        int(lf_indices[i]) for i in different
                    ],
                }

        return {
            "diverged": False,
            "first_difference_time_ms": None,
            "first_differing_neurons": [],
        }

    for control, perturbation in zip(
        control_records,
        perturbation_records,
    ):
        _require(
            control["time_ms"] == perturbation["time_ms"],
            f"{stage_name} neural-step time mismatch",
        )

        control_neurons = np.asarray(
            control["neurons"],
            dtype=np.intp,
        )
        perturbation_neurons = np.asarray(
            perturbation["neurons"],
            dtype=np.intp,
        )

        if not np.array_equal(
            control_neurons,
            perturbation_neurons,
        ):
            differing = np.setxor1d(
                control_neurons,
                perturbation_neurons,
                assume_unique=True,
            )
            return {
                "diverged": True,
                "first_difference_time_ms": float(
                    control["time_ms"]
                ),
                "first_differing_neurons": [
                    int(i) for i in differing
                ],
            }

    return {
        "diverged": False,
        "first_difference_time_ms": None,
        "first_differing_neurons": [],
    }

def _rng_digest(brain) -> str:
    return _digest(brain.rng.bit_generator.state)


def execute_assay(replay: np.ndarray, provenance: dict[str, Any], *, brain_factory=None,
                  data_loader=None) -> dict[str, Any]:
    """Execute only after ``provenance_gate`` has returned validated bytes."""
    from malecns_backend import MaleCNSBrain, load_malecns
    brain_factory = brain_factory or MaleCNSBrain
    data_loader = data_loader or load_malecns
    followup_prereg = provenance["followup_preregistration"]
    parent_prereg = provenance["parent_preregistration"]
    interfaces = load_six_tibia_interfaces()
    schedule = frozen_sensory_indices(interfaces)
    populations = _candidate_populations(parent_prereg)
    candidate_indices = np.concatenate(tuple(populations.values()))
    _require(not np.intersect1d(candidate_indices, schedule).size,
             "candidate neuron is directly externally driven")
    data = data_loader()

    observation_populations = reconstruct_observation_populations(
        data,
        interfaces,
        followup_prereg,
    )
    lf_indices = observation_populations["lf_sensory_sources"]
    anatomical_one_hop_indices = observation_populations[
        "anatomical_one_hop_targets"
    ]
    admitted_one_hop_indices = observation_populations[
        "runtime_admitted_one_hop_targets"
    ]

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

        propagation_telemetry = {
            condition: {
                "encoded_lf_rates": [],
                "delivered_lf_external_events": [],
                "lf_sensory_neural_events": [],
                "anatomical_one_hop_neural_events": [],
                "runtime_admitted_one_hop_neural_events": [],
                "candidate_motor_neural_events": [],
            }
            for condition in CONDITIONS
        }
        for sample in range(250, 1000):
            for condition, (branch, branch_observer) in branches.items():
                row = replay[sample].copy()
                if sample < 750:
                    if condition == "LF_MIN_BOUND": row[0] = -1.35
                    elif condition == "LF_MAX_BOUND": row[0] = 1.30
                encoded = _apply_sample(
                    branch,
                    encoders,
                    interfaces,
                    row,
                    sample,
                )

                lf_drive = encoded["LF"]
                _require(
                    np.array_equal(
                        np.asarray(lf_drive.indices, dtype=np.intp),
                        lf_indices,
                    ),
                    "LF encoded-drive indices differ from frozen LF population",
                )
                _require(
                    len(lf_drive.rates_hz) == len(lf_indices),
                    "LF encoded-drive rate-vector width mismatch",
                )

                propagation_telemetry[condition]["encoded_lf_rates"].append({
                    "sample_time_ms": float(sample),
                    "rates_hz": [
                        float(x)
                        for x in np.asarray(
                            lf_drive.rates_hz,
                            dtype=np.float64,
                        )
                    ],
                })

                for _ in range(2):
                    fired = branch.step()
                    _require(branch._external_rng_step_draws == 392, "CRN draw-count invariant failed")
                    _require(np.array_equal(branch._last_external_rng_indices, schedule),
                             "CRN slot mapping invariant failed")
                    fired_candidates = _record_propagation_step(
                        branch,
                        fired,
                        propagation_telemetry[condition],
                        lf_indices,
                        anatomical_one_hop_indices,
                        admitted_one_hop_indices,
                        candidate_indices,
                    )
                    step_time_ms = float(branch.time_ms)
                    events[condition].extend(
                        (step_time_ms, int(i))
                        for i in fired_candidates
                    )
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
                "propagation_telemetry": propagation_telemetry[condition],
                "final_rng_digest": _rng_digest(branch),
            }
        all_seed_results.append({"seed": seed, "branch_time_ms": 250.0,
                                 "pre_intervention_state_digests": pre_digests,
                                 "conditions": condition_results})
    stage_definitions = (
        ("encoded_lf_rates", "MANIPULATION_CHECK"),
        ("delivered_lf_external_events", "FIRST_PROPAGATION_STAGE"),
        ("lf_sensory_neural_events", "NEURAL_PROPAGATION_STAGE"),
        ("anatomical_one_hop_neural_events", "NEURAL_PROPAGATION_STAGE"),
        ("runtime_admitted_one_hop_neural_events", "NEURAL_PROPAGATION_STAGE"),
        ("candidate_motor_neural_events", "NEURAL_PROPAGATION_STAGE"),
    )

    paired_divergence = {}
    propagation_stage_names = [
        name
        for name, role in stage_definitions
        if role != "MANIPULATION_CHECK"
    ]

    for perturbation in CONDITIONS[1:]:
        per_seed = []

        for seed_result in all_seed_results:
            control_telemetry = seed_result["conditions"][
                "CONTROL_REPLAY"
            ]["propagation_telemetry"]
            perturbation_telemetry = seed_result["conditions"][
                perturbation
            ]["propagation_telemetry"]

            stage_results = {}
            for stage_name, role in stage_definitions:
                comparison = _compare_recorded_stage(
                    control_telemetry[stage_name],
                    perturbation_telemetry[stage_name],
                    stage_name,
                    lf_indices,
                )
                comparison["role"] = role
                stage_results[stage_name] = comparison

            earliest_propagation_stage = next(
                (
                    stage_name
                    for stage_name in propagation_stage_names
                    if stage_results[stage_name]["diverged"]
                ),
                None,
            )

            per_seed.append({
                "seed": int(seed_result["seed"]),
                "stages": stage_results,
                "earliest_propagation_divergence_stage":
                    earliest_propagation_stage,
            })

        paired_divergence[perturbation] = per_seed

    return {
        "schema": "LF-PROXIMAL-PROPAGATION-LOCALIZATION-RESULT.1",
        "seeds": list(SEEDS),
        "conditions": list(CONDITIONS),
        "observation_stages": [
            {
                "name": name,
                "role": role,
            }
            for name, role in stage_definitions
        ],
        "provenance": provenance,
        "seed_results": all_seed_results,
        "paired_divergence": paired_divergence,
    }

def check_ready(**paths) -> dict[str, Any]:
    replay, provenance = provenance_gate(**paths)

    interfaces = load_six_tibia_interfaces()
    sensory_indices = frozen_sensory_indices(interfaces)

    # Static connectome loading only.  Do not instantiate MaleCNSBrain here:
    # readiness must remain incapable of advancing neural runtime state.
    from malecns_backend import load_malecns

    data = load_malecns()
    populations = reconstruct_observation_populations(
        data,
        interfaces,
        provenance["followup_preregistration"],
    )

    return {
        "status": "READY_FOR_IMPLEMENTATION_VALIDATION",
        "scientific_execution_authorized": False,
        "replay_shape": list(replay.shape),
        "replay_dtype": str(replay.dtype),
        "sensory_rng_slots": len(sensory_indices),
        "observation_populations": {
            "lf_sensory_sources": {
                "count": len(populations["lf_sensory_sources"]),
                "sha256": _population_sha256(
                    populations["lf_sensory_sources"]
                ),
            },
            "anatomical_one_hop_targets": {
                "count": len(populations["anatomical_one_hop_targets"]),
                "sha256": _population_sha256(
                    populations["anatomical_one_hop_targets"]
                ),
            },
            "runtime_admitted_one_hop_targets": {
                "count": len(
                    populations["runtime_admitted_one_hop_targets"]
                ),
                "sha256": _population_sha256(
                    populations["runtime_admitted_one_hop_targets"]
                ),
            },
        },
        "provenance_sha256": provenance["sha256"],
        "simulation_steps": 0,
        "physics_steps": 0,
        "neural_runtime_steps": 0,
    }


def _write_result_exclusive(output_path: Path, result: dict[str, Any]) -> None:
    """Write one scientific result without permitting replacement."""
    serialized = (
        json.dumps(
            result,
            sort_keys=True,
            allow_nan=False,
            indent=2,
        )
        + "\n"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Exclusive creation is deliberate. Scientific results must never be
    # silently truncated or replaced by a later run or test.
    with output_path.open(
        "x",
        encoding="utf-8",
        newline="\n",
    ) as handle:
        handle.write(serialized)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument(
        "--check-ready",
        action="store_true",
        help="validate frozen provenance without creating a brain",
    )
    actions.add_argument(
        "--execute",
        action="store_true",
        help="reserved; scientific execution is not yet authorized",
    )
    parser.add_argument("--replay-dir", type=Path, default=REPLAY_DIR)
    parser.add_argument(
        "--output",
        type=Path,
        help="reserved for a future separately authorized scientific execution",
    )
    args = parser.parse_args(argv)

    if not args.check_ready and not args.execute:
        parser.print_usage()
        print("No action selected; zero scientific steps executed.")
        return 0

    if args.execute:
        paths = {
            "preregistration": PREREGISTRATION,
            "parent_preregistration": PARENT_PREREGISTRATION,
            "parent_result": PARENT_RESULT,
            "clarification": CLARIFICATION,
            "addendum": ADDENDUM,
            "analysis_clarification": ANALYSIS_CLARIFICATION,
            "replay": args.replay_dir / REPLAY.name,
            "manifest": args.replay_dir / MANIFEST.name,
            "report": args.replay_dir / EXTRACTION_REPORT.name,
        }

        output_path = (
            args.output
            or SPEC_DIR / "lf_proximal_propagation_localization_result.json"
        )

        try:
            # Refuse before constructing or advancing the scientific assay.
            # The exclusive writer below remains a second line of defense.
            if output_path.exists():
                raise FileExistsError(
                    f"refusing to overwrite existing scientific result: {output_path}"
                )

            replay, provenance = provenance_gate(**paths)
            authorization = execution_authorization_gate()

            result = execute_assay(
                replay,
                provenance,
            )

            _write_result_exclusive(
                output_path,
                result,
            )

            print(json.dumps({
                "status": "SCIENTIFIC_EXECUTION_COMPLETE",
                "scientific_execution_authorized": True,
                "authorization_sha256": authorization["identity"],
                "output": str(output_path),
                "seeds": result["seeds"],
                "conditions": result["conditions"],
            }, sort_keys=True))

            return 0

        except (RecruitmentFailure, OSError, ValueError) as exc:
            print(json.dumps({
                "status": "FAIL_CLOSED",
                "error": str(exc),
                "scientific_execution_authorized": False,
                "neural_runtime_steps": 0,
            }, sort_keys=True))
            return 1

    paths = {
        "replay": args.replay_dir / REPLAY.name,
        "manifest": args.replay_dir / MANIFEST.name,
        "report": args.replay_dir / EXTRACTION_REPORT.name,
    }

    try:
        result = check_ready(**paths)
    except (RecruitmentFailure, OSError, ValueError) as exc:
        print(json.dumps({
            "status": "FAIL_CLOSED",
            "error": str(exc),
            "scientific_execution_authorized": False,
            "neural_runtime_steps": 0,
        }, sort_keys=True))
        return 1

    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
