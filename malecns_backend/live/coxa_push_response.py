"""Fore-aft push response with the four conditional coxa channels (V1).

Preregistered in docs/evidence/coxa-push-response-v1/protocol.json (design:
docs/COXA_PUSH_RESPONSE_V1.md). 27 fixed arms ({N, C, X} x {no push, F, B} x CNS seeds 1-3)
on Step C arm A_ON, one fresh process each. The pulse is the existing M9B engineering pulse
(1.024 native force on the Thorax COM, outgoing transitions 5000-5199, zero torque) applied
through the kernel's external_force_by_transition callback, with a declared fore-aft
direction. C/X add the four CONDITIONAL channels (COXA_CONDITIONAL_H1) H1 / H1_FLIP through a
hypothesis-labelled derivation of live-v3. The kernel and live_v3 are unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np

from . import assistance_native as mechanical
from . import coxa_admission as ca
from . import coxa_hypothesis_loop as loop
from . import hair_plate_posture as c
from . import tactile_recovery_metrics as metrics
from .contact_context import LEGS as CONTACT_LEGS
from .tactile_boundary import native

context = c.context
ROOT = loop.ROOT
PROTOCOL = 'docs/evidence/coxa-push-response-v1/protocol.json'
PROTOCOL_SHA256 = 'ec3f0de12aea92b53cc2aedd2df08c7e4020619ecb8ae088c0b08cbfb098b7c6'
SCHEMA = 'coxa-push-response-arm-v1'
LABEL = 'COXA_CONDITIONAL_H1'
CANDIDATES = ('joint_LFCoxa', 'joint_LHCoxa', 'joint_LMCoxa', 'joint_RMCoxa')
SEEDS = (1, 2, 3)
SETS = {'N': None, 'C': 'H1', 'X': 'H1_FLIP'}
PUSHES = {'0': 0., 'F': 1., 'B': -1.}
ARMS = tuple(f'{k}{p}_{s}' for s in SEEDS for k in SETS for p in PUSHES)
MAGNITUDE, START, STOP = 1.024, 5000, 5200
DT = 1e-4
FIRST_CLEARED = STOP + 1  # first stored state after the last forced transition (520.1 ms)
ATTENUATE, AMPLIFY = .90, 1.10


def protocol():
    raw = (ROOT/PROTOCOL).read_bytes()
    if PROTOCOL_SHA256 is None or hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('preregistered protocol changed')
    return json.loads(raw)


def split(arm):
    head, seed = arm.rsplit('_', 1)
    if len(head) != 2 or head[0] not in SETS or head[1] not in PUSHES or int(seed) not in SEEDS:
        raise ValueError('unknown arm')
    return head[0], head[1], int(seed)


def force_at_transition(push, transition):
    """World force on the Thorax COM during outgoing transition `transition`."""
    sign = PUSHES[push]
    return (MAGNITUDE*sign if sign and START <= transition < STOP else 0., 0., 0.)


def candidate_defs(d2_arm, saved):
    defs = loop.definitions(d2_arm, saved)  # action-index order, as in D3
    out = {n: d for n, d in defs.items() if n in CANDIDATES}
    if set(out) != set(CANDIDATES):
        raise ValueError('candidate channel missing from D2')
    return out


def support_count(contacts, table):
    ground = {i for i in table['ground_geom_ids']
              if context.identities.namespace_component(table['geom_names'][i]) == 'ground'}
    by_geom = {i: leg for leg in CONTACT_LEGS for i, name in enumerate(table['geom_names'])
               if context.identities.namespace_component(name) == f'{leg}Tarsus5'}
    legs = set()
    for pair in contacts:
        a, b = pair['geom1_id'], pair['geom2_id']
        if a in ground and b in by_geom:
            legs.add(by_geom[b])
        if b in ground and a in by_geom:
            legs.add(by_geom[a])
    return len(legs)


# ---- adapter -----------------------------------------------------------------------

class Trial(loop.Trial):
    """Step C A_ON + channel inventory, with a declared seed, push and exact force record."""

    def __init__(self, arm):
        kind, push, seed = split(arm)
        super().__init__(arm)
        self.kind, self.push, self.seed = kind, push, seed

    def bind(self, sim, physics, obs):
        if not (int(physics.model.jnt_type[0]) == 0 and int(physics.model.jnt_qposadr[0]) == 0
                and int(physics.model.jnt_dofadr[0]) == 0):
            raise RuntimeError('native leading free-joint pose/velocity layout required')
        names = [context.identities.compiled_name(physics.model, 'body', i) for i in range(int(physics.model.nbody))]
        thorax = [i for i, n in enumerate(names) if context.identities.namespace_component(n) == 'Thorax']
        if len(thorax) != 1 or thorax[0] == 0:
            raise RuntimeError('unique exact Thorax body required')
        self.thorax_id = thorax[0]
        super().bind(sim, physics, obs)
        if self.thorax_id in self.context['identity']['tarsus5_body_ids'].values():
            raise RuntimeError('disturbance body overlaps a distal force sensor')
        self.context_force_body = dict(id=self.thorax_id, name=names[self.thorax_id], frame='world',
                                       point='body COM', torque=[0., 0., 0.])

    def capture(self, physics, obs, action):
        context.PassiveRecorder.capture(self, physics, obs, action)
        s = self.samples[-1]
        wrenches = np.asarray(physics.data.xfrc_applied)
        self.samples[-1] = dict(
            time_s=s['time_s'], qpos=s['qpos'], qvel=s['qvel'], commanded_joints=s['commanded_joints'],
            telemetry_forces=s['telemetry_forces'], supports=support_count(s['contacts'], self.context['identity']),
            applied_body_wrenches=[dict(body_id=int(i), wrench=wrenches[i].tolist())
                                   for i in np.flatnonzero(np.any(wrenches != 0, axis=1))],
            external_applied_max=s['external_applied_max'], generalized_applied_max=s['generalized_applied_max'])
        index = len(self.samples) - 1
        if index == c.EVENT_STATE:  # Step C A_ON boundary: observe only, model must be unchanged
            before = mechanical.model_record(physics.model, physics.data)
            if before != self.original:
                raise RuntimeError('undeclared mechanical model change')
            self.event = dict(state_index=index, time_s=float(physics.data.time), operation='OBSERVE_ONLY',
                              after_sha256=before['sha256'], original_sha256=self.original['sha256'])

    def attach(self, brain, channels, *, sensory_sources):
        fresh = np.random.default_rng(1).bit_generator.state
        if (brain.time_ms != 0. or int(brain.spike_counts.sum()) != 0
                or not brain._rng_states_equal(brain.rng.bit_generator.state, fresh)):
            raise RuntimeError('seed must be applied before the first neural transition')
        brain.rng = np.random.default_rng(self.seed)
        out = super().attach(brain, channels, sensory_sources=sensory_sources)
        self.initial['cns_seed'] = self.seed
        self.initial['force_body'] = self.context_force_body
        return out


def create_session(trial, d2_arm, defs):
    """tactile_boundary/D3 session settings plus the kernel's existing force callback."""
    from ..embodiment import _windows_m7d_corrected_spontaneous_adapter as adapter
    from ..embodiment import _windows_m8_live_condition as kernel
    from ..embodiment import live_v2_motor_interface as v2, live_v3_motor_interface as v3
    from ..embodiment import m7d_corrected_spontaneous as m7d
    v1_protocol, records, v1_table = adapter._protocol()
    v2_protocol, records, v2_table = v2.derive_v2(v1_protocol, records, v1_table)
    value, records, table = v3.derive_v3(v2_protocol, records, v2_table)
    if defs is None:
        names, assertion, gate, supplemental = (v3.V3_MOTOR, v3.assert_v3_physical_admission, v3.gate_contributions,
                                                v3.SUPPLEMENTAL_MOTOR_CHANNELS)
    else:
        value, records, table, names = loop.derive(d2_arm, defs, value, records, table)
        assertion, gate = loop.make_assertion(names), loop.make_gate(names)
        supplemental = {**dict(v3.SUPPLEMENTAL_MOTOR_CHANNELS), **defs}

    def runtime(flygym, interfaces):
        sim, physics, obs, tid, sid = adapter._runtime(flygym, interfaces)
        try:
            trial.bind(sim, physics, obs)
        except BaseException:
            sim.close()
            raise
        return context.ObservedSimulation(sim, physics, trial), physics, obs, tid, sid
    return kernel.create_scientific_session(
        protocol=value, condition=m7d.CONDITIONS[0], condition_number=1, progress=lambda *_: '',
        cached_admission_assertion=assertion, cached_records=records, cached_table=table,
        condition_names=m7d.CONDITIONS, contribution_gate=gate, compact_telemetry=False, runtime_factory=runtime,
        proprioception_only=True, fixed_initial_baseline=True, m8_extended_telemetry=False, continuous=True,
        motor_channel_names=names, supplemental_motor_channels=supplemental, telemetry_observer=trial.observe,
        motor_state_probe_factory=trial.attach,
        external_force_by_transition=lambda _, i: force_at_transition(trial.push, i))


