"""Coxa hypothesis D3: does the closed hair-plate loop act as a resistance reflex?

Preregistered in docs/evidence/coxa-hypothesis-d3-v1/protocol.json. Four fixed arms
(C0, H1, H1_FLIP, H2) on Step C arm A_ON, one fresh process each. C0 is the
unchanged Step C session; H arms add the D2 hypothesis channels through a
hypothesis-labelled derivation of live-v3. live_v3_motor_interface is not modified.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np

from . import contact_context as context
from . import hair_plate_posture as c
from .tactile_boundary import create_session as create_v3_session, native
from ..embodiment import hair_plate_encoder as hp

ROOT = context.ROOT
PROTOCOL = 'docs/evidence/coxa-hypothesis-d3-v1/protocol.json'
PROTOCOL_SHA256 = 'b8d524d5fe14acba8c32d1c01b95f35839b77aee0065e6797719561f30eaa3a1'
SCHEMA = 'coxa-hypothesis-d3-arm-v1'
ARMS = ('C0', 'H1', 'H1_FLIP', 'H2')
BOUND, EPS, BAR = .25, 1e-9, .02
STEPS, TICKS, WINDOW_MS = c.STEPS, c.TICKS, c.WINDOW_MS


def protocol():
    raw = (ROOT/PROTOCOL).read_bytes()
    if PROTOCOL_SHA256 is None or hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('preregistered protocol changed')
    return json.loads(raw)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def d2_channels(spec):
    src = spec['sources']['d2_result']
    if sha(ROOT/src['path']) != src['sha256']:
        raise ValueError('D2 result identity mismatch')
    saved = json.loads((ROOT/src['path']).read_text(encoding='utf-8'))
    if saved['status'] != src['status']:
        raise ValueError('D2 result not ready')
    return saved['channels']


def definitions(arm, saved):
    """Kernel-format definitions for one H arm, ordered by action index."""
    defs = saved[arm]
    out = {}
    for name in sorted(defs, key=lambda n: defs[n]['action_index']):
        d = dict(defs[name])
        for key in ('positive_populations', 'negative_populations'):
            if key in d:
                d[key] = {p: tuple(int(i) for i in ids) for p, ids in d[key].items()}
        if 'body_ids' in d:
            d['body_ids'] = tuple(int(i) for i in d['body_ids'])
        out[name] = d
    return out


# ---- hypothesis-labelled live-v3 derivation ----------------------------------------

def derive(arm, defs, v3_protocol, records, v3_table):
    """Copies of the v3 objects with only the arm's coxa rows marked; inputs untouched."""
    from ..embodiment import live_v3_motor_interface as v3
    v3.validate_v3(v3_protocol, v3_table)
    value, rows = copy.deepcopy(dict(v3_protocol)), copy.deepcopy(list(v3_table))
    for name, d in defs.items():
        row = rows[d['action_index']]
        if row['actuator'] != name or row['neural_motor_admission']:
            raise RuntimeError('hypothesis row identity mismatch: ' + name)
        row.update(neural_motor_admission=True, coordinate_sign=int(d['coordinate_sign']),
                   motor_status=f'COXA_HYPOTHESIS_{arm}', handling='baseline_plus_neural_contribution',
                   reason='labelled coxa hypothesis channel (not an admission)')
    names = tuple(v3.V3_MOTOR) + tuple(defs)
    value['admitted_motor_interfaces'] = list(names)
    return value, copy.deepcopy(list(records)), rows, names


def table_difference(v3_table, rows):
    """{action_index: changed field names} between v3 and the derived table."""
    return {i: sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
            for i, (a, b) in enumerate(zip(v3_table, rows)) if a != b}


def make_gate(names):
    from ..embodiment.m7d_corrected_spontaneous import CONDITIONS
    names = tuple(names)

    def gate(values, condition, admitted):
        if condition not in CONDITIONS or tuple(values) != names or tuple(admitted) != names:
            raise RuntimeError('hypothesis contribution inventory or condition mismatch')
        return {n: float(values[n]) if condition == CONDITIONS[0] else 0. for n in admitted}
    return gate


def make_assertion(names):
    names = frozenset(names)

    def assertion(vector, table):
        if len(vector) != 42 or len(table) != 42:
            raise RuntimeError('hypothesis action-vector shape failure')
        if {r['actuator'] for r in table if r['neural_motor_admission']} != names:
            raise RuntimeError('hypothesis admitted inventory mismatch')
        for row, value in zip(table, vector):
            if not math.isfinite(float(value)) or (not row['neural_motor_admission'] and value != 0.):
                raise RuntimeError(f"unauthorized hypothesis neural contribution: {row['actuator']}")
    return assertion


