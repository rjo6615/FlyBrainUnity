"""Synthetic checks for antennal gravity Step D2; no recorded arm, CNS or physics."""
import copy
import math

import numpy as np
import pytest

from malecns_backend.embodiment import jo_rollover_timing as m

N, TICKS = m.END_STATE + 1, 4000
CH = [f'joint_{i}' for i in range(20)]


def record(tilt0=17., cmd0=0., d=(-.18, -.18), spikes=1.):
    tick_ms = np.arange(1, TICKS + 1)*.5
    return dict(tilt=np.full(N, tilt0), peak_window_tilt=tilt0, cmd=np.full((N, 20), cmd0), channels=list(CH),
                supports=np.full(N, 6), tick_ms=tick_ms, leg_spikes=np.full((TICKS, 6), spikes),
                leg_size=np.full(6, 10.), d=np.tile(np.array(d, float), (TICKS, 1)), qpos0=[0., 1.])


def ramp_tilt(r, start, fall):
    """Tilt rises linearly from start and reaches 60 deg at fall + 100."""
    k = fall + 100
    r['tilt'][start:k] = np.linspace(r['tilt'][start], 60., k - start)
    r['tilt'][k:] = 60.
    return r


def test_leg_groups_and_labels():
    g = m.leg_groups({'T1 left femur': {1}, 'T3 right tibia': {2, 3}, 'T2 left coxa': {4}})
    assert g['LF'] == {1} and g['RH'] == {2, 3} and g['LM'] == {4} and g['RF'] == set()
    assert m.order_label(None, 6000) == 'BODY_FIRST'
    assert m.order_label(5899, 6000) == 'COMMAND_FIRST'
    assert m.order_label(5900, 6000) == 'CONCURRENT'
    assert m.order_label(6100, 6000) == 'CONCURRENT'
    assert m.order_label(6101, 6000) == 'BODY_FIRST'
    assert m.order_label(5000, None) == 'UNRESOLVED'
    c, b = 'COMMAND_FIRST', 'BODY_FIRST'
    assert m.order_summary([c, c, c, c, b]) == 'ORDER_COMMAND_FIRST'
    assert m.order_summary([b, b, b, b, 'CONCURRENT']) == 'ORDER_BODY_FIRST'
    assert m.order_summary([c, c, c, b, b]) == 'ORDER_MIXED'
    assert m.separation([3, 4], [1, 2]) == 'SEPARATES' and m.separation([0, 1], [2, 3]) == 'SEPARATES'
    assert m.separation([2, 4], [1, 2]) == 'OVERLAPS' and m.separation([None, 4], [1]) == 'NOT_EVALUABLE'


def test_body_onset_must_be_sustained():
    e = np.zeros(N)
    e[5100:5200] = 9.      # transient excursion is not an onset
    e[6000:7001] = 8.
    assert m.body_onset(e, 7000) == 6000
    assert m.body_onset(e, 7001) is None
    e[5006:7001] = 8.
    assert m.body_onset(e, 7000) == 5006


def test_command_first_with_tonic_baseline_removed():
    off, on = record(), record(tilt0=21., cmd0=.03)       # tonic ON-OFF offsets are baselined away
    on['cmd'][6000:, 3] += .1
    ramp_tilt(on, 7000, 9000)
    on['supports'][8000:] = 2
    on['d'][on['tick_ms'] > 510.] = (.15, .16)
    on['leg_spikes'][(on['tick_ms'] > 500.5) & (on['tick_ms'] <= 550.), 2] += 4
    r = m.analyse_pair(on, off)
    assert r['fell'] and r['order'] == 'COMMAND_FIRST'
    assert r['t_cmd_ms'] == pytest.approx(99.5) and r['t_cmd_channel'] == 'joint_3' and r['t_cmd_sign'] == 1.
    assert 150. < r['t_body_ms'] < r['t_fall_ms']
    assert r['t_support_ms'] == pytest.approx(299.5)
    assert r['t_jo_ms'] == pytest.approx(10.)
    assert r['window_end_ms'] == 550. and r['F3'] == 6
    assert r['F1'] == pytest.approx(0.) and r['F2'] == pytest.approx(99*4/10/.0495)
    assert r['F2_per_leg_hz']['LH'] == pytest.approx(r['F2'])
    assert r['F4_per_side']['L'] == pytest.approx((-.18*19 + .15*80)/99)
    assert set(r['pre_body_50ms']['command_abs_mean']) == set(CH)