def run_arm(arm, progress=print, steps=c.STEPS):
    spec = protocol()
    kind, push, seed = split(arm)
    defs = None
    if SETS[kind] is not None:
        defs = candidate_defs(SETS[kind], loop.d2_channels(loop.protocol()))
        if ca.defs_sha256(defs) != spec['candidates'][SETS[kind]]['sha256']:
            raise RuntimeError('candidate definitions differ from preregistration')
    trial = Trial(arm)
    result = dict(schema=SCHEMA, arm=arm, run_status='ERROR', protocol_sha256=PROTOCOL_SHA256, cns_seed=seed, push=push,
                  hypothesis_channels=sorted(defs) if defs else [], label=LABEL if defs else None,
                  definitions_sha256=ca.defs_sha256(defs) if defs else None)
    session = None
    try:
        session = create_session(trial, SETS[kind], defs)
        progress(f'{arm}: fresh CNS/physics initialization', flush=True)
        state = session.initialize()
        if state.time_ms != 0.:
            raise RuntimeError('nonzero initial simulation time')
        last = time.monotonic()
        for step in range(1, steps + 1):
            state = session.step(lightweight=True)
            if state.physics_transitions != step or state.neural_transitions != step // 5:
                raise RuntimeError('authoritative transition count mismatch')
            if time.monotonic() - last >= 30:
                progress(f'{arm}: {step}/{steps}', flush=True)
                last = time.monotonic()
        result['run_status'] = 'COMPLETE' if steps == c.STEPS else 'SMOKE'
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


