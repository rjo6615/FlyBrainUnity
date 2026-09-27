import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from malecns_backend.neural import MaleCNSBrain, ModelConfig
from malecns_backend.embodiment import lf_proximal_motor_recruitment as runner
from malecns_backend.embodiment.motor import MotorActivityObserver


class TinyData:
    neuron_count = 400
    row_ptr = np.zeros(401, dtype=np.int64)
    target_indices = np.empty(0, dtype=np.int32)
    synapse_counts = np.empty(0, dtype=np.float32)
    superclasses = ("sensory",)
    superclass_ids = np.zeros(400, dtype=np.intp)
    neuron_sizes = np.ones(400, dtype=np.float32)
    neurotransmitter_ids = np.zeros(400, dtype=np.intp)
    nt_signs = np.zeros(400, dtype=np.float32)
    types = ("fixture",) * 400
    classes = ("fixture",)
    class_ids = np.zeros(400, dtype=np.intp)


def brain(seed=1):
    value = MaleCNSBrain(TinyData(), ModelConfig())
    value.reset(seed)
    value.configure_external_rng_schedule(np.arange(392))
    return value


def test_crn_fixed_draw_count_mapping_and_zero_drive_discard():
    value = brain(7)
    before = copy.deepcopy(value.rng.bit_generator.state)
    value.step()
    reference = np.random.Generator(np.random.PCG64())
    reference.bit_generator.state = before
    expected = reference.random(392)
    assert value._external_rng_step_draws == 392
    assert np.array_equal(value._last_external_rng_indices, np.arange(392))
    assert np.array_equal(value._last_external_rng_uniforms, expected)
    assert value._last_external_candidates.size == 0
    assert value.rng.bit_generator.state == reference.bit_generator.state


def test_eligible_neuron_uses_its_slot_and_refractory_slot_is_discarded():
    value = brain(11)
    expected_rng = np.random.Generator(np.random.PCG64())
    expected_rng.bit_generator.state = copy.deepcopy(value.rng.bit_generator.state)
    uniforms = expected_rng.random(392)
    selected = int(np.argmin(uniforms))
    refractory = (selected + 1) % 392
    value.external_drive[[selected, refractory]] = 2000.0
    value.refractory[refractory] = 1.0
    value.step()
    assert selected in value._last_external_candidates
    assert refractory not in value._last_external_candidates
    assert value._last_external_rng_uniforms[refractory] == uniforms[refractory]


@pytest.mark.parametrize("field", ["external_drive", "refractory"])
def test_different_masks_preserve_pairing_and_branch_rng_alignment(field):
    left, right = brain(3), brain(3)
    if field == "external_drive":
        left.external_drive[:100] = 100
        right.external_drive[100:200] = 100
    else:
        left.external_drive[:200] = right.external_drive[:200] = 100
        left.refractory[:100] = 1
        right.refractory[100:200] = 1
    left.step(); right.step()
    assert np.array_equal(left._last_external_rng_uniforms, right._last_external_rng_uniforms)
    assert left.rng.bit_generator.state == right.rng.bit_generator.state


def test_unauthorized_rng_consumer_is_detected():
    value = brain()
    value.rng.random()
    with pytest.raises(RuntimeError, match="unauthorized"):
        value.step()


def _fixture_artifacts(tmp_path, monkeypatch):
    replay = np.zeros((1000, 6), dtype=np.float64)
    replay_path = tmp_path / "replay.npy"
    np.save(replay_path, replay, allow_pickle=False)
    prereg = tmp_path / "prereg.json"; prereg.write_text("{}")
    clarification = tmp_path / "clarification.json"; clarification.write_text("{}")
    addendum = tmp_path / "addendum.json"; addendum.write_text("{}")
    report = tmp_path / "report.md"; report.write_text("report")
    manifest_data = {
        "schema": "LF-PROXIMAL-MOTOR-RECRUITMENT-SENSORY-REPLAY.1",
        "condition": "CORRECTED_SPONTANEOUS_NEURAL_EMODIMENT",  # fixed below
        "field": "physics_joint_position", "rows": list(range(0, 10000, 10)),
        "columns": [5, 12, 19, 26, 33, 40], "channel_names_order": list(runner.CHANNELS),
        "units": "radians", "interval_ms": {"start_inclusive": 0, "stop_exclusive": 1000},
        "replay_cadence_ms": 1, "sample_count": 1000, "shape": [1000, 6], "dtype": "float64",
        "exact_copy_policy": "direct NumPy advanced indexing only; no numerical transformation",
        "source": {"sha256": runner.EXPECTED["source_m8"], "size": 345584215},
        "replay": {}, "validation_provenance": {"final_status": "READY_FOR_AUTHORIZED_REPLAY_EXTRACTION"},
        "maximum_nominal_timestamp_deviation_ms": runner.FROZEN_MAXIMUM_NOMINAL_TIMESTAMP_DEVIATION_MS,
        "nominal_timestamps_ms": [float(i) for i in range(1000)],
        "actual_source_timestamps_ms": dict(runner.FROZEN_ACTUAL_SOURCE_TIMESTAMPS_MS),
    }
    manifest_data["condition"] = "CORRECTED_SPONTANEOUS_NEURAL_EMBODIMENT"
    expected = dict(runner.EXPECTED)
    expected.update({"preregistration": runner.sha256_file(prereg),
                     "clarification": runner.sha256_file(clarification),
                     "addendum": runner.sha256_file(addendum),
                     "replay": runner.sha256_file(replay_path),
                     "report": runner.sha256_file(report)})
    manifest_data["addendum_canonical_lf_sha256"] = expected["addendum"]
    manifest_data["replay"]["sha256"] = expected["replay"]
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(manifest_data))
    expected["manifest"] = runner.sha256_file(manifest)
    monkeypatch.setattr(runner, "EXPECTED", expected)
    return {"preregistration": prereg, "clarification": clarification, "addendum": addendum,
            "replay": replay_path, "manifest": manifest, "report": report}, manifest_data


