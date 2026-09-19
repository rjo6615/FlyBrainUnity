import hashlib
import json

import pytest

from malecns_backend.embodiment import proprioceptive_closed_loop as subject
from malecns_backend.embodiment.motor import MotorDecoder, MotorSafety
from malecns_backend.embodiment.proprioceptive_activation import sample_candidates
from malecns_backend.embodiment.sensory import SensoryEncoder
from malecns_backend.embodiment.tactile_motor_matched_control import MatchedControlPipeline


def test_locked_protocol_and_mappings():
    assert (subject.SEED, subject.DURATION_MS, subject.PHYSICS_DT_MS,
            subject.NEURAL_DT_MS, subject.AUTOMATIC_RETRIES) == (1, 100, .1, .5, 0)
    expected = {"LF": (5, 23), "LM": (12, 80), "LH": (19, 93),
                "RF": (26, 13), "RM": (33, 83), "RH": (40, 100)}
    inventory = subject.mapping_inventory()
    assert {leg: (x["action_index"], x["mapped_neuron_count"])
            for leg, x in inventory.items()} == expected
    assert sum(x[1] for x in expected.values()) == 392
    assert subject.ACTUATOR_INDICES == {x: y[0] for x, y in expected.items()}


def test_locked_existing_encoder_and_decoder():
    assert subject.encoder_parameters() == {
        "implementation": "malecns_backend.embodiment.sensory.SensoryEncoder",
        "angle_range_rad": [-1.35, 1.3], "preferred_positions": "(k + 0.5) / population_size",
        "gaussian_width_normalized": .25, "maximum_rate_hz": 120., "cutoff_hz": 5.,
        "baseline_hz": 0., "normalization": "(angle-angle_min)/(angle_max-angle_min)",
        "event_probability": "rate_hz * 0.5 / 1000"}
    assert SensoryEncoder.__module__.endswith(".sensory")
    assert MotorDecoder.half_activation_hz == 17
    assert MotorSafety() == MotorSafety(-1.35, 1.30, .25, 4.)


def test_condition_changes_only_admission_and_disabled_pipeline_evolves():
    assert subject.admit_neural_contribution(.2, subject.CONDITIONS[0]) == .2
    assert subject.admit_neural_contribution(.2, subject.CONDITIONS[1]) == 0
    enabled, disabled = MatchedControlPipeline(True), MatchedControlPipeline(False)
    e = enabled.update(.1, .2, .0005); d = disabled.update(.1, .2, .0005)
    assert e.raw_neural_contribution == d.raw_neural_contribution == .2
    assert e.baseline_target == d.baseline_target == .1
    assert enabled.previous_physical_target == e.actuator_command
    assert disabled.previous_physical_target == d.actuator_command
    assert d.previous_physical_target == .1  # not a special disabled branch


def test_rng_is_common_and_deterministic():
    left, right = subject.proprio_rngs(), subject.proprio_rngs()
    rates = [120.] * 100
    assert {k: sample_candidates(rates, left[k]).tolist() for k in left} == {
        k: sample_candidates(rates, right[k]).tolist() for k in right}


def test_provenance_locks_authoritative_complete_artifact():
    result = subject.verify_provenance()
    assert result["verified"] and result["m5d5a_authoritative_complete"]
    path = subject.ROOT / "malecns_backend/embodiment/interface_output/proprioceptive_activation_100ms.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == subject.M5D5A_LOCKS["interface_output/proprioceptive_activation_100ms.json"]


@pytest.mark.parametrize("broken,expected", [
    ({"provenance": False}, "PROVENANCE_FAILURE"),
    ({"provenance": True, "physics_stable": False}, "PHYSICS_FAILURE"),
    ({"provenance": True, "physics_stable": True, "rng_aligned": False}, "RNG_PARITY_FAILURE"),
    ({"provenance": True, "physics_stable": True, "rng_aligned": True, "pre_equal": False}, "PRE_INTERVENTION_DIVERGENCE"),
])
def test_classification_fails_closed(broken, expected):
    assert subject.classify(broken) == expected


def test_feedback_classification_ladder_and_nulls():
    e = dict(provenance=True, physics_stable=True, rng_aligned=True, pre_equal=True,
             C3=True, C6=True, C7=True, C8=True, C10=True, C11=True, C12=True, C13=True)
    assert subject.classify(e) == "PROPRIOCEPTIVE_CLOSED_LOOP_CAUSAL_CHAIN_CONFIRMED"
    assert subject.classify({**e, "C13": False}) == "CLOSED_LOOP_TO_CNS_CONFIRMED"
    assert subject.classify({**e, "C11": False}) == "MOTOR_TO_PROPRIOCEPTIVE_FEEDBACK_CONFIRMED"
    assert subject.base_report()["milestones"] == {f"C{i}": None for i in range(14)}


def test_causal_ordering_guards():
    subject.validate_order({"C3": 1, "C4": 2, "C5": 3, "C6": 4,
                            "C7": 4, "C8": 5, "C10": 6, "C11": 7, "C12": 8, "C13": 9})
    with pytest.raises(ValueError): subject.validate_order({"C3": 2, "C4": 1})
    with pytest.raises(ValueError): subject.validate_order({"C10": 4, "C11": 4})


def test_report_contract_tactile_exclusions_and_no_controllers():
    report = subject.base_report()
    assert report["architecture"]["both_conditions_proprioception"]
    assert report["architecture"]["both_conditions_tactile"]
    assert report["tactile"] == {"channel": "LM Tarsus5", "transduction_modified": False, "rng_modified": False}
    assert report["aggregate"]["directly_driven_neurons_excluded"]
    assert report["aggregate"]["tactile_direct_neurons_separately_excluded"]
    assert not any(report["science_controls"].values())
    assert json.loads(subject.serialize(report)) == report
    assert subject.serialize(report) == subject.serialize(report)
