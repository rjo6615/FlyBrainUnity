import copy
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from malecns_backend.embodiment import integrated_whole_leg_readiness as m6c
from malecns_backend.embodiment import isolated_tier_b_motor_validation as m6b
from malecns_backend.embodiment import _windows_integrated_whole_leg_readiness_adapter as adapter


ROOT = Path(__file__).resolve().parents[1]


def completed_m6b():
    data = m6b.build_not_run_artifact()
    data.update(run_status="COMPLETE",
        classification="ISOLATED_TIER_B_VALIDATION_COMPLETE_WITH_PARTIAL_CAUSALITY")
    classes = {name: "ISOLATED_MOTOR_CAUSALITY_CONFIRMED" for name in m6c.EXPECTED_TIER_B}
    classes.update({name: "NO_MAPPED_MOTOR_ACTIVITY" for name in m6c.SILENT_M6B})
    data["per_joint"] = [{"actuator": name, "classification": classes[name],
        "physical_sign_status": "RESOLVED"} for name in m6b.TIER_B]
    data["m6c_eligible"] = [name for name in m6b.TIER_B if name in m6c.EXPECTED_TIER_B]
    return data


def test_tier_a_raw_bytes_survive_autocrlf_checkout(tmp_path):
    """The raw-byte provenance lock must survive Windows-style materialization."""
    expected_sha256 = "18aaafd51360e0a60b56f98c0b93e156e4cba2a27efd653111b04a5b8c329271"
    source = ROOT / "six_tibia_causal_result.json"
    source_bytes = source.read_bytes()
    assert len(source_bytes) == 9555
    assert hashlib.sha256(source_bytes).hexdigest() == expected_sha256

    origin = tmp_path / "origin"
    checkout = tmp_path / "checkout"
    origin.mkdir()
    (origin / ".gitattributes").write_bytes((ROOT / ".gitattributes").read_bytes())
    (origin / source.name).write_bytes(source_bytes)
    subprocess.run(["git", "init", "-q"], cwd=origin, check=True)
    subprocess.run(["git", "add", ".gitattributes", source.name], cwd=origin, check=True)
    subprocess.run(
        ["git", "-c", "user.name=M6C test", "-c", "user.email=m6c@example.invalid",
         "commit", "-qm", "fixture"],
        cwd=origin,
        check=True,
    )
    subprocess.run(
        ["git", "-c", "core.autocrlf=true", "clone", "-q", str(origin), str(checkout)],
        check=True,
    )

    materialized = (checkout / source.name).read_bytes()
    assert len(materialized) == 9555
    assert hashlib.sha256(materialized).hexdigest() == expected_sha256
    assert b"\r" not in materialized
    assert json.loads(materialized) == json.loads(source_bytes)


@pytest.fixture
def protocol():
    m6a = json.loads(m6c.M6A_PATH.read_text())
    tier_a = json.loads(m6c.TIER_A_PATH.read_text())
    return m6c.build_not_run_artifact(m6a, completed_m6b(), tier_a,
        {"m6a_sha256": m6c.M6A_SHA256, "m6b_sha256": "fixture", "tier_a_sha256": m6c.TIER_A_SHA256})


def test_exact_derived_admissions_and_42_table(protocol):
    assert m6c.validate_m6b(completed_m6b()) == m6c.EXPECTED_TIER_B
    assert m6c.TIER_A == ("joint_LFTibia", "joint_LMTibia", "joint_LHTibia",
        "joint_RFTibia", "joint_RMTibia", "joint_RHTibia")
    assert len(protocol["actuator_admission_table"]) == 42
    admitted = [x for x in protocol["actuator_admission_table"] if x["neural_motor_admission"]]
    assert {x["actuator"] for x in admitted} == set(m6c.TIER_A + m6c.EXPECTED_TIER_B)
    assert [x["action_index"] for x in admitted] == [3, 5, 10, 12, 17, 19, 26, 31, 33, 38, 40]
    assert {x["coordinate_sign"] for x in admitted} == {-1, 1}


def test_unsupported_and_sensory_policy(protocol):
    by_name = {x["actuator"]: x for x in protocol["actuator_admission_table"]}
    assert all(not by_name[x]["neural_motor_admission"] and by_name[x]["coordinate_sign_status"] == "SIGN_UNRESOLVED" for x in m6c.COXA_YAW)
    assert all(not by_name[x]["neural_motor_admission"] for x in m6c.SILENT_M6B)
    assert {x["actuator"] for x in protocol["actuator_admission_table"] if x["neural_sensory_admission"]} == set(m6c.TIER_A)
    assert all(not by_name[x]["neural_sensory_admission"] for x in m6c.EXPECTED_TIER_B)


def test_three_conditions_seed_duration_and_fresh_runtime(protocol):
    assert tuple(x["name"] for x in protocol["conditions"]) == m6c.CONDITIONS
    assert all(x["fresh_runtime"] for x in protocol["conditions"])
    assert (protocol["seed"], protocol["duration_ms"]) == (1, 500)


