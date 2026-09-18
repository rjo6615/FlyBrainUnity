import hashlib
import inspect
import json
from pathlib import Path

import numpy as np

from malecns_backend.embodiment.tactile_contact import (
    DISTAL_SEGMENT, LEGS, TactileContactConfig, TactileContactEncoder,
    distal_contact_vectors, load_tactile_populations,
)
from malecns_backend.embodiment.tactile_contact_audit import build_audit, serialized_audit

ROOT = Path(__file__).parents[1]
LOCKED = {
    "malecns_backend/embodiment/six_leg_map.json": "575186602ac1e5a6e3b2c6d680309880266f5d80e18fff44f989440f6cd0a4bc",
    "malecns_backend/embodiment/interface_output/m5d_tarsal_contact_load_audit.json": "a8f8c0451f615cd3632ffc2730893ab7aedc3448a9745416bcaf6d4543454090",
}


def forces(value=0.0):
    result = np.zeros((36, 3))
    result[5::6] = value
    return result


def test_exact_six_populations_complete_ids_and_sizes():
    populations = load_tactile_populations()
    assert tuple(populations) == LEGS
    assert [len(p.body_ids) for p in populations.values()] == [151, 378, 394, 115, 428, 411]
    source = build_audit()["populations"]
    assert [x["body_ids"] for x in source] == [list(p.body_ids) for p in populations.values()]
    assert all(len(p.dense_indices) == len(p.body_ids) for p in populations.values())


def test_distal_selection_norm_and_raw_telemetry():
    raw = np.arange(108.0).reshape(36, 3)
    selected = distal_contact_vectors(raw)
    assert DISTAL_SEGMENT == "Tarsus5"
    for i, leg in enumerate(LEGS):
        np.testing.assert_array_equal(selected[leg], raw[i * 6 + 5])
    frame = TactileContactEncoder(config=TactileContactConfig(seed=4)).encode(raw, 0, 1)["LF"]
    assert frame.force_magnitude == np.linalg.norm(raw[5])
    assert frame.all_segment_vectors == tuple(tuple(x) for x in raw[:6])


def test_strict_threshold_onset_release_reonset_and_bounded_transient():
    config = TactileContactConfig(engineering_threshold=1.0, transient_duration_ms=10,
                                  maximum_modeled_rate_hz=100, seed=2)
    encoder = TactileContactEncoder(config=config)
    assert not encoder.encode(forces(0), 0, 1)["LF"].contact
    assert not encoder.encode(forces(1 / np.sqrt(3)), 1, 1)["LF"].contact
    first = encoder.encode(forces(1), 2, 1)["LF"]
    held = encoder.encode(forces(1), 3, 1)["LF"]
    expired = encoder.encode(forces(1), 12, 1)["LF"]
    assert first.onset_time_ms == held.onset_time_ms == 2
    assert first.modeled_rate_hz == 100 and held.modeled_rate_hz == 90
    assert expired.modeled_rate_hz == 0
    assert encoder.encode(forces(0), 13, 1)["LF"].onset_time_ms is None
    assert encoder.encode(forces(1), 14, 1)["LF"].onset_time_ms == 14


def test_population_rng_streams_independent_and_disabled_draws_none():
    cfg = TactileContactConfig(seed=77)
    a, b = TactileContactEncoder(config=cfg), TactileContactEncoder(config=cfg)
    af, bf = a.encode(forces(1), 0, 10), b.encode(forces(1), 0, 10)
    assert {leg: f.generated_dense_indices for leg, f in af.items()} == {
        leg: f.generated_dense_indices for leg, f in bf.items()}
    states = {leg: repr(r.bit_generator.state) for leg, r in a.rng.items()}
    disabled = TactileContactEncoder(config=TactileContactConfig(seed=77, enabled=False))
    before = {leg: repr(r.bit_generator.state) for leg, r in disabled.rng.items()}
    disabled.encode(forces(1), 0, 10)
    after = {leg: repr(r.bit_generator.state) for leg, r in disabled.rng.items()}
    assert before == after
    # Different population streams are spawned rather than aliased.
    assert len(set(states.values())) == 6


def test_external_drive_api_only():
    class Brain:
        def __init__(self): self.calls = []
        def set_external_drive(self, indices, rate): self.calls.append((indices, rate))
    encoder = TactileContactEncoder(config=TactileContactConfig(seed=8, maximum_modeled_rate_hz=1000))
    frames = encoder.encode(forces(1), 0, 1)
    brain = Brain()
    delivered = encoder.apply_external_drive(brain, frames, 1)
    assert brain.calls == [(delivered, 1000.0)]
    source = inspect.getsource(TactileContactEncoder.apply_external_drive)
    assert "set_external_drive" in source
    for forbidden in (".v", "weights", "threshold", "connectivity"):
        assert forbidden not in source


def test_synthetic_validation_and_serialization_deterministic():
    first, second = build_audit(), build_audit()
    assert first["synthetic_open_loop"]["status"] == "PASS"
    assert serialized_audit(first) == serialized_audit(second)
    assert json.loads(serialized_audit(first)) == first


def test_locked_artifact_hashes_unchanged():
    for relative, expected in LOCKED.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
