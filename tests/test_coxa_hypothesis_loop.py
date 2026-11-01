"""Synthetic checks for coxa hypothesis D3; no CNS or physics stepping."""
import copy
import json

import pytest

from malecns_backend.live import coxa_hypothesis_loop as d3
from malecns_backend.embodiment import hair_plate_encoder as hp

D2 = json.loads((d3.ROOT/'docs/evidence/coxa-hypothesis-v1/run/result.json').read_text(encoding='utf-8'))['channels']


def test_definitions_from_d2_are_ordered_and_sized():
    h1, h2, flip = (d3.definitions(a, D2) for a in ('H1', 'H2', 'H1_FLIP'))
    assert len(h1) == 13 and len(h2) == 8 and set(flip) == set(h1)
    assert [d['action_index'] for d in h1.values()] == sorted(d['action_index'] for d in h1.values())
    assert all(flip[n]['coordinate_sign'] == -h1[n]['coordinate_sign'] for n in h1)
    assert all(isinstance(v, tuple) for d in h1.values() for v in d.get('positive_populations', {}).values())


def test_gate_and_assertion_scope():
    from malecns_backend.embodiment.m7d_corrected_spontaneous import CONDITIONS
    names = ('a', 'b')
    gate = d3.make_gate(names)
    assert gate({'a': 1., 'b': 2.}, CONDITIONS[0], names) == {'a': 1., 'b': 2.}
    with pytest.raises(RuntimeError):
        gate({'a': 1.}, CONDITIONS[0], ('a',))
    table = [dict(actuator=f'j{i}', neural_motor_admission=i in (0, 1)) for i in range(42)]
    ok = d3.make_assertion(('j0', 'j1'))
    ok([1., -1.] + [0.]*40, table)
    with pytest.raises(RuntimeError):
        ok([0., 0., 1.] + [0.]*39, table)
    with pytest.raises(RuntimeError):
        d3.make_assertion(('j0',))([0.]*42, table)


@pytest.fixture(scope='module')
def v3_objects():
    from malecns_backend.embodiment import _windows_m7d_corrected_spontaneous_adapter as adapter
    from malecns_backend.embodiment import live_v2_motor_interface as v2, live_v3_motor_interface as v3
    p1, r, t1 = adapter._protocol()
    p2, r, t2 = v2.derive_v2(p1, r, t1)
    return v3.derive_v3(p2, r, t2)


def test_derive_marks_only_declared_rows(v3_objects):
    from malecns_backend.embodiment import live_v3_motor_interface as v3
    protocol, records, table = v3_objects
    before = copy.deepcopy(table)
    defs = d3.definitions('H1', D2)
    value, _, rows, names = d3.derive('H1', defs, protocol, records, table)
    assert table == before  # inputs untouched
    diff = d3.table_difference(table, rows)
    assert set(diff) == {d['action_index'] for d in defs.values()}
    assert all(set(v) <= {'neural_motor_admission', 'coordinate_sign', 'motor_status', 'handling', 'reason'} for v in diff.values())
    assert names[:20] == tuple(v3.V3_MOTOR) and value['admitted_motor_interfaces'] == list(names)
    assert all(rows[d['action_index']]['motor_status'] == 'COXA_HYPOTHESIS_H1' for d in defs.values())
    bad = {'joint_LFFemur': dict(action_index=table[[r['actuator'] for r in table].index('joint_LFFemur')]['action_index'],
                                 coordinate_sign=1)}
    with pytest.raises(RuntimeError):
        d3.derive('H1', bad, protocol, records, table)


# ---- synthetic evaluation world -------------------------------------------------

V3N = ('v0', 'v1')
DEFS = {arm: {'joint_LFCoxa': dict(action_index=0), 'joint_LHCoxa': dict(action_index=14),
              'joint_RFCoxa': dict(action_index=21), 'joint_RHCoxa': dict(action_index=35)} for arm in d3.ARMS[1:]}
FIRING = ('LF', 'LH', 'RF', 'RH')
BODYMAP = dict(muscles=[dict(name='Sternal posterior rotator MN T1 left', actuator='coxa_twist_T1_left', idx=[3]),
                        dict(name='Sternal anterior rotator MN T1 left', actuator='coxa_twist_T1_left', idx=[4])])