# ---- evaluation (pure on arm records) ------------------------------------------------

def force_ok(arm, push):
    body = (arm['initial'] or {}).get('force_body') or {}
    bid = body.get('id')
    good = (body.get('frame') == 'world' and body.get('point') == 'body COM' and body.get('torque') == [0., 0., 0.])
    for i, s in enumerate(arm['samples']):
        v = np.asarray(force_at_transition(push, i - 1) if i else (0., 0., 0.))
        expected = [] if not np.any(v) else [dict(body_id=bid, wrench=v.tolist() + [0., 0., 0.])]
        good &= (s['applied_body_wrenches'] == expected and s['external_applied_max'] == float(np.max(np.abs(v)))
                 and s['generalized_applied_max'] == 0)
    return bool(good)


def deviation_integral(pushed, control):
    """Trapezoidal integral (model mm * s) of root-position deviation over the cleared window."""
    d = np.linalg.norm(pushed['position'] - control['position'], axis=1)
    return float(np.sum((d[FIRST_CLEARED:-1] + d[FIRST_CLEARED + 1:])*.5)*DT)


def q_loop(ratios):
    if all(r <= ATTENUATE for r in ratios):
        return 'LOOP_ATTENUATES'
    if all(r >= AMPLIFY for r in ratios):
        return 'LOOP_AMPLIFIES'
    return 'NO_CONSISTENT_LOOP_EFFECT'


