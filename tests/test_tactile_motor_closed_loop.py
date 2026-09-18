import json
import hashlib
from pathlib import Path
import pytest

from malecns_backend.embodiment import tactile_motor_closed_loop as loop
from malecns_backend.embodiment import tactile_motor_closed_loop_audit as audit
from malecns_backend.embodiment.tactile_motor_matched_control import MatchedControlPipeline
from malecns_backend.embodiment.tactile_motor_loop import ACTUATOR_INDICES


def test_locked_protocol_and_mapping():
    assert (loop.SEED, loop.DURATION_MS, loop.DEFAULT_TIMESTEP_S, loop.NEURAL_DT_MS) == (1, 100.0, .0001, .5)
    assert ACTUATOR_INDICES == {"LF": 5, "LM": 12, "LH": 19, "RF": 26, "RM": 33, "RH": 40}


def test_m5d4c_artifact_and_implementation_are_locked():
    assert loop.verify_m5d4c_lock()["verified"]


def test_m5d4c_implementation_lock_is_line_ending_invariant(tmp_path, monkeypatch):
    source = loop.M5D4C_IMPLEMENTATION.read_bytes()
    crlf = source.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    assert hashlib.sha256(crlf).hexdigest() == (
        "967afaf2f6cde59956cee5b3c3c2d3a1c49ce5d007d7b8d92924615bf66d5048")
    candidate = tmp_path / "tactile_motor_matched_control.py"
    candidate.write_bytes(crlf)
    monkeypatch.setattr(loop, "M5D4C_IMPLEMENTATION", candidate)
    assert loop.verify_m5d4c_lock()["verified"]


def test_m5d4c_semantic_implementation_change_fails_closed(tmp_path, monkeypatch):
    candidate = tmp_path / "tactile_motor_matched_control.py"
    candidate.write_bytes(loop.M5D4C_IMPLEMENTATION.read_bytes() + b"\nSCIENTIFIC_CHANGE = True\n")
    monkeypatch.setattr(loop, "M5D4C_IMPLEMENTATION", candidate)
    with pytest.raises(RuntimeError, match="M5D-4C provenance mismatch"):
        loop.verify_m5d4c_lock()


def test_m5d4c_validated_implementation_and_artifact_digests_are_unchanged():
    assert hashlib.sha256(loop._canonical_bytes(
        loop.M5D4C_IMPLEMENTATION.read_bytes())).hexdigest() == loop.M5D4C_LOCKS["implementation_sha256"]
    assert hashlib.sha256(loop.M5D4C_ARTIFACT.read_bytes()).hexdigest() == loop.M5D4C_LOCKS["artifact_sha256"]


def test_first_failed_attempt_is_preserved_and_diagnostic_only():
    path = loop.M5D4C_ARTIFACT.with_name(
        "tactile_motor_closed_loop_100ms_first_attempt_provenance_failure.json")
    artifact = json.loads(path.read_text(encoding="utf-8"))
    assert artifact["run_status"] == "FAILED"
    assert artifact["classification"] == "UNRESOLVED_CAUSAL_FAILURE"
    assert artifact["reason"] == "RuntimeError: M5D-4C provenance mismatch"
    assert "Traceback" in artifact["traceback"]
    assert artifact["diagnostic"]["simulation_entered"] is False


def test_diagnostic_mode_never_enters_100ms_simulation(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "run_live", lambda *_: pytest.fail("simulation entered"))
    output = tmp_path / "diagnostic.json"
    assert audit.main(["--json", str(output)]) == 0
    assert json.loads(output.read_text())["run_status"] == "NOT_RUN"


def test_all_earlier_provenance_locks_remain_fail_closed():
    from malecns_backend.embodiment.tactile_motor_loop import verify_locked_hashes
    assert verify_locked_hashes()