@pytest.mark.parametrize("artifact", ["replay", "manifest", "report", "clarification"])
def test_wrong_artifact_hash_rejected_before_brain_creation(tmp_path, monkeypatch, artifact):
    paths, _ = _fixture_artifacts(tmp_path, monkeypatch)
    paths[artifact].write_bytes(paths[artifact].read_bytes() + b"bad")
    with pytest.raises(runner.RecruitmentFailure, match="SHA-256"):
        runner.provenance_gate(**paths)


def test_canonical_lf_preregistration_and_exact_crlf_checkout_both_pass(tmp_path, monkeypatch):
    paths, _ = _fixture_artifacts(tmp_path, monkeypatch)
    canonical = b'{\n  "frozen_evidence_dependencies": []\n}\n'
    paths["preregistration"].write_bytes(canonical)
    runner.EXPECTED["preregistration"] = hashlib.sha256(canonical).hexdigest()
    runner.provenance_gate(**paths)

    paths["preregistration"].write_bytes(canonical.replace(b"\n", b"\r\n"))
    _, provenance = runner.provenance_gate(**paths)
    assert provenance["sha256"]["preregistration"] == hashlib.sha256(canonical).hexdigest()


@pytest.mark.parametrize("mutation", [
    lambda value: value.replace(b"dependencies", b"dependencieX"),
    lambda value: value.replace(b": []", b":  []"),
    lambda value: value.replace(b"  ", b"\t", 1),
])
def test_canonical_text_rejects_non_line_ending_changes(tmp_path, monkeypatch, mutation):
    paths, _ = _fixture_artifacts(tmp_path, monkeypatch)
    canonical = b'{\n  "frozen_evidence_dependencies": []\n}\n'
    runner.EXPECTED["preregistration"] = hashlib.sha256(canonical).hexdigest()
    paths["preregistration"].write_bytes(mutation(canonical.replace(b"\n", b"\r\n")))
    with pytest.raises(runner.RecruitmentFailure, match="preregistration SHA-256"):
        runner.provenance_gate(**paths)


@pytest.mark.parametrize("artifact", ["clarification", "addendum"])
def test_other_protocol_text_uses_canonical_lf_identity(tmp_path, monkeypatch, artifact):
    paths, manifest = _fixture_artifacts(tmp_path, monkeypatch)
    canonical = b'{\n  "protocol": "unchanged"\n}\n'
    runner.EXPECTED[artifact] = hashlib.sha256(canonical).hexdigest()
    paths[artifact].write_bytes(canonical.replace(b"\n", b"\r\n"))
    if artifact == "addendum":
        manifest["addendum_canonical_lf_sha256"] = runner.EXPECTED[artifact]
        paths["manifest"].write_text(json.dumps(manifest))
        runner.EXPECTED["manifest"] = runner.sha256_file(paths["manifest"])
    runner.provenance_gate(**paths)


