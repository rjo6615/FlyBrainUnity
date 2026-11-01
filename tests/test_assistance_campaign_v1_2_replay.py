"""V1.2 replay gating, single-pass projection and explicit arm descriptions; no native/CNS model."""
import copy
import json
import math
from unittest.mock import patch

import pytest

from malecns_backend.live import assistance_campaign_v1_2_replay as r


def evaluation():
    comparisons = {
        'A_NP_vs_R_NP': dict(first='A_NP', second='R_NP', tilt_label='LOWER_WORLD_TILT_IN_A_NP',
                             world_tilt_mean_first_minus_second_deg=-146.625),
        'A_NC_vs_A_WC': dict(first='A_NC', second='A_WC', tilt_label='MIXED_OR_UNRESOLVED',
                             world_tilt_mean_first_minus_second_deg=-.372)}
    return dict(scientific=dict(accepted=True, status='INTEGRITY_ACCEPTED', unity_replay_eligible=True,
                                behavior=dict(comparisons=comparisons), reach=math.inf),
                display={a: dict(status='UNCONFIRMED') for a in r.ARM_IDS},
                reference_comparison={}, visual_review='UNCONFIRMED')


def write_report(folder, value=None):
    report = dict(schema=r.experiment.SCHEMA, evaluation=r.saved_form(value or evaluation()),
                  arm_artifacts={a: dict(path=a+'.json.gz') for a in r.ARM_IDS})
    (folder/'report.json').write_text(json.dumps(report))
    return report


def fake_evaluate(result):
    def run(report, folder, *, loader):
        for arm_id in r.ARM_IDS:
            loader(folder, arm_id, report['arm_artifacts'][arm_id])
        return result
    return run


def test_single_pass_projects_every_arm_the_evaluator_reads_and_matches_saved_markers(tmp_path):
    saved = write_report(tmp_path)
    assert saved['evaluation']['scientific']['reach'] == {'__arrow_nonfinite_float__': '+Infinity'}
    report, clips = r.load_verified(tmp_path, evaluate=fake_evaluate(evaluation()),
                                    reader=lambda f, a, art: {'arm_id': a}, project=lambda arm: ['pose-'+arm['arm_id']])
    assert report == saved and list(clips) == list(r.ARM_IDS) and clips['R_WP'] == ['pose-R_WP']


@pytest.mark.parametrize('fault', ['rejected', 'ineligible', 'changed', 'missing_arm', 'schema'])
def test_unverified_evidence_returns_no_clips(tmp_path, fault):
    write_report(tmp_path)
    result = evaluation()
    if fault == 'rejected': result['scientific']['accepted'] = False
    if fault == 'ineligible': result['scientific']['unity_replay_eligible'] = False
    if fault == 'changed': result['display']['A_NC']['status'] = 'CONFIRMED'
    evaluate = fake_evaluate(result)
    if fault == 'missing_arm':
        evaluate = lambda report, folder, *, loader: (loader(folder, 'A_NC', {}), result)[1]
    if fault == 'schema':
        saved = json.loads((tmp_path/'report.json').read_text()); saved['schema'] = 'assistance-contribution-campaign-v1.1'
        (tmp_path/'report.json').write_text(json.dumps(saved))
        evaluate = lambda *a, **k: pytest.fail('evaluator must not run for another schema')
    with pytest.raises(ValueError, match='V1.2'):
        r.load_verified(tmp_path, evaluate=evaluate, reader=lambda f, a, art: {}, project=lambda arm: ['pose'])


def test_projection_failure_inside_evaluator_is_not_displayable(tmp_path):
    write_report(tmp_path)
    def evaluate(report, folder, *, loader):
        try:
            loader(folder, 'A_NC', {})
        except ValueError:
            return dict(evaluation(), scientific=dict(accepted=False, unity_replay_eligible=False))
    def bad(arm): raise ValueError('finite complete native pose/clock required')
    with pytest.raises(ValueError, match='integrity'):
        r.load_verified(tmp_path, evaluate=evaluate, reader=lambda f, a, art: {}, project=bad)


def test_default_reader_and_projection_are_the_existing_validated_ones():
    assert r.load_verified.__defaults__ is None and r.load_verified.__kwdefaults__ == dict(evaluate=None, reader=None, project=None)
    assert r.experiment.read_arm.__module__.endswith('assistance_campaign_v1_2')
    assert r.playback.pose_only.__module__.endswith('balance_contribution_replay')


@pytest.mark.parametrize('arms', ['', 'A_NP,A_NP', 'X_NP', 'A_NP,'])
def test_arm_selection_rejects_unrecorded_or_duplicate_arms(arms):
    with pytest.raises(ValueError):
        r.selected(arms)


def test_arm_descriptions_follow_declared_policies():
    assert len(list(r.describe('A_NC'))) == 2
    text = ' '.join(r.describe('R_WP'))
    assert 'neutralized after recorded state 5005' in text and 'withdrawn' in text and '5000-5199' in text
    assert 'continues' in ' '.join(r.describe('A_NP'))


class Server:
    def __init__(self): self.packets = []
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def publish(self, snapshot, now): self.packets.append(snapshot)


def clip():
    return [dict(time_s=i*.0001, qpos=[0., 0., 1., 1., 0., 0., 0.], joint_positions=[0.]*42) for i in range(r.STATES)]


def test_replay_publishes_selected_arms_in_order_with_labels(capsys):
    report = dict(schema=r.experiment.SCHEMA, evaluation=evaluation())
    server = Server(); now = [0.]
    r.replay(report, {'A_NP': clip(), 'R_NP': clip()}, 'A_NP,R_NP', speed=1., loop=False,
             server_factory=lambda: server, clock=lambda: now[0], sleep=lambda s: now.__setitem__(0, now[0]+s))
    assert len(server.packets) == 2*r.STATES and server.packets[-1].diagnostics['physics_transition'] == 20000
    out = capsys.readouterr().out
    assert 'no physics/CNS is running' in out and 'A_NP_vs_R_NP: LOWER_WORLD_TILT_IN_A_NP' in out
    assert 'A_NC_vs_A_WC' not in out and out.index('-> A_NP') < out.index('-> R_NP')


@pytest.mark.parametrize('fault', ['schema', 'accepted', 'speed', 'clip'])
def test_replay_never_opens_server_for_invalid_request(fault):
    report = dict(schema=r.experiment.SCHEMA, evaluation=evaluation()); clips = {'A_NP': clip(), 'R_NP': clip()}
    speed = .1
    if fault == 'schema': report['schema'] = 'old'
    if fault == 'accepted': report['evaluation']['scientific']['accepted'] = False
    if fault == 'speed': speed = 2.
    if fault == 'clip': clips['R_NP'] = clips['R_NP'][:-1]
    with pytest.raises(ValueError):
        r.replay(report, clips, speed=speed, loop=False, server_factory=lambda: pytest.fail('opened server'))
