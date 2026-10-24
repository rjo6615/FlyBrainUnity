"""Batch ordering and fail-closed evaluation of legacy per-leg evidence."""
import copy
import json
from unittest.mock import patch

import pytest

from malecns_backend.embodiment import six_foot_contact_calibration as batch


def condition(leg, contact):
    pairs = [{'geom1_id': 1, 'geom1_name': batch.single.SURFACE_NAME,
              'geom2_id': 2, 'geom2_name': f'0/{leg}Tarsus5'}]
    return {
        'samples': [{'simulation_time_s': i * .0001, 'raw_tarsus5_vector': [1., 0., 0.] if contact else [0., 0., 0.],
                     'magnitude': 1. if contact else 0., 'selected_pair_present': contact,
                     'contact_metadata': {'all_contact_pairs': pairs if contact else []}}
                    for i in range(501)],
        'pose_proof': {'qpos_before': [0., 1.], 'qpos_after_surface_placement': [0., 1.], 'exactly_equal': True},
        'tarsus_geom': {'id': 2, 'name': f'0/{leg}Tarsus5'},
        'surface_geom': {'id': 1, 'name': batch.single.SURFACE_NAME},
        'placement': {'gap': 0. if contact else batch.single.CONTROL_GAP,
                      'penetration': batch.single.CONTACT_PENETRATION if contact else 0.,
                      'surface_half_size': list(batch.single.SURFACE_HALF_SIZE)},
    }


def complete(leg='LM'):
    # Let the actual legacy report builder compute statistics/correspondence.
    with patch.object(batch.single.importlib, 'import_module', return_value=object()), \
            patch.object(batch.single, '_run_condition', side_effect=[condition(leg, False), condition(leg, True)]):
        return batch.single.build_report(live=True, leg=leg)


def test_actual_legacy_report_structure_passes_without_mutation():
    report = complete()
    before = copy.deepcopy(report)
    result = batch.evaluate_leg(report, 'LM')
    assert result['accepted'] and all(result['checks'].values())
    assert result['negative_control_samples'] == result['verified_contact_samples'] == 501
    assert report == before


@pytest.mark.parametrize('change', [
    'no_contact', 'control_force', 'missing_control', 'truncated', 'different_schedule',
    'pose', 'geometry', 'penetration', 'nan', 'wrong_magnitude', 'wrong_leg', 'control_touch', 'wrong_pair',
])
def test_incomplete_or_disagreeing_evidence_never_admits_a_leg(change):
    report = complete()
    if change == 'no_contact':
        for s in report['contact']['samples']: s['selected_pair_present'] = False
    elif change == 'control_force':
        s = report['control']['samples'][0]; s.update(magnitude=1., raw_tarsus5_vector=[1., 0., 0.])
    elif change == 'missing_control': report['control']['samples'] = []
    elif change == 'truncated': report['contact']['samples'].pop()
    elif change == 'different_schedule': report['contact']['samples'][1]['simulation_time_s'] += .00001
    elif change == 'pose': report['contact']['pose_proof']['qpos_after_surface_placement'][0] = .1
    elif change == 'geometry': report['contact']['tarsus_geom']['name'] = '0/LFTarsus1'
    elif change == 'penetration': report['contact']['placement']['penetration'] *= 2
    elif change == 'nan': report['contact']['samples'][0]['magnitude'] = float('nan')
    elif change == 'wrong_magnitude': report['contact']['samples'][0]['magnitude'] = 2.
    elif change == 'wrong_leg': report['selected_leg'] = 'LF'
    elif change == 'wrong_pair': report['contact']['samples'][0]['contact_metadata']['all_contact_pairs'][0]['geom2_id'] = 999
    elif change == 'control_touch': report['control']['samples'][0]['selected_pair_present'] = True
    assert not batch.evaluate_leg(report, 'LM')['accepted']


def test_all_legs_run_once_with_fixed_settings_and_preserve_partial_failure(tmp_path):
    calls = []
    original = batch.single.build_report
    def run(**kwargs):
        calls.append(kwargs)
        if kwargs['leg'] == 'RF': raise RuntimeError('physical measurement failed')
        with patch.object(batch.single.importlib, 'import_module', return_value=object()), \
                patch.object(batch.single, '_run_condition', side_effect=[condition(kwargs['leg'], False), condition(kwargs['leg'], True)]):
            return original(**kwargs)
    with patch.object(batch.single, 'build_report', side_effect=run):
        report = batch.build_report(live=True, progress=lambda *_: None)
    assert [c['leg'] for c in calls] == list(batch.LEGS)
    assert all(c['duration_s'] == .05 and c['timestep_s'] == .0001 and c['live'] for c in calls)
    assert report['accepted_legs'] == ['LF', 'LM', 'LH', 'RM', 'RH']
    assert not report['all_six_accepted'] and report['run_status'] == 'INCOMPLETE'
    assert report['legs']['RF']['evidence']['run_status'] == 'ERROR'
    assert report['protocol']['automatic_retries'] == 0
    json.dumps(report, allow_nan=False)


def test_dry_run_is_not_evidence_and_cli_has_no_tuning_knobs(tmp_path):
    output = tmp_path / 'dry.json'
    assert batch.main(['--output', str(output)]) == 1
    report = json.loads(output.read_text())
    assert report['accepted_legs'] == []
    assert all(x['evidence']['run_status'] == 'NOT_RUN' for x in report['legs'].values())
    with pytest.raises(SystemExit): batch.main(['--output', str(output), '--duration-s', '1'])


def test_nonfinite_evidence_is_rejected_and_saved_as_explicit_null_locations():
    evidence = complete()
    evidence['contact']['samples'][0]['magnitude'] = float('nan')
    with patch.object(batch.single, 'build_report', return_value=evidence):
        report = batch.build_report(live=True, progress=lambda *_: None)
    assert report['accepted_legs'] == []
    assert report['legs']['LM']['evidence']['contact']['samples'][0]['magnitude'] is None
    assert report['legs']['LM']['nonfinite_measurement_paths'] == ['evidence.contact.samples[0].magnitude']
    json.dumps(report, allow_nan=False)