def test_actual_m5d4c_pipeline_is_reused_and_gate_only_changes_admission():
    assert loop.MatchedControlPipeline is MatchedControlPipeline
    enabled = MatchedControlPipeline(True).update(.1, .2, .0005)
    disabled = MatchedControlPipeline(False).update(.1, .2, .0005)
    assert enabled.raw_neural_contribution == disabled.raw_neural_contribution == .2
    assert enabled.admitted_neural_contribution == .2 and disabled.admitted_neural_contribution == 0


def test_prefix_is_observed_not_blindly_asserted():
    report = loop.base_report()
    assert not loop.validate_prefix(report)
    report["m5d4c_prefix_validation"]["observed"] = {
        "mapped": 14.5, "raw": 14.5, "admitted": 14.5, "action": 14.5,
        "ctrl": 14.6, "physical": 14.6}
    assert loop.validate_prefix(report)
    report["m5d4c_prefix_validation"]["observed"]["ctrl"] = 14.7
    assert not loop.validate_prefix(report)


@pytest.mark.parametrize(("change", "expected"), [
    ({"provenance": False}, "PROVENANCE_FAILURE"),
    ({"pre_equal": False}, "PRE_INTERVENTION_DIVERGENCE"),
    ({"prefix": False}, "PREFLIGHT_PREFIX_MISMATCH"),
    ({"intervention": False}, "NO_NEURAL_INTERVENTION"),
    ({"physical_before_intervention": True}, "UNRESOLVED_CAUSAL_FAILURE"),
    ({"rng_parity": False}, "RNG_PARITY_FAILURE"),
])
def test_fail_closed_precedence(change, expected):
    evidence = dict(provenance=True, pre_equal=True, prefix=True, intervention=True,
        physical_before_intervention=False, rng_parity=True, physical=True)
    evidence.update(change); assert loop.classify(evidence) == expected


def test_feedback_classifications_require_ordered_stages():
    e = dict(provenance=True, pre_equal=True, prefix=True, intervention=True,
        physical_before_intervention=False, rng_parity=True, physical=True)
    assert loop.classify(e) == "MOTOR_CAUSALITY_CONFIRMED_NO_FEEDBACK_WITHIN_WINDOW"
    e.update(physical_sensory=True, sensory_encoding=True)
    assert loop.classify(e) == "MOTOR_TO_SENSORY_FEEDBACK_CONFIRMED"
    e["post_cns"] = True; assert loop.classify(e) == "CLOSED_LOOP_TO_CNS_CONFIRMED"
    e["post_motor"] = True; assert loop.classify(e) == "CLOSED_LOOP_CAUSAL_CHAIN_CONFIRMED"


def test_not_run_artifact_is_complete_compact_and_deterministic():
    artifact = json.loads(audit.DEFAULT_OUTPUT.read_text())
    assert artifact["run_status"] == "NOT_RUN" and artifact["classification"] is None
    required = {"protocol", "provenance", "m5d4c_prefix_validation", "pre_intervention_equivalence",
        "contact_evidence", "tactile_transduction_evidence", "tactile_delivery_evidence",
        "downstream_cns_evidence", "mapped_motor_evidence", "raw_neural_contribution_evidence",
        "admitted_neural_contribution_evidence", "action_divergence", "ctrl_divergence",
        "qacc_divergence", "qvel_divergence", "qpos_divergence", "physical_sensory_divergence",
        "modeled_sensory_encoding_divergence", "post_feedback_cns_divergence",
        "post_feedback_mapped_motor_divergence", "rng_parity", "causal_milestones",
        "causal_ordering", "per_leg_summary", "limitations"}
    assert required <= artifact.keys() and audit.DEFAULT_OUTPUT.stat().st_size < 30000
    assert loop.serialize(loop.base_report()) == loop.serialize(loop.base_report())


def test_no_retry_or_noncanonical_protocol():
    assert loop.base_report()["protocol"]["automatic_retries"] == 0
    with pytest.raises(ValueError): audit.run_live(99.0, 1)