def create_hypothesis_session(trial, arm, defs):
    """tactile_boundary.create_session with only the declared hypothesis substitutions."""
    from ..embodiment import _windows_m7d_corrected_spontaneous_adapter as adapter
    from ..embodiment import _windows_m8_live_condition as kernel
    from ..embodiment import live_v2_motor_interface as v2, live_v3_motor_interface as v3
    from ..embodiment import m7d_corrected_spontaneous as m7d
    v1_protocol, records, v1_table = adapter._protocol()
    v2_protocol, records, v2_table = v2.derive_v2(v1_protocol, records, v1_table)
    v3_protocol, records, v3_table = v3.derive_v3(v2_protocol, records, v2_table)
    protocol_h, records, table, names = derive(arm, defs, v3_protocol, records, v3_table)

    def runtime(flygym, interfaces):
        sim, physics, obs, tid, sid = adapter._runtime(flygym, interfaces)
        try:
            trial.bind(sim, physics, obs)
        except BaseException:
            sim.close()
            raise
        return context.ObservedSimulation(sim, physics, trial), physics, obs, tid, sid
    return kernel.create_scientific_session(
        protocol=protocol_h, condition=m7d.CONDITIONS[0], condition_number=1,
        progress=lambda *_: '', cached_admission_assertion=make_assertion(names),
        cached_records=records, cached_table=table, condition_names=m7d.CONDITIONS,
        contribution_gate=make_gate(names), compact_telemetry=False, runtime_factory=runtime,
        proprioception_only=True, fixed_initial_baseline=True, m8_extended_telemetry=False,
        continuous=True, motor_channel_names=names,
        supplemental_motor_channels={**dict(v3.SUPPLEMENTAL_MOTOR_CHANNELS), **defs},
        telemetry_observer=trial.observe, motor_state_probe_factory=trial.attach)


# ---- preflight ---------------------------------------------------------------------

def historical_dense(data, v3_table):
    """Dense indices of the 20 v3 channels' populations, resolved as the kernel does."""
    from ..embodiment import live_v3_motor_interface as v3
    from ..embodiment.six_tibia import load_six_tibia_interfaces
    from ..embodiment.integrated_whole_leg_readiness import TIER_A
    from ..embodiment._windows_isolated_tier_b_motor_validation_adapter import _population_index
    interfaces = {x['physical_joint']: x for x in json.loads(
        (ROOT/'malecns_backend/embodiment/interface_output/isolated_tier_b_motor_validation.json')
        .read_text())['interfaces']}
    tibia, rows = load_six_tibia_interfaces(), {r['actuator']: r for r in v3_table}
    out = set()
    for name in v3.V3_MOTOR:
        if name in v3.SUPPLEMENTAL_MOTOR_CHANNELS:
            out |= channel_dense({name: v3.SUPPLEMENTAL_MOTOR_CHANNELS[name]}, data)
        elif name in TIER_A:
            out |= {int(i) for p in tibia[rows[name]['leg']].motor_populations for i in p.dense_indices}
        else:
            populations, _, _ = _population_index(interfaces[name], data)
            out |= {int(i) for ids in populations.values() for i in ids}
    return out


def channel_dense(defs, data):
    out = set()
    for d in defs.values():
        pops = [d['body_ids']] if 'body_ids' in d else [*d['positive_populations'].values(), *d['negative_populations'].values()]
        out |= {int(data.body_id_to_index[int(b)]) for ids in pops for b in ids}
    return out


