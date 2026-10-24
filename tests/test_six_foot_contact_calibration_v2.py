"""Synthetic evidence tests; these do not substitute for FlyGym physics."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest

from malecns_backend.embodiment import six_foot_contact_calibration_v2 as v2


def evidence(leg='LM'):
    names = ['ground', v2.single.SURFACE_NAME, f'0/{leg}Tarsus5']
    report = {'protocol': copy.deepcopy(v2.PROTOCOL), 'run_status': 'COMPLETE',
              'selected_leg': leg, 'selected_segment': 'Tarsus5', 'male_cns_used': False,
              'duration_s': .05, 'timestep_s': .0001}
    for label in ('control', 'contact'):
        contact = label == 'contact'
        pos = (v2.single.surface_position([0., 0., 1.], .1, contact=True).tolist()
               if contact else list(v2.REMOTE_POSITION))
        positions, radii = [[0., 0., 1.], pos], [.1, .04]
        pair = {'geom1_id': 2, 'geom1_name': names[2], 'geom2_id': 1, 'geom2_name': names[1]}
        report[label] = {
            'run_status': 'COMPLETE', 'geom_names': names.copy(),
            'tarsus_geom': {'id': 2, 'name': names[2]}, 'surface_geom': {'id': 1, 'name': names[1]},
            'reset_qvel': [0., 0.], 'held_joints': [1., 2.],
            'pose_proof': {'qpos_before': [0., 1.], 'qpos_after_surface_placement': [0., 1.], 'exactly_equal': True},
            'placement': {'surface_position': pos, 'surface_half_size': list(v2.single.SURFACE_HALF_SIZE),
                          'tarsus_world_position': [0., 0., 1.], 'tarsus_conservative_radius': .1,
                          'gap': 0. if contact else None,
                          'penetration': v2.single.CONTACT_PENETRATION if contact else 0.},
            'samples': [copy.deepcopy({
                'simulation_time_s': i * .0001, 'magnitude': 1. if contact else 0.,
                'raw_tarsus5_vector': [1., 0., 0.] if contact else [0., 0., 0.],
                'selected_pair_present': contact,
                'contact_metadata': {'all_contact_pairs': [pair] if contact else []},
                'geom_positions': positions, 'geom_radii': radii,
                'sphere_clearance': v2.clearance(*np.asarray(positions), np.asarray(radii)),
                'collision_masks': v2.collision_masks(3, 2, 1, contact).tolist(),
                'explicit_pair_count': 0}) for i in range(501)]}
    return report


def test_complete_synthetic_evidence_and_unmodified_v1_rejection():
    report = evidence()
    before = copy.deepcopy(report)
    assert v2.evaluate_leg(report, 'LM')['accepted']
    assert not v2.v1.evaluate_leg(report, 'LM')['accepted']
    assert report == before


@pytest.mark.parametrize('defect', [
    'mask', 'explicit_pair', 'unexpected_pair', 'pair_name', 'identity', 'duplicate',
    'clearance', 'overlap', 'moving_surface', 'radius_nan', 'velocity', 'command',
    'protocol', 'truncated', 'schedule', 'pose', 'force', 'negative_touch',
    'positive_noncontact_force', 'no_positive', 'partial', 'placement', 'threshold',
])
def test_fail_closed_on_integrity_or_measurement_defect(defect):
    r = evidence()
    c, p = r['control'], r['contact']
    s = c['samples'][0]
    if defect == 'mask': s['collision_masks'][0] = [1, 2]
    elif defect == 'explicit_pair': s['explicit_pair_count'] = 1
    elif defect == 'unexpected_pair':
        s['contact_metadata']['all_contact_pairs'].append(
            {'geom1_id': 0, 'geom1_name': 'ground', 'geom2_id': 2, 'geom2_name': '0/LMTarsus5'})
    elif defect == 'pair_name': p['samples'][0]['contact_metadata']['all_contact_pairs'][0]['geom2_name'] = 'ground'
    elif defect == 'identity': c['tarsus_geom']['id'] = 0
    elif defect == 'duplicate': c['geom_names'][0] = 'other/LMTarsus5'
    elif defect == 'clearance': s['sphere_clearance'] = 0.
    elif defect == 'overlap': s['geom_positions'][0] = s['geom_positions'][1][:]
    elif defect == 'moving_surface': p['samples'][0]['geom_positions'][1][0] += .1
    elif defect == 'radius_nan': s['geom_radii'][0] = float('nan')
    elif defect == 'velocity': p['reset_qvel'][0] = .1
    elif defect == 'command': p['held_joints'][0] = .1
    elif defect == 'protocol': r['protocol']['seed'] = 1
    elif defect == 'threshold': r['protocol']['engineering_threshold'] = 2.
    elif defect == 'truncated': c['samples'].pop()
    elif defect == 'schedule':
        for arm in (c, p):
            for sample in arm['samples']: sample['simulation_time_s'] += 1.
    elif defect == 'pose': p['pose_proof']['qpos_after_surface_placement'][0] = 1.
    elif defect == 'force': s.update(magnitude=1., raw_tarsus5_vector=[1., 0., 0.])
    elif defect == 'negative_touch': s['selected_pair_present'] = True
    elif defect == 'positive_noncontact_force':
        p['samples'][0].update(selected_pair_present=False, contact_metadata={'all_contact_pairs': []})
    elif defect == 'no_positive':
        for sample in p['samples']:
            sample.update(selected_pair_present=False, contact_metadata={'all_contact_pairs': []},
                          magnitude=0., raw_tarsus5_vector=[0., 0., 0.])
    elif defect == 'partial': p.update(run_status='ERROR', reason='physics error')
    elif defect == 'placement': p['placement']['penetration'] *= 2
    assert not v2.evaluate_leg(r, 'LM')['accepted']


def test_masks_exclude_every_pair_except_positive_target():
    for contact in (False, True):
        masks = v2.collision_masks(8, 2, 7, contact)
        allowed = [(i, j) for i in range(8) for j in range(i + 1, 8)
                   if masks[i, 0] & masks[j, 1] or masks[j, 0] & masks[i, 1]]
        assert allowed == ([(2, 7)] if contact else [])
    with pytest.raises(ValueError): v2.collision_masks(3, 1, 1, True)


def test_observer_promotes_float32_before_norm_and_refreshes_observation():
    forces = np.zeros((36, 3), dtype=np.float32)
    forces[11] = [.1234567, .9876543, .0001234]  # LM Tarsus5
    physics = SimpleNamespace(
        model=SimpleNamespace(geom_rbound=np.array([.1, .04]),
                              geom_contype=np.zeros(2), geom_conaffinity=np.zeros(2), npair=0),
        data=SimpleNamespace(geom_xpos=np.array([[0., 0., 1.], [1000000., 0., 0.]]), time=0.))
    sim = SimpleNamespace(physics=physics, get_observation=lambda: {'contact_forces': forces})
    with patch.object(v2.single, '_pairs', return_value=()):
        sample = v2._sample(sim, 'LM', {'tarsus_geom': {'id': 0}, 'surface_geom': {'id': 1}})
    assert sample['magnitude'] == np.linalg.norm(np.asarray(sample['raw_tarsus5_vector'], dtype=np.float64))


def test_all_twelve_arms_attempted_once_and_partial_samples_preserved():
    calls = []
    def run(_, leg, *, contact):
        calls.append((leg, contact))
        arm = evidence(leg)['contact' if contact else 'control']
        if leg == 'RF' and not contact:
            arm.update(run_status='ERROR', reason='failed after reset', samples=arm['samples'][:2])
        return arm
    with patch.object(v2.importlib, 'import_module', return_value=object()), \
            patch.object(v2, 'run_condition', side_effect=run):
        report = v2.build_report(live=True, progress=lambda *_: None)
    assert calls == [(leg, contact) for leg in v2.v1.LEGS for contact in (False, True)]
    assert report['accepted_legs'] == ['LF', 'LM', 'LH', 'RM', 'RH']
    assert report['run_status'] == 'INCOMPLETE'
    assert len(report['legs']['RF']['evidence']['control']['samples']) == 2
    json.dumps(report, allow_nan=False)


def test_nonfinite_locations_and_no_acceptance():
    arm = evidence()['control']
    arm['samples'][0]['geom_radii'][0] = float('nan')
    with patch.object(v2.importlib, 'import_module', return_value=object()), \
            patch.object(v2, 'run_condition', return_value=arm):
        report = v2.build_report(live=True, progress=lambda *_: None)
    assert report['accepted_legs'] == []
    assert report['legs']['LM']['nonfinite_measurement_paths']
    json.dumps(report, allow_nan=False)


def test_dry_unavailable_and_overwrite_protection(tmp_path):
    path = tmp_path / 'dry.json'
    assert v2.main(['--output', str(path)]) == 1
    before = path.read_bytes()
    with pytest.raises(FileExistsError): v2.main(['--live', '--output', str(path)])
    assert path.read_bytes() == before
    assert json.loads(before)['accepted_legs'] == []
    with patch.object(v2.importlib, 'import_module', side_effect=ImportError('missing')):
        report = v2.build_report(live=True, progress=lambda *_: None)
    assert report['accepted_legs'] == []
    assert report['legs']['LF']['evidence']['control']['run_status'] == 'UNAVAILABLE'
    with pytest.raises(SystemExit): v2.main(['--output', str(path), '--duration-s', '1'])


def test_archived_physics_evidence_hashes_and_strict_reevaluation():
    root = Path(__file__).parents[1]
    directory = root / 'docs/evidence'
    manifest = json.loads((directory / 'six-foot-contact-v2-checkpoint.json').read_text())
    for run in manifest['runs']:
        packed = (directory / run['raw_artifact']).read_bytes()
        raw = gzip.decompress(packed)
        assert hashlib.sha256(packed).hexdigest() == run['gzip_sha256']
        assert hashlib.sha256(raw).hexdigest() == run['raw_json_sha256']
        report = json.loads(raw)
        assert report['accepted_legs'] == run['accepted_legs']
        for leg, value in report['legs'].items():
            # Historical evidence must be checked against its declared version.
            # All remaining protocol fields and acceptance rules are identical.
            assert value['evidence']['protocol'] == dict(v2.PROTOCOL, schema=report['schema'])
            with patch.dict(v2.PROTOCOL, schema=report['schema']):
                result = v2.evaluate_leg(value['evidence'], leg)
            assert result['accepted'] == value['evaluation']['accepted']
            assert result['checks'] == value['evaluation']['checks']
        if report['schema'] == v2.SCHEMA:
            for name, expected in report['source_sha256_lf'].items():
                path = root / ('docs' if name.endswith('.md') else 'malecns_backend/embodiment') / name
                assert hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest() == expected
