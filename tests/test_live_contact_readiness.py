"""Exact distal identity, bounded reductions, and bounded runner without physics."""
import copy
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
import pytest

from malecns_backend.live.contact_readiness import (
    LEGS, ContactReadinessSurvey, sample_distal_contact, main)


def fixture():
    # Geom 0 ground, 1 LF Tarsus1 (must be excluded), 2..7 exact Tarsus5.
    model = SimpleNamespace(ngeom=8, geom_bodyid=[0, 99, 1, 2, 3, 4, 5, 6])
    pairs = [SimpleNamespace(geom1=0, geom2=1), SimpleNamespace(geom1=3, geom2=0)]
    physics = SimpleNamespace(model=model, data=SimpleNamespace(contact=pairs, ncon=2))
    identity = {'ground_geom_ids': (0,), 'tarsus5_body_ids': dict(zip(LEGS, range(1, 7)))}
    forces = np.zeros((36, 3)); forces[5] = [3, 4, 0]; forces[11] = [0, 0, 2]
    return physics, identity, forces


def record(time, values):
    return {'physics_transition_index': int(time), 'physics_time_ms': time,
            'contact_information': {'distal_contact_readiness': values}}


def test_exact_distal_pairs_and_force_rows_without_state_mutation():
    physics, identity, forces = fixture()
    before = forces.copy(); old_identity = copy.deepcopy(identity)
    result = sample_distal_contact(physics, identity, forces)
    assert not result['LF']['ground_contact']  # Tarsus1 contact is insufficient.
    assert result['LF']['force_magnitude'] == 5
    assert result['LM']['ground_contact']
    assert result['LM']['exact_geom_pairs'] == ((3, 0),)
    assert [result[x]['force_row'] for x in LEGS] == [5, 11, 17, 23, 29, 35]
    np.testing.assert_array_equal(forces, before)
    assert identity == old_identity
    identity['tarsus5_body_ids']['LM'] = None
    assert not sample_distal_contact(physics, identity, forces)['LM']['identity_available']
    for bad in (np.zeros((6, 3)), np.full((36, 3), np.nan)):
        with pytest.raises(ValueError): sample_distal_contact(physics, identity, bad)


def test_aggregates_distinguish_missing_identity_force_and_contact():
    physics, identity, forces = fixture()
    survey = ContactReadinessSurvey()
    survey({'neural_transition_index': 1})
    survey(record(1., sample_distal_contact(physics, identity, forces)))
    forces[:] = 0
    survey(record(2., sample_distal_contact(physics, identity, forces)))
    report = survey.report()
    assert report['samples'] == 2 and not report['tactile_delivery_enabled']
    assert report['legs']['LM']['contact_with_force_samples'] == 1
    assert report['legs']['LM']['contact_without_force_samples'] == 1
    assert report['legs']['LM']['ground_contact_onsets'] == 1
    assert report['legs']['LF']['force_without_ground_contact_samples'] == 1
    assert report['legs']['LF']['status'] == 'NO_OBSERVED_TARSUS5_GROUND_CONTACT'
    snapshot = survey.report()
    with pytest.raises(ValueError): survey(record(2., sample_distal_contact(physics, identity, forces)))
    assert survey.report() == snapshot
    assert ContactReadinessSurvey().report()['legs']['LM']['status'] == 'IDENTITY_UNAVAILABLE'


def test_runner_bounds_simulated_time_closes_and_saves(tmp_path):
    physics, identity, forces = fixture()
    def factory(*, telemetry_observer):
        session = Mock()
        session.initialize.return_value = SimpleNamespace(time_ms=0.)
        times = iter([1., 2.])
        def step(**kwargs):
            time = next(times)
            telemetry_observer(record(time, sample_distal_contact(physics, identity, forces)))
            return SimpleNamespace(time_ms=time)
        session.step.side_effect = step
        factory.session = session
        return session
    output = tmp_path / 'survey.json'
    with patch('malecns_backend.live.headless.create_live_v3_session', side_effect=factory):
        assert main(['--duration-s', '.002', '--output', str(output)]) == 0
    assert factory.session.step.call_count == 2
    factory.session.close.assert_called_once()
    report = json.loads(output.read_text())
    assert report['completed'] and report['samples'] == 2
    with pytest.raises(SystemExit): main(['--duration-s', 'nan', '--output', str(output)])


def test_interruption_saves_partial_report_and_closes(tmp_path):
    session = Mock()
    session.initialize.return_value = SimpleNamespace(time_ms=0.)
    session.step.side_effect = KeyboardInterrupt
    output = tmp_path / 'partial.json'
    with patch('malecns_backend.live.headless.create_live_v3_session', return_value=session):
        assert main(['--output', str(output)]) == 1
    session.close.assert_called_once()
    report = json.loads(output.read_text())
    assert not report['completed'] and report['error'] == 'KeyboardInterrupt'
    assert report['samples'] == 0