def preflight():
    from malecns_backend import load_malecns
    from ..embodiment import _windows_m7d_corrected_spontaneous_adapter as adapter
    from ..embodiment import _windows_m8_live_condition as kernel
    from ..embodiment import live_v2_motor_interface as v2, live_v3_motor_interface as v3
    spec = protocol()
    checks, detail = {}, {}
    try:
        saved = d2_channels(spec)
        checks['P1_d2'] = True
    except ValueError as exc:
        return dict(status='PREFLIGHT_FAILED', checks=dict(P1_d2=False), error=str(exc))
    data = load_malecns()
    v1_protocol, records, v1_table = adapter._protocol()
    v2_protocol, records, v2_table = v2.derive_v2(v1_protocol, records, v1_table)
    v3_protocol, records, v3_table = v3.derive_v3(v2_protocol, records, v2_table)
    table_by_name = {r['actuator']: r for r in v3_table}
    hist = historical_dense(data, v3_table)
    p2, p5 = True, True
    for arm in ARMS[1:]:
        defs = definitions(arm, saved)
        try:
            kernel._resolve_supplemental_channels({**dict(v3.SUPPLEMENTAL_MOTOR_CHANNELS), **defs}, data,
                                                  table_by_name, tuple(n for n in v3.V3_MOTOR
                                                                       if n not in v3.SUPPLEMENTAL_MOTOR_CHANNELS))
            overlap = sorted(channel_dense(defs, data) & hist)
        except ValueError as exc:
            detail[arm] = str(exc)
            p2 = False
            continue
        p2 &= not overlap
        _, _, rows, names = derive(arm, defs, v3_protocol, records, v3_table)
        diff = table_difference(v3_table, rows)
        expected = {d['action_index'] for d in defs.values()}
        allowed = {'neural_motor_admission', 'coordinate_sign', 'motor_status', 'handling', 'reason'}
        p5 &= set(diff) == expected and all(set(v) <= allowed for v in diff.values())
        try:
            v3.validate_v3(v3_protocol, v3_table)
        except RuntimeError:
            p5 = False
        detail[arm] = dict(channels=len(defs), historical_overlap=overlap, changed_rows=sorted(diff))
    checks['P2_resolver'] = p2
    checks['P3_schedule'] = 'ENFORCED_AT_RUN_TIME_BY_STEP_C_TRIAL_ATTACH'
    src = spec['sources']
    report = json.loads((ROOT/src['step_c_report']['path']).read_text(encoding='utf-8'))
    raw = ROOT/src['step_c_a_on_raw']['path']
    checks['P4_step_c_raw'] = (sha(ROOT/src['step_c_report']['path']) == src['step_c_report']['sha256']
                               and raw.exists() and sha(raw) == src['step_c_a_on_raw']['sha256']
                               == report['arm_sha256']['A_ON'])
    checks['P5_derivation'] = p5
    ok = all(v is True or isinstance(v, str) for v in checks.values())
    return dict(status='PREFLIGHT_PASSED' if ok else 'PREFLIGHT_FAILED', checks=checks, detail=detail)


# ---- arms --------------------------------------------------------------------------

class Trial(c.Trial):
    """Step C A_ON trial unchanged, plus a record of the kernel's channel inventory."""

    def __init__(self, arm):
        super().__init__('A_ON')
        self.d3_arm = arm

    def attach(self, brain, channels, *, sensory_sources):
        out = super().attach(brain, channels, sensory_sources=sensory_sources)
        self.initial['channels'] = {name: dict(
            index=int(ch['index']), sign=int(ch['sign']), decoder_mode=str(ch['decoder_mode']),
            bound=float(ch['bound']), positive=list(ch['positive']), negative=list(ch['negative']),
            populations={p: sorted(int(i) for i in ids) for p, ids in ch['populations'].items()})
            for name, ch in channels.items()}
        return out


def run_arm(arm, progress=print):
    spec = protocol()
    if arm not in ARMS:
        raise ValueError('unknown arm')
    defs = None if arm == 'C0' else definitions(arm, d2_channels(spec))
    trial = Trial(arm)
    result = dict(schema=SCHEMA, arm=arm, run_status='ERROR', protocol_sha256=PROTOCOL_SHA256,
                  hypothesis_channels=sorted(defs) if defs else [])
    session = None
    try:
        session = create_v3_session(trial) if defs is None else create_hypothesis_session(trial, arm, defs)
        progress(f'{arm}: fresh CNS/physics initialization', flush=True)
        state = session.initialize()
        if state.time_ms != 0.:
            raise RuntimeError('nonzero initial simulation time')
        last = time.monotonic()
        for step in range(1, STEPS + 1):
            state = session.step(lightweight=True)
            if state.physics_transitions != step or state.neural_transitions != step // 5:
                raise RuntimeError('authoritative transition count mismatch')
            if time.monotonic() - last >= 30:
                progress(f'{arm}: {step}/{STEPS}', flush=True)
                last = time.monotonic()
        result['run_status'] = 'COMPLETE'
    except (Exception, KeyboardInterrupt) as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        if session is not None:
            try:
                session.close()
            except Exception as exc:
                result.update(run_status='ERROR', close_error=f'{type(exc).__name__}: {exc}')
        trial.detach()
        result.update(samples=trial.samples, neural=trial.neural, initial=trial.initial, event=trial.event)
    return result


# ---- evaluation --------------------------------------------------------------------

def window(arm):
    lo, hi = WINDOW_MS
    return [t for t in arm['neural'] if lo < t['time_ms'] <= hi]


def mean_by_leg(arm, key):
    w = window(arm)
    return {leg: float(np.mean([t[key][leg] for t in w])) for leg in hp.LEGS}