def q_sign(loop_label, flip_ratios):
    if loop_label == 'NO_CONSISTENT_LOOP_EFFECT':
        return 'NOT_EVALUATED'
    passes = [r <= ATTENUATE if loop_label == 'LOOP_ATTENUATES' else r >= AMPLIFY for r in flip_ratios]
    return 'SIGN_SPECIFIC' if sum(not p for p in passes) >= 2 else 'SIGN_INDEPENDENT'


def prefix_equal(a, b, n_samples, t_ms):
    return (all(x['qpos'] == y['qpos'] and x['commanded_joints'] == y['commanded_joints']
                for x, y in zip(a['samples'][:n_samples], b['samples'][:n_samples]))
            and all(x['fired'] == y['fired'] for x, y in zip(a['neural'], b['neural']) if x['time_ms'] <= t_ms))


def integrity(arms, c0, spec, v3_names, indices):
    checks = {}
    checks['I1_complete'] = all(a['run_status'] == 'COMPLETE' and len(a['samples']) == c.STEPS + 1
                                and len(a['neural']) == c.TICKS for a in arms.values())
    if not checks['I1_complete']:
        return checks, {}
    i2 = True
    for s in SEEDS:
        ref = arms[f'N0_{s}']
        uni = [t['uniforms_sha256'] for t in ref['neural']]
        i2 &= all(arms[f'{k}{p}_{s}']['initial']['external_schedule'] == ref['initial']['external_schedule']
                  and [t['uniforms_sha256'] for t in arms[f'{k}{p}_{s}']['neural']] == uni for k in SETS for p in PUSHES)
    checks['I2_common_rng_within_seed'] = bool(i2)
    i3 = True
    for s in SEEDS:
        a, r = arms[f'N0_{s}'], c0[s]
        i3 &= (len(r['samples']) == len(a['samples']) and len(r['neural']) == len(a['neural'])
               and all(x['qpos'] == y['qpos'] for x, y in zip(a['samples'], r['samples']))
               and all(x['fired'] == y['fired'] and x['uniforms_sha256'] == y['uniforms_sha256']
                       and x['hair_delivered'] == y['hair_delivered'] for x, y in zip(a['neural'], r['neural'])))
    checks['I3_reproduces_c0'] = bool(i3)
    checks['I4_exact_force'] = all(force_ok(a, split(k)[1]) for k, a in arms.items())
    v3_inv = {n: arms['N0_1']['initial']['channels'][n] for n in v3_names}
    v3_idx = {ch['index'] for ch in v3_inv.values()}
    outside = [i for i in range(42) if i not in v3_idx and i not in indices.values()]
    i5, first, offs = True, {}, {}
    for s in SEEDS:
        for p in PUSHES:
            n = arms[f'N{p}_{s}']
            base = n['samples'][1]['commanded_joints']
            i5 &= set(n['initial']['channels']) == set(v3_names) and not n['hypothesis_channels']
            i5 &= all(x['commanded_joints'][i] == base[i] for x in n['samples'][1:] for i in indices.values())
            for k in ('C', 'X'):
                arm = f'{k}{p}_{s}'
                a = arms[arm]
                i5 &= ({nm: a['initial']['channels'].get(nm) for nm in v3_names} == v3_inv
                       and set(a['initial']['channels']) == set(v3_names) | set(CANDIDATES)
                       and a['hypothesis_channels'] == sorted(CANDIDATES) and a['label'] == LABEL
                       and a['definitions_sha256'] == spec['candidates'][SETS[k]]['sha256'])
                i5 &= all(x['commanded_joints'][i] == y['commanded_joints'][i]
                          for x, y in zip(a['samples'][1:], n['samples'][1:]) for i in outside)
                off = ca.offsets(a, base, indices)
                i5 &= all(abs(x) <= loop.BOUND + loop.EPS for v in off.values() for x in v)
                offs[arm] = off
                first[arm] = loop.first_command_change(a, list(indices.values()), base)
            i5 &= {nm: n['initial']['channels'].get(nm) for nm in v3_names} == v3_inv
    checks['I5_channels_bounds'] = bool(i5)
    i6 = True
    t_force = START*DT*1000.
    for s in SEEDS:
        for k in SETS:
            for p in ('F', 'B'):
                i6 &= prefix_equal(arms[f'{k}{p}_{s}'], arms[f'{k}0_{s}'], START + 1, t_force)
    for arm, kf in first.items():
        a = arms[arm]
        n = arms[f'N{split(arm)[1]}_{split(arm)[2]}']
        kf = len(a['samples']) if kf is None else kf
        t_k = a['samples'][kf]['time_s']*1000. if kf < len(a['samples']) else math.inf
        i6 &= all(x['qpos'] == y['qpos'] and x['commanded_joints'] == y['commanded_joints']
                  for x, y in zip(a['samples'][:kf], n['samples'][:kf]))
        i6 &= all(x['fired'] == y['fired'] for x, y in zip(a['neural'], n['neural']) if x['time_ms'] < t_k)
    checks['I6_prefixes'] = bool(i6)
    tick1 = [arms[f'N0_{s}']['neural'][0]['uniforms_sha256'] for s in SEEDS]
    checks['I7_seeds_applied'] = (len(set(tick1)) == len(SEEDS)
                                  and all(a['initial'].get('cns_seed') == split(k)[2] for k, a in arms.items()))
    return checks, dict(first_command_sample=first, offsets=offs)


