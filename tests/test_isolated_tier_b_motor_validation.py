"""M6B preregistration, isolation, decoder, and classification contracts."""
import json
from pathlib import Path
import pytest
from malecns_backend.embodiment import isolated_tier_b_motor_validation as m6b

@pytest.fixture(scope="module")
def report(): return m6b.build_not_run_artifact()

def test_exact_14_m6a_eligible_actuators(report):
    assert tuple(x["physical_joint"] for x in report["interfaces"]) == m6b.TIER_B
    assert len(report["interfaces"]) == 14

def test_no_tier_c_d_or_tier_a_admitted(report):
    assert all(x["physical_joint"] in m6b.TIER_B for x in report["interfaces"])
    assert not ({x["action_index"] for x in report["interfaces"]} & m6b.TIBIA_INDICES)
    with pytest.raises(ValueError): m6b.admitted_tier_b(m6b.TIER_B[0], {"joint_LFCoxa": 1.0}, "ENABLED")

def test_six_tibia_unchanged_and_inactive(report):
    assert report["protocol"]["tier_a_neural_contribution"] is False
    assert report["m6a_lock"]["semantic_requirements"]["six_tibia_regression"] == "PASS"

def test_exactly_one_tier_b_admitted():
    raw = {name: .1 for name in m6b.TIER_B}
    out = m6b.admitted_tier_b(m6b.TIER_B[3], raw, "ENABLED")
    assert sum(v != 0 for v in out.values()) == 1

def test_exact_matched_control_gate():
    assert m6b.matched_control_gate(.123, "ENABLED") == .123
    assert m6b.matched_control_gate(.123, "MOTOR_OUTPUT_DISABLED") == 0
    with pytest.raises(ValueError): m6b.matched_control_gate(.1, "OTHER")

def test_sign_evidence_required(report):
    assert all(x["physical_sign_status"] == "PHYSICAL_SIGN_CALIBRATION_REQUIRED" for x in report["interfaces"])
    assert all(x["nmf_positive_group"] is None and x["nmf_negative_group"] is None for x in report["interfaces"])
    assert m6b.classify_joint(provenance=True, sign_resolved=False, equivalent=True, mapped_activity=True,
        decoder_output=True, admitted=True, joint_diverged=True, divergence_before_admission=False,
        physics_valid=True) == "SIGN_UNRESOLVED"

def test_safe_joint_bounds_and_decoder_clamp():
    assert m6b.safe_contribution_bound(-1, 1, 0) == .25
    assert m6b.safe_contribution_bound(-.1, .8, 0) == .1
    assert abs(m6b.decoded_contribution(1e9, 0, .1)) <= .1
    with pytest.raises(ValueError): m6b.decoded_contribution(1, 0, .251)

def test_same_update_milestone_ordering_accepted():
    assert m6b.milestones_ordered({f"B{i}": 7 for i in range(6)})
    assert not m6b.milestones_ordered({"B0": 2, "B1": 1})

def _sample(value=0): return {field: value for field in m6b.EQUIVALENCE_FIELDS}
def test_strict_pre_intervention_equivalence():
    a=[_sample(), _sample()]; b=[_sample(), _sample()]
    assert m6b.strict_pre_intervention_equivalence(a,b,1)
    b[0]["rng_state"] = 1
    assert not m6b.strict_pre_intervention_equivalence(a,b,1)
    del b[0]["rng_state"]
    assert not m6b.strict_pre_intervention_equivalence(a,b,1)

def test_deterministic_single_seed_fixed_duration(report):
    p=report["protocol"]
    assert p["canonical_seed"] == m6b.CANONICAL_SEED == 1
    assert p["seed_sweep"] is False
    assert p["duration_ms_per_condition"] == m6b.DURATION_MS == 500.0
    assert p["duration_frozen_before_live_run"] is True

def test_synthetic_diagnostic_separated(report):
    d=report["protocol"]["synthetic_diagnostic"]
    assert d == {"classification":"SYNTHETIC_INTERFACE_DIAGNOSTIC_ONLY", "part_of_scientific_result":False}

def test_classification_logic_and_m6c_eligibility():
    common=dict(provenance=True,sign_resolved=True,equivalent=True,mapped_activity=True,
        decoder_output=True,admitted=True,joint_diverged=True,divergence_before_admission=False,physics_valid=True)
    assert m6b.classify_joint(**common) == "ISOLATED_MOTOR_CAUSALITY_CONFIRMED"
    common["mapped_activity"]=False
    assert m6b.classify_joint(**common) == "NO_MAPPED_MOTOR_ACTIVITY"
    rows=[{"actuator":"a","classification":"ISOLATED_MOTOR_CAUSALITY_CONFIRMED","physical_sign_status":"RESOLVED"},
          {"actuator":"b","classification":"ISOLATED_MOTOR_CAUSALITY_CONFIRMED","physical_sign_status":"SIGN_UNRESOLVED"}]
    assert m6b.m6c_eligible(rows) == ["a"]
    complete=[{"actuator": name, "classification": "NO_MAPPED_MOTOR_ACTIVITY"} for name in m6b.TIER_B]
    assert m6b.aggregate_classification(complete) == "ISOLATED_TIER_B_VALIDATION_COMPLETE_NO_CAUSAL_RESPONSES"
    complete[0]["classification"] = "ISOLATED_MOTOR_CAUSALITY_CONFIRMED"
    assert m6b.aggregate_classification(complete) == "ISOLATED_TIER_B_VALIDATION_COMPLETE_WITH_PARTIAL_CAUSALITY"

def test_provenance_fail_closed(tmp_path):
    p=tmp_path/"m6a.json"; p.write_text("{}")
    with pytest.raises(m6b.ValidationFailure) as e: m6b.load_locked_m6a(p)
    assert e.value.classification == "PROVENANCE_FAILURE"

def test_not_run_artifact_is_current(report):
    committed=json.loads(m6b.OUTPUT.read_text(encoding="utf-8"))
    assert committed == report
    assert committed["run_status"] == "NOT_RUN" and committed["per_joint"] == []
    assert committed["m6c_eligible"] == []