def first_command_change(arm, indices, base):
    for k, s in enumerate(arm['samples']):
        if s['commanded_joints'] is not None and any(s['commanded_joints'][i] != base[i] for i in indices):
            return k
    return None


def evaluate(arms, step_c, defs, v3_names, bodymap):
    checks = {}
    checks['I1_complete'] = all(a['run_status'] == 'COMPLETE' and len(a['samples']) == STEPS + 1
                                and len(a['neural']) == TICKS for a in arms.values())
    if not checks['I1_complete']:
        return dict(status='INCONCLUSIVE_INTEGRITY', checks=checks)
    ref = arms['C0']
    uni = [t['uniforms_sha256'] for t in ref['neural']]
    checks['I2_common_rng'] = all(a['initial']['external_schedule'] == ref['initial']['external_schedule']
                                  and [t['uniforms_sha256'] for t in a['neural']] == uni for a in arms.values())
    checks['I3_reproduces_step_c'] = (
        len(step_c['neural']) == TICKS and len(step_c['samples']) == STEPS + 1
        and all(x['fired'] == y['fired'] and x['uniforms_sha256'] == y['uniforms_sha256']
                and x['hair_delivered'] == y['hair_delivered'] for x, y in zip(ref['neural'], step_c['neural']))
        and all(x['qpos'] == y['qpos'] for x, y in zip(ref['samples'], step_c['samples'])))
    v3_inv = {n: ref['initial']['channels'][n] for n in v3_names}
    base = ref['samples'][1]['commanded_joints']  # sample 0 is the bind-time state (no command)
    v3_idx = {ch['index'] for ch in v3_inv.values()}
    i4, offsets, first = True, {}, {}
    for arm in ARMS[1:]:
        a, d = arms[arm], defs[arm]
        h_idx = {name: x['action_index'] for name, x in d.items()}
        i4 &= ({n: a['initial']['channels'].get(n) for n in v3_names} == v3_inv
               and set(a['initial']['channels']) == set(v3_names) | set(d))
        i4 &= all(s['commanded_joints'][i] == base[i] for s in ref['samples'][1:] for i in h_idx.values())
        outside = [i for i in range(42) if i not in v3_idx and i not in h_idx.values()]
        i4 &= all(s['commanded_joints'][i] == r['commanded_joints'][i]
                  for s, r in zip(a['samples'][1:], ref['samples'][1:]) for i in outside)
        off = {name: [s['commanded_joints'][i] - base[i] for s in a['samples'][1:]] for name, i in h_idx.items()}
        i4 &= all(abs(x) <= BOUND + EPS for v in off.values() for x in v)
        offsets[arm] = {name: dict(mean=float(np.mean(v)), max_abs=float(np.max(np.abs(v))),
                                   saturated_fraction=float(np.mean([abs(x) >= BOUND - 1e-6 for x in v])))
                        for name, v in off.items()}
        first[arm] = first_command_change(a, list(h_idx.values()), base)
    checks['I4_inventory_bounds'] = bool(i4)
    i5 = True
    for arm in ARMS[1:]:
        a, k = arms[arm], first[arm]
        k = len(a['samples']) if k is None else k
        t_k = a['samples'][k]['time_s']*1000. if k < len(a['samples']) else math.inf
        i5 &= all(x['qpos'] == y['qpos'] and x['commanded_joints'] == y['commanded_joints']
                  for x, y in zip(a['samples'][:k], ref['samples'][:k]))
        i5 &= all(x['fired'] == y['fired'] for x, y in zip(a['neural'], ref['neural']) if x['time_ms'] < t_k)
    checks['I5_prefix'] = bool(i5)
    if not all(checks.values()):
        return dict(status='INCONCLUSIVE_INTEGRITY', checks=checks, first_h_command_sample=first)
    rate0 = mean_by_leg(ref, 'hair_rate_hz')
    firing = [leg for leg in hp.LEGS if rate0[leg] > 0]
    f0 = mean_by_leg(ref, 'hair_forward')
    delta = {arm: {leg: mean_by_leg(arms[arm], 'hair_forward')[leg] - f0[leg] for leg in hp.LEGS} for arm in ARMS[1:]}
    post = {arm: [leg for leg in firing if delta[arm][leg] <= -BAR] for arm in ARMS[1:]}
    ant_flip = [leg for leg in post['H1'] if delta['H1_FLIP'][leg] >= BAR]
    if len(firing) < 3:
        q3 = 'NOT_TESTABLE'
    elif len(post['H1']) >= 3:
        q3 = 'RESISTANCE_CONSISTENT' if len(ant_flip) >= 3 else 'SIGN_ONLY_CONSISTENT'
    else:
        q3 = 'NOT_CONSISTENT'
    n1, n2 = len(post['H1']), len(post['H2'])
    q4 = 'H1_FAVOURED' if n1 > n2 else 'H2_FAVOURED' if n2 > n1 else 'NOT_DISTINGUISHED'
    return dict(status='INTEGRITY_ACCEPTED', checks=checks, first_h_command_sample=first,
                firing_legs=firing, c0_hair_rate_hz=rate0, c0_forward=f0, delta_f=delta,
                posterior_shift_legs=post, flip_anterior_legs_among_h1=ant_flip,
                Q3=dict(label=q3), Q4=dict(label=q4, h1=n1, h2=n2),
                descriptive=descriptive(arms, bodymap, offsets))


