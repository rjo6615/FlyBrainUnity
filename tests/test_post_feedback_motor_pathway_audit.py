import hashlib
import json
from copy import deepcopy

import pytest

from malecns_backend.embodiment import post_feedback_motor_pathway_audit as subject


def authoritative():
    return json.loads(subject.AUTHORITATIVE_ARTIFACT.read_bytes())


def test_raw_artifact_and_canonical_lf_sources_are_locked():
    artifact, provenance = subject.verify_provenance()
    assert artifact["classification"] == "CLOSED_LOOP_TO_CNS_CONFIRMED"
    assert provenance["verified"] is True
    assert provenance["observed_locks"] == subject.M5D5B_LOCKS
    assert hashlib.sha256(subject.AUTHORITATIVE_ARTIFACT.read_bytes()).hexdigest() == (
        subject.M5D5B_LOCKS["interface_output/proprioceptive_closed_loop_100ms.json"])


@pytest.mark.parametrize("path,value", [
    (("schema",), "wrong"), (("run_status",), "NOT_RUN"),
    (("classification",), "wrong"), (("provenance", "verified"), False),
    (("rng", "aligned"), False), (("physics_safety", "stable"), False),
    (("milestones", "C7"), None), (("milestones", "C12"), None),
])
def test_authoritative_semantics_fail_closed(path, value):
    artifact = deepcopy(authoritative())
    target = artifact
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value
    with pytest.raises(RuntimeError, match="authoritative semantic mismatch"):
        subject.validate_authoritative_semantics(artifact)


def test_audit_truthfully_reports_recorded_aggregate_and_missing_detail():
    artifact, provenance = subject.verify_provenance()
    report = subject.analyze(artifact, provenance)
    assert (report["schema"], report["run_status"], report["classification"]) == (
        "M5D-5C.0", "COMPLETE", "MIXED_OR_UNRESOLVED")
    population = report["feedback_population"]
    assert population["directly_driven_proprioceptive_neurons"] == 392
    assert not population["directly_driven_proprioceptive_neurons_counted_as_downstream"]
    assert population["state_divergent_downstream_neuron_count"] == 14212
    assert population["spike_divergent_downstream_neuron_count"] == 1274
    assert population["aggregate_spike_difference_events"] == 4564
    assert population["per_neuron_body_ids_annotations_and_spike_differences"] == "INSUFFICIENT_TELEMETRY"


def test_no_unsupported_anatomy_dynamics_tactile_or_c1_reconstruction():
    artifact, provenance = subject.verify_provenance()
    report = subject.analyze(artifact, provenance)
    assert report["anatomical_reachability"]["status"] == "INSUFFICIENT_TELEMETRY"
    assert report["dynamic_propagation"]["status"] == "INSUFFICIENT_TELEMETRY"
    assert report["sensory_attribution"]["classification"] == "INSUFFICIENT_TELEMETRY"
    assert report["c1_telemetry"]["classification"] == "C1_TELEMETRY_INSUFFICIENT"
    assert set(report["path_depth_summary"]) == {"1", "2", "3", "4", "5"}
    assert all(item["status"] == "INSUFFICIENT_TELEMETRY"
               for item in report["path_depth_summary"].values())


def test_only_existing_mapped_tibia_motor_populations_are_targets():
    report = subject.analyze(*subject.verify_provenance())
    targets = report["anatomical_reachability"]["targets"]
    assert len(targets) == 12
    assert sum(item["neuron_count"] for item in targets) == 49
    assert all(item["population"].startswith(("Ti extensor MN T", "Ti flexor MN T"))
               for item in targets)


def test_required_json_contract_and_no_live_runner_dependency():
    report = subject.analyze(*subject.verify_provenance())
    assert {"schema", "run_status", "classification", "reason", "provenance",
            "authoritative_m5d5b_result", "feedback_population", "sensory_attribution",
            "anatomical_reachability", "path_depth_summary", "dynamic_propagation",
            "mapped_motor_subthreshold", "decoder_analysis", "c1_telemetry",
            "limitations"} <= report.keys()
    source = subject.__file__ and open(subject.__file__, encoding="utf-8").read()
    assert "run_canonical_pair" not in source
    assert "flygym" not in source.lower()
