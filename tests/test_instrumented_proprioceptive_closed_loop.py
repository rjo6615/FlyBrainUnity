import json
import hashlib
from pathlib import Path
import shutil

import pytest

from malecns_backend.embodiment import instrumented_proprioceptive_closed_loop as subject
from malecns_backend.embodiment.instrumented_proprioceptive_closed_loop_post_audit import (
    divergent_neurons, reachability)


def test_protocol_and_failed_pre_simulation_artifact_are_preserved():
    assert (subject.SEED, subject.DURATION_MS, subject.PHYSICS_DT_MS,
            subject.NEURAL_DT_MS, subject.AUTOMATIC_RETRIES) == (1, 100.0, 0.1, 0.5, 0)
    artifact = json.loads((subject.BASE / "interface_output/instrumented_proprioceptive_closed_loop_100ms.json").read_text())
    assert artifact["run_status"] == "FAILED"
    assert artifact["classification"] == "PROVENANCE_FAILURE"
    assert artifact["telemetry"]["sha256"] is None
    assert "7dd802b893c7c94f498a6742d1d3f6538019f5ec6fba54ac68c67714d5e32d48" in artifact["reason"]


def test_historical_provenance_and_semantics_are_locked():
    provenance = subject.verify_provenance()
    assert provenance["verified"] is True
    assert provenance["lock_method"] == {
        "authoritative_artifacts": "raw-byte SHA-256",
        "implementation_sources": "canonical-LF SHA-256"}


def _provenance_copy(tmp_path, monkeypatch):
    for relative in subject.LOCKS:
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(subject.BASE / relative, destination)
    monkeypatch.setattr(subject, "BASE", tmp_path)


def test_semantically_modified_m5d5c_fails_even_with_matching_raw_lock(tmp_path, monkeypatch):
    _provenance_copy(tmp_path, monkeypatch)
    relative = "interface_output/post_feedback_motor_pathway_audit.json"
    path = tmp_path / relative
    artifact = json.loads(path.read_bytes())
    artifact["classification"] = "CHANGED"
    raw = (json.dumps(artifact, indent=2, sort_keys=True, ensure_ascii=False) + "\n").replace("\n", "\r\n").encode()
    path.write_bytes(raw)
    monkeypatch.setattr(subject, "RAW_ARTIFACT_LOCKS", {
        **subject.RAW_ARTIFACT_LOCKS, relative: hashlib.sha256(raw).hexdigest()})
    with pytest.raises(RuntimeError, match="authoritative semantics mismatch"):
        subject.verify_provenance()


def test_source_modification_fails_but_source_line_endings_are_canonical(tmp_path, monkeypatch):
    _provenance_copy(tmp_path, monkeypatch)
    source = tmp_path / "post_feedback_motor_pathway_audit.py"
    source.write_bytes(source.read_bytes().replace(b"\n", b"\r\n"))
    assert subject.verify_provenance()["verified"] is True
    source.write_bytes(source.read_bytes() + b"# semantic source change\r\n")
    with pytest.raises(RuntimeError, match="post_feedback_motor_pathway_audit.py"):
        subject.verify_provenance()


def test_artifact_line_endings_are_locked_as_raw_bytes(tmp_path, monkeypatch):
    _provenance_copy(tmp_path, monkeypatch)
    artifact = tmp_path / "interface_output/post_feedback_motor_pathway_audit.json"
    assert b"\r\n" in artifact.read_bytes()
    artifact.write_bytes(subject.canonical_lf(artifact.read_bytes()))
    with pytest.raises(RuntimeError, match="post_feedback_motor_pathway_audit.json"):
        subject.verify_provenance()


def test_classification_fails_closed_and_replication_strength():
    good = dict(provenance=True, physics_stable=True, rng_aligned=True,
        instrumentation_complete=True, pre_equal=True, prefix=True, C11=True, C12=True, C13=False)
    assert subject.classify(good) == "INSTRUMENTED_CLOSED_LOOP_TO_CNS_REPLICATED"
    assert subject.classify({**good, "C13": True}) == "INSTRUMENTED_FULL_CLOSED_LOOP_REPLICATED"
    assert subject.classify({**good, "pre_equal": False}) == "REPLICATION_FAILED_PRE_INTERVENTION_EQUIVALENCE"
    assert subject.classify({**good, "rng_aligned": False}) == "RNG_PARITY_FAILURE"


@pytest.mark.parametrize("proprio,tactile,expected", [(2,None,"NO_TACTILE_DIVERGENCE_WITHIN_WINDOW"),
    (2,3,"PROPRIOCEPTIVE_FEEDBACK_PRECEDES_OTHER_ACTIVE_SENSORY_DIVERGENCE"),
    (3,2,"TACTILE_FEEDBACK_PRECEDES_PROPRIOCEPTIVE_DELIVERY_DIVERGENCE"),
    (2,2,"SIMULTANEOUS_OR_MIXED_SENSORY_FEEDBACK")])
def test_sensory_attribution(proprio, tactile, expected):
    assert subject.sensory_attribution(proprio, tactile) == expected


def test_per_neuron_difference_and_direct_exclusion():
    np = pytest.importorskip("numpy")
    ids=np.array([10,20,30]); times=np.array([.5,1.,1.5])
    a=np.zeros((3,3)); b=a.copy(); a[2,1]=1; a[2,2]=1
    sa=np.zeros((3,3),dtype=np.uint16); sb=sa.copy(); sa[2,2]=1
    rows=divergent_neurons(ids,times,a,b,sa,sb,1.0,excluded={1})
    assert rows == [{"dense_index":2,"body_id":30,"first_state_divergence_ms":1.5,
        "first_spike_divergence_ms":1.5,"enabled_spike_count":1,
        "disabled_spike_count":0,"spike_count_difference":1}]


def test_reachability_uses_presynaptic_rows():
    class Graph:
        row_ptr=[0,1,2,3,3]; target_indices=[1,2,3]
    out=reachability(Graph(),[0],[3],3)
    assert out["1"]["reachable_mapped_motor_neurons"] == 0
    assert out["3"]["reachable_mapped_motor_dense_indices"] == [3]
