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
    assert activation.verify_provenance()["verified"]


def test_not_run_artifact_truthful_null_and_deterministic():
    artifact = json.loads(audit.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    assert artifact["run_status"] == "NOT_RUN" and artifact["classification"] is None
    assert all(x["first_candidate_spike_ms"] is None for x in artifact["per_leg"].values())
    encode = lambda x: json.dumps(x, sort_keys=True, separators=(",", ":"))
    assert encode(activation.base_report()) == encode(activation.base_report())


def test_source_has_no_controller_cpg_or_motor_command_path():
    source = Path(audit.__file__).read_text(encoding="utf-8")
    assert "commands = _joint_positions(obs).copy()" in source
    assert "commands.copy()" in source
    assert "decoder.decode" not in source and "MatchedControlPipeline" not in source
