import hashlib
import json
from pathlib import Path

import pytest

from malecns_backend.embodiment import tactile_motor_matched_control as matched
from malecns_backend.embodiment import tactile_motor_matched_control_audit as runner
from malecns_backend.embodiment.tactile_motor_loop import ACTUATOR_INDICES


def row(time=0.0, **updates):
    value = {"time_ms": time, "measured_positions": [0.0] * 6,
        "baseline_targets": [0.0] * 6, "previous_physical_targets": [0.0] * 6,
        "raw_neural_contributions": [0.0] * 6, "observer_states": {},
        "decoder_states": {}, "sensory_encoding": {}, "rng_state": "same",
        "action_joints": [0.0] * 42, "six_tibia_action": [0.0] * 6,
        "adhesion": [0.0] * 6, "ctrl": [0.0] * 42, "qacc": [0.0],
        "qvel": [0.0], "qpos": [0.0], "contact_forces": [[0.0]],
        "contact_set": []}
    value.update(updates); return value


def test_locked_six_tibia_indices_unchanged():
    assert ACTUATOR_INDICES == {"LF": 5, "LM": 12, "LH": 19,
        "RF": 26, "RM": 33, "RH": 40}


def test_prior_semantic_locks_and_canonical_bytes_are_preserved():
    before = runner.ARTIFACTS["m5d4"].read_bytes()
    result = runner.verify_provenance()
    assert result["verified"] and result["m5d4b_semantic_digest"]
    assert runner.ARTIFACTS["m5d4"].read_bytes() == before
    assert json.loads(runner.ARTIFACTS["m5d4a"].read_text())["classification"] == "EXACT_REPEATABILITY_CONFIRMED"


def test_same_baseline_and_zero_raw_give_identical_common_path():
    enabled = matched.MatchedControlPipeline(True)
    disabled = matched.MatchedControlPipeline(False)
    assert enabled.update(.2, 0.0, .0005) == disabled.update(.2, 0.0, .0005)


def test_nonzero_gate_is_the_only_condition_difference():
    enabled = matched.MatchedControlPipeline(True).update(0.0, .1, .0005)
    disabled = matched.MatchedControlPipeline(False).update(0.0, .1, .0005)
    assert enabled.raw_neural_contribution == disabled.raw_neural_contribution == .1
    assert enabled.admitted_neural_contribution == .1
    assert disabled.admitted_neural_contribution == 0.0
    assert enabled.actuator_command != disabled.actuator_command


def test_previous_target_clamp_and_slew_are_common_before_intervention():
    enabled = matched.MatchedControlPipeline(True)
    disabled = matched.MatchedControlPipeline(False)
    for measured in (0.0, .01, -.02):
        left = enabled.update(measured, 0.0, .0005)
        right = disabled.update(measured, 0.0, .0005)
        assert left == right
        assert left.previous_physical_target == right.previous_physical_target
        assert left.range_clamped_target == right.range_clamped_target
        assert left.slew_limited_target == right.slew_limited_target


def test_old_bug_reproduces_but_corrected_path_does_not():
    assert matched.legacy_bug_command(-.0048, -.0045, True) != \
           matched.legacy_bug_command(-.0048, -.0045, False)
    assert matched.MatchedControlPipeline(True).update(-.0048, 0, .0005) == \
           matched.MatchedControlPipeline(False).update(-.0048, 0, .0005)


def test_full_actions_ctrl_and_exact_physics_are_compared():
    for field, index in (("action_joints", 41), ("ctrl", 41), ("qacc", 0),
                         ("qvel", 0), ("qpos", 0), ("contact_forces", 0)):
        left, right = row(), row(); right[field][index] = 1.0
        classification, evidence = matched.classify_traces([left], [right], 1.0)
        expected = "PRE_INTERVENTION_COMMAND_DIVERGENCE" if field in ("action_joints", "ctrl") \
            else "PRE_INTERVENTION_PHYSICAL_DIVERGENCE"
        assert classification == expected and not evidence["exactly_equal"]


def test_contact_comparison_uses_m5d4a_semantic_names_and_exact_force():
    contact0 = {"all_contact_pairs": [{"geom1_id": 1, "geom2_id": 2,
        "geom1_name": "surface", "geom2_name": "0/LMTarsus5", "force": 1.0}]}
    contact1 = {"all_contact_pairs": [{"geom1_id": 9, "geom2_id": 8,
        "geom1_name": "surface", "geom2_name": "1/LMTarsus5", "force": 1.0}]}
    assert matched.compare_contact_sets(contact0, contact1)["exactly_equal"]
    contact1["all_contact_pairs"][0]["force"] = 1.0000000000000002
    assert not matched.compare_contact_sets(contact0, contact1)["exactly_equal"]


@pytest.mark.parametrize(("field", "classification"), [
    ("baseline_targets", "BASELINE_STATE_DIVERGENCE"),
    ("previous_physical_targets", "BASELINE_STATE_DIVERGENCE"),
    ("observer_states", "DECODER_STATE_DIVERGENCE"),
    ("raw_neural_contributions", "DECODER_STATE_DIVERGENCE"),
    ("rng_state", "RNG_OR_SENSORY_DIVERGENCE"),
])
def test_pre_intervention_internal_divergence_fails(field, classification):
    left, right = row(), row(); right[field] = "different"
    assert matched.classify_traces([left], [right], 1.0)[0] == classification


def test_successful_ordering_passes_and_no_intervention_is_distinct():
    left = [row(0), row(1)]; right = [row(0), row(1)]
    left[1]["action_joints"][12] = .1; left[1]["ctrl"][12] = .1
    left[1]["qacc"][0] = .1; left[1]["qvel"][0] = .1; left[1]["qpos"][0] = .1
    assert matched.classify_traces(left, right, 1.0)[0] == "PREFLIGHT_PASS"
    assert matched.classify_traces([row()], [row()], None)[0] == "NO_NEURAL_INTERVENTION"


def test_serialization_is_deterministic_and_artifact_is_truthful():
    assert matched.serialize(matched.base_report()) == matched.serialize(matched.base_report())
    artifact = json.loads(Path(runner.DEFAULT_OUTPUT).read_text())
    assert artifact["run_status"] == "NOT_RUN" and artifact["classification"] is None
    required = {"control_pipeline_definition", "baseline_definition", "intervention_definition",
        "first_raw_neural_contribution", "first_enabled_admitted_neural_contribution",
        "first_action_divergence", "first_ctrl_divergence", "first_qacc_divergence",
        "first_qvel_divergence", "first_qpos_divergence", "first_force_divergence",
        "first_contact_divergence", "causal_ordering", "per_leg_summary"}
    assert required <= artifact.keys()


def test_provenance_fails_closed():
    with pytest.raises(RuntimeError):
        matched.semantic_lock({"classification": "changed"}, {"classification": "LOCKED"})


def test_canonical_100ms_cannot_be_run_from_preflight():
    with pytest.raises(ValueError, match="fixed at 25.0"):
        runner.run_live(100.0, 1)
    assert matched.base_report()["protocol"]["canonical_100ms_run_permitted"] is False
