"""Frozen-data math/integrity checks; no simulated or biological balance claim."""
import copy
import json
from unittest.mock import Mock

import numpy as np
import pytest

from malecns_backend.live import group_posture_analysis as study


def quaternion(axis,degrees,n=1):
    a=np.radians(degrees)/2
    q=np.zeros((n,4))
    q[:,0]=np.cos(a)
    q[:,axis+1]=np.sin(a)
    return q


def test_absolute_relative_and_heading_are_distinct_and_sign_invariant():
    q=quaternion(2,30,3)
    up=study.world_up(q)
    np.testing.assert_allclose(up,[[0.,0.,1.]]*3,atol=1e-15)
    np.testing.assert_allclose(study.angle_between(up,study.world_up(quaternion(2,0,3))),0.,atol=1e-7)
    np.testing.assert_allclose(study.metrics.quaternion_shortest_arc_deg(q,quaternion(2,0,3)),30.)
    np.testing.assert_allclose(study.world_up(-q),up)
    np.testing.assert_allclose(study.world_up(quaternion(0,20))[0,2],np.cos(np.radians(20)))


def test_large_control_tilt_can_create_relative_error_despite_more_upright_pushed_body():
    traces={}
    for policy in study.POLICIES:
        traces[policy]=dict(position=np.zeros((3,3)),quaternion=quaternion(0,10,3))
        traces[study.CONTROLS[policy]]=dict(position=np.zeros((3,3)),quaternion=quaternion(0,25,3))
    curve=study.curves(traces)['ON_P']
    np.testing.assert_allclose(curve['absolute_tilt_deg'],10.)
    np.testing.assert_allclose(curve['control_tilt_deg'],25.)
    np.testing.assert_allclose(curve['relative_rotation_deg'],15.)
    np.testing.assert_allclose(curve['relative_up_deg'],15.)


def test_signed_vector_interaction_cancels_additive_effects_and_retains_xyz():
    base=np.tile([2.,3.,4.],(4,1))
    a=np.tile([.2,-.1,.4],(4,1))
    b=np.tile([.5,.7,-.2],(4,1))
    vectors=dict(ON_P=base,T_P=base+a,C_P=base+b,Y_P=base+a+b)
    np.testing.assert_allclose(study.interaction(vectors),0.,atol=1e-14)
    vectors['Y_P']+=np.array([.03,-.04,0.])
    result=study.interaction(vectors)
    np.testing.assert_allclose(result,np.tile([.03,-.04,0.],(4,1)))
    summary=study.vector_summary(result,start=0)
    assert summary['peak_norm']['index']==0
    np.testing.assert_allclose(summary['peak_norm']['value'],.05)
    np.testing.assert_allclose(summary['signed_xyz_integral'],[.03*.0003,-.04*.0003,0.],atol=1e-15)


@pytest.mark.parametrize('defect',['nan','shape','length'])
def test_interaction_rejects_unaligned_or_nonfinite_vectors(defect):
    vectors={p:np.zeros((3,3)) for p in study.POLICIES}
    if defect=='nan': vectors['ON_P'][0,0]=float('nan')
    if defect=='shape': vectors['C_P']=np.zeros((3,2))
    if defect=='length': vectors['T_P']=np.zeros((2,3))
    with pytest.raises(ValueError): study.interaction(vectors)


def test_peak_ties_and_cross_metric_values_use_aligned_sample():
    curve=dict(absolute_tilt_deg=np.array([99.,1.,4.,4.]),relative_rotation_deg=np.array([99.,6.,2.,1.]),
        control_tilt_deg=np.array([0.,10.,11.,12.]),relative_up_deg=np.array([0.,3.,1.,2.]))
    result=study.summarize(curve,start=1)
    assert result['absolute_tilt_peak']['index']==2 and result['relative_rotation_peak']['index']==1
    assert result['at_absolute_tilt_peak']==dict(relative_rotation_deg=2.,control_tilt_deg=11.)
    assert result['at_relative_rotation_peak']==dict(absolute_tilt_deg=1.,control_tilt_deg=10.,relative_up_deg=3.)
    with pytest.raises(ValueError): study.peak(np.array([1.,2.]),2)


