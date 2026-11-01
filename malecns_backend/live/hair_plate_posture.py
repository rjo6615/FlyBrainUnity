"""Step C: does SNpp45 hair-plate input make coxa MN activity posture-sensitive?

Preregistered in docs/evidence/hair-plate-posture-v1/protocol.json. Four fixed arms
(A_OFF, A_ON, R_OFF, R_ON), one fresh process each. Reuses the live-v3 kernel, the
tactile_boundary input pattern, the V1.2 row-zeroing operation and the Step B encoder.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np

from . import assistance_native as mechanical
from . import contact_context as context
from .tactile_boundary import array_digest, create_session, native, neural_state_digest
from ..embodiment import hair_plate_encoder as hp

ROOT = context.ROOT
PROTOCOL = 'docs/evidence/hair-plate-posture-v1/protocol.json'
PROTOCOL_SHA256 = 'ab7d60b9458fa1c46f25797e3bf2acc5bf68dd3ce466eacc1e2001c5ccf021a7'
SCHEMA = 'hair-plate-posture-arm-v1'
ARMS = ('A_OFF', 'A_ON', 'R_OFF', 'R_ON')
STEPS, TICKS, EVENT_STATE = 20000, 4000, 5005
ENCODER_RESULT = 'docs/evidence/hair-plate-encoder-v1/run/result.json'
WINDOW_MS = (520., 2000.)


def protocol():
    raw = (ROOT/PROTOCOL).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('preregistered protocol changed')
    return json.loads(raw)


def encoder_spec():
    saved = json.loads((ROOT/ENCODER_RESULT).read_text(encoding='utf-8'))
    if saved['status'] != 'ENCODER_READY':
        raise ValueError('Step B encoder not ready')
    return saved['tuning'], {leg: set(saved['populations'][leg]) for leg in hp.LEGS}


class Trial(context.PassiveRecorder):
    """Instance-local input boundary plus the declared R-arm row write; kernel unchanged."""

    def __init__(self, arm):
        super().__init__()
        if arm not in ARMS:
            raise ValueError('unknown arm')
        self.arm, self.release, self.deliver = arm, arm.startswith('R_'), arm.endswith('_ON')
        self.tuning, self.populations = encoder_spec()
        self.neural, self.initial, self.brain, self.event = [], None, None, None
        self.original_step = self.original_trials = None

    def bind(self, sim, physics, obs):
        self.physics = physics
        self.inventory, self.original = mechanical.bind(physics.model, physics.data, sim.fly)
        self.neutral = mechanical.neutral_record(self.original, self.inventory)
        self.frames = hp.BodyFrames(getattr(physics.model, 'ptr', physics.model))
        self.encoder = hp.HairPlateEncoder(self.frames, self.tuning, self.populations)
        super().bind(sim, physics, obs)

    def capture(self, physics, obs, action):
        super().capture(physics, obs, action)
        s = self.samples[-1]
        self.samples[-1] = dict(time_s=s['time_s'], qpos=s['qpos'], qvel=s['qvel'],
                                commanded_joints=s['commanded_joints'], telemetry_forces=s['telemetry_forces'])
        index = len(self.samples) - 1
        if index == EVENT_STATE:
            before = mechanical.model_record(physics.model, physics.data)
            if before != self.original:
                raise RuntimeError('model changed before the declared boundary')
            if self.release:
                mechanical.write_rows(physics.model, self.original, self.inventory, True)
            after = mechanical.model_record(physics.model, physics.data)
            if after != (self.neutral if self.release else self.original):
                raise RuntimeError('undeclared mechanical model change')
            self.event = dict(state_index=index, time_s=float(physics.data.time),
                              operation='ZERO_FULL_SELECTED_ROWS' if self.release else 'OBSERVE_ONLY',
                              after_sha256=after['sha256'], neutral_sha256=self.neutral['sha256'],
                              original_sha256=self.original['sha256'])

    def attach(self, brain, channels, *, sensory_sources):
        if self.brain is not None or self.context is None:
            raise RuntimeError('input adapter must attach once after physical reset')
        self.brain, self.channels = brain, channels
        self.proprio = np.asarray(sorted({int(i) for v in sensory_sources.values() for i in v}), dtype=np.intp)
        self.hair = np.asarray(sorted({int(i) for v in self.populations.values() for i in v}), dtype=np.intp)
        if len(self.proprio) != 392 or len(self.hair) != 52 or np.intersect1d(self.proprio, self.hair).size:
            raise RuntimeError('complete disjoint sensory inventories required')
        self.schedule = np.union1d(self.proprio, self.hair).astype(np.intp)
        for name, channel in channels.items():
            if np.intersect1d(np.asarray(channel['observer'].used), self.schedule).size:
                raise RuntimeError('motor readout overlaps externally driven sensory inventory')
        self.initial = dict(neural_state_sha256=neural_state_digest(brain), external_schedule=self.schedule.tolist(),
                            hair_plate_neurons={leg: sorted(map(int, v)) for leg, v in self.populations.items()},
                            tuning=self.tuning, rng=native(brain.rng.bit_generator.state))
        self.expected_rng = copy.deepcopy(brain.rng.bit_generator.state)
        self.original_withheld = brain.external_drive_withheld_indices.copy()
        self.original_step, self.original_trials = brain.step, brain._external_event_trials
        brain.step, brain._external_event_trials = self.step, self.event_trials
        return self

    def event_trials(self, candidate_available, parameters):
        """Same Bernoulli equation as tactile_boundary; fixed common slots."""
        brain = self.brain
        if context.digest(brain.rng.bit_generator.state) != context.digest(self.expected_rng):
            raise RuntimeError('unexpected CNS RNG consumption')
        uniforms = brain.rng.random(len(self.schedule))
        self.expected_rng = copy.deepcopy(brain.rng.bit_generator.state)
        if np.setdiff1d(np.flatnonzero(brain.external_drive > 0), self.schedule).size:
            raise RuntimeError('unauthorized external input neuron')
        eligible = self.available[self.schedule] & (brain.external_drive[self.schedule] > 0)
        selected = eligible & (uniforms < brain.external_drive[self.schedule] * parameters.dt / 1000.)
        forced = np.zeros(brain.n, dtype=bool)
        forced[self.schedule[selected]] = True
        brain._last_external_rng_indices = self.schedule.astype(np.int32)
        brain._last_external_rng_uniforms = uniforms.copy()
        brain._external_rng_step_draws = len(self.schedule)
        self.current_uniforms = array_digest(uniforms)
        return forced

    def step(self):
        brain = self.brain
        proprio = np.flatnonzero(brain.external_drive > 0)
        if (np.setdiff1d(proprio, self.proprio).size
                or not np.all(brain.external_drive[proprio] == 1000. / brain.config.dt)):
            raise RuntimeError('unexpected kernel proprioceptive input boundary')
        encoded = self.encoder.encode(getattr(self.physics.data, 'ptr', self.physics.data))
        self.encoder.apply(brain, encoded)
        self.available = brain.refractory <= 0
        brain.external_drive_withheld_indices = (np.empty(0, dtype=np.intp) if self.deliver else self.hair.copy())
        fired = self.original_step()  # exactly one canonical neural transition
        delivered = [int(i) for i in brain._last_external_delivered if int(i) in self._hair_set]
        brain.external_drive[self.hair] = 0.
        self.neural.append(dict(time_ms=float(brain.time_ms), uniforms_sha256=self.current_uniforms,
            hair_rate_hz={leg: encoded[leg]['rate_hz'] for leg in hp.LEGS},
            hair_forward={leg: encoded[leg]['forward'] for leg in hp.LEGS},
            hair_delivered=delivered, fired=list(map(int, fired)), motor_readout_verified=False))
        return fired

    @property
    def _hair_set(self):
        if not hasattr(self, '_hair_cache'):
            self._hair_cache = set(map(int, self.hair))
        return self._hair_cache

    def sample(self, brain, *, encoded_sensory=None):
        for channel in self.channels.values():
            observer = channel['observer']
            if not np.array_equal(observer.last_counts, brain.spike_counts[observer.used]):
                raise RuntimeError('actual motor observer readout mismatch')
        self.neural[-1]['motor_readout_verified'] = True
        return {'experimental_input_adapter': self.arm}

    def observe(self, record):
        if 'neural_transition_index' in record and int(record['neural_transition_index']) != len(self.neural):
            raise RuntimeError('neural telemetry boundary mismatch')

    def detach(self):
        if self.brain is not None and self.original_step is not None:
            self.brain.step, self.brain._external_event_trials = self.original_step, self.original_trials
            self.brain.external_drive_withheld_indices = self.original_withheld.copy()


def run_arm(arm, progress=print):
    protocol()
    trial = Trial(arm)
    result = dict(schema=SCHEMA, arm=arm, run_status='ERROR', protocol_sha256=PROTOCOL_SHA256)
    session = None
    try:
        session = create_session(trial)
        progress(f'{arm}: fresh live-v3 CNS/physics initialization', flush=True)
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


# ---- evaluation -------------------------------------------------------------------

def tilt_deg(qpos):
    w, x, y, z = qpos[3:7]
    n = w*w + x*x + y*y + z*z
    return math.degrees(math.acos(max(-1., min(1., 1 - 2*(x*x + y*y)/n))))


def mn_sets(bodymap):
    import re
    name = re.compile(r'^(.+) (T[123]) (left|right)$')
    coxa, post, ant, per_leg = set(), set(), set(), {}
    for e in bodymap['muscles']:
        m = name.match(e['name'])
        if not m:
            continue
        cls = e['actuator'][:-len(f'_{m.group(2)}_{m.group(3)}')]
        idx = {int(i) for i in e['idx']}
        if cls in ('coxa', 'coxa_abduct', 'coxa_twist'):
            coxa |= idx
            per_leg.setdefault(f'{m.group(2)} {m.group(3)}', set()).update(idx)
        if m.group(1) in ('Pleural remotor/abductor MN', 'Sternal posterior rotator MN'):
            post |= idx
        if m.group(1) in ('Tergopleural/Pleural promotor MN', 'Sternal anterior rotator MN'):
            ant |= idx
    return dict(coxa=coxa, posterior=post, anterior=ant), per_leg


def rate(arm, ids):
    lo, hi = WINDOW_MS
    count = sum(1 for t in arm['neural'] if lo < t['time_ms'] <= hi for i in t['fired'] if i in ids)
    return count/len(ids)/((hi - lo)/1000.)


def evaluate(arms, bodymap):
    checks = {}
    checks['I1_complete'] = all(a['run_status'] == 'COMPLETE' and len(a['samples']) == STEPS + 1
                                and len(a['neural']) == TICKS for a in arms.values())
    if not checks['I1_complete']:
        return dict(status='INCONCLUSIVE_INTEGRITY', checks=checks)
    ref = arms['A_OFF']
    checks['I2_common_rng'] = all(a['initial']['external_schedule'] == ref['initial']['external_schedule']
        and [t['uniforms_sha256'] for t in a['neural']] == [t['uniforms_sha256'] for t in ref['neural']]
        for a in arms.values())
    first = {}
    for on in ('OFF', 'ON'):
        a, r = arms[f'A_{on}']['samples'], arms[f'R_{on}']['samples']
        first[on] = next((i for i, (x, y) in enumerate(zip(a, r)) if x['qpos'] != y['qpos']), None)
    checks['I3_prefix'] = all(f is not None and f >= EVENT_STATE + 1 for f in first.values())
    checks['I4_intervention'] = all(
        a['event'] is not None and a['event']['state_index'] == EVENT_STATE
        and a['event']['operation'] == ('ZERO_FULL_SELECTED_ROWS' if k.startswith('R_') else 'OBSERVE_ONLY')
        and a['event']['after_sha256'] == (a['event']['neutral_sha256'] if k.startswith('R_') else a['event']['original_sha256'])
        for k, a in arms.items())
    delivered = {k: sum(len(t['hair_delivered']) for t in a['neural']) for k, a in arms.items()}
    checks['I5_delivery'] = all((delivered[k] > 0) == k.endswith('_ON') for k in arms)
    if not all(checks.values()):
        return dict(status='INCONCLUSIVE_INTEGRITY', checks=checks, delivered=delivered, first_divergence=first)
    sets, per_leg = mn_sets(bodymap)
    rates = {k: {name: rate(a, ids) for name, ids in sets.items()} for k, a in arms.items()}
    leg_rates = {k: {leg: rate(a, ids) for leg, ids in per_leg.items()} for k, a in arms.items()}
    d_off = abs(rates['A_OFF']['coxa'] - rates['R_OFF']['coxa'])
    d_on = abs(rates['A_ON']['coxa'] - rates['R_ON']['coxa'])
    q1 = 'POSTURE_SENSITIVE' if d_on >= 2*d_off and d_on >= .5 else 'NOT_POSTURE_SENSITIVE'
    d_post = rates['A_ON']['posterior'] - rates['A_OFF']['posterior']
    d_ant = rates['A_ON']['anterior'] - rates['A_OFF']['anterior']
    q2 = 'REFLEX_DIRECTION_CONSISTENT' if d_post > 0 and d_post > d_ant else 'NOT_CONSISTENT'
    posture = {}
    for k, a in arms.items():
        tilts = [tilt_deg(s['qpos']) for s in a['samples'][5201:]]
        posture[k] = dict(tilt_mean_deg=float(np.mean(tilts)), tilt_peak_deg=float(np.max(tilts)),
                          rollover_samples=int(sum(t > 90 for t in tilts)))
    on_off = next((i for i, (x, y) in enumerate(zip(arms['A_OFF']['samples'], arms['A_ON']['samples']))
                   if x['qpos'] != y['qpos']), None)
    return dict(status='INTEGRITY_ACCEPTED', checks=checks, delivered=delivered, first_divergence_A_vs_R=first,
                first_physical_divergence_A_OFF_vs_A_ON=on_off, rates_hz=rates, coxa_rates_per_leg_hz=leg_rates,
                Q1=dict(label=q1, d_off_hz=d_off, d_on_hz=d_on), Q2=dict(label=q2, d_posterior_hz=d_post, d_anterior_hz=d_ant),
                posture=posture, R_ON_minus_R_OFF_tilt_mean_deg=posture['R_ON']['tilt_mean_deg'] - posture['R_OFF']['tilt_mean_deg'])


def save(path, payload):
    data = gzip.compress(json.dumps(native(payload), allow_nan=False, separators=(',', ':')).encode(), mtime=0)
    with Path(path).open('xb') as stream:
        stream.write(data)
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(gzip.decompress(Path(path).read_bytes()))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arm', choices=ARMS)
    parser.add_argument('--evaluate', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.arm:
        args.output.mkdir(parents=True, exist_ok=True)
        target = args.output/f'{args.arm}.json.gz'
        with target.open('xb'):
            pass  # claim the exclusive path before running
        target.unlink()
        result = run_arm(args.arm)
        digest = save(target, result)
        print(json.dumps(dict(arm=args.arm, run_status=result['run_status'], error=result.get('error'), sha256=digest)))
        return 0 if result['run_status'] == 'COMPLETE' else 1
    folder = args.evaluate
    arms = {k: load(folder/f'{k}.json.gz') for k in ARMS}
    hashes = {k: hashlib.sha256((folder/f'{k}.json.gz').read_bytes()).hexdigest() for k in ARMS}
    bodymap = json.loads((ROOT/'fly-brain-main/public/data/bodymap.json').read_text(encoding='utf-8'))
    report = dict(schema='hair-plate-posture-report-v1', protocol_sha256=PROTOCOL_SHA256, arm_sha256=hashes,
                  evaluation=evaluate(arms, bodymap))
    with args.output.open('xb') as stream:
        stream.write((json.dumps(native(report), indent=1, allow_nan=False) + '\n').encode())
    e = report['evaluation']
    print(json.dumps({k: e.get(k) for k in ('status', 'checks', 'Q1', 'Q2', 'posture')}, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