def test_fail_closed_contribution_gate_and_cached_assertion(protocol):
    admitted = protocol["admitted_motor_interfaces"]
    values = dict.fromkeys(admitted, .1)
    assert all(v == .1 for v in m6c.gate_contributions(values, m6c.CONDITIONS[0], admitted).values())
    assert not any(m6c.gate_contributions(values, m6c.CONDITIONS[1], admitted).values())
    tier_a_only = m6c.gate_contributions(values, m6c.CONDITIONS[2], admitted)
    assert all(tier_a_only[x] == .1 for x in m6c.TIER_A)
    assert all(tier_a_only[x] == 0 for x in m6c.EXPECTED_TIER_B)
    vector = [0.] * 42; m6c.assert_physical_admission(vector, protocol["actuator_admission_table"])
    vector[0] = .1
    with pytest.raises(RuntimeError, match="unauthorized"): m6c.assert_physical_admission(vector, protocol["actuator_admission_table"])


def test_equivalence_includes_all_preregistered_state():
    state = {key: [1, {"x": 2}] for key in m6c.EQUIVALENCE_FIELDS}
    assert m6c.pre_intervention_equivalent(state, copy.deepcopy(state))
    changed = copy.deepcopy(state); changed["rng_state"] = [2]
    assert not m6c.pre_intervention_equivalent(state, changed)


def test_c0_c12_and_conservative_classification():
    milestones = {x: True for x in m6c.MILESTONES}
    assert m6c.classify(milestones) == "INTEGRATED_SENSORIMOTOR_MOTOR_RETURN_OBSERVED"
    milestones["C12"] = False
    assert m6c.classify(milestones) == "INTEGRATED_SENSORIMOTOR_FEEDBACK_OBSERVED"
    milestones["C10"] = False
    assert m6c.classify(milestones) == "INTEGRATED_MULTI_LEG_CAUSALITY_CONFIRMED"
    milestones["C7"] = False
    assert m6c.classify(milestones) == "INTEGRATED_MULTI_CHANNEL_CAUSALITY_CONFIRMED"
    milestones["C6"] = False
    assert m6c.classify(milestones) == "INTEGRATED_MOTOR_CAUSALITY_CONFIRMED"
    milestones["C5"] = False
    assert m6c.classify(milestones) == "MAPPED_ACTIVITY_NO_PHYSICAL_CAUSALITY"


def test_condition_reduction_a_vs_b_and_a_vs_c():
    enabled = {"local_milestones": {f"C{i}": True for i in (1, 2, 3, 6, 7)},
        "first_command_divergence_vs_all_disabled": 2, "first_physical_divergence_vs_all_disabled": 3,
        "first_command_divergence_vs_tier_b_disabled": 4, "first_femur_divergence_vs_tier_b_disabled": 5,
        "first_body_divergence_vs_tier_b_disabled": 6, "unauthorized_contribution_count": 0,
        "physics_instability": False, "feedback_milestones": {}}
    control = {"pre_intervention_equivalence": True, "unauthorized_contribution_count": 0,
        "physics_instability": False}
    result = adapter.reduce_conditions({m6c.CONDITIONS[0]: enabled,
        m6c.CONDITIONS[1]: control, m6c.CONDITIONS[2]: control})
    assert result["milestones"]["C0"] and result["milestones"]["C9"]
    assert result["a_vs_b"]["first_physical_divergence"] == 3
    assert result["a_vs_c"]["first_femur_physical_divergence"] == 5


def test_stability_and_m7_readiness_logic():
    m = {x: True for x in m6c.MILESTONES}
    assert m6c.classify({**m, "C9": False}) == "PHYSICS_INSTABILITY"
    assert m6c.m7_readiness(provenance=True, milestones=m, interface_valid=True,
        sensory_valid=True, hidden_assistance=False, admissions=11).endswith("READY")
    assert m6c.m7_readiness(provenance=True, milestones=m, interface_valid=True,
        sensory_valid=True, hidden_assistance=True, admissions=11) == "NOT_READY"


def test_no_per_step_inventory_and_progress_rng_neutral(protocol, monkeypatch, capsys):
    import inspect, random
    source = inspect.getsource(adapter.run_canonical)
    assert source.count("enumerate_live_actuators") == 1
    assert source.index("enumerate_live_actuators") < source.index("for number, condition")
    state = random.getstate(); adapter.progress_header(); adapter.format_progress(1, m6c.CONDITIONS[0], .1, 500, 1, 1, None)
    assert random.getstate() == state
    assert "11 admitted motor channels" in capsys.readouterr().out
    assert protocol["performance_guards"]["per_physics_step_environment_construction"] is False


def test_ctrl_c_writes_incomplete_provenance(protocol, tmp_path, monkeypatch):
    def interrupt(**kwargs): raise KeyboardInterrupt
    records = [{"index": row["action_index"], "name": row["actuator"]}
               for row in protocol["actuator_admission_table"]]
    monkeypatch.setattr(adapter, "enumerate_live_actuators", lambda: records)
    with pytest.raises(KeyboardInterrupt):
        adapter.run_canonical(protocol, tmp_path / "result.json", interrupt)
    checkpoint = json.loads((tmp_path / "result.progress.json").read_text())
    assert checkpoint["run_status"] == "ABORTED_USER_INTERRUPT"
    assert checkpoint["canonical_result_complete"] is False


def test_hidden_assistance_audit_and_provenance_fail_closed():
    audit = m6c.hidden_assistance_audit()
    assert audit["hidden_locomotion_assistance_executed"] is False
    with pytest.raises(m6c.ProvenanceFailure): m6c.validate_m6b(m6b.build_not_run_artifact())
    with pytest.raises(m6c.ProvenanceFailure): m6c.load_provenance()
