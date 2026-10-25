"""Rotation-map/reference integrity tests, not neural or behavioral validation."""
import copy
import json

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from malecns_backend.embodiment import lf_pose_force as pose


def axes(q):
    return np.column_stack(([1., 0., 0.], Rotation.from_euler('X', q[0]).apply([0., 1., 0.]),
        Rotation.from_euler('XY', q[:2]).apply([0., 0., 1.])))


@pytest.mark.parametrize('offset', [(0., 0., 0.), (.05, -.05, .05), (-.05, .05, -.05)])
def test_intrinsic_rotation_map_derivative_and_virtual_work(offset):
    ref = np.array([.1745, .4357, .2614])
    q = ref+offset
    r0 = Rotation.from_euler('XYZ', ref).as_matrix()
    r = Rotation.from_euler('XYZ', q).as_matrix()
    rm = np.array([[.1, -.2, .3, -.4], [.2, .1, -.4, -.3], [-.1, .2, .4, .3]])
    mapped = pose.transfer(r, r0, axes(q), rm)
    jac = np.array(mapped['J'])
    numerical = []
    for axis in range(3):
        delta = np.eye(3)[axis]*pose.EPSILON
        minus = pose.rotation_map(Rotation.from_euler('XYZ', q-delta).as_matrix(), r0)[0]
        plus = pose.rotation_map(Rotation.from_euler('XYZ', q+delta).as_matrix(), r0)[0]
        numerical.append((plus-minus)/(2*pose.EPSILON))
    assert np.max(np.abs(np.array(numerical).T-jac)) < 1e-7
    dq = np.array([.013, -.027, .009])
    tensions = np.array([.25, .5, .75, 1.])
    assert (np.array(mapped['R_G'])@tensions)@(jac@dq) == pytest.approx((rm@tensions)@dq, abs=1e-12)


@pytest.mark.parametrize('bad', [np.zeros((3, 3)), np.diag([1, 1, -1]), np.full((3, 3), np.nan), np.zeros((2, 2))])
def test_nonrotations_are_rejected(bad):
    with pytest.raises(ValueError): pose.rotation_map(bad, np.eye(3))


def test_singular_target_or_source_basis_is_not_substituted():
    with pytest.raises(ValueError):
        pose.rotation_map(Rotation.from_euler('XYZ', [0., np.pi/2, 0.]).as_matrix(), np.eye(3))
    with pytest.raises((ValueError, np.linalg.LinAlgError)):
        pose.transfer(np.eye(3), np.eye(3), np.zeros((3, 3)), np.ones((3, 4)))


def test_fixed_pose_inventory_includes_every_corner_without_selection():
    assert len(pose.OFFSETS) == len(set(pose.OFFSETS)) == 15
    assert pose.OFFSETS[0] == (0., 0., 0.)
    assert len([p for p in pose.OFFSETS if all(abs(x)==.05 for x in p)]) == 8


def test_static_preflight_does_not_construct_native_model(monkeypatch):
    import mujoco
    from malecns_backend.embodiment import _windows_m7_spontaneous_locomotion_adapter as old
    def forbidden(*a, **k): raise AssertionError('preflight/review must not construct models or run dynamics')
    monkeypatch.setattr(mujoco, 'MjModel', forbidden)
    monkeypatch.setattr(mujoco, 'mj_forward', forbidden)
    monkeypatch.setattr(mujoco, 'mj_step', forbidden)
    monkeypatch.setattr(old, 'enumerate_live_actuators', forbidden)
    ready = pose.preflight()
    assert ready['inputs']['xml_sha256'] == pose.binding.MODEL_HASH
    assert len(ready['inputs']['assets']) == 71


def test_manifest_rejects_changed_source_without_refresh(tmp_path):
    path = tmp_path/'model.xml'
    path.write_text('<mujoco/>')
    with pytest.raises(ValueError, match='raw hash'): pose.manifest(path)


def test_failed_execution_preserves_record_and_output_namespace(tmp_path, monkeypatch):
    monkeypatch.setattr(pose, 'preflight', lambda model=None: {})
    def fail(*a, **k): raise ValueError('frozen geometry mismatch')
    monkeypatch.setattr(pose, 'execute', fail)
    output = tmp_path/'new'
    args = ['--execute', '--model', 'missing.xml', '--output-dir', str(output)]
    assert pose.main(args) == 1
    raw = (output/'validation.json').read_bytes()
    assert json.loads(raw)['status'] == 'INTEGRITY_ERROR'
    with pytest.raises(FileExistsError): pose.main(args)
    assert (output/'validation.json').read_bytes() == raw


def test_saved_report_rechecks_without_model_or_forward_calls(monkeypatch):
    import mujoco
    def forbidden(*a, **k): raise AssertionError('review must not run source dynamics')
    monkeypatch.setattr(mujoco, 'MjModel', forbidden)
    monkeypatch.setattr(mujoco, 'mj_forward', forbidden)
    monkeypatch.setattr(mujoco, 'mj_step', forbidden)
    assert pose.main(['--report', str(pose.ROOT/(pose.DIRECTORY+'run/validation.json'))]) == 0


@pytest.mark.parametrize('defect', ['drop_pose', 'fd_pose', 'moment', 'force', 'counter', 'activation'])
def test_saved_corruption_cannot_pass(defect):
    report = json.loads((pose.ROOT/(pose.DIRECTORY+'run/validation.json')).read_text(encoding='utf-8'))
    if defect == 'drop_pose': report['poses'].pop()
    if defect == 'fd_pose': report['poses'][0]['differences'][0][0]['qpos'][0] += .01
    if defect == 'moment': report['poses'][0]['samples'][0]['moments'][0][0] += 1.
    if defect == 'force': report['poses'][0]['samples'][0]['actuator_force'][0] += 10.
    if defect == 'counter': report['observed_api_calls']['mj_forward'] += 1
    if defect == 'activation': report['poses'][0]['samples'][1]['act'][0] = .7
    assert not pose.evaluate(report, report['ready'])['passed']
