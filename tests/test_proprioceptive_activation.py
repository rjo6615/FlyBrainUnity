import copy
import hashlib
import json
from pathlib import Path

import pytest

from malecns_backend.embodiment import proprioceptive_activation as activation
from malecns_backend.embodiment import proprioceptive_activation_audit as audit
from malecns_backend.embodiment.sensory import SensoryEncoder


EXPECTED = {
    "LF": (5, "chordotonal T1 left", 23), "LM": (12, "chordotonal T2 left", 80),
    "LH": (19, "chordotonal T3 left", 93), "RF": (26, "chordotonal T1 right", 13),
    "RM": (33, "chordotonal T2 right", 83), "RH": (40, "chordotonal T3 right", 100),
}


def test_locked_six_mappings_counts_and_sources():
    got = activation.mapping_inventory()
    assert {leg: (x["action_index"], x["population"], x["mapped_neuron_count"])
            for leg, x in got.items()} == EXPECTED
    assert len(got) == 6 and len({i for x in got.values() for i in x["dense_indices"]}) == 392


def test_existing_encoder_and_parameters_are_not_reimplemented():
    assert activation.SensoryEncoder is SensoryEncoder
    assert activation.encoder_parameters() == {
        "implementation": "malecns_backend.embodiment.sensory.SensoryEncoder",
        "angle_range_rad": [-1.35, 1.3], "preferred_positions": "(k + 0.5) / population_size",
        "gaussian_width_normalized": .25, "maximum_rate_hz": 120., "cutoff_hz": 5.,
        "baseline_hz": 0., "normalization": "(angle-angle_min)/(angle_max-angle_min)",
        "event_probability": "rate_hz * 0.5 / 1000"}


def test_per_leg_rngs_are_independent_deterministic_and_common():
    a, b = activation.proprio_rngs(), activation.proprio_rngs()
    draws_a = {leg: rng.random(8).tolist() for leg, rng in a.items()}
    draws_b = {leg: rng.random(8).tolist() for leg, rng in b.items()}
    assert draws_a == draws_b
    assert len({tuple(x) for x in draws_a.values()}) == 6


def test_protocol_gate_tactile_and_motor_safety_are_explicit():
    report = activation.base_report()
    assert report["protocol"] == {"seed": 1, "duration_ms": 100., "physics_dt_ms": .1,
        "neural_dt_ms": .5, "conditions": ["PROPRIO_ENABLED", "PROPRIO_DISABLED"],
        "automatic_retries": 0, "parameter_mutations": []}
    assert report["intervention"]["only_difference"] == "proprioceptive delivery gate"
    assert report["intervention"]["motor_output_applied"] is False
    assert report["intervention"]["neural_motor_contribution_to_actuators"] == 0
    assert report["tactile"]["encoder_modified"] is False


def test_live_rejects_retries_seed_sweeps_and_protocol_changes():
    with pytest.raises(ValueError): audit.run_live(99, 1)
    with pytest.raises(ValueError): audit.run_live(100, 2)


def test_classification_is_fail_closed_and_evidence_driven():
    common = {"provenance": True, "physics_ok": True, "rng_parity": True, "pre_equal": True}
    assert activation.classify({}) == "PROVENANCE_FAILURE"
    assert activation.classify({**common, "rng_parity": False}) == "RNG_PARITY_FAILURE"
    assert activation.classify({**common, "pre_equal": False}) == "PRE_DELIVERY_NEURAL_DIVERGENCE"
    assert activation.classify({**common, "delivered": True}) == "PROPRIOCEPTIVE_DELIVERY_NO_DOWNSTREAM_EFFECT"
    assert activation.classify({**common, "propagated_legs": 5}) == "PARTIAL_PROPRIOCEPTIVE_PROPAGATION"
    assert activation.classify({**common, "propagated_legs": 6}) == "SIX_TIBIA_PROPRIOCEPTIVE_PROPAGATION_CONFIRMED"


def test_provenance_and_locked_artifacts_are_unchanged():
    result = activation.verify_provenance()
    assert result["verified"]
    assert result["locks"]["sensory_feedback_boundary_100ms.json"] == (
        "151eb07263b4c7d5e5af8668f8405738e320faac451742a1eecc765dd3fa20f9")