@pytest.fixture
def synthetic():
    trace=dict(position=np.tile([0.,0.,1.],(20001,1)),quaternion=quaternion(0,0,20001),
        velocity=np.zeros((20001,6)),up_z=np.ones(20001),supports=np.full(20001,6))
    traces={i:copy.deepcopy(trace) for i in (*study.POLICIES,*study.CONTROLS.values())}
    expected={p:study.metrics.response(traces[p],traces[study.CONTROLS[p]]) for p in study.POLICIES}
    return traces,expected


def test_complete_matching_data_is_integrity_not_recovery_and_inventory_is_admission(synthetic):
    report,_,_=study.analyze(*synthetic)
    assert report['integrity_passed'] and report['scientific_transitions']==0
    assert report['active_balance_proven'] is False
    assert report['responses']['ON_P']['recovery_status']=='NO_BAND_EXIT'
    inv=report['inventory']
    assert inv['admitted_motor_coordinates']==20 and inv['model_coordinates']==42
    assert inv['remaining_breakdown']==dict(coxa=18,middle_hind_tarsus=4)
    assert inv['ordinary_live_tactile_enabled'] is False


@pytest.mark.parametrize('defect',['control','prefix','summary','missing','nan','short','support'])
def test_saved_evidence_contract_defects_fail(synthetic,defect):
    traces,expected=synthetic
    if defect=='control': traces['T_C']['position'][19000,0]=1.
    if defect=='prefix': traces['ON_P']['position'][4000,0]=1.
    if defect=='summary': expected['C_P']['post_peak_orientation_deg']=99.
    if defect=='missing': del traces['Y_P']
    if defect=='nan': traces['T_P']['velocity'][0,0]=float('nan')
    if defect=='short': traces['T_P']['position']=traces['T_P']['position'][:-1]
    if defect=='support': traces['ON_P']['supports'][0]=7
    if defect in ('missing','nan','short','support'):
        with pytest.raises(ValueError): study.analyze(traces,expected)
    else: assert not study.analyze(traces,expected)[0]['integrity_passed']


def test_exclusive_output_preserves_failure_and_no_live_flag(tmp_path,monkeypatch):
    path=tmp_path/'analysis'
    monkeypatch.setattr(study,'load_verified',Mock(side_effect=ValueError('bad frozen artifact')))
    assert study.main(['--output-dir',str(path)])==1
    raw=(path/'analysis.json').read_bytes()
    assert json.loads(raw)['scientific_transitions']==0 and 'bad frozen artifact' in json.loads(raw)['error']
    with pytest.raises(FileExistsError): study.main(['--output-dir',str(path)])
    assert (path/'analysis.json').read_bytes()==raw
    with pytest.raises(SystemExit): study.main(['--output-dir',str(path),'--live'])


def test_npz_numeric_roundtrip_and_no_extra_fields(tmp_path,synthetic):
    traces,_=synthetic
    path=tmp_path/'aligned.npz'
    study.write_npz(path,traces)
    actual=study.read_npz(path)
    assert all(np.array_equal(actual[i][f],traces[i][f]) for i in traces for f in traces[i])
    with pytest.raises(FileExistsError): study.write_npz(path,traces)
    bad=tmp_path/'bad.npz'
    np.savez(bad,unknown=np.array([1.]))
    with pytest.raises(ValueError): study.read_npz(bad)
    with pytest.raises(ValueError): study.write_npz(tmp_path/'object.npz',dict(ON_P={'bad':np.array([object()])}))


def test_archived_analysis_outputs_math_and_original_raw_hashes():
    from malecns_backend.live import group_posture_review as review
    report=review.verify(study.ROOT/'docs/evidence/group-posture-analysis-v1/analysis.json',progress=lambda _:None)
    assert report['source_integrity'] and report['scientific_transitions']==0
    assert report['evaluation']['active_balance_proven'] is False


@pytest.mark.parametrize('defect',['source','status','protocol'])
def test_reviewer_rejects_incomplete_or_wrong_source_before_artifact_access(tmp_path,defect):
    from malecns_backend.live import group_posture_review as review
    report=dict(protocol=study.PROTOCOL,run_status='COMPLETE',scientific_transitions=0,
        source_integrity=True,sources_before=study.sources(),sources_after=study.sources())
    if defect=='source': report['sources_after']={}
    if defect=='status': report['run_status']='ERROR'
    if defect=='protocol': report['protocol']={}
    path=tmp_path/'report.json'
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError): review.verify(path)
