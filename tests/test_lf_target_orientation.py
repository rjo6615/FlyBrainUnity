"""Reference math, ownership and evidence guards; no native campaign in tests."""
import copy
import json
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from malecns_backend.embodiment import lf_target_orientation as target


def synthetic_sample(q, thorax=None, mount=None):
    thorax = np.eye(3) if thorax is None else thorax
    mount = np.eye(3) if mount is None else mount
    r = Rotation.from_euler('XYZ', q).as_matrix()
    axes = np.column_stack(([1., 0., 0.], Rotation.from_euler('X', q[0]).apply([0., 1., 0.]),
        Rotation.from_euler('XY', q[:2]).apply([0., 0., 1.])))
    return dict(thorax_rotation=thorax.tolist(), coxa_rotation=(thorax@r@mount).tolist(), world_axes=(thorax@axes).tolist())


@pytest.mark.parametrize('offset', [(0., 0., 0.), (.05, -.05, .05), (-.05, .05, -.05)])
def test_native_frame_derivative_contract_with_nonidentity_mount_and_thorax(offset):
    ref = np.array([.1745, .4357, .2614]); q = ref+offset
    r0 = Rotation.from_euler('XYZ', ref).as_matrix(); r = Rotation.from_euler('XYZ', q).as_matrix()
    source_basis = np.column_stack(([1., 0., 0.], Rotation.from_euler('X', q[0]).apply([0., 1., 0.]),
        Rotation.from_euler('XY', q[:2]).apply([0., 0., 1.])))
    mapped = target.native.pose.transfer(r, r0, source_basis, np.ones((3, 4)))
    chain = [[target.native.pose.rotation_map(Rotation.from_euler('XYZ', q+sign*target.EPSILON*np.eye(3)[i]).as_matrix(), r0)[0].tolist()
              for sign in (-1, 1)] for i in range(3)]
    plan = dict(mapped=mapped, source_basis=source_basis.tolist(), chain_angles=chain)
    t = Rotation.from_euler('XYZ', [.3, -.2, .1]).as_matrix()
    mount = Rotation.from_euler('XYZ', [-.1, .4, -.3]).as_matrix()
    samples = [synthetic_sample(angle, t, mount) for _, angle in target.angles_for(plan)]
    values = target.metrics(samples, synthetic_sample([0., 0., 0.], t, mount), plan)
    assert values['rotation'] < 1e-10 and values['basis'] < 1e-10
    assert max(values[k] for k in ('target_fd', 'jacobian', 'chain_fd')) < 1e-7
    assert len(samples) == 13
    wrong = copy.deepcopy(samples); wrong[0]['world_axes'][0][0] += .01
    assert target.metrics(wrong, synthetic_sample([0., 0., 0.], t, mount), plan)['basis'] > .001


@pytest.fixture
def original_native():
    saved = target.native.load_report(target.ROOT/target.NATIVE_RECORD)
    return saved['inventory'], saved['models']['BASELINE']


@pytest.mark.parametrize('defect', ['body', 'qpos', 'action', 'thorax_duplicate', 'ancestry'])
def test_exact_native_identity_cannot_be_replaced_by_matching_names(original_native, defect):
    inv, _ = copy.deepcopy(original_native)
    arrays = dict(body_parentid=[0]+[1]*71)
    if defect == 'body': target.native.targets(inv)[0]['body_id'] = 14
    if defect == 'qpos': target.native.targets(inv)[0]['qpos_range'] = [8, 9]
    if defect == 'action': target.native.targets(inv)[0]['action_index'] = 0
    if defect == 'thorax_duplicate': inv['names']['body'][2] = inv['names']['body'][1]
    if defect == 'ancestry': arrays['body_parentid'][13] = 0
    with pytest.raises(ValueError): target.exact_frames(inv, arrays)


def test_accounting_forbids_probe_forwards_resets_and_all_integrators_and_restores():
    calls = []
    def fn(*args): calls.append('called')
    names = ('mj_kinematics', 'mj_forward', 'mj_resetData', *target.native.INTEGRATORS)
    fake = SimpleNamespace(**{key: fn for key in names})
    with target.accounting(fake) as (counts, phase):
        fake.mj_forward(); fake.mj_resetData()
        phase[0] = 'probes'; fake.mj_kinematics()
        for name in ('mj_forward', 'mj_resetData', *target.native.INTEGRATORS):
            with pytest.raises(ValueError): getattr(fake, name)()
        assert counts['probes']['mj_kinematics'] == 1
    assert all(getattr(fake, key) is fn for key in names)
    assert len(calls) == 3