def test_frozen_tracked_text_dependency_uses_canonical_lf_identity(tmp_path, monkeypatch):
    paths, _ = _fixture_artifacts(tmp_path, monkeypatch)
    dependency_lf = b"first line\nsecond line\n"
    dependency = tmp_path / "dependency.py"
    dependency.write_bytes(dependency_lf.replace(b"\n", b"\r\n"))
    prereg_data = {"frozen_evidence_dependencies": [{
        "path": "dependency.py", "sha256": hashlib.sha256(dependency_lf).hexdigest()
    }]}
    prereg_lf = (json.dumps(prereg_data, indent=2) + "\n").encode()
    paths["preregistration"].write_bytes(prereg_lf)
    runner.EXPECTED["preregistration"] = hashlib.sha256(prereg_lf).hexdigest()
    monkeypatch.setattr(runner, "REPO", tmp_path)
    runner.provenance_gate(**paths)

    dependency.write_bytes(dependency.read_bytes().replace(b"second", b"changed"))
    with pytest.raises(runner.RecruitmentFailure, match="frozen dependency mismatch"):
        runner.provenance_gate(**paths)


def test_replay_and_extraction_artifacts_remain_raw_byte_exact(tmp_path, monkeypatch):
    paths, _ = _fixture_artifacts(tmp_path, monkeypatch)
    # CRLF/LF equivalence is deliberately not extended to extraction text.
    for artifact in ("manifest", "report"):
        original = paths[artifact].read_bytes()
        paths[artifact].write_bytes(original + b"\r\n")
        with pytest.raises(runner.RecruitmentFailure, match=f"{artifact} SHA-256"):
            runner.provenance_gate(**paths)
        paths[artifact].write_bytes(original)
    paths["replay"].write_bytes(paths["replay"].read_bytes() + b"\x00")
    with pytest.raises(runner.RecruitmentFailure, match="replay SHA-256"):
        runner.provenance_gate(**paths)


@pytest.mark.parametrize("mutation", ["shape", "dtype", "nonfinite"])
def test_invalid_replay_rejected(tmp_path, monkeypatch, mutation):
    paths, manifest = _fixture_artifacts(tmp_path, monkeypatch)
    value = (np.zeros((999, 6)) if mutation == "shape" else
             np.zeros((1000, 6), dtype=np.float32) if mutation == "dtype" else
             np.zeros((1000, 6), dtype=np.float64))
    if mutation == "nonfinite": value[0, 0] = np.nan
    np.save(paths["replay"], value)
    runner.EXPECTED["replay"] = runner.sha256_file(paths["replay"])
    manifest["replay"]["sha256"] = runner.EXPECTED["replay"]
    paths["manifest"].write_text(json.dumps(manifest))
    runner.EXPECTED["manifest"] = runner.sha256_file(paths["manifest"])
    with pytest.raises(runner.RecruitmentFailure):
        runner.provenance_gate(**paths)


@pytest.mark.parametrize("field,bad", [("replay_cadence_ms", 2), ("channel_names_order", []),
                                        ("units", "degrees")])
def test_manifest_semantics_rejected(tmp_path, monkeypatch, field, bad):
    paths, manifest = _fixture_artifacts(tmp_path, monkeypatch)
    manifest[field] = bad
    paths["manifest"].write_text(json.dumps(manifest))
    runner.EXPECTED["manifest"] = runner.sha256_file(paths["manifest"])
    with pytest.raises(runner.RecruitmentFailure, match=field):
        runner.provenance_gate(**paths)


def _write_mutated_manifest(paths, manifest, monkeypatch):
    paths["manifest"].write_text(json.dumps(manifest))
    monkeypatch.setitem(runner.EXPECTED, "manifest", runner.sha256_file(paths["manifest"]))


def test_authoritative_frozen_timestamp_contract_is_accepted(tmp_path, monkeypatch):
    paths, manifest = _fixture_artifacts(tmp_path, monkeypatch)
    _, provenance = runner.provenance_gate(**paths)
    assert provenance["manifest"]["actual_source_timestamps_ms"] == {
        "first": 0.0, "last": 998.9999999999063}
    assert provenance["manifest"]["maximum_nominal_timestamp_deviation_ms"] == \
        9.367795428261161e-11


@pytest.mark.parametrize("field,bad,message", [
    ("nominal_timestamps_ms", [float(i) for i in range(999)] + [999.0000000001],
     "timestamp sequence"),
    ("rows", list(range(0, 10_000, 10))[:-1] + [9981], "rows"),
    ("replay_cadence_ms", 1.0000000001, "replay_cadence_ms"),
    ("sample_count", 999, "sample_count"),
    ("actual_source_timestamps_ms", {"first": 0.0, "last": 998.9999999999064},
     "source timestamp bounds"),
    ("actual_source_timestamps_ms", {"first": 0.0, "last": 999.0},
     "source timestamp bounds"),
    ("maximum_nominal_timestamp_deviation_ms", 0.0, "maximum timestamp deviation"),
])
def test_frozen_extraction_contract_mutations_fail_closed(
        tmp_path, monkeypatch, field, bad, message):
    paths, manifest = _fixture_artifacts(tmp_path, monkeypatch)
    manifest[field] = bad
    _write_mutated_manifest(paths, manifest, monkeypatch)
    with pytest.raises(runner.RecruitmentFailure, match=message):
        runner.provenance_gate(**paths)


