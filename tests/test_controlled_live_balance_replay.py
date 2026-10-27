"""New-schema gating, existing presentation reuse and explicit live/replay limits."""
import copy
import json
from unittest.mock import patch

import pytest

from malecns_backend.live import controlled_live_balance_replay as r


def accepted():
    return dict(schema=r.experiment.SCHEMA, evaluation=dict(scientific=dict(accepted=True,
        unity_replay_eligible=True, behavior=dict(primary_label='MIXED_OR_UNRESOLVED')),
        display=dict(NC=dict(status='UNCONFIRMED', sent_frames=0))),
        arm_artifacts={c:dict(path=c+'.json.gz') for c in r.experiment.base.CONDITIONS})


@pytest.mark.parametrize('fault',['incomplete','changed','ineligible'])
def test_failed_or_changed_evidence_never_loads_pose_clips(tmp_path,fault):
    saved=accepted(); evaluated=copy.deepcopy(saved['evaluation'])
    if fault=='incomplete':evaluated['scientific']['accepted']=False
    if fault=='changed':evaluated['display']['NC']['sent_frames']=1
    if fault=='ineligible':evaluated['scientific']['unity_replay_eligible']=False
    (tmp_path/'report.json').write_text(json.dumps(saved))
    with patch.object(r.experiment,'evaluate',return_value=evaluated), \
            patch.object(r.experiment.original,'read_arm',side_effect=AssertionError('must not load')):
        with pytest.raises(ValueError,match='scientific integrity'):r.load_verified(tmp_path)


def test_no_client_live_record_can_be_reviewed_after_scientific_acceptance(tmp_path):
    saved=accepted();(tmp_path/'report.json').write_text(json.dumps(saved));loaded=[]
    with patch.object(r.experiment,'evaluate',return_value=saved['evaluation']), \
            patch.object(r.experiment.original,'read_arm',side_effect=lambda f,c,a:loaded.append(c) or {'condition':c}), \
            patch.object(r.playback,'pose_only',side_effect=lambda a:['projected-'+a['condition']]):
        report,clips=r.load_verified(tmp_path)
    assert report==saved and loaded==list(r.experiment.base.CONDITIONS)
    assert clips['NP']==['projected-NP']


def test_presentation_api_reuse_does_not_pass_new_report_to_old_evaluator(capsys):
    report=accepted();clips={'NP':['synthetic poses']}
    with patch.object(r.playback,'replay') as presentation, \
            patch.object(r.playback.experiment,'evaluate',side_effect=AssertionError('old evaluator forbidden')):
        r.replay(report,clips,'NP',speed=.1,loop=False)
    assert presentation.call_args.args==(dict(evaluation=report['evaluation']['scientific']),clips,'NP')
    assert presentation.call_args.kwargs==dict(speed=.1,loop=False)
    text=capsys.readouterr().out
    assert 'RECORDED CONTROLLED-LIVE V1.1' in text and 'UNCONFIRMED' in text


@pytest.mark.parametrize('fault',['schema','accepted','eligible'])
def test_replay_does_not_open_server_for_unaccepted_summary(fault):
    report=accepted()
    if fault=='schema':report['schema']='old'
    if fault=='accepted':report['evaluation']['scientific']['accepted']=False
    if fault=='eligible':report['evaluation']['scientific']['unity_replay_eligible']=False
    with patch.object(r.playback,'replay',side_effect=AssertionError('opened server')):
        with pytest.raises(ValueError):r.replay(report,{})