def test_authoritative_m5d4e_result_and_critical_findings():
    path = activation._lock_paths()["sensory_feedback_boundary_100ms.json"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == activation.LOCKS[path.name]
    artifact = json.loads(path.read_text(encoding="utf-8"))
    activation._validate_m5d4e_artifact(artifact)
    channel = artifact["channels"]["LM_Tarsus5_tactile"]
    assert artifact["run_status"] == "COMPLETE"
    assert artifact["classification"] == "NO_SENSOR_RELEVANT_PHYSICAL_DIVERGENCE"
    assert artifact["full_body_physics"]["first_contact_force"]["first_differing_index"] == "[24][0]"
    assert artifact["full_body_physics"]["first_divergence_ms"] == pytest.approx(14.6)
    assert channel["source_row"] == 11
    assert channel["global_first_force_is_encoder_source"] is False
    assert channel["maximum_force_magnitude_difference"]["value"] == 0
    assert artifact["sensor_relevant_physics"]["first_divergence_ms"] is None
    assert artifact["active_sensory_channels"][0]["mapped_neuron_count"] == 378
    assert len(artifact["available_but_inactive_proprioception"]) == 6


def test_modified_m5d4e_raw_artifact_fails_provenance(tmp_path, monkeypatch):
    paths = activation._lock_paths()
    copies = {}
    for name, source in paths.items():
        destination = tmp_path / name
        destination.write_bytes(source.read_bytes())
        copies[name] = destination
    copies["sensory_feedback_boundary_100ms.json"].write_bytes(
        copies["sensory_feedback_boundary_100ms.json"].read_bytes() + b" ")
    monkeypatch.setattr(activation, "_lock_paths", lambda: copies)
    with pytest.raises(RuntimeError, match="provenance mismatch"):
        activation.verify_provenance()


@pytest.mark.parametrize(("path", "value"), [
    (("run_status",), "NOT_RUN"),
    (("classification",), "SOME_OTHER_RESULT"),
    (("first_blocked_boundary",), "another boundary"),
    (("prefix_reproduction", "passed"), False),
    (("provenance", "verified"), False),
])
def test_m5d4e_semantic_lock_fails_closed(path, value):
    artifact_path = activation._lock_paths()["sensory_feedback_boundary_100ms.json"]
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    altered = copy.deepcopy(artifact)
    target = altered
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(RuntimeError, match="semantic provenance mismatch"):
        activation._validate_m5d4e_artifact(altered)


def test_earlier_and_implementation_locks_remain_unchanged():
    assert activation.LOCKS == {
        "sensory_feedback_boundary_100ms.json": "151eb07263b4c7d5e5af8668f8405738e320faac451742a1eecc765dd3fa20f9",
        "sensory_feedback_boundary.py": "71f8dabb2cca77670a32e493dc028619ec5f070097b5bf3aac04ad0432388585",
        "sensory_feedback_boundary_audit.py": "e61d501d856895519f320739a79ef17e8eef376f18cef1df5960496366e10732",
        "tactile_motor_closed_loop_100ms.json": "d684f38cd50edf6f494f00678d33a67c8cd89b50a34fd4815d5af90f05611e09",
        "tactile_motor_closed_loop.py": "8434a6a8e946c2405a1a2271956a9aa88e8f4ba412b0861c55e109b33637d1d6",
        "tactile_motor_closed_loop_audit.py": "450a98112047a4a271d01a29caafff76b960a9bf79b22af68fbc25106cb653c8",
    }


def test_failed_first_invocation_is_preserved_and_base_report_is_deterministic():
    artifact = json.loads(audit.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    preserved = audit.DEFAULT_OUTPUT.with_name(
        "proprioceptive_activation_100ms_first_attempt_provenance_failure.json")
    assert preserved.read_bytes() == audit.DEFAULT_OUTPUT.read_bytes()
    assert artifact["run_status"] == "FAILED"
    assert artifact["classification"] == "PROVENANCE_FAILURE"
    assert artifact["traceback"]
    assert artifact["provenance"]["expected"]["sensory_feedback_boundary_100ms.json"] == (
        "318217af36f326b31464bc5373f9b1956fb49cf4bb433f26fe4ce82182d3b38c")
    assert all(x["first_candidate_spike_ms"] is None for x in artifact["per_leg"].values())
    encode = lambda x: json.dumps(x, sort_keys=True, separators=(",", ":"))
    assert encode(activation.base_report()) == encode(activation.base_report())


def test_source_has_no_controller_cpg_or_motor_command_path():
    source = Path(audit.__file__).read_text(encoding="utf-8")
    assert "commands = _joint_positions(obs).copy()" in source
    assert "commands.copy()" in source
    assert "decoder.decode" not in source and "MatchedControlPipeline" not in source