def test_body_first_and_upright():
    off, on = record(), record()
    ramp_tilt(on, 5300, 7000)
    on['cmd'][9000:, 0] -= .2
    r = m.analyse_pair(on, off)
    assert r['order'] == 'BODY_FIRST' and r['t_cmd_ms'] > r['t_body_ms']
    assert r['window_end_ms'] <= 550.
    up = m.analyse_pair(record(), record())
    assert not up['fell'] and up['order'] is None and up['t_body_ms'] is None and up['t_cmd_ms'] is None
    assert up['t_jo_ms'] is None and up['t_support_ms'] is None


def test_reduce_maps_legs_and_window_peak():
    legs = {leg: set() for leg in m.LEG_ORDER}
    legs['LF'], legs['RM'] = {7}, {8, 9}
    chans = {f'joint_{k}': dict(index=i) for k, i in (('b', 5), ('a', 3))}
    samples = [dict(time_s=t, qpos=[0, 0, 0, math.cos(a/2), 0, math.sin(a/2), 0], gravity=[0, 0, -9810.],
                    commanded_joints=list(range(42)), supports=4)
               for t, a in ((.5, 0.), (.5199, .5), (.5201, .2), (1.9, .1))]
    neural = [dict(time_ms=.5, fired=[7, 8, 9, 1], jo_d=dict(L=.1, R=.2))]
    samples[0]['commanded_joints'] = None      # reset state records no command
    r = m.reduce(dict(initial=dict(channels=chans), samples=samples, neural=neural), legs)
    assert r['channels'] == ['joint_a', 'joint_b'] and np.isnan(r['cmd'][0]).all() and r['cmd'][1].tolist() == [3, 5]
    assert r['peak_window_tilt'] == pytest.approx(math.degrees(.2))
    assert r['leg_spikes'][0].tolist() == [1, 0, 0, 0, 2, 0] and r['leg_size'].tolist() == [1, 0, 0, 0, 2, 0]


# ---- evaluate with records in place of raw arms ------------------------------------------

def world(fell=m.EXPECTED_FELL):
    recs, body = {}, {}
    for s in m.SEEDS:
        for tilt in ('LEVEL', 'DOWN20'):
            for t in ('OFF',) + m.ON_TYPES:
                name = f'{t}_{tilt}_{s}'
                r = record()
                if name in fell:
                    r['cmd'][6000:, 1] += .2
                    ramp_tilt(r, 7000, 8000)
                    r['peak_window_tilt'] = 60.
                recs[name] = r
                body[name] = dict(tilt_max_deg=r['peak_window_tilt'])
    hashes = {k: 'h' + k for k in recs}
    hashes['REPRO_N0_7'] = 'hr'
    report = dict(arm_sha256=dict(hashes), evaluation=dict(body=body))
    return recs, hashes, report


def run(recs, hashes, report, monkeypatch):
    monkeypatch.setattr(m, 'reduce', lambda arm, legs: arm)
    return m.evaluate(lambda k: recs[k], hashes, report, {})


def test_evaluate_accepts(monkeypatch):
    e = run(*world(), monkeypatch)
    assert e['status'] == 'INTEGRITY_ACCEPTED', e['checks']
    assert sorted(e['fell']) == sorted(m.EXPECTED_FELL) and len(e['upright']) == 7
    assert e['Q1']['summary'] == 'ORDER_COMMAND_FIRST'
    assert e['Q2']['F3']['label'] == 'OVERLAPS'
    assert e['expectation']['order'] == 'HELD'


def test_evaluate_integrity_failures(monkeypatch):
    recs, hashes, report = world()
    bad = dict(hashes, OFF_LEVEL_20='x')
    assert run(recs, bad, report, monkeypatch)['checks']['R1_hashes'] is False
    r2 = copy.deepcopy(report)
    r2['evaluation']['body']['G1_LEVEL_22']['tilt_max_deg'] += 1e-6
    assert run(recs, hashes, r2, monkeypatch)['checks']['R2_peak_tilt'] is False
    for extra in ('G1_DOWN20_20', 'OFF_DOWN20_19', 'FLIP_LEVEL_21'):
        rec2, h2, rep2 = world(m.EXPECTED_FELL | {extra})
        e = run(rec2, h2, rep2, monkeypatch)
        assert e['status'] == 'INCONCLUSIVE_INPUT' and e['checks']['R3_fell_set'] is False, extra
    recs['FLIP_DOWN20_22']['qpos0'] = [0., 2.]
    e = run(recs, hashes, report, monkeypatch)
    assert e['status'] == 'INCONCLUSIVE_INPUT' and e['checks']['R4_state0'] is False