def test_wrong_extraction_provenance_fails_before_brain_creation(tmp_path, monkeypatch):
    paths, manifest = _fixture_artifacts(tmp_path, monkeypatch)
    manifest["validation_provenance"]["final_status"] = "NUMERICAL_VALIDATION_FAILURE"
    _write_mutated_manifest(paths, manifest, monkeypatch)
    brain_creations = []
    monkeypatch.setattr(runner, "load_six_tibia_interfaces",
                        lambda: brain_creations.append("brain") or object())
    with pytest.raises(runner.RecruitmentFailure, match="validation was not ready"):
        runner.check_ready(**paths)
    assert brain_creations == []


@pytest.mark.parametrize("mutation", ["source", "provenance"])
def test_manifest_source_and_provenance_rejected(tmp_path, monkeypatch, mutation):
    paths, manifest = _fixture_artifacts(tmp_path, monkeypatch)
    if mutation == "source": manifest["source"]["sha256"] = "0" * 64
    else: manifest["validation_provenance"]["final_status"] = "FAILED"
    paths["manifest"].write_text(json.dumps(manifest))
    runner.EXPECTED["manifest"] = runner.sha256_file(paths["manifest"])
    with pytest.raises(runner.RecruitmentFailure):
        runner.provenance_gate(**paths)


def test_branch_copy_is_exact_independent_and_mismatch_invalidates_triplet():
    source = brain(2)
    source.time_ms = 250.0
    source._ring[0] = [3, 4]
    observer = MotorActivityObserver({"candidate": [395]})
    observer.reset(source.spike_counts)
    observer.filtered_hz[0] = 12.5
    branches = {name: runner.clone_branch(source, observer) for name in runner.CONDITIONS}
    digest = runner.require_identical_branches(branches, np.zeros((250, 6)))
    assert digest["rng"] == runner._digest(source.rng.bit_generator.state)
    assert branches["CONTROL_REPLAY"][0]._ring == source._ring
    assert branches["CONTROL_REPLAY"][1].filtered_hz[0] == 12.5
    branches["LF_MIN_BOUND"][0]._ring[0].append(8)
    with pytest.raises(runner.RecruitmentFailure, match="invalidates"):
        runner.require_identical_branches(branches, np.zeros((250, 6)))


def test_import_help_and_default_are_inert():
    module = "malecns_backend.embodiment.lf_proximal_motor_recruitment"
    imported = subprocess.run([sys.executable, "-c", f"import {module}; print('ok')"],
                              check=True, capture_output=True, text=True)
    helped = subprocess.run([sys.executable, "-m", module, "--help"],
                            check=True, capture_output=True, text=True)
    default = subprocess.run([sys.executable, "-m", module],
                             check=True, capture_output=True, text=True)
    assert imported.stdout.strip() == "ok"
    assert "--execute" in helped.stdout
    assert "zero scientific steps" in default.stdout


def test_provenance_failure_occurs_before_brain_factory(tmp_path):
    calls = []
    with pytest.raises(runner.RecruitmentFailure):
        runner.provenance_gate(replay=tmp_path / "missing")
    assert calls == []  # no factory is accepted or reachable by the gate


def test_check_ready_provenance_failure_precedes_runtime_setup(tmp_path, monkeypatch):
    paths, _ = _fixture_artifacts(tmp_path, monkeypatch)
    paths["preregistration"].write_bytes(b"changed")
    runtime_calls = []
    monkeypatch.setattr(runner, "load_six_tibia_interfaces",
                        lambda: runtime_calls.append("interfaces"))
    with pytest.raises(runner.RecruitmentFailure, match="preregistration SHA-256"):
        runner.check_ready(**paths)
    assert runtime_calls == []


def test_check_ready_performs_zero_neural_execution(tmp_path, monkeypatch):
    paths, _ = _fixture_artifacts(tmp_path, monkeypatch)
    monkeypatch.setattr(runner, "load_six_tibia_interfaces", lambda: object())
    monkeypatch.setattr(runner, "frozen_sensory_indices", lambda interfaces: np.arange(392))
    monkeypatch.setattr(runner, "execute_assay",
                        lambda *args, **kwargs: pytest.fail("scientific execution called"))
    result = runner.check_ready(**paths)
    assert result["status"] == "READY_FOR_SCIENTIFIC_EXECUTION"
    assert result["neural_runtime_steps"] == 0
