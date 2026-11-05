"""Antennal gravity Step D2: order of divergence before the ON-arm rollovers (V1).

Preregistered in docs/evidence/jo-rollover-timing-v1/protocol.json (design:
docs/JO_ROLLOVER_TIMING_V1.md). Descriptive replay of the 37 recorded Step D arms: each ON
arm is compared with the matched OFF arm (same seed and tilt). No simulation, CNS or
physics stepping; Step C/D measures (body_angles, pools) are reused unchanged.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path

import numpy as np

from ..live import antennal_gravity_live as live
from ..live import hair_plate_posture as c
from ..live import jo_zone_crossing as zc
from ..live.tactile_boundary import native

ROOT = c.ROOT
SCHEMA = 'jo-rollover-timing-result-v1'
PROTOCOL = 'docs/evidence/jo-rollover-timing-v1/protocol.json'
PROTOCOL_SHA256 = '12ca7a70b385d6ba1e148ff3a9ea0817b912b20a1e45330932450868b071fb94'
REPORT = 'docs/evidence/jo-zone-crossing-v1/run/report.json'
REPORT_SHA256 = 'e64811f7253478b0f2d91031d5b63d9acc8ea2c86ed4878959c49d9e3a80f571'

TILT_STATE, END_STATE = 5005, 20000
BASE_STATES = (4005, 5005)          # inclusive
BASE_MS = (400.5, 500.5)            # lo < t <= hi
TILT_MS = 500.5
WIN_END_STATE, WIN_END_MS = 5500, 550.
FALL_DEG, BODY_DEG, CMD_DELTA, SUPPORT_MIN = 45., 5., .05, 3
MARGIN_STATES = 100                 # 10 ms
PRE_STATES, PRE_MS = 500, 50.
SEEDS = zc.SEEDS
ON_TYPES = ('G1', 'FLIP')
EXPECTED_FELL = {'G1_DOWN20_19', 'G1_DOWN20_21', 'G1_DOWN20_24', 'FLIP_DOWN20_23', 'FLIP_DOWN20_24'}
LEGS = {('T1', 'left'): 'LF', ('T2', 'left'): 'LM', ('T3', 'left'): 'LH',
        ('T1', 'right'): 'RF', ('T2', 'right'): 'RM', ('T3', 'right'): 'RH'}
LEG_ORDER = ('LF', 'LM', 'LH', 'RF', 'RM', 'RH')
FEATURES = ('F1', 'F2', 'F3', 'F4')


def protocol():
    raw = (ROOT/PROTOCOL).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('preregistered protocol changed')
    return json.loads(raw)


def leg_groups(groups):
    """{'LF': ids, ...} from Step C pools '<T> <side> <class>'."""
    out = {leg: set() for leg in LEG_ORDER}
    for k, ids in groups.items():
        seg, side = k.split(' ')[:2]
        out[LEGS[(seg, side)]].update(ids)
    return out


def reduce(arm, legs):
    """Compact per-arm record; the raw arm can be released afterwards."""
    ch = sorted(arm['initial']['channels'].items(), key=lambda kv: kv[1]['index'])
    idx = [v['index'] for _, v in ch]
    samples = arm['samples']
    tilt = np.array([live.body_angles(s)[0] for s in samples])
    times = [s['time_s']*1000. for s in samples]
    win = [t for t, ms in zip(tilt, times) if 520. < ms <= 2000.]
    lookup = {i: leg for leg, ids in legs.items() for i in ids}
    spikes = np.zeros((len(arm['neural']), len(LEG_ORDER)))
    for k, t in enumerate(arm['neural']):
        for i in t['fired']:
            leg = lookup.get(i)
            if leg is not None:
                spikes[k, LEG_ORDER.index(leg)] += 1
    return dict(tilt=tilt, peak_window_tilt=float(max(win)),
                # state 0 (reset) records no command; it is NaN and lies outside every definition
                cmd=np.array([[np.nan]*len(idx) if s['commanded_joints'] is None else
                              [s['commanded_joints'][i] for i in idx] for s in samples]),
                channels=[k for k, _ in ch], supports=np.array([s['supports'] for s in samples]),
                tick_ms=np.array([t['time_ms'] for t in arm['neural']]), leg_spikes=spikes,
                leg_size=np.array([len(legs[leg]) for leg in LEG_ORDER], float),
                d=np.array([[t['jo_d']['L'], t['jo_d']['R']] for t in arm['neural']]),
                qpos0=list(samples[0]['qpos']))


def ms_after(state):
    return None if state is None else (state - TILT_STATE)*.1


def leg_rates(r, lo, hi):
    """Per-leg MN rate (Hz) over ticks lo < time_ms <= hi; None if no tick."""
    m = (r['tick_ms'] > lo) & (r['tick_ms'] <= hi)
    if not m.any():
        return None
    return r['leg_spikes'][m].sum(axis=0)/r['leg_size']/((hi - lo)/1000.)


def fall_state(r):
    hit = np.nonzero(r['tilt'][TILT_STATE + 1:] >= FALL_DEG)[0]
    return None if hit.size == 0 else int(hit[0]) + TILT_STATE + 1


def body_onset(e, end):
    """First i >= 5006 with e[j] > 5 for all j in [i, end]; None if e[end] <= 5."""
    if e[end] <= BODY_DEG:
        return None
    seg = e[TILT_STATE + 1:end + 1]
    low = np.nonzero(seg <= BODY_DEG)[0]
    return TILT_STATE + 1 if low.size == 0 else int(low[-1]) + TILT_STATE + 2


def baselined(x):
    lo, hi = BASE_STATES
    return x - x[lo:hi + 1].mean(axis=0)


def cmd_onset(dc, channels):
    a = np.abs(dc[TILT_STATE + 1:])
    rows = np.nonzero((a > CMD_DELTA).any(axis=1))[0]
    if rows.size == 0:
        return None, None, None
    i = int(rows[0]) + TILT_STATE + 1
    j = int(np.argmax(np.abs(dc[i])))
    return i, channels[j], float(np.sign(dc[i, j]))


def support_onset(on, off):
    m = (on['supports'] < SUPPORT_MIN) & (off['supports'] >= SUPPORT_MIN)
    hit = np.nonzero(m[TILT_STATE + 1:])[0]
    return None if hit.size == 0 else int(hit[0]) + TILT_STATE + 1


def jo_onset(on):
    m = (on['tick_ms'] > TILT_MS) & (on['d'] > 0).any(axis=1)
    hit = np.nonzero(m)[0]
    return None if hit.size == 0 else float(on['tick_ms'][hit[0]])


def order_label(t_cmd, t_body):
    if t_body is None:
        return 'UNRESOLVED'
    if t_cmd is not None and t_cmd < t_body - MARGIN_STATES:
        return 'COMMAND_FIRST'
    if t_cmd is None or t_cmd > t_body + MARGIN_STATES:
        return 'BODY_FIRST'
    return 'CONCURRENT'


def order_summary(labels):
    n = list(labels)
    if n.count('COMMAND_FIRST') >= 4:
        return 'ORDER_COMMAND_FIRST'
    if n.count('BODY_FIRST') >= 4:
        return 'ORDER_BODY_FIRST'
    return 'ORDER_MIXED'


def separation(fell, upright):
    if any(v is None for v in list(fell) + list(upright)):
        return 'NOT_EVALUABLE'
    if min(fell) > max(upright) or max(fell) < min(upright):
        return 'SEPARATES'
    return 'OVERLAPS'


def analyse_pair(on, off):
    """Timings and early-window features for one ON arm against its matched OFF arm."""
    tf = fall_state(on)
    end = tf if tf is not None else END_STATE
    e = baselined(on['tilt'] - off['tilt'])
    tb = body_onset(e, end)
    dc = baselined(on['cmd'] - off['cmd'])
    tc, ch, sign = cmd_onset(dc, on['channels'])
    ts = support_onset(on, off)
    tj = jo_onset(on)
    w_end = WIN_END_STATE if tb is None else min(WIN_END_STATE, tb)
    w_ms = w_end*.1
    sl = slice(TILT_STATE + 1, w_end + 1)
    base_mn = leg_rates(on, *BASE_MS) - leg_rates(off, *BASE_MS)
    r_on, r_off = leg_rates(on, TILT_MS, w_ms), leg_rates(off, TILT_MS, w_ms)
    f2_leg = None if r_on is None else (r_on - r_off - base_mn)
    dm = (on['tick_ms'] > TILT_MS) & (on['tick_ms'] <= w_ms)
    f4_side = on['d'][dm].mean(axis=0) if dm.any() else None
    out = dict(fell=tf is not None, t_fall_ms=ms_after(tf), t_body_ms=ms_after(tb), t_cmd_ms=ms_after(tc),
               t_cmd_channel=ch, t_cmd_sign=sign, t_support_ms=ms_after(ts),
               t_jo_ms=None if tj is None else tj - TILT_MS, order=order_label(tc, tb) if tf is not None else None,
               window_end_ms=w_ms,
               F1=float(np.abs(dc[sl]).mean(axis=0).max()),
               F1_channel=on['channels'][int(np.argmax(np.abs(dc[sl]).mean(axis=0)))],
               F2=None if f2_leg is None else float(np.abs(f2_leg).max()),
               F2_per_leg_hz=None if f2_leg is None else dict(zip(LEG_ORDER, map(float, f2_leg))),
               F3=int(on['supports'][sl].min()),
               F4=None if f4_side is None else float(f4_side.mean()),
               F4_per_side=None if f4_side is None else dict(L=float(f4_side[0]), R=float(f4_side[1])),
               max_baselined_tilt_diff_deg=float(e[TILT_STATE + 1:].max()))
    if tf is not None and tb is not None:
        lo = tb - PRE_STATES + 1
        pre = np.abs(dc[lo:tb + 1]).mean(axis=0)
        tb_ms = tb*.1
        p_on, p_off = leg_rates(on, tb_ms - PRE_MS, tb_ms), leg_rates(off, tb_ms - PRE_MS, tb_ms)
        out['pre_body_50ms'] = dict(
            command_abs_mean=dict(zip(on['channels'], map(float, pre))),
            leg_mn_hz=None if p_on is None else dict(zip(LEG_ORDER, map(float, p_on - p_off - base_mn))))
    return out


def evaluate(load, hashes, report, legs):
    """load(arm) -> raw arm; hashes: {arm: sha}; report: Step D report (parsed); legs: leg_groups."""
    expected = report['arm_sha256']
    body = report['evaluation']['body']
    checks = dict(R1_hashes=all(hashes.get(k) == v for k, v in expected.items()) and len(expected) == 37,
                  R2_peak_tilt=True, R3_fell_set=True, R4_state0=True)
    pairs, fell_set, upright_ref = {}, set(), True
    for s in SEEDS:
        for tilt in zc.TILTS:
            off = reduce(load(f'OFF_{tilt}_{s}'), legs)
            gc.collect()
            name_off = f'OFF_{tilt}_{s}'
            checks['R2_peak_tilt'] &= abs(off['peak_window_tilt'] - body[name_off]['tilt_max_deg']) <= 1e-9
            if fall_state(off) is not None:
                upright_ref = False
            for t in ON_TYPES:
                name = f'{t}_{tilt}_{s}'
                on = reduce(load(name), legs)
                gc.collect()
                checks['R2_peak_tilt'] &= abs(on['peak_window_tilt'] - body[name]['tilt_max_deg']) <= 1e-9
                checks['R4_state0'] &= on['qpos0'] == off['qpos0']
                pairs[name] = analyse_pair(on, off)
                if pairs[name]['fell']:
                    fell_set.add(name)
                del on
            del off
    checks['R3_fell_set'] = fell_set == EXPECTED_FELL and upright_ref
    checks = {k: bool(v) for k, v in checks.items()}
    if not all(checks.values()):
        return dict(status='INCONCLUSIVE_INPUT', checks=checks, fell=sorted(fell_set), pairs=pairs)
    down = [f'{t}_DOWN20_{s}' for t in ON_TYPES for s in SEEDS]
    fell = [k for k in down if pairs[k]['fell']]
    upright = [k for k in down if not pairs[k]['fell']]
    order = {k: pairs[k]['order'] for k in fell}
    q2 = {f: dict(label=separation([pairs[k][f] for k in fell], [pairs[k][f] for k in upright]),
                  fell={k: pairs[k][f] for k in fell}, upright={k: pairs[k][f] for k in upright})
          for f in FEATURES}
    summary = order_summary(order.values())
    expectation = dict(order='HELD' if summary == 'ORDER_COMMAND_FIRST' else 'NOT_HELD',
                       F1='HELD' if q2['F1']['label'] == 'SEPARATES' and
                       min(q2['F1']['fell'].values()) > max(q2['F1']['upright'].values()) else 'NOT_HELD')
    return dict(status='INTEGRITY_ACCEPTED', checks=checks, Q1=dict(per_arm=order, summary=summary), Q2=q2,
                expectation=expectation, fell=fell, upright=upright, pairs=pairs)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arms', type=Path, required=True, help='folder with the 37 Step D raw arms')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--smoke', action='store_true', help='plumbing only: two LEVEL control pairs, not evidence')
    args = parser.parse_args(argv)
    spec = protocol()
    if live.sha(ROOT/REPORT) != REPORT_SHA256:
        raise ValueError('Step D report identity mismatch')
    report = json.loads((ROOT/REPORT).read_text(encoding='utf-8'))
    bodymap = json.loads((ROOT/spec['sources']['bodymap']).read_text(encoding='utf-8'))
    legs = leg_groups(live.pools(bodymap))
    if args.smoke:
        off = reduce(c.load(args.arms/'OFF_LEVEL_19.json.gz'), legs)
        for t in ON_TYPES:
            analyse_pair(reduce(c.load(args.arms/f'{t}_LEVEL_19.json.gz'), legs), off)
        print('smoke ok')
        return 0
    hashes = {k: live.sha(args.arms/f'{k}.json.gz') for k in report['arm_sha256']}

    e = evaluate(lambda k: c.load(args.arms/f'{k}.json.gz'), hashes, report, legs)
    result = dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, report_sha256=REPORT_SHA256, evaluation=e,
                  interpretation_limits=spec['interpretation_limits'])
    with args.output.open('xb') as stream:
        stream.write((json.dumps(native(result), indent=1, allow_nan=False) + '\n').encode())
    print(json.dumps(native({k: e.get(k) for k in ('status', 'checks', 'fell', 'Q1', 'expectation')}), indent=1))
    print(json.dumps(native({f: v['label'] for f, v in (e.get('Q2') or {}).items()}), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
