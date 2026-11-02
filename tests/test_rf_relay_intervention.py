"""Synthetic checks for the relay intervention adapter, rules and evaluator; no physics."""
import copy

import numpy as np
import pytest

from malecns_backend.live import hair_plate_posture as c
from malecns_backend.live import rf_relay_intervention as r
from malecns_backend.neural import MaleCNSBrain, ModelConfig
from test_coxa_drive_asymmetry import tiny


def graph(edges, n):
    """CSR from {pre: [(post, count)]}."""
    indptr, indices, counts = [0], [], []
    for i in range(n):
        for post, k in edges.get(i, []):
            indices.append(post); counts.append(k)
        indptr.append(len(indices))
    return np.array(indptr), np.array(indices), np.array(counts)


def test_relay_and_sham_rules():
    # 0 LF hair; 1 LF post MN; 2 RF post MN; 3 other coxa MN
    types = ['SNpp45', 'MN', 'MN', 'MN', 'IN03A066', 'IN03A075', 'IN03A080', 'IN03A066',
             'IN03A001', 'IN03A002', 'IN03A003', 'IN03A004', 'IN19A001']
    side = {i: s for i, s in enumerate([None]*4 + ['left', 'left', 'right', 'left',
                                                   'left', 'left', 'left', 'right', 'left'])}
    edges = {0: [(4, 9), (5, 9), (7, 3)],      # 7 below floor from hair
             4: [(1, 8)], 5: [(1, 8)], 6: [(2, 7)], 7: [(1, 9)],
             9: [(3, 6)],                         # sham candidate touches a coxa MN
             10: [(4, 9)]}
    indptr, indices, counts = graph(edges, len(types))
    sign = np.ones(len(types)); sign[5] = -1.  # 5 inhibitory
    left, right = r.relay_sets(types, side, indptr, indices, counts, sign, 6, {0}, {1}, {2})
    assert left == [4] and right == [6]
    rates = np.zeros(len(types)); rates[[4, 8, 10]] = [10., 3., 9.]
    sham = r.sham_set(left, 'left', types, side, indptr, indices, counts, 6, {1, 2, 3}, {4, 6}, rates)
    assert sham == [10]  # 9 excluded by coxa edge, 12 wrong prefix, 11 wrong side, closest rate wins
    assert r.sham_set([4, 5, 7, 6], 'left', types, side, indptr, indices, counts, 6, {1, 2, 3}, {4}, rates) is None
    assert r.injection_rates([4, 7], [6], ['']*4 + ['A', 'B', 'A', 'A'], rates) == [5.]
    assert r.injection_rates([4], [5], ['']*4 + ['A', 'B'], rates) is None


def test_trains_deterministic_and_independent():
    np.random.seed(7); before = np.random.random()
    a = r.trains([20., 0., 120.], 4000, .5)
    np.random.seed(7)
    assert r.trains([20., 0., 120.], 4000, .5) == a and np.random.random() == before
    assert a[1] == [] and 20 < len(a[0]) < 60 and 180 < len(a[2]) < 300
    assert r.train_sha256(a) != r.train_sha256(r.trains([20., 0., 120.], 4000, .5, seed=1))


def harness(brain, schedule, silenced=(), inject=None):
    """RelayTrial hooks on a tiny engine without physics: the Step C event_trials equation."""
    t = r.RelayTrial.__new__(r.RelayTrial)
    t.brain, t.schedule, t.neural = brain, np.asarray(schedule, np.intp), []
    t.silenced = np.asarray(sorted(silenced), np.intp)
    t.schedule_by_tick = inject or {}
    t.expected_rng = copy.deepcopy(brain.rng.bit_generator.state)
    brain._external_event_trials = t.event_trials
    brain.transmission_withheld_indices = t.silenced.copy()
    return t


def drive(t, ticks):
    brain = t.brain
    out = []
    for _ in range(ticks):
        brain.external_drive[t.schedule] = 400.
        t.available = brain.refractory <= 0
        t.pending = None
        fired = brain.step()
        p = t.pending
        t.neural.append(dict(fired=list(map(int, fired)), uniforms=t.current_uniforms, injected=p['injected'],
                             inject_blocked=p['blocked'], withheld=list(map(int, brain._last_transmission_withheld))))
        out.append(fired)
    return t.neural


def test_injection_keeps_rng_and_respects_refractoriness():
    config = ModelConfig.calibrated()
    base = MaleCNSBrain(tiny(), config); base.reset(5)
    ref = drive(harness(base, range(6)), 200)
    brain = MaleCNSBrain(tiny(), config); brain.reset(5)
    target = 20
    inject = {k: [target] for k in range(10, 200)}  # every tick: refractoriness must block most
    rec = drive(harness(brain, range(6), inject=inject), 200)
    assert [x['uniforms'] for x in rec] == [x['uniforms'] for x in ref]
    assert rec[:10] == [dict(x) for x in ref[:10]]
    done = [k for k, x in enumerate(rec) if x['injected']]
    blocked = [k for k, x in enumerate(rec) if x['inject_blocked']]
    assert done and blocked and sorted(done + blocked) == list(range(10, 200))
    assert all(target in rec[k]['fired'] for k in done)


