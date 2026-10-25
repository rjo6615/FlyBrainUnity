"""Prospective analytic/guard tests, distinct from the one native campaign."""
import copy
import json
from unittest.mock import patch

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from malecns_backend.embodiment import lf_endpoint_frames as endpoint


def test_two_point_lengths_and_local_to_world_ignore_global_rigid_motion():
    points = np.arange(24, dtype=float).reshape(8, 3)/10
    r = Rotation.from_euler('XYZ', [.2, -.4, .3]).as_matrix(); p = [1., -2., .5]
    moved = np.asarray([endpoint.local_to_world(p, r, point) for point in points])
    assert endpoint.lengths(moved) == pytest.approx(endpoint.lengths(points), abs=1e-14)
    with pytest.raises(ValueError): endpoint.lengths(np.zeros((7, 3)))


def test_compiled_geom_offset_and_source_site_observer():
    r = Rotation.from_euler('XYZ', [.2, -.1, .3]).as_matrix()
    local = [[.1, .2, .3], [.3, -.1, .2]]; positions = [[1., 2., 3.], [-1., 0., .5]]
    meta = dict(body_ids=[2, 4], geom_ids=[0, 1], arrays=dict(site_bodyid=[2, 4], site_pos=local,
        geom_pos=local, geom_quat=[[1., 0., 0., 0.]]*2))
    sample = dict(body_positions=positions, body_rotations=[r.tolist()]*2,
        geom_positions=[endpoint.local_to_world(p, r, q).tolist() for p, q in zip(positions, local)],
        geom_rotations=[r.tolist()]*2,
        source_site_positions=[endpoint.local_to_world(p, r, q).tolist() for p, q in zip(positions, local)])
    assert endpoint.frame_errors(sample, meta, [0, 1]) == pytest.approx([0., 0.], abs=1e-14)
    sample['source_site_positions'][0][1] += .01
    assert endpoint.frame_errors(sample, meta, [0, 1])[0] == pytest.approx(.01)


def test_source_preflight_rejects_model_or_asset_changes_before_compilation(tmp_path):
    model = tmp_path/'changed.xml';model.write_text('<mujoco/>')
    snapshot = endpoint.o.lineage.transfer.read(endpoint.route.SNAPSHOT)
    with pytest.raises(ValueError, match='raw identity mismatch'):
        endpoint.route.inspect_assets(snapshot, model)


def test_static_preflight_cannot_construct_or_execute_native_or_solver():
    import mujoco
    import scipy.integrate
    def forbidden(*args, **kwargs): raise AssertionError('native/solver attempted during static preflight')
    with patch.object(mujoco, 'MjModel', forbidden), patch.object(mujoco, 'mj_kinematics', forbidden), \
         patch.object(mujoco, 'mj_forward', forbidden), patch.object(mujoco, 'mj_step', forbidden), \
         patch.object(scipy.integrate, 'solve_ivp', forbidden), \
         patch.object(endpoint.o.lineage.transfer.coupling.v1, 'solve_ivp', forbidden):
        ready = endpoint.preflight()
    assert len(ready['plans']) == 15 and sum(len(p['samples']) for p in ready['plans']) == 105
    assert [p['offset'] for p in ready['plans']] == [list(p) for p in endpoint.n.pose.OFFSETS]


def test_missing_record_cannot_be_classified_as_observer_pass():
    ready = dict(sources={}, installed_inputs={})
    result = endpoint.evaluate(dict(schema='other', ready=ready), ready)
    assert not result['integrity_passed'] and result['classification'] == 'ENDPOINT_FRAME_INTEGRITY_FAILURE'


def test_failed_preflight_retains_error_and_forbids_overwrite(tmp_path):
    output = tmp_path/'new'
    with patch.object(endpoint, 'preflight', side_effect=ValueError('source lock failed')):
        args = ['--execute', '--model', 'missing.xml', '--output-dir', str(output)]
        assert endpoint.main(args) == 1
        raw = (output/'validation.json').read_bytes()
        assert json.loads(raw)['error'] == 'ValueError: source lock failed'
        with pytest.raises(FileExistsError): endpoint.main(args)
        assert (output/'validation.json').read_bytes() == raw


@pytest.fixture(scope='module')
def saved():
    path = endpoint.ROOT/(endpoint.DIRECTORY+'run/validation.json')
    if not path.exists(): pytest.skip('prospective saved-evidence tests; campaign not yet executed')
    record = endpoint.n.load_report(path)
    if record['status'] != 'COMPLETE':
        pytest.skip('completed-record tests inapplicable to preserved V1 setup failure; explicit failure test below')
    return record


def test_archived_v1_setup_failure_cannot_be_reclassified_as_observer_success():
    path = endpoint.ROOT/(endpoint.DIRECTORY+'run/validation.json')
    if not path.exists(): pytest.skip('campaign not yet executed')
    record = endpoint.n.load_report(path)
    assert record['status'] == 'INCOMPLETE' and record['cases'] == []
    result = endpoint.evaluate(record, record['ready'])
    assert result == record['evaluation'] and result['classification'] == 'ENDPOINT_FRAME_INTEGRITY_FAILURE'
    assert not any(record['api_calls']['probes'].values())


def test_saved_campaign_reconstructs_without_reexecution(saved):
    assert endpoint.evaluate(saved, saved['ready']) == saved['evaluation']
    assert saved['evaluation']['integrity_passed']


@pytest.mark.parametrize('defect', ['pose', 'sample', 'site', 'owner', 'wrap', 'force', 'time', 'count', 'model', 'source'])
def test_evidence_integrity_tampering_rejected(saved, defect):
    record = copy.deepcopy(saved)
    sample = record['cases'][0]['samples'][0]['source']
    if defect == 'pose': record['cases'].pop()
    if defect == 'sample': record['cases'][0]['samples'].pop()
    if defect == 'site': record['source_site_ids'][0] = record['source_site_ids'][1]
    if defect == 'owner': record['source']['arrays']['site_bodyid'][record['source_site_ids'][0]] = 0
    if defect == 'wrap': record['source']['arrays']['wrap_objid'][0] = 999
    if defect == 'force': sample['before']['qfrc_applied'][0] = sample['after']['qfrc_applied'][0] = 1.
    if defect == 'time': sample['before']['time'] = sample['after']['time'] = .001
    if defect == 'count': record['api_calls']['probes']['mj_step'] = 1
    if defect == 'model': record['target_after']['sha256'] = '0'*64
    if defect == 'source': record['sources_after'] = {}
    assert not endpoint.evaluate(record, saved['ready'])['integrity_passed']


def test_finite_endpoint_disagreement_is_preserved_as_numeric_result(saved):
    record = copy.deepcopy(saved)
    for case in record['cases']:
        for pair in case['samples']: pair['source']['source_site_positions'][0][0] += .01
    result = endpoint.evaluate(record, saved['ready'])
    assert result['integrity_passed'] and not result['numerical_passed']
    assert result['classification'] == ('ENDPOINT_FRAME_DISAGREEMENT_TRANSFER_BLOCKED' if result['all_samples_in_range']
                                        else 'ENDPOINT_FRAME_OUTSIDE_LIMITS_TRANSFER_BLOCKED')