def test_preflight_uses_saved_authorities_without_native_or_solver_execution():
    import mujoco
    import scipy.integrate
    from malecns_backend.embodiment import remaining_leg_admission_audit as audit
    def forbidden(*args, **kwargs): raise AssertionError('native/solver/live audit attempted')
    with patch.object(mujoco, 'MjModel', forbidden), patch.object(mujoco, 'mj_kinematics', forbidden), \
         patch.object(mujoco, 'mj_forward', forbidden), patch.object(mujoco, 'mj_step', forbidden), \
         patch.object(scipy.integrate, 'solve_ivp', forbidden), \
         patch.object(target.lineage.transfer.coupling.v1, 'solve_ivp', forbidden), \
         patch.object(audit, 'build', forbidden):
        ready = target.preflight()
    assert [p['offset'] for p in ready['plans']] == [list(p) for p in target.native.pose.OFFSETS]
    assert sum(len(target.angles_for(p)) for p in ready['plans'])+1 == 196


def test_incomplete_or_wrong_schema_record_cannot_verify():
    ready = dict(sources={}, installed_inputs={})
    result = target.evaluate(dict(schema='other', status='COMPLETE', ready=ready), ready)
    assert not result['integrity_passed']
    assert result['classification'] == 'TARGET_ORIENTATION_INTEGRITY_FAILURE'


def test_failed_preflight_is_retained_and_never_overwritten(tmp_path):
    output = tmp_path/'failed'
    with patch.object(target, 'preflight', side_effect=ValueError('changed source')):
        assert target.main(['--execute', '--output-dir', str(output)]) == 1
        raw = (output/'validation.json').read_bytes()
        assert json.loads(raw)['error'] == 'ValueError: changed source'
        with pytest.raises(FileExistsError): target.main(['--execute', '--output-dir', str(output)])
        assert (output/'validation.json').read_bytes() == raw


@pytest.fixture(scope='module')
def saved_campaign():
    path = target.ROOT/(target.DIRECTORY+'run/validation.json')
    if not path.exists(): pytest.skip('prospective tests; archived native campaign not yet executed')
    return target.native.load_report(path)


def test_saved_campaign_reconstructs_original_classification_without_execution(saved_campaign):
    actual = target.evaluate(saved_campaign, saved_campaign['ready'])
    assert actual['integrity_passed'] and actual == saved_campaign['evaluation']


@pytest.mark.parametrize('defect', ['drop_pose', 'drop_sample', 'time', 'force', 'count', 'center', 'shape', 'body', 'source'])
def test_saved_campaign_integrity_tampering_rejected(saved_campaign, defect):
    record = copy.deepcopy(saved_campaign)
    sample = record['cases'][0]['samples'][0]
    if defect == 'drop_pose': record['cases'].pop()
    if defect == 'drop_sample': record['cases'][0]['samples'].pop()
    if defect == 'time': sample['before']['time'] = sample['after']['time'] = .001
    if defect == 'force': sample['before']['qfrc_applied'][0] = sample['after']['qfrc_applied'][0] = 1.
    if defect == 'count': record['api_calls']['probes']['mj_step'] = 1
    if defect == 'center': record['center'][30] += .01
    if defect == 'shape': sample['before']['ctrl'] = sample['after']['ctrl'] = []
    if defect == 'body': record['frames']['coxa_id'] = 14
    if defect == 'source': record['sources_after'][target.POSE_RECORD] = '0'*64
    assert not target.evaluate(record, saved_campaign['ready'])['integrity_passed']


def test_proper_rotation_disagreement_is_not_hidden_as_integrity_failure(saved_campaign):
    record = copy.deepcopy(saved_campaign)
    # Change all non-reference coxa frames by a known rotation. This is a
    # synthetic verifier test, not another physical measurement or a correction.
    shift = Rotation.from_rotvec([.01, 0., 0.]).as_matrix()
    for case in record['cases']:
        for sample in case['samples']:
            sample['coxa_rotation'] = (shift@np.asarray(sample['coxa_rotation'])).tolist()
    result = target.evaluate(record, saved_campaign['ready'])
    assert result['integrity_passed'] and not result['numerical_passed']
    assert result['classification'] == ('TARGET_ORIENTATION_DISAGREEMENT_TRANSFER_BLOCKED'
        if result['all_samples_in_range'] else 'TARGET_ORIENTATION_OUTSIDE_NATIVE_LIMITS_TRANSFER_BLOCKED')
