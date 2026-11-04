"""Synthetic checks for the open-loop coxa offset yoke: index replacement, audit, labels, integrity."""
import numpy as np
import pytest

from malecns_backend.live import coxa_offset_yoke as y
from malecns_backend.live import coxa_push_response as pr
from malecns_backend.live import hair_plate_posture as c

V3 = ('a', 'b')
IDX = (0, 7, 14, 28)
BODY = dict(id=3, name='Thorax', frame='world', point='body COM', torque=[0., 0., 0.])
DEV = {'N': .1, 'C': .13, 'Y': .13}  # C amplifies 1.3x; the open-loop yoke reproduces it


def make_arm(kind, push, seed, dev=None):
    dev = DEV[kind] if dev is None else dev
    sign = pr.PUSHES[push]
    base = [0.]*42
    cmd = list(base)
    for i in IDX:
        cmd[i] = .1
    samples = []
    for i in range(c.STEPS + 1):
        x = dev*sign if sign and i > pr.START else 0.
        v = pr.force_at_transition(push, i - 1) if i else (0., 0., 0.)
        applied = None if i == 0 else (base if kind == 'N' or i < 1000 else cmd)
        row = dict(time_s=i*1e-4, qpos=[x, 0, 1., 1, 0, 0, 0], qvel=[0.]*6, supports=6, commanded_joints=applied,
                   applied_body_wrenches=[] if not any(v) else [dict(body_id=3, wrench=list(v) + [0., 0., 0.])],
                   external_applied_max=float(max(abs(t) for t in v)), generalized_applied_max=0.)
        if kind == 'Y':
            row['proposed_joints'] = None if i == 0 else list(base)
        samples.append(row)
    neural = [dict(time_ms=(k + 1)*.5, uniforms_sha256=f'{seed}-{k}', fired=[], hair_delivered=[]) for k in range(c.TICKS)]
    channels = {'a': dict(index=5), 'b': dict(index=6)}
    if kind == 'C':
        channels.update({f'h{i}': dict(index=i) for i in IDX})
    return dict(run_status='COMPLETE', samples=samples, neural=neural, hypothesis_channels=[], label=None,
                initial=dict(external_schedule=[1, 2], channels=channels, cns_seed=seed, force_body=dict(BODY)))


def world(**over):
    refs = {k: make_arm(k[0], k[1], int(k[-1])) for k in y.REFERENCES}
    arms = {k: make_arm(*y.split(k)) for k in y.ARMS}
    arms.update(over)
    return arms, refs


def test_selected_action_and_sample_convention():
    proposed, archived = np.arange(42.), -np.arange(42.)
    out = y.selected_action(proposed, archived)
    assert [i for i in range(42) if out[i] != proposed[i]] == [7, 14, 28]  # index 0 is 0 == -0
    assert all(out[i] == archived[i] for i in IDX)
    trial = y.Trial.__new__(y.Trial)
    trial.samples, trial.actions = [{}, {}], np.stack([np.full(42, 1.), np.full(42, 2.)])
    trial.original_sim_step = lambda action: action
    sent = trial.apply(dict(joints=np.zeros(42), adhesion=np.zeros(6)))
    assert [sent['joints'][i] for i in IDX] == [2.]*4 and sent['joints'].sum() == 8.  # transition 1 <- samples[2]
    with pytest.raises(ValueError):
        trial.apply(dict(joints=np.zeros(42), adhesion=np.zeros(6), extra=1))


def test_labels():
    assert y.label([1.1, 1.3, 2.], [.9, 1., 1.1]) == 'OFFSETS_REPRODUCE'
    assert y.label([1.1, 1.3, 2.], [.89, 1., 1.]) == 'OFFSETS_PARTLY_REPRODUCE'
    assert y.label([1.1, 1.3, 2.], [1., 1., 1.11]) == 'OFFSETS_PARTLY_REPRODUCE'
    assert y.label([1.09, 1.3, 2.], [1., 1., 1.]) == 'OFFSETS_DO_NOT_REPRODUCE'


def test_accepted_world():
    arms, refs = world()
    e = y.evaluate(arms, refs, True, V3)
    assert e['status'] == 'INTEGRITY_ACCEPTED', e['checks']
    assert e['labels'] == dict(F='OFFSETS_REPRODUCE', B='OFFSETS_REPRODUCE')
    assert e['ratios']['F']['R_Y'] == pytest.approx([1.3]*3) and e['ratios']['B']['E'] == pytest.approx([1.]*3)
    assert e['c_arm_loop_modulation']['CF_1']['differing_transitions']['joint_LFCoxa'] == 0
    assert e['y_arm_applied_minus_proposed_mean_abs_rad']['YB_2']['joint_RMCoxa'] == pytest.approx(.1*(c.STEPS - 999)/c.STEPS)


@pytest.mark.parametrize('dev,expected', [(.1, 'OFFSETS_DO_NOT_REPRODUCE'), (.16, 'OFFSETS_PARTLY_REPRODUCE')])
def test_label_outcomes(dev, expected):
    arms, refs = world(YF_2=make_arm('Y', 'F', 2, dev=dev))
    assert y.evaluate(arms, refs, True, V3)['labels']['F'] == expected


@pytest.mark.parametrize('fault', ['incomplete', 'sources', 'c0', 'yoke', 'other_coordinate', 'proposed', 'rng',
                                   'force', 'inventory', 'label', 'prefix', 'seed'])
def test_integrity_faults(fault):
    arms, refs = world()
    ok = True
    if fault == 'incomplete': arms['YB_3']['run_status'] = 'ERROR'
    if fault == 'sources': ok = False
    if fault == 'c0': arms['Y0_1']['samples'][15000]['qpos'] = [0, 0, 2., 1, 0, 0, 0]
    if fault == 'yoke': arms['YF_2']['samples'][3000]['commanded_joints'][14] = .2
    if fault == 'other_coordinate': arms['YB_1']['samples'][3000]['commanded_joints'][3] = .2
    if fault == 'proposed': arms['YF_1']['samples'][10]['proposed_joints'] = None
    if fault == 'rng': arms['YB_2']['neural'][7]['uniforms_sha256'] = 'x'
    if fault == 'force': arms['YF_3']['samples'][5100]['applied_body_wrenches'][0]['wrench'][0] = 1.
    if fault == 'inventory': arms['Y0_2']['initial']['channels']['h0'] = dict(index=0)
    if fault == 'label': arms['YF_1']['label'] = 'COXA_CONDITIONAL_H1'
    if fault == 'prefix': arms['YB_2']['samples'][4000]['qpos'] = [0, 0, 2., 1, 0, 0, 0]
    if fault == 'seed': arms['YF_3']['initial']['cns_seed'] = 1
    e = y.evaluate(arms, refs, ok, V3)
    assert e['status'] == 'INCONCLUSIVE_INTEGRITY' and 'labels' not in e


def test_protocol_lock():
    spec = y.protocol()
    assert spec['arms']['order'] == list(y.ARMS)
    assert set(spec['sources']['reference_arms']) == set(y.REFERENCES)
