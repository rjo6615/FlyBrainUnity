import json
from pathlib import Path

import pytest

from malecns_backend.embodiment import instrumented_proprioceptive_closed_loop as subject
from malecns_backend.embodiment.instrumented_proprioceptive_closed_loop_post_audit import (
    divergent_neurons, reachability)


def test_protocol_and_checked_artifact_are_not_run():
    assert (subject.SEED, subject.DURATION_MS, subject.PHYSICS_DT_MS,
            subject.NEURAL_DT_MS, subject.AUTOMATIC_RETRIES) == (1, 100.0, 0.1, 0.5, 0)
    artifact = json.loads((subject.BASE / "interface_output/instrumented_proprioceptive_closed_loop_100ms.json").read_text())
    assert artifact["run_status"] == "NOT_RUN"


def test_historical_provenance_and_semantics_are_locked():
    assert subject.verify_provenance()["verified"] is True


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