def descriptive(arms, bodymap, offsets):
    sets, per_leg = c.mn_sets(bodymap)
    out = dict(channel_offsets_rad=offsets)
    out['hair_rate_hz'] = {k: mean_by_leg(a, 'hair_rate_hz') for k, a in arms.items()}
    out['hair_delivered'] = {k: sum(len(t['hair_delivered']) for t in a['neural']) for k, a in arms.items()}
    out['coxa_mn_rates_hz'] = {k: {n: c.rate(a, ids) for n, ids in sets.items()} for k, a in arms.items()}
    out['coxa_mn_rates_per_leg_hz'] = {k: {leg: c.rate(a, ids) for leg, ids in per_leg.items()} for k, a in arms.items()}
    bins = np.arange(0., 2000.01, 100.)
    out['forward_100ms_bins'] = {k: {leg: [float(np.mean([t['hair_forward'][leg] for t in a['neural'] if lo < t['time_ms'] <= hi]))
                                        for lo, hi in zip(bins[:-1], bins[1:])] for leg in hp.LEGS} for k, a in arms.items()}
    out['tilt_deg'] = {k: dict(mean=float(np.mean([c.tilt_deg(s['qpos']) for s in a['samples']])),
                               peak=float(np.max([c.tilt_deg(s['qpos']) for s in a['samples']]))) for k, a in arms.items()}
    ref = arms['C0']['samples']
    out['first_physical_divergence_vs_C0'] = {k: next((i for i, (x, y) in enumerate(zip(a['samples'], ref))
                                                       if x['qpos'] != y['qpos']), None) for k, a in arms.items() if k != 'C0'}
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--arm', choices=ARMS)
    parser.add_argument('--evaluate', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.preflight:
        result = preflight()
        with args.output.open('xb') as stream:
            stream.write((json.dumps(native(result), indent=1) + '\n').encode())
        print(json.dumps(native(result), indent=1))
        return 0 if result['status'] == 'PREFLIGHT_PASSED' else 1
    if args.arm:
        args.output.mkdir(parents=True, exist_ok=True)
        target = args.output/f'{args.arm}.json.gz'
        with target.open('xb'):
            pass  # claim the exclusive path before running
        target.unlink()
        result = run_arm(args.arm)
        digest = c.save(target, result)
        print(json.dumps(dict(arm=args.arm, run_status=result['run_status'], error=result.get('error'), sha256=digest)))
        return 0 if result['run_status'] == 'COMPLETE' else 1
    spec = protocol()
    from ..embodiment import live_v3_motor_interface as v3
    folder = args.evaluate
    arms = {k: c.load(folder/f'{k}.json.gz') for k in ARMS}
    hashes = {k: sha(folder/f'{k}.json.gz') for k in ARMS}
    raw = ROOT/spec['sources']['step_c_a_on_raw']['path']
    if sha(raw) != spec['sources']['step_c_a_on_raw']['sha256']:
        raise ValueError('Step C A_ON raw identity mismatch')
    saved = d2_channels(spec)
    defs = {arm: definitions(arm, saved) for arm in ARMS[1:]}
    bodymap = json.loads((ROOT/'fly-brain-main/public/data/bodymap.json').read_text(encoding='utf-8'))
    report = dict(schema='coxa-hypothesis-d3-report-v1', protocol_sha256=PROTOCOL_SHA256, arm_sha256=hashes,
                  evaluation=evaluate(arms, c.load(raw), defs, tuple(v3.V3_MOTOR), bodymap))
    with args.output.open('xb') as stream:
        stream.write((json.dumps(native(report), indent=1, allow_nan=False) + '\n').encode())
    e = report['evaluation']
    print(json.dumps(native({k: e.get(k) for k in ('status', 'checks', 'firing_legs', 'delta_f', 'Q3', 'Q4')}), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
