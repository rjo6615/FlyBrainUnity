"""M6B preregistration, isolation, decoder, and classification contracts."""
import hashlib
import json
from pathlib import Path
import pytest
from malecns_backend.embodiment import isolated_tier_b_motor_validation as m6b

@pytest.fixture(scope="module")
def report(): return m6b.build_not_run_artifact()

def test_exact_eight_canonical_and_six_unresolved_excluded(report):
    assert tuple(report["eligible_interfaces"]) == m6b.TIER_B
    assert tuple(report["excluded_unresolved_interfaces"]) == m6b.EXCLUDED_UNRESOLVED
    assert report["eligible_interface_count"] == 8
    assert report["excluded_unresolved_count"] == 6
    assert tuple(x["physical_joint"] for x in report["interfaces"]) == m6b.ANNOTATION_TIER_B
    excluded = [x for x in report["interfaces"] if x["physical_joint"] in m6b.EXCLUDED_UNRESOLVED]
    assert all(x["annotation_backed_motor_mapping"] is True for x in excluded)
    assert all(x["physical_sign_status"] == "SIGN_UNRESOLVED" and
               x["canonical_m6b_neural_actuation"] == "WITHHELD" for x in excluded)

def test_no_tier_c_d_or_tier_a_admitted(report):
    eligible = [x for x in report["interfaces"] if x["canonical_m6b_neural_actuation"] == "ELIGIBLE"]
    assert all(x["physical_joint"] in m6b.TIER_B for x in eligible)
    assert not ({x["action_index"] for x in eligible} & m6b.TIBIA_INDICES)
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
    eligible = [x for x in report["interfaces"] if x["physical_joint"] in m6b.TIER_B]
    assert {x["physical_joint"]: x["coordinate_sign"] for x in eligible} == m6b.LOCKED_SIGNS
    assert all(x["mechanical_calibration"]["evidence"]["uses_neural_behavior"] is False
               for x in eligible)
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
    assert report["canonical_seed"] == 1 and report["duration_ms"] == 500
    assert report["conditions_per_interface"] == 2

def test_frozen_actions_populations_and_constants(report):
    locks = report["preregistration_locks"]
    assert locks["action_indices"] == m6b.LOCKED_ACTION_INDICES
    assert locks["coordinate_signs"] == m6b.LOCKED_SIGNS
    assert locks["decoder_constants"] == {"observer_tau_ms": 40.0,
        "half_activation_hz": 17.0, "decoder_max_rad": .25, "slew_rad_s": 4.0}
    assert all(locks["motor_population_mappings"][name]["positive"] and
               locks["motor_population_mappings"][name]["negative"] for name in m6b.TIER_B)

def test_unresolved_and_other_tiers_cannot_be_admitted():
    for name in (*m6b.EXCLUDED_UNRESOLVED, "joint_LFTibia", "joint_LFCoxa", "joint_LFTarsus2"):
        with pytest.raises(ValueError):
            m6b.admitted_tier_b(name, {name: .1}, "ENABLED")

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

@pytest.mark.parametrize("field,value", [("action_index", 99), ("coordinate_sign", 1)])
def test_p2_resolved_action_and_sign_locks_fail_closed(tmp_path, monkeypatch, field, value):
    data = json.loads(m6b.P2_PATH.read_text(encoding="utf-8"))
    row = next(x for x in data["interfaces"] if x["physical_actuator_name"] == m6b.TIER_B[0])
    (row if field == "action_index" else row["sign_calibration"])[field] = value
    candidate = tmp_path / "p2.json"
    candidate.write_text(json.dumps(data), encoding="utf-8", newline="\n")
    monkeypatch.setattr(m6b, "P2_PATH", candidate)
    monkeypatch.setattr(m6b, "P2_SHA256", hashlib.sha256(candidate.read_bytes()).hexdigest())
    with pytest.raises(m6b.ValidationFailure, match="resolved sign/action lock mismatch"):
        m6b.load_preregistration_locks()

def test_m6a_raw_lock_is_cross_platform_lf_and_rejects_crlf(tmp_path):
    """Git supplies LF bytes; an unprotected CRLF checkout must not weaken the lock."""
    authoritative = m6b.M6A_PATH.read_bytes()
    assert b"\r\n" not in authoritative
    assert hashlib.sha256(authoritative).hexdigest() == m6b.M6A_SHA256
    assert m6b.load_locked_m6a(m6b.M6A_PATH)["schema"] == "M6A.0"

    crlf = tmp_path / "m6a-crlf.json"
    crlf.write_bytes(authoritative.replace(b"\n", b"\r\n"))
    assert json.loads(crlf.read_bytes()) == json.loads(authoritative)
    with pytest.raises(m6b.ValidationFailure, match="raw-byte provenance mismatch"):
        m6b.load_locked_m6a(crlf)

    # This models Git's `-text` byte-preserving checkout behavior, not loader-side
    # normalization: provenance remains a strict raw-byte lock.
    canonical = tmp_path / "m6a-canonical-lf.json"
    canonical.write_bytes(crlf.read_bytes().replace(b"\r\n", b"\n"))
    assert m6b.load_locked_m6a(canonical)["classification"] == "WHOLE_LEG_MOTOR_AUDIT_COMPLETE"
    attributes = (m6b.ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "whole_leg_motor_mapping_audit.json -text" in attributes

def test_m6a_one_byte_content_change_and_malformed_json_fail_closed(tmp_path):
    authoritative = m6b.M6A_PATH.read_bytes()
    changed = tmp_path / "changed.json"
    changed.write_bytes(authoritative.replace(b'M6A.0', b'M6A.1', 1))
    with pytest.raises(m6b.ValidationFailure, match="raw-byte provenance mismatch"):
        m6b.load_locked_m6a(changed)

    malformed = tmp_path / "malformed.json"
    malformed.write_bytes(b"{")
    malformed_hash = hashlib.sha256(malformed.read_bytes()).hexdigest()
    with pytest.raises(json.JSONDecodeError):
        m6b.load_locked_m6a(malformed, malformed_hash)

@pytest.mark.parametrize("mutation", [
    lambda data: data.update(schema="M6A.1"),
    lambda data: data.update(run_status="FAILED"),
    lambda data: data.update(classification="OTHER"),
    lambda data: data["summary"].update(tier_counts={"A": 5, "B": 15, "C": 18, "D": 4}),
    lambda data: data.update(m6b_eligible=data["m6b_eligible"][:-1]),
    lambda data: data["six_tibia_regression"].update(passed=False),
    lambda data: next(r for r in data["per_actuator"]
                      if r["motor_embodiment_tier"] == "A").update(motor_embodiment_tier="C"),
])
def test_m6a_semantic_constraints_fail_even_with_matching_raw_lock(tmp_path, mutation):
    data = json.loads(m6b.M6A_PATH.read_text(encoding="utf-8"))
    mutation(data)
    candidate = tmp_path / "semantic-change.json"
    candidate.write_text(json.dumps(data), encoding="utf-8", newline="\n")
    candidate_hash = hashlib.sha256(candidate.read_bytes()).hexdigest()
    with pytest.raises(m6b.ValidationFailure, match="M6A .* differs|M6A semantic lock mismatch"):
        m6b.load_locked_m6a(candidate, candidate_hash)

def test_not_run_artifact_is_current(report):
    committed=json.loads(m6b.OUTPUT.read_text(encoding="utf-8"))
    assert committed == report
    assert committed["run_status"] == "NOT_RUN" and committed["per_joint"] == []
    assert committed["scientific_run_number"] is None
    assert committed["m6c_eligible"] == []
