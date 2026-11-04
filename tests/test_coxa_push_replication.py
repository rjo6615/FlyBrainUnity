"""Synthetic checks for the seeds 7-12 replication: arms, labels, pooled spread, integrity per seed block."""
import math

import pytest

from malecns_backend.live import coxa_push_replication as rp
from malecns_backend.live import coxa_push_response as pr
from malecns_backend.live import hair_plate_posture as c

V3 = ('a', 'b')
IDX = rp.INDICES
BODY = dict(id=3, name='Thorax', frame='world', point='body COM', torque=[0., 0., 0.])
DEV = {'N': .1, 'C': .13, 'Y': .12}  # R 1.3, E 0.923, R_Y 1.2
OLD_TICK1 = ['1-0', '2-0', '3-0']
C0_SHA = {s: f'c0-{s}' for s in rp.SEEDS}


def make_arm(kind, push, seed, dev=None):
    dev = DEV[kind] if dev is None else dev
    sign = pr.PUSHES[push]
    base = [0.]*42
    cmd = list(base)
    for i in IDX.values():
        cmd[i] = .1
    samples = []
    for i in range(c.STEPS + 1):
        x = dev*sign if sign and i > pr.START else 0.
        v = pr.force_at_transition(push, i - 1) if i else (0., 0., 0.)
        row = dict(time_s=i*1e-4, qpos=[x, 0, 1., 1, 0, 0, 0], qvel=[0.]*6, supports=6,
                   commanded_joints=None if i == 0 else (base if kind == 'N' or i < 1000 else cmd),
                   applied_body_wrenches=[] if not any(v) else [dict(body_id=3, wrench=list(v) + [0., 0., 0.])],
                   external_applied_max=float(max(abs(t) for t in v)), generalized_applied_max=0.)
        if kind == 'Y':
            row['proposed_joints'] = None if i == 0 else base
        samples.append(row)
    neural = [dict(time_ms=(k + 1)*.5, uniforms_sha256=f'{seed}-{k}', fired=[], hair_delivered=[]) for k in range(c.TICKS)]
    channels = {'a': dict(index=5), 'b': dict(index=6)}
    if kind == 'C':
        channels.update({n: dict(index=i) for n, i in IDX.items()})
    arm = dict(run_status='COMPLETE', samples=samples, neural=neural,
               hypothesis_channels=sorted(pr.CANDIDATES) if kind == 'C' else [], label=pr.LABEL if kind == 'C' else None,
               definitions_sha256='h1' if kind == 'C' else None,
               initial=dict(external_schedule=[1, 2], channels=channels, cns_seed=seed, force_body=dict(BODY)))
    if kind == 'Y':
        arm['source_sha256'] = C0_SHA[seed]
    return arm


OLD_D = {f'{k}{p}_{s}': DEV[k] for k in 'NCY' for p in 'FB' for s in pr.SEEDS}


@pytest.fixture(scope='module')
def base():
    arms = {k: make_arm(*rp.split(k)) for k in rp.ARMS}
    return arms, make_arm('N', '0', 1)


def run(base, ok=True, **over):
    arms, ref = base
    return rp.evaluate(lambda k: over.get(k, arms[k]), ref, ok, OLD_D, OLD_TICK1, V3, 'h1', C0_SHA)


def test_arms_and_order():
    assert len(rp.ARMS) == 55 and rp.ARMS[0] == 'REPRO_N0_1' and rp.ARMS[1:10] == rp.block(7)
    assert rp.split('YB_12') == ('Y', 'B', 12) and rp.split('REPRO_N0_1') == ('N', '0', 1)
    with pytest.raises(ValueError):
        rp.split('NF_1')


def test_labels():
    assert rp.q1([1.1]*6) == 'AMPLIFICATION_REPLICATES'
    assert rp.q1([1.09] + [2.]*5) == 'AMPLIFICATION_DIRECTIONAL'
    assert rp.q1([1.] + [2.]*5) == 'AMPLIFICATION_NOT_REPLICATED'
    assert rp.q2b([.99]*6) == 'FREE_COMMANDS_INCREASE_D' and rp.q2b([1.01]*6) == 'FREE_COMMANDS_DECREASE_D'
    assert rp.q2b([.5]*5 + [1.]) == 'NO_CONSISTENT_SIGN'
    s = rp.spread([1., math.e, math.e**2])
    assert s['median'] == pytest.approx(math.e) and s['log_mean'] == pytest.approx(1.) and s['log_sd'] == pytest.approx(1.)


