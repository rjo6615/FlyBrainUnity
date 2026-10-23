"""Coverage extremes and matched resets on the real LIF runtime."""
from types import SimpleNamespace

import numpy as np
import pytest

from malecns_backend.embodiment.six_tibia import load_six_tibia_interfaces
from malecns_backend.live.sensory_coverage import angle_at, encoder_coverage, run_condition, main
from test_live_upstream_diagnostics import fixture


def test_all_frozen_sensors_recruited_somewhere_in_range():
    coverage = encoder_coverage(load_six_tibia_interfaces())
    assert len(coverage) == 6
    assert sum(len(value['neurons']) for value in coverage.values()) == 392
    for value in coverage.values():
        assert value['minimum_active_neurons'] > 0
        assert all(row['peak_rate_hz'] > 119.9 for row in value['neurons'])
        assert all(row['active_angle_samples'] > 0 for row in value['neurons'])


def test_prescribed_angles_and_invalid_inputs():
    assert angle_at('sweep_up', 0, (-1.35, 1.3)) == -1.35
    assert angle_at('sweep_down', 0, (-1.35, 1.3)) == 1.3
    assert angle_at('midpoint', .9, (-1., 1.)) == 0
    with pytest.raises(ValueError):
        encoder_coverage({}, 1)
    with pytest.raises(SystemExit):
        main(['--output', 'unused.json', '--duration-s', 'nan'])


def test_real_lif_matched_reset_and_event_delivery():
    brain, _ = fixture()
    sensor = SimpleNamespace(body_ids=(101,), dense_indices=(0,), name='sensor')
    interfaces = {'LF': SimpleNamespace(sensor=sensor, joint_range_rad=(-1.35, 1.3))}
    targets = {'motor': (2,)}
    first = run_condition(brain, interfaces, targets, 'midpoint', .2)
    # Contaminate state; next condition must reset it completely.
    brain.spike_counts[:] = 900
    second = run_condition(brain, interfaces, targets, 'midpoint', .2)
    assert first == second
    sensor_row = first['sensory']['LF'][0]
    assert sensor_row['delivered_events'] > 0
    assert sensor_row['spikes'] == sensor_row['delivered_events']
    assert first['candidate_motors']['motor'][0]['body_id'] == 103
    with pytest.raises(ValueError):
        run_condition(brain, interfaces, targets, 'midpoint', 0)


def test_pathway_probe_preserves_neural_arrays_rng_and_reports_each_condition():
    from test_live_upstream_diagnostics import DEFINITIONS, NAME
    brain, _ = fixture()
    # Excitatory sensor -> intermediate -> candidate motor, plus direct branch.
    brain.pre_sign[1] = 1.
    brain.indptr = np.array([0, 1, 3, 3, 3])
    brain.indices = np.array([1, 2, 3])
    brain.weights = np.array([6., 8., 7.])
    brain.data.synapse_counts = np.array([6, 8, 7])
    sensor = SimpleNamespace(body_ids=(101,), dense_indices=(0,), name='sensor')
    interfaces = {'LF': SimpleNamespace(sensor=sensor, joint_range_rad=(-1.35, 1.3))}
    targets = {NAME: (2, 3)}
    for condition in ('midpoint', 'sweep_up', 'sweep_down'):
        plain = run_condition(brain, interfaces, targets, condition, .2)
        arrays = {key: value.copy() for key, value in vars(brain).items()
                  if isinstance(value, np.ndarray)}
        rng_state = str(brain.rng.bit_generator.state)
        traced = run_condition(brain, interfaces, targets, condition, .2,
                               pathway_definitions=DEFINITIONS)
        state = traced.pop('pathway_diagnostics')
        assert traced == plain
        for key, value in arrays.items():
            np.testing.assert_array_equal(getattr(brain, key), value)
        assert str(brain.rng.bit_generator.state) == rng_state
        assert state['samples'] == traced['neural_steps']
        assert state['identity_verified'] and state['readout_verified']
        assert state['pathway_identity_verified']
        nodes = {row['body_id']: row for row in state['pathway_nodes']}
        assert set(nodes) == {101, 102}
        assert nodes[101]['encoded_rate_samples'] == traced['neural_steps']
        assert nodes[101]['external_delivered_steps'] == traced['sensory']['LF'][0]['delivered_events']
        assert nodes[102]['max_v'] is not None
        assert nodes[102]['peak_abs_g_exc'] > 0
        for row in state['channels'][NAME]:
            assert row['sensory_path']['body_ids'][:2] == (101, 102)
            assert row['spikes'] == next(x['spikes'] for x in traced['candidate_motors'][NAME]
                                         if x['body_id'] == row['body_id'])
    with pytest.raises(ValueError, match='targets'):
        run_condition(brain, interfaces, {NAME: (3, 2)}, 'midpoint', .2,
                      pathway_definitions=DEFINITIONS)


def test_pathway_flag_requires_neural_before_loading(tmp_path):
    from unittest.mock import patch
    with patch('malecns_backend.live.sensory_coverage.load_six_tibia_interfaces') as load:
        with pytest.raises(SystemExit):
            main(['--pathway-diagnostics', '--output', str(tmp_path / 'unused.json')])
        load.assert_not_called()
