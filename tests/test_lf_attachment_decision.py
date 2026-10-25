"""Read-only decision/request guards; no target mapping or native experiment."""
import copy
import json
from unittest.mock import patch

import pytest

from malecns_backend.embodiment import lf_attachment_decision as decision


def test_current_candidate_arguments_never_compute_or_authorize_a_transform():
    review = decision.endpoint.o.lineage.transfer.read(decision.REVIEW)
    rows = decision.assess_current_review(review)
    assert len(rows) == 6
    assert all(not r['registration_authorized'] and not r['transform_computed'] for r in rows)
    origins = next(r for r in rows if r['candidate'] == 'ALIGN_BODY_ORIGINS_OR_FRAMES')
    assert 'mathematical transform can be defined' in origins['reason']


@pytest.mark.parametrize('field', ['qualifying_endpoint_correspondences',
    'independently_labeled_source_target_landmark_pairs', 'target_anatomical_annotation_artifacts', 'citation_flag'])
def test_new_reference_strings_or_coordinates_are_not_automatically_admitted(field):
    review = decision.endpoint.o.lineage.transfer.read(decision.REVIEW)
    if field == 'citation_flag': review['primary_sources'][0]['exact_target_endpoint_authority_established'] = True
    else: review[field] = [dict(citation='paper', position=[0, 0, 0], proposed_transform='identity')]
    with pytest.raises(ValueError, match='separately versioned scientific decision'):
        decision.assess_current_review(review)


@pytest.fixture(scope='module')
def rebuilt():
    import mujoco
    import scipy.integrate
    from malecns_backend.embodiment import remaining_leg_admission_audit as audit
    def forbidden(*args, **kwargs): raise AssertionError('decision attempted native/solver/live audit execution')
    with patch.object(mujoco, 'MjModel', forbidden), patch.object(mujoco, 'mj_kinematics', forbidden), \
         patch.object(mujoco, 'mj_forward', forbidden), patch.object(mujoco, 'mj_step', forbidden), \
         patch.object(mujoco, 'mju_muscleDynamics', forbidden), \
         patch.object(scipy.integrate, 'solve_ivp', forbidden), \
         patch.object(decision.endpoint.o.lineage.transfer.coupling.v1, 'solve_ivp', forbidden), \
         patch.object(audit, 'build', forbidden):
        return decision.build()


def test_real_observer_pass_is_retained_without_target_attachment_acceptance(rebuilt):
    result, request = rebuilt
    assert result['accepted_observer_classification'] == 'ENDPOINT_FRAME_V1_1_OBSERVER_VERIFIED_TRANSFER_BLOCKED'
    assert result['historical_v1_classification'] == 'ENDPOINT_FRAME_INTEGRITY_FAILURE'
    assert result['supported_target_correspondences'] == result['new_admissions'] == 0
    assert result['current_motor_count'] == 20 and not result['registration_authorized']
    assert not request['executable_mapping'] and not request['authorizes_production']
    assert result['target_coordinates'] is result['attachment_transforms'] is None


def test_request_preserves_exact_source_ids_mesh_reflection_and_null_targets(rebuilt):
    _, request = rebuilt
    rows = request['required_endpoint_references']
    assert [r['source_site_id'] for r in rows] == [4, 11, 8, 15, 6, 13, 7, 14]
    assert {r['source_owner_body_id'] for r in rows} == {2, 19}
    assert {r['target_named_body_inventory_id'] for r in rows} == {3, 13}
    assert request['mesh_locks']['target_active_coxa']['path'].endswith('/RFCoxa.stl')
    assert request['active_target_coxa_scale'] == '1000 -1000 1000'
    assert all(r['target_local_position'] is None and r['registration_transform'] is None
        and r['independent_correspondence_authority'] is None for r in rows)


def test_source_export_canonical_identity_is_not_raw_waiver_or_target_authority(rebuilt):
    result, _ = rebuilt
    export = result['additional_source_export_review']
    assert export['canonical_content_matches_recorded_export_hash']
    assert not export['raw_matches_recorded_export_hash']
    assert not export['target_endpoint_authority_established']
    assert not result['registration_authorized'] and result['physical_force_conversion'] is None


@pytest.mark.parametrize('defect', ['registration', 'transform', 'production', 'historical_failure',
                                   'target_coordinate', 'source_id', 'request_authorization', 'raw_type'])
def test_saved_decision_and_request_tampering_rejected(rebuilt, tmp_path, defect):
    result, request = copy.deepcopy(rebuilt)
    if defect == 'registration': result['registration_authorized'] = True
    if defect == 'transform': result['candidate_methods'][2]['transform_computed'] = True
    if defect == 'production': result['production_transfer_enabled'] = True
    if defect == 'historical_failure': result['historical_v1_classification'] = 'PASS'
    if defect == 'target_coordinate': request['required_endpoint_references'][0]['target_local_position'] = [0, 0, 0]
    if defect == 'source_id': request['required_endpoint_references'][0]['source_site_id'] = 99
    if defect == 'request_authorization': request['authorizes_registration'] = True
    if defect == 'raw_type': result['current_original_raw_freezes_satisfied'] = 'false'
    path = tmp_path/'decision.json';path.write_text(json.dumps(result))
    (tmp_path/'reference-request.json').write_text(json.dumps(request))
    with patch.object(decision, 'build', return_value=rebuilt), pytest.raises(ValueError): decision.verify(path)


def test_dated_review_snapshot_cannot_be_silently_refreshed(monkeypatch):
    monkeypatch.setattr(decision, 'REVIEW_SHA', '0'*64)
    with pytest.raises(ValueError, match='reference review changed'): decision.sources()


def test_failed_v1_raw_record_is_still_an_upstream_lock(monkeypatch):
    monkeypatch.setattr(decision.endpoint, 'OLD_SHA', '0'*64)
    with pytest.raises(ValueError, match='failed raw record changed'): decision.sources()
