"""Static XML/asset/evidence guards; not executed native or biological tests."""
import copy
import json
import struct
from unittest.mock import patch

import numpy as np
import pytest

from malecns_backend.embodiment import lf_route_attachment as audit


def stl(header=b'A', vertex=1.):
    return header*80+struct.pack('<I12fH', 1, 0., 0., 1., 0., 0., 0., vertex, 0., 0., 0., 1., 0., 0)


def test_binary_stl_header_difference_is_not_geometry_or_homology_difference():
    a, b = stl(), stl(b'B')
    assert audit.orientation.lineage.sha(a) != audit.orientation.lineage.sha(b)
    assert audit.mesh_summary(a) == audit.mesh_summary(b)
    assert audit.mesh_summary(a)['ordered_vertices_sha256'] != audit.mesh_summary(stl(vertex=2.))['ordered_vertices_sha256']
    assert audit.mesh_summary(a)['triangles'] == 1
    assert audit.mesh_summary(a)['maximum'] == [1., 1., 0.]


@pytest.mark.parametrize('raw', [b'', stl()[:-1], stl()+b'X', stl(vertex=float('nan')), b'A'*80+struct.pack('<I', 0)])
def test_malformed_or_nonfinite_binary_mesh_rejected(raw):
    with pytest.raises(ValueError): audit.mesh_summary(raw)


def test_missing_and_duplicate_xml_bodies_rejected():
    for raw in [b'<mujoco><worldbody/></mujoco>',
                b'<mujoco><worldbody><body name="Thorax"/><body name="Thorax"/></worldbody></mujoco>']:
        with pytest.raises(ValueError, match='unique exact XML body'): audit.extract_xml(raw)


def test_unresolved_includes_cannot_supply_hidden_site_ownership():
    with pytest.raises(ValueError, match='included definitions'):
        audit.extract_xml(b'<mujoco><include file="other.xml"/><worldbody/></mujoco>')


def test_source_identity_rejected_before_any_route_inference():
    with pytest.raises(ValueError, match='raw hash'):
        audit.orientation.native.pose.binding.inspect_model(b'<different/>',
            audit.orientation.native.pose.binding.MODEL_HASH, audit.TENDONS)


def test_actual_snapshot_keeps_route_order_local_ownership_and_active_mesh():
    snapshot = audit.orientation.lineage.transfer.read(audit.SNAPSHOT)
    source = snapshot['files']['source_xml']['extract']
    assert [r['tendon'] for r in source['routes']] == list(audit.TENDONS)
    assert all([s['owner_body'] for s in r['sites']] == ['Thorax', 'LFCoxa'] for r in source['routes'])
    assert all(s['compiled_site_id'] is None for r in source['routes'] for s in r['sites'])
    target = snapshot['files']['target_xml']['extract']
    coxa = next(r for r in target['bodies'] if r['body']['name'] == 'LFCoxa')
    assert coxa['mesh']['file'] == '../mesh/RFCoxa.stl'
    assert coxa['mesh']['scale'] == '1000 -1000 1000'
    assert target['sites'] == [] and target['tendon_count'] == 0
    assert snapshot['files']['target_unused_left_coxa']['path'].endswith('/LFCoxa.stl')


def test_changed_asset_extract_cannot_be_hidden_behind_original_hash():
    snapshot = audit.orientation.lineage.transfer.read(audit.SNAPSHOT)
    snapshot['files']['target_active_coxa']['extract']['triangles'] += 1
    with pytest.raises(ValueError, match='extract differs'): audit.inspect_assets(snapshot)


@pytest.fixture(scope='module')
def rebuilt():
    import mujoco
    import scipy.integrate
    from malecns_backend.embodiment import remaining_leg_admission_audit as legacy
    def forbidden(*args, **kwargs): raise AssertionError('native/solver/live audit attempted')
    with patch.object(mujoco, 'MjModel', forbidden), patch.object(mujoco, 'mj_kinematics', forbidden), \
         patch.object(mujoco, 'mj_forward', forbidden), patch.object(mujoco, 'mj_step', forbidden), \
         patch.object(scipy.integrate, 'solve_ivp', forbidden), \
         patch.object(audit.orientation.lineage.transfer.coupling.v1, 'solve_ivp', forbidden), \
         patch.object(legacy, 'build', forbidden):
        return audit.build()


def test_real_saved_reconstruction_does_not_turn_body_names_into_attachments(rebuilt):
    assert len(rebuilt['endpoints']) == 8 and rebuilt['source_route_count'] == 4
    assert len(rebuilt['target_compiled_site_names']) == 37 and rebuilt['target_compiled_tendon_count'] == 0
    assert rebuilt['exact_source_site_names_found_in_compiled_target'] == []
    assert all(e['target_site_id'] is None and e['target_local_position'] is None
        and e['correspondence_authority'] is None and e['attachment_transform'] is None for e in rebuilt['endpoints'])
    assert {e['target_body_counterpart_inventory_id'] for e in rebuilt['endpoints']} == {3, 13}
    assert all(e['source_compiled_owner_id_from_prior_pose_record'] == 19 for e in rebuilt['endpoints']
               if e['source_site']['owner_body'] == 'LFCoxa')
    assert not rebuilt['production_transfer_enabled'] and rebuilt['physical_force_conversion'] is None
    assert rebuilt['physics_transitions'] == rebuilt['cns_transitions'] == rebuilt['new_admissions'] == 0


@pytest.mark.parametrize('defect', ['attachment', 'coordinate', 'scale', 'admit', 'landmark', 'mesh', 'raw_type'])
def test_saved_audit_tampering_rejected(rebuilt, tmp_path, defect):
    saved = copy.deepcopy(rebuilt)
    if defect == 'attachment': saved['endpoints'][0]['correspondence_authority'] = 'body_name'
    if defect == 'coordinate': saved['endpoints'][0]['target_local_position'] = [0, 0, 0]
    if defect == 'scale': saved['length_scale_conversion'] = 1
    if defect == 'admit': saved['production_transfer_enabled'] = True
    if defect == 'landmark': saved['landmark_scope'] = 'MUSCLE_INSERTION_AUTHORITY'
    if defect == 'mesh': saved['mesh_comparisons'][1]['anatomical_homology'] = True
    if defect == 'raw_type': saved['current_original_raw_freezes_satisfied'] = 'false'
    path = tmp_path/'audit.json';path.write_text(json.dumps(saved))
    with patch.object(audit, 'build', return_value=rebuilt), pytest.raises(ValueError): audit.verify(path)


def test_changed_snapshot_fails_closed(monkeypatch):
    monkeypatch.setattr(audit, 'SNAPSHOT_SHA', '0'*64)
    with pytest.raises(ValueError, match='snapshot changed'): audit.sources()