def test_silencing_records_and_withholds_delivery():
    config = ModelConfig.calibrated()
    base = MaleCNSBrain(tiny(), config); base.reset(5)
    ref = drive(harness(base, range(6)), 300)
    brain = MaleCNSBrain(tiny(), config); brain.reset(5)
    silenced = {0, 1, 2}
    rec = drive(harness(brain, range(6), silenced=silenced), 300)
    assert all(sorted(set(x['fired']) & silenced) == sorted(x['withheld']) for x in rec)
    assert sum(len(x['withheld']) for x in rec) > 0
    assert [x['uniforms'] for x in rec] == [x['uniforms'] for x in ref]
    assert any(x['fired'] != y['fired'] for x, y in zip(rec, ref))  # removing delivery changes downstream


def test_labels():
    assert r.q_nec(.4, .95) == 'NECESSARY' and r.q_nec(.5, .9) == 'NECESSARY'
    assert r.q_nec(.6, .9) == 'CONTRIBUTES' and r.q_nec(.8, .9) == 'CONTRIBUTES'
    assert r.q_nec(.81, .9) == 'NOT_NECESSARY' and r.q_nec(.1, .79) == 'NONSPECIFIC'
    assert r.q_suf(30., 1., 1.5, 48.) == 'RESCUED' and r.q_suf(30., 2., 1.5, 48.) == 'NONSPECIFIC'
    assert r.q_suf(6.5, 0., 1.5, 48.) == 'PARTIAL' and r.q_suf(6.4, 0., 1.5, 48.) == 'NO_EFFECT'


SPEC = dict(engine=dict(dt_ms=.5), resolved=dict(
    sets=dict(LEFT_RELAY=[dict(dense=10)], LEFT_SHAM=[dict(dense=11)], RIGHT_RELAY=[dict(dense=20)],
              RIGHT_SHAM=[dict(dense=21)]),
    injection_rates_hz=[40.], train_ticks=c.TICKS, train_seed=r.TRAIN_SEED))


def synthetic_arms():
    train = r.trains([40.], c.TICKS, .5)[0]
    samples = [dict(qpos=[0, 0, 0, 1, 0, 0, 0]) for _ in range(c.STEPS + 1)]
    def arm(name):
        neural = []
        for k in range(c.TICKS):
            fired = [10, 11] if k % 50 == 30 else []
            rec = dict(time_ms=(k + 1)*.5, uniforms_sha256=str(k), fired=fired, hair_delivered=[],
                       injected=[], inject_blocked=[], transmission_withheld=[])
            if name in r.SILENCE:
                rec['transmission_withheld'] = [10] if name == 'L_SIL' and fired else [11] if fired else []
            if name in r.INJECT and k in train:
                j = 20 if name == 'R_INJ' else 21
                rec['injected'] = [j]; rec['fired'] = fired + [j]
            neural.append(rec)
        return dict(run_status='COMPLETE', samples=copy.deepcopy(samples), neural=neural,
                    initial=dict(external_schedule=[1, 2]))
    arms = {k: arm(k) for k in r.ARMS}
    return arms, copy.deepcopy(arms['C0'])


def test_integrity_accepts_consistent_arms():
    arms, a_on = synthetic_arms()
    checks, audit = r.integrity(arms, a_on, SPEC)
    assert all(checks.values()), checks
    assert audit['first_intervention_tick']['L_SIL'] == 30 and audit['first_intervention_tick']['C0'] is None


@pytest.mark.parametrize('fault', ['c0', 'rng', 'missing_inject', 'extra_withheld', 'prefix', 'incomplete'])
def test_integrity_faults(fault):
    arms, a_on = synthetic_arms()
    if fault == 'c0': a_on['neural'][7]['fired'] = [3]
    if fault == 'rng': arms['L_SHAM']['neural'][9]['uniforms_sha256'] = 'x'
    if fault == 'missing_inject':
        k = next(k for k, x in enumerate(arms['R_INJ']['neural']) if x['injected'])
        arms['R_INJ']['neural'][k]['injected'] = []
    if fault == 'extra_withheld': arms['L_SIL']['neural'][31]['transmission_withheld'] = [10]
    if fault == 'prefix': arms['L_SIL']['samples'][5]['qpos'] = [9]*7
    if fault == 'incomplete': arms['R_SHAM']['run_status'] = 'ERROR'
    checks, _ = r.integrity(arms, a_on, SPEC)
    assert not all(checks.values())


def test_protocol_lock_and_resolution():
    spec = r.protocol()
    res = spec['resolved']
    assert res['status'] == 'BUILDABLE' and list(spec['arms']) == list(r.ARMS)
    sizes = {k: len(v) for k, v in res['sets'].items()}
    assert sizes['LEFT_SHAM'] == sizes['LEFT_RELAY'] and sizes['RIGHT_SHAM'] == sizes['RIGHT_RELAY']
    train = r.trains(res['injection_rates_hz'], res['train_ticks'], spec['engine']['dt_ms'], res['train_seed'])
    assert r.train_sha256(train) == res['train_sha256'] and [len(x) for x in train] == res['train_events']
    ids = [x['dense'] for v in res['sets'].values() for x in v]
    assert len(ids) == len(set(ids))