def arm(name, shift=0., offset=0., start=10):
    cmd = [0.]*42
    samples = [dict(qpos=[0, 0, 0, 1, 0, 0, 0], commanded_joints=None, time_s=0.)]
    for k in range(1, d3.STEPS + 1):
        c = list(cmd)
        if name != 'C0' and k >= start:
            for d in DEFS[name].values():
                c[d['action_index']] = offset
        q = [0, 0, 0, 1, 0, 0, 0] if name == 'C0' or k < start else [0, 0, 0, 1, 0, 0, 1e-3]
        samples.append(dict(qpos=q, commanded_joints=c, time_s=k*1e-4))
    neural = []
    for t in range(d3.TICKS):
        ms = (t + 1)*.5
        f = {leg: (shift if (leg in FIRING and ms > 10) else 0.) for leg in hp.LEGS}
        neural.append(dict(time_ms=ms, uniforms_sha256=str(t), fired=[], hair_delivered=[],
                           hair_rate_hz={leg: (50. if leg in FIRING else 0.) for leg in hp.LEGS}, hair_forward=f))
    channels = {n: dict(index=i) for i, n in enumerate(V3N)}
    if name != 'C0':
        channels.update({n: dict(index=d['action_index']) for n, d in DEFS[name].items()})
    return dict(run_status='COMPLETE', samples=samples, neural=neural,
                initial=dict(external_schedule=[1, 2], channels=channels))


def world(h1=-.05, flip=.05, h2=0., **over):
    arms = dict(C0=arm('C0'), H1=arm('H1', h1, .1), H1_FLIP=arm('H1_FLIP', flip, -.1), H2=arm('H2', h2, .05))
    arms.update(over)
    return arms


def run(arms, step_c=None):
    return d3.evaluate(arms, step_c or copy.deepcopy(arms['C0']), DEFS, V3N, BODYMAP)


def test_resistance_consistent_and_h1_favoured():
    e = run(world())
    assert e['status'] == 'INTEGRITY_ACCEPTED', e['checks']
    assert e['firing_legs'] == list(FIRING)
    assert e['Q3']['label'] == 'RESISTANCE_CONSISTENT' and e['Q4']['label'] == 'H1_FAVOURED'
    assert e['first_h_command_sample']['H1'] == 10


def test_sign_only_and_not_consistent_and_ties():
    assert run(world(flip=0.))['Q3']['label'] == 'SIGN_ONLY_CONSISTENT'
    e = run(world(h1=-.01, h2=-.01))
    assert e['Q3']['label'] == 'NOT_CONSISTENT' and e['Q4']['label'] == 'NOT_DISTINGUISHED'
    assert run(world(h2=-.05))['Q4']['label'] == 'NOT_DISTINGUISHED'


@pytest.mark.parametrize('fault', ['incomplete', 'rng', 'step_c', 'bound', 'outside', 'prefix', 'inventory'])
def test_integrity_failures_block_labels(fault):
    arms = world()
    step_c = copy.deepcopy(arms['C0'])
    if fault == 'incomplete': arms['H2']['run_status'] = 'ERROR'
    if fault == 'rng': arms['H1']['neural'][7]['uniforms_sha256'] = 'x'
    if fault == 'step_c': step_c['neural'][50]['fired'] = [9]
    if fault == 'bound': arms['H1']['samples'][500]['commanded_joints'][0] = .3
    if fault == 'outside': arms['H1_FLIP']['samples'][500]['commanded_joints'][5] = .01
    if fault == 'prefix': arms['H2']['samples'][3]['qpos'] = [9]*7
    if fault == 'inventory': arms['H1']['initial']['channels']['v0'] = dict(index=7)
    e = d3.evaluate(arms, step_c, DEFS, V3N, BODYMAP)
    assert e['status'] == 'INCONCLUSIVE_INTEGRITY' and 'Q3' not in e


def test_not_testable_with_few_firing_legs():
    arms = world()
    for a in arms.values():
        for t in a['neural']:
            t['hair_rate_hz'] = {leg: (50. if leg in ('LF', 'RF') else 0.) for leg in hp.LEGS}
    assert run(arms)['Q3']['label'] == 'NOT_TESTABLE'