def test_accepted_world(base):
    e = run(base)
    assert e['status'] == 'INTEGRITY_ACCEPTED', e['checks']
    for p in ('F', 'B'):
        assert e['labels'][p] == dict(Q1='AMPLIFICATION_REPLICATES', Q2a='OFFSETS_REPRODUCE', Q2b='FREE_COMMANDS_INCREASE_D')
        assert e['ratios'][p]['R'] == pytest.approx([1.3]*6) and e['ratios'][p]['E'] == pytest.approx([.12/.13]*6)
        assert e['pooled_seeds_1_3_and_7_12'][p]['R']['n'] == 9
        assert e['pooled_seeds_1_3_and_7_12'][p]['R']['median'] == pytest.approx(1.3)
    assert e['c_arm_loop_modulation']['CF_9']['differing_transitions']['joint_LMCoxa'] == 0


def test_label_outcome_and_pulse(base):
    assert run(base, CF_10=make_arm('C', 'F', 10, dev=.105))['labels']['F']['Q1'] == 'AMPLIFICATION_DIRECTIONAL'
    assert run(base, YB_8=make_arm('Y', 'B', 8, dev=.14))['labels']['B']['Q2b'] == 'NO_CONSISTENT_SIGN'
    assert run(base, NF_11=make_arm('N', 'F', 11, dev=.001))['status'] == 'INCONCLUSIVE_PULSE'


def faulted(name, fn):
    arm = make_arm(*rp.split(name)) if name != 'REPRO_N0_1' else make_arm('N', '0', 1)
    fn(arm)
    return {name: arm}


FAULTS = {
    'incomplete': ('XX', lambda a: a.update(run_status='ERROR')),
    'repro': ('REPRO_N0_1', lambda a: a['samples'][15000].update(qpos=[0, 0, 2., 1, 0, 0, 0])),
    'rng': ('CB_9', lambda a: a['neural'][7].update(uniforms_sha256='x')),
    'force': ('NF_8', lambda a: a['samples'][5100]['applied_body_wrenches'][0]['wrench'].__setitem__(0, 1.)),
    'n_command': ('NB_7', lambda a: a['samples'][3000].update(commanded_joints=[.1] + [0.]*41)),
    'c_bound': ('CF_12', lambda a: [s.update(commanded_joints=[.3 if i == 7 else 0. for i in range(42)]) for s in a['samples'][2000:]]),
    'c_hash': ('C0_10', lambda a: a.update(definitions_sha256='hf')),
    'y_source': ('YF_11', lambda a: a.update(source_sha256='other')),
    'y_audit': ('YB_7', lambda a: a['samples'][3000].update(commanded_joints=[0.]*42)),
    'y_repro': ('Y0_8', lambda a: a['samples'][15000].update(qpos=[0, 0, 2., 1, 0, 0, 0])),
    'y_label': ('YF_9', lambda a: a.update(label=pr.LABEL)),
    'prefix': ('XB_10', lambda a: a['samples'][4000].update(qpos=[0, 0, 2., 1, 0, 0, 0])),
    'seed': ('NF_12', lambda a: a['initial'].update(cns_seed=1)),
}


@pytest.mark.parametrize('fault', sorted(FAULTS) + ['source_hash', 'old_seed'])
def test_integrity_faults(base, fault):
    if fault == 'source_hash':
        e = run(base, ok=False)
    elif fault == 'old_seed':
        arms = {}
        for k in rp.block(7):
            arm = make_arm(*rp.split(k))
            for t in arm['neural']:
                t['uniforms_sha256'] = t['uniforms_sha256'].replace('7-', '1-', 1)
            arms[k] = arm
        e = run(base, **arms)
    else:
        name, fn = FAULTS[fault]
        if name.startswith('XX'):
            name = 'YB_12'
        if name.startswith('XB'):
            name = 'YB_10'
        e = run(base, **faulted(name, fn))
    assert e['status'] == 'INCONCLUSIVE_INTEGRITY' and 'labels' not in e, fault


def test_protocol_lock():
    spec = rp.protocol()
    assert spec['arms']['order'] == list(rp.ARMS) and spec['arms']['seeds'] == list(rp.SEEDS)
