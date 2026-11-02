"""Synthetic checks for the coxa admission confirmation: seeds, labels, flags, integrity."""
import copy

import numpy as np
import pytest

from malecns_backend.live import coxa_admission as ca
from malecns_backend.live import coxa_hypothesis_loop as loop
from malecns_backend.live import hair_plate_posture as c
from malecns_backend.neural import MaleCNSBrain, ModelConfig
from test_coxa_drive_asymmetry import tiny

V3 = ('a', 'b')
IDX = {'joint_LFCoxa': 0, 'joint_LHCoxa': 14}
HASHES = {'H1': 'h1', 'H1_FLIP': 'hf'}
LEGS = dict.fromkeys(('LF', 'LM', 'LH', 'RF', 'RM', 'RH'), 0.)


def test_arms_and_candidates_match_d2():
    assert ca.ARMS == ('C0_1', 'CAND_1', 'FLIP_1', 'C0_2', 'CAND_2', 'FLIP_2', 'C0_3', 'CAND_3', 'FLIP_3')
    spec = ca.protocol()
    assert spec['arms']['order'] == list(ca.ARMS)
    saved = loop.d2_channels(loop.protocol())
    for kind in ('H1', 'H1_FLIP'):
        defs = ca.candidate_defs(kind, saved)
        assert sorted(defs) == list(ca.CANDIDATES)
        assert ca.defs_sha256(defs) == spec['candidates'][kind]['sha256']
        assert defs == {n: loop.definitions(kind, saved)[n] for n in ca.CANDIDATES}
        assert {n: d['coordinate_sign'] for n, d in defs.items()} == spec['candidates'][kind]['coordinate_sign']


def test_seed_applied_only_before_first_transition(monkeypatch):
    monkeypatch.setattr(loop.Trial, 'attach', lambda self, brain, channels, **kw: self)
    brain = MaleCNSBrain(tiny(), ModelConfig.calibrated()); brain.reset(1)
    t = ca.Trial.__new__(ca.Trial); t.seed, t.initial = 3, {}
    t.attach(brain, {}, sensory_sources={})
    assert brain.rng.random() == np.random.default_rng(3).random() and t.initial['cns_seed'] == 3
    late = MaleCNSBrain(tiny(), ModelConfig.calibrated()); late.reset(1)
    late.set_external_drive(range(6), 400.); late.step()
    with pytest.raises(RuntimeError):
        t.attach(late, {}, sensory_sources={})
    drawn = MaleCNSBrain(tiny(), ModelConfig.calibrated()); drawn.reset(1); drawn.rng.random()
    with pytest.raises(RuntimeError):
        t.attach(drawn, {}, sensory_sources={})


def test_seed_pass_and_labels():
    assert ca.seed_pass(True, -.02, .02) and not ca.seed_pass(False, -.5, .5)
    assert not ca.seed_pass(True, -.019, .5) and not ca.seed_pass(True, -.5, .019)
    assert ca.label([True]*3) == 'CONFIRMED' and ca.label([True, False, True]) == 'PARTIAL'
    assert ca.label([False]*3) == 'NOT_CONFIRMED'


