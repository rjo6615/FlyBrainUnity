"""Namespace contract and original acceptance guards; no campaign in tests."""
import copy

import pytest

from malecns_backend.embodiment import lf_endpoint_frames_v1_1 as endpoint


def test_independent_dm_control_attachment_contract_exposes_v1_comparison_defect():
    from dm_control import mjcf
    root = mjcf.RootElement(model='container'); child = mjcf.RootElement(model='fly')
    mesh = child.asset.add('mesh', name='mesh_Thorax', vertex=[0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1])
    root.attach(child)
    assert mesh.full_identifier == 'fly/mesh_Thorax' and mesh.full_identifier != mesh.name
    assert endpoint.n.namespace_component(mesh.full_identifier) == mesh.name


@pytest.mark.parametrize('defect', [None, 'other_namespace', 'wrong_name', 'wrong_body', 'raw_inventory'])
def test_numeric_and_full_namespace_ownership_are_both_required(defect):
    meta = dict(raw_mesh_names=['fly/mesh_Thorax'], names=dict(mesh=['mesh_Thorax'], geom=['fly/Thorax']),
        arrays=dict(geom_dataid=[0], geom_bodyid=[3]), geom_ids=[0], body_ids=[3])
    bodies = [dict(mesh=dict(name='mesh_Thorax'))]
    if defect == 'other_namespace': meta['raw_mesh_names'][0] = 'other/mesh_Thorax'
    if defect == 'wrong_name': bodies[0]['mesh']['name'] = 'mesh_LFCoxa'
    if defect == 'wrong_body': meta['arrays']['geom_bodyid'][0] = 13
    if defect == 'raw_inventory': meta['names']['mesh'] = ['altered']
    if defect is None: assert endpoint.mesh_namespace_links(meta, bodies)
    else:
        with pytest.raises(ValueError): endpoint.mesh_namespace_links(meta, bodies)


def test_original_v1_failure_raw_lock_is_not_refreshed(monkeypatch):
    monkeypatch.setattr(endpoint, 'OLD_SHA', '0'*64)
    with pytest.raises(ValueError, match='failed raw record changed'): endpoint.sources()


@pytest.fixture(scope='module')
def saved():
    path = endpoint.ROOT/(endpoint.DIRECTORY+'run/validation.json')
    if not path.exists(): pytest.skip('prospective V1.1 campaign not yet executed')
    return endpoint.n.load_report(path)


def test_saved_v1_1_reconstruction_preserves_all_v1_nonschema_guards(saved):
    result = endpoint.evaluate(saved, saved['ready'])
    assert result == saved['evaluation'] and result['integrity_passed']
    old = endpoint.v1.evaluate(saved, saved['ready'])
    assert old['checks']['schema'] is False and not old['integrity_passed']
    assert all(value is True for key, value in old['checks'].items() if key != 'schema')


@pytest.mark.parametrize('defect', ['pose', 'sample', 'site', 'owner', 'wrap', 'force', 'time', 'count', 'namespace', 'source', 'shape'])
def test_saved_v1_1_integrity_tampering_rejected(saved, defect):
    record = copy.deepcopy(saved); sample = record['cases'][0]['samples'][0]['source']
    if defect == 'pose': record['cases'].pop()
    if defect == 'sample': record['cases'][0]['samples'].pop()
    if defect == 'site': record['source_site_ids'][0] = record['source_site_ids'][1]
    if defect == 'owner': record['source']['arrays']['site_bodyid'][record['source_site_ids'][0]] = 0
    if defect == 'wrap': record['source']['arrays']['wrap_objid'][0] = 999
    if defect == 'force': sample['before']['qfrc_applied'][0] = sample['after']['qfrc_applied'][0] = 1.
    if defect == 'time': sample['before']['time'] = sample['after']['time'] = .001
    if defect == 'count': record['api_calls']['probes']['mj_step'] = 1
    if defect == 'namespace': record['target']['raw_mesh_names'] = ['other/'+n for n in record['target']['names']['mesh']]
    if defect == 'source': record['sources_after'] = {}
    if defect == 'shape': sample['before']['ctrl'] = sample['after']['ctrl'] = []
    assert not endpoint.evaluate(record, saved['ready'])['integrity_passed']


def test_v1_1_finite_endpoint_disagreement_is_a_preserved_numeric_outcome(saved):
    record = copy.deepcopy(saved)
    for case in record['cases']:
        for pair in case['samples']: pair['source']['source_site_positions'][0][0] += .01
    result = endpoint.evaluate(record, saved['ready'])
    assert result['integrity_passed'] and not result['numerical_passed']
    assert result['classification'] == ('ENDPOINT_FRAME_DISAGREEMENT_TRANSFER_BLOCKED' if result['all_samples_in_range']
                                        else 'ENDPOINT_FRAME_OUTSIDE_LIMITS_TRANSFER_BLOCKED')