def evaluate(arms, c0, spec, v3_names, indices, bodymap=None):
    checks, audit = integrity(arms, c0, spec, v3_names, indices)
    if not all(checks.values()):
        return dict(status='INCONCLUSIVE_INTEGRITY', checks=checks)
    traces = {k: metrics.trace(a, [x['supports'] for x in a['samples']]) for k, a in arms.items()}
    responses, d_int, fore_aft = {}, {}, {}
    for k in arms:
        kind, push, s = split(k)
        if push == '0':
            continue
        ctrl = traces[f'{kind}0_{s}']
        responses[k] = metrics.response(traces[k], ctrl, start=START, stop=STOP)
        d_int[k] = deviation_integral(traces[k], ctrl)
        dx = (traces[k]['position'][:, 0] - ctrl['position'][:, 0])*PUSHES[push]
        fore_aft[k] = dict(peak_along_push_mm=float(np.max(dx[START:])), min_along_push_mm=float(np.min(dx[START:])),
                           cleared_mean_along_push_mm=float(np.mean(dx[FIRST_CLEARED:])))
    pulse = {f'N{p}_{s}': responses[f'N{p}_{s}']['resolved_perturbation'] for s in SEEDS for p in ('F', 'B')}
    base = dict(checks=checks, pulse_resolved=pulse, responses=responses, deviation_integral_mm_s=d_int,
                fore_aft_deviation=fore_aft, first_command_sample=audit['first_command_sample'])
    if not all(pulse.values()):
        return dict(status='INCONCLUSIVE_PULSE', **base)
    labels, ratios = {}, {}
    for p in ('F', 'B'):
        r = [d_int[f'C{p}_{s}']/d_int[f'N{p}_{s}'] for s in SEEDS]
        rf = [d_int[f'X{p}_{s}']/d_int[f'N{p}_{s}'] for s in SEEDS]
        ql = q_loop(r)
        labels[p] = dict(Q_LOOP=ql, Q_SIGN=q_sign(ql, rf))
        ratios[p] = dict(loop=r, flip=rf)
    lo, hi = c.WINDOW_MS
    hair = {k: loop.mean_by_leg(a, 'hair_rate_hz') for k, a in arms.items()}
    offsets = {k: {n: float(np.mean([x for x, inside in zip(v, ca.in_window(arms[k])) if inside])) for n, v in off.items()}
               for k, off in audit['offsets'].items()}
    out = dict(status='INTEGRITY_ACCEPTED', labels=labels, ratios=ratios, **base, hair_rate_hz=hair,
               channel_offsets_window_rad=offsets,
               tilt_deg={k: dict(mean=float(np.mean([c.tilt_deg(x['qpos']) for x in a['samples']])),
                                 peak=float(np.max([c.tilt_deg(x['qpos']) for x in a['samples']]))) for k, a in arms.items()})
    if bodymap is not None:
        _, per_leg = c.mn_sets(bodymap)
        out['coxa_mn_rates_per_leg_hz'] = {k: {leg: c.rate(a, ids) for leg, ids in per_leg.items()} for k, a in arms.items()}
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hashes', action='store_true', help='print candidate definition hashes')
    parser.add_argument('--arm', choices=ARMS)
    parser.add_argument('--smoke-steps', type=int, help='plumbing smoke only; output is not evidence')
    parser.add_argument('--evaluate', type=Path)
    parser.add_argument('--c0-dir', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    saved = loop.d2_channels(loop.protocol())
    if args.hashes:
        print(json.dumps({k: dict(sha256=ca.defs_sha256(candidate_defs(k, saved)),
                                  action_index={n: d['action_index'] for n, d in candidate_defs(k, saved).items()},
                                  coordinate_sign={n: d['coordinate_sign'] for n, d in candidate_defs(k, saved).items()})
                          for k in ('H1', 'H1_FLIP')}, indent=1))
        return 0
    if args.arm:
        args.output.mkdir(parents=True, exist_ok=True)
        target = args.output/(f'{args.arm}.json.gz' if args.smoke_steps is None else f'smoke_{args.arm}.json.gz')
        with target.open('xb'):
            pass  # claim the exclusive path before running
        target.unlink()
        result = run_arm(args.arm, steps=args.smoke_steps or c.STEPS)
        digest = c.save(target, result)
        print(json.dumps(dict(arm=args.arm, run_status=result['run_status'], error=result.get('error'), sha256=digest)))
        return 0 if result['run_status'] in ('COMPLETE', 'SMOKE') else 1
    spec = protocol()
    from ..embodiment import live_v3_motor_interface as v3
    c0 = {}
    for s in SEEDS:
        raw = args.c0_dir/f'C0_{s}.json.gz'
        if loop.sha(raw) != spec['sources']['c0'][str(s)]:
            raise SystemExit(f'coxa-admission C0_{s} raw identity mismatch')
        c0[s] = c.load(raw)
    if any(ca.defs_sha256(candidate_defs(k, saved)) != spec['candidates'][k]['sha256'] for k in ('H1', 'H1_FLIP')):
        raise SystemExit('candidate definitions differ from preregistration')
    indices = {n: d['action_index'] for n, d in candidate_defs('H1', saved).items()}
    folder = args.evaluate
    arms = {k: c.load(folder/f'{k}.json.gz') for k in ARMS}
    hashes = {k: loop.sha(folder/f'{k}.json.gz') for k in ARMS}
    bodymap = json.loads((ROOT/'fly-brain-main/public/data/bodymap.json').read_text(encoding='utf-8'))
    report = dict(schema='coxa-push-response-report-v1', protocol_sha256=PROTOCOL_SHA256, arm_sha256=hashes,
                  evaluation=evaluate(arms, c0, spec, tuple(v3.V3_MOTOR), indices, bodymap),
                  interpretation_limits=spec['interpretation_limits'])
    with args.output.open('xb') as stream:
        stream.write((json.dumps(native(report), indent=1, allow_nan=False) + '\n').encode())
    e = report['evaluation']
    print(json.dumps(native({k: e.get(k) for k in ('status', 'checks', 'pulse_resolved', 'labels', 'ratios',
                                                   'deviation_integral_mm_s')}), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