def make_arm(kind, seed, *, shift=.05, offset=.1, firing=True):
    base = [0.]*42
    cmd = list(base)
    if kind != 'C0':
        sign = 1 if kind == 'CAND' else -1
        cmd[0] = cmd[14] = sign*offset
    samples = [dict(time_s=i*1e-4, qpos=[0, 0, 0, 1, 0, 0, 0], commanded_joints=(base if i < 1000 else cmd))
               for i in range(c.STEPS + 1)]
    samples[0]['commanded_joints'] = None
    df = 0. if kind == 'C0' else (-shift if kind == 'CAND' else shift)
    neural = []
    for k in range(c.TICKS):
        t = (k + 1)*.5
        f = dict(LEGS, LF=.5 + (df if t > 200 else 0.), LH=.5 + (df if t > 200 else 0.))
        neural.append(dict(time_ms=t, uniforms_sha256=f'{seed}-{k}', fired=[], hair_delivered=[], hair_forward=f,
                           hair_rate_hz=dict(LEGS, LF=120. if firing else 0., LH=120.)))
    channels = {'a': dict(index=5), 'b': dict(index=6)}
    if kind != 'C0':
        channels.update({n: dict(index=i) for n, i in IDX.items()})
    return dict(run_status='COMPLETE', samples=samples, neural=neural, hypothesis_channels=[] if kind == 'C0' else sorted(IDX),
                definitions_sha256=None if kind == 'C0' else HASHES[ca.KINDS[kind]],
                initial=dict(external_schedule=[1, 2], channels=channels, cns_seed=seed))


def world(**over):
    arms = {f'{k}_{s}': make_arm(k, s) for s in ca.SEEDS for k in ca.KINDS}
    arms.update(over)
    return arms, copy.deepcopy(arms['C0_1'])


def test_confirmed_when_all_seeds_pass():
    arms, step_c = world()
    e = ca.evaluate(arms, step_c, HASHES, V3, IDX)
    assert e['status'] == 'INTEGRITY_ACCEPTED', e['checks']
    assert e['labels'] == {'joint_LFCoxa': 'CONFIRMED', 'joint_LHCoxa': 'CONFIRMED'}
    assert not any(f['BOUND_LIMITED'] or f['ROLLOVER'] for f in e['flags'].values())


def test_partial_not_confirmed_and_bound_flag():
    arms, step_c = world(CAND_2=make_arm('CAND', 2, shift=.01), C0_3=make_arm('C0', 3, firing=False),
                         FLIP_1=make_arm('FLIP', 1, offset=.245))
    e = ca.evaluate(arms, step_c, HASHES, V3, IDX)
    assert e['status'] == 'INTEGRITY_ACCEPTED', e['checks']
    assert e['labels'] == {'joint_LFCoxa': 'PARTIAL', 'joint_LHCoxa': 'PARTIAL'}  # LF 1/3, LH 2/3
    assert [r['passed'] for r in e['per_seed']['joint_LFCoxa'].values()] == [True, False, False]
    assert [r['passed'] for r in e['per_seed']['joint_LHCoxa'].values()] == [True, False, True]
    assert e['per_seed']['joint_LFCoxa'][3]['firing'] is False
    assert e['flags']['joint_LFCoxa']['BOUND_LIMITED'] and e['flags']['joint_LHCoxa']['BOUND_LIMITED']


@pytest.mark.parametrize('fault', ['incomplete', 'rng', 'step_c', 'hash', 'bound', 'prefix', 'seed', 'outside'])
def test_integrity_faults(fault):
    arms, step_c = world()
    if fault == 'incomplete': arms['FLIP_3']['run_status'] = 'ERROR'
    if fault == 'rng': arms['CAND_2']['neural'][9]['uniforms_sha256'] = 'x'
    if fault == 'step_c': step_c['neural'][3]['fired'] = [1]
    if fault == 'hash': arms['FLIP_2']['definitions_sha256'] = 'zz'
    if fault == 'bound': arms['CAND_1'] = make_arm('CAND', 1, offset=.3)
    if fault == 'prefix': arms['CAND_3']['samples'][10]['qpos'] = [9]*7
    if fault == 'seed':
        for k in ca.KINDS:
            arms[f'{k}_3']['neural'][0]['uniforms_sha256'] = '1-0'
    if fault == 'outside':
        s = arms['FLIP_1']['samples'][500]
        s['commanded_joints'] = list(s['commanded_joints']); s['commanded_joints'][20] = .1
    e = ca.evaluate(arms, step_c, HASHES, V3, IDX)
    assert e['status'] == 'INCONCLUSIVE_INTEGRITY' and 'labels' not in e
