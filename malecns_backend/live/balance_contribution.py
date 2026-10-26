"""Prospective balance V1 runner; ordinary live defaults remain unchanged.

Uses the frozen ScientificSession kernel. No tactile Trial, second integrator,
replacement encoder, or final-target gate is installed.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
import copy
from dataclasses import asdict
import gc
import gzip
import hashlib
import importlib.metadata as packages
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

import numpy as np

from . import contact_context as context
from . import tactile_recovery_metrics as metrics
from .protocol import JOINT_NAMES
from .tactile_boundary import array_digest, native, neural_state_digest
from ..embodiment.tactile_motor_matched_control import MatchedControlPipeline
from ..embodiment.motor import MotorSafety
from ..embodiment.m9b_external_perturbation import force_at_transition

ROOT = context.ROOT
DESIGN = 'docs/evidence/balance-contribution-v1/protocol.json'
SCHEMA = 'balance-contribution-execution-v1'
CONDITIONS = ('NC', 'WC', 'NP', 'WP')
STEPS, TICKS, STRIDE = 20000, 4000, 5
WITHDRAW_TICK = 1001


def design():
    return json.loads((ROOT / DESIGN).read_text(encoding='utf-8'))


def source_hashes():
    d = design()
    paths = (*d['source_code_sha256'], DESIGN, d['design_document']['path'],
             'malecns_backend/live/balance_contribution.py')
    return {p: hashlib.sha256((ROOT / p).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
            for p in paths}


def validate_design():
    d = design()
    hashes = source_hashes()
    if any(hashes[p] != h for p, h in d['source_code_sha256'].items()):
        raise ValueError('original design code fingerprint mismatch')
    doc = d['design_document']
    if hashes[doc['path']] != doc['canonical_lf_sha256']:
        raise ValueError('original design document fingerprint mismatch')
    from ..embodiment.live_v3_motor_interface import V3_MOTOR
    if ([c['id'] for c in d['conditions']] != list(CONDITIONS)
            or [(r['name'], r['action_index']) for r in d['motors']] !=
            [(n, JOINT_NAMES.index(n)) for n in V3_MOTOR]
            or len(V3_MOTOR) != 20 or len(set(V3_MOTOR)) != 20
            or (d['physics_transitions_per_arm'], d['neural_updates_per_arm'], d['seed']) != (STEPS, TICKS, 1)):
        raise ValueError('fixed design or motor inventory mismatch')
    return d


def force(condition, outgoing):
    if condition not in CONDITIONS or type(outgoing) is not int or not 0 <= outgoing < STEPS:
        raise ValueError('declared arm and outgoing transition required')
    return force_at_transition('A_P' if condition.endswith('P') else 'A_C', outgoing)


def gated(values, condition, tick, admitted):
    if (condition not in CONDITIONS or type(tick) is not int or not 1 <= tick <= TICKS
            or tuple(values) != tuple(admitted) or len(admitted) != 20
            or not np.isfinite(list(values.values())).all()):
        raise ValueError('invalid decoder boundary')
    withdraw = condition.startswith('W') and tick >= WITHDRAW_TICK
    return {n: 0. if withdraw else float(values[n]) for n in admitted}


def command_is_applied(tick):
    if type(tick) is not int or not 1 <= tick <= TICKS:
        raise ValueError('neural tick outside fixed budget')
    return tick * STRIDE < STEPS


def environment():
    expected = design()['expected_environment']
    observed = {'python': '.'.join(platform.python_version().split('.')[:2])}
    errors = {}
    for p in ('flygym', 'mujoco', 'dm_control', 'numpy'):
        try:
            observed[p] = packages.version(p)
        except packages.PackageNotFoundError:
            observed[p] = None
    for p, v in observed.items():
        if v != expected[p]:
            errors[p] = dict(expected=expected[p], observed=v)
    return dict(verified=not errors, observed=observed, mismatches=errors)


def static_authority():
    """Existing construction-free authority; never old._inventory/audit.build."""
    from ..embodiment import lf_force_static_reference as static
    from ..embodiment import _windows_m7_spontaneous_locomotion_adapter as old
    from ..embodiment import m7d_corrected_spontaneous as m7d
    from ..embodiment import live_v2_motor_interface as v2, live_v3_motor_interface as v3
    from ..embodiment.proprioceptive_activation import verify_provenance
    from .matched_tactile_delivery import prerequisites as contact_prerequisites
    result = static.load()
    if not result['original_raw_freezes_satisfied']:
        raise ValueError('original motor/sign/registration raw locks failed')
    verify_provenance()
    m7d.verify_b4()
    m7d.verify_m7()
    contact_prerequisites()
    protocol = old.build_live_protocol()
    protocol, _, table = v2.derive_v2(protocol, [], protocol['actuator_admission_table'])
    protocol, _, table = v3.derive_v3(protocol, [], table)
    if table != result['static_admission_table']:
        raise ValueError('static admission authorities disagree')
    return protocol, table


def preflight():
    """No native imports/constructors or CNS initialization, including failures."""
    result = dict(environment=environment(), scientific_transitions=0, native_constructions=0,
                  cns_initializations=0, checks={}, errors={})
    for label, check in (('design', validate_design), ('original_authorities', static_authority),
                         ('original_neural_data', data_identities)):
        try:
            check()
            result['checks'][label] = True
        except Exception as exc:
            result['checks'][label] = False
            result['errors'][label] = f'{type(exc).__name__}: {exc}'
    result['verified'] = result['environment']['verified'] and all(result['checks'].values())
    return result


@contextmanager
def initialization_operations():
    """Count observed Python/C API entries, not invisible native internals.

    Covers both mujoco and dm_control namespaces. Each event is labeled with
    its exact module/name. It also captures constructor/reset/step activity;
    no zero-clock inference or extra inventory model is used.
    """
    counts = Counter()
    previous = sys.getprofile()
    if previous is not None:
        raise RuntimeError('cannot replace an existing profiler')
    def profile(frame, event, arg):
        if event == 'call':
            module, name = frame.f_globals.get('__name__', ''), frame.f_code.co_name
        elif event == 'c_call':
            module, name = getattr(arg, '__module__', '') or '', getattr(arg, '__name__', '')
        else:
            return
        if module.startswith(('flygym', 'dm_control', 'mujoco')) and (
                name.startswith('mj_') or name in ('__init__', 'reset', 'forward', 'step', 'reset_context')):
            counts[f'{event}:{module}.{name}'] += 1
        if ((module == 'malecns_backend.loader' and name == 'load_malecns')
                or (module == 'malecns_backend.neural' and name in ('__init__', 'reset'))):
            counts[f'{event}:{module}.{name}'] += 1
    sys.setprofile(profile)
    try:
        yield counts
    finally:
        sys.setprofile(previous)


class Trial(context.PassiveRecorder):
    def __init__(self, condition):
        super().__init__()
        if condition not in CONDITIONS:
            raise ValueError('unknown condition')
        self.condition = condition
        self.neural = []
        self.initial = None
        self.brain = None
        self.tick = 0
        self.session = None

    def bind(self, sim, physics, obs):
        from ..embodiment.lf_native_isolation import inventory, validate_inventory
        self.physics = physics
        self.inventory = inventory(physics.model, sim.fly)
        from ..embodiment.m8_contact_kinematics import namespace_component
        ids = [i for i, n in enumerate(self.inventory['names']['body']) if namespace_component(n) == 'Thorax']
        if len(ids) != 1:
            raise ValueError('unique exact Thorax required')
        self.thorax = ids[0]
        free = np.flatnonzero(np.asarray(physics.model.jnt_type) == 0)
        if (len(free) != 1 or int(physics.model.jnt_qposadr[free[0]]) != 0
                or int(physics.model.jnt_dofadr[free[0]]) != 0):
            raise ValueError('exact free-root addresses required for existing recovery observer')
        self.root = dict(joint_id=int(free[0]), qpos_address=0, dof_address=0)
        # Populate the kernel's caller-owned record list from THIS actual model.
        self.records.extend(dict(index=r['action_index'], name=r['coordinate'], mujoco_metadata=dict(r))
                            for r in self.inventory['rows'])
        super().bind(sim, physics, obs)
        self.inventory.update(nq=int(physics.model.nq), nv=int(physics.model.nv))
        validate_inventory(self.inventory, self.context['physics_model_identity'])
        self.context.update(native_inventory=self.inventory, free_root=self.root, thorax_body_id=self.thorax)

    def capture(self, physics, obs, action):
        super().capture(physics, obs, action)
        self.samples[-1].update(ctrl=np.asarray(physics.data.ctrl).tolist(),
            xfrc_applied=np.asarray(physics.data.xfrc_applied).tolist(),
            qfrc_applied=np.asarray(physics.data.qfrc_applied).tolist())

    def attach(self, brain, channels, *, sensory_sources):
        if self.brain is not None:
            raise RuntimeError('adapter attached twice')
        self.brain, self.channels = brain, channels
        schedule = sorted({int(i) for indices in sensory_sources.values() for i in indices})
        brain.configure_external_rng_schedule(schedule)
        motor = {}
        for name, ch in channels.items():
            indices = list(map(int, ch['observer'].used))
            if set(indices).intersection(schedule):
                raise ValueError('motor/sensory overlap')
            motor[name] = dict(action_index=ch['index'], dense_indices=indices,
                body_ids=[int(brain.data.body_ids[i]) for i in indices], populations=native(ch['populations']),
                positive=list(ch['positive']), negative=list(ch['negative']), sign=ch['sign'],
                mode=ch['decoder_mode'], safety=asdict(ch['pipeline'].safety), bound=ch['bound'])
        ids = list(map(int, brain.data.body_ids))
        if (len(set(ids)) != brain.n or any(brain.data.body_id_to_index[b] != i for i, b in enumerate(ids))):
            raise ValueError('neural body-ID/dense-index order mismatch')
        self.initial = dict(neural_config=asdict(brain.config),
            neural_state_sha256=neural_state_digest(brain),
            rng_state=native(brain.rng.bit_generator.state),
            neural_model_sha256=array_digest(brain.weights, brain.pre_sign, brain.indices, brain.indptr),
            graph_sha256=array_digest(brain.data.row_ptr, brain.data.target_indices, brain.data.synapse_counts),
            delay_steps=int(brain.delay_steps), body_id_order_sha256=context.digest(ids),
            external_schedule=schedule, external_schedule_body_ids=[ids[i] for i in schedule], motors=motor,
            initial_observers={n: dict(filtered=ch['observer'].filtered_hz.tolist(),
                counts=ch['observer'].last_counts.tolist(), previous=ch['pipeline'].previous_physical_target)
                for n, ch in channels.items()})
        self.original_step = brain.step
        brain.step = self.step
        return self

    def step(self):
        b = self.brain
        self.tick += 1
        before = neural_state_digest(b)
        offered = np.flatnonzero(b.external_drive > 0).tolist()
        if not set(offered).issubset(self.initial['external_schedule']) or not np.all(
                b.external_drive[offered] == 1000. / b.config.dt):
            raise ValueError('unexpected external drive')
        fired = self.original_step()
        self.neural.append(dict(tick=self.tick, time_ms=float(b.time_ms), pre_state_sha256=before,
            post_state_sha256=neural_state_digest(b), offered=offered,
            eligible=b._last_external_candidates.astype(int).tolist(),
            delivered=b._last_external_delivered.astype(int).tolist(), fired=list(map(int, fired)),
            rng_state=native(b.rng.bit_generator.state), uniforms_sha256=array_digest(b._last_external_rng_uniforms),
            rng_indices=b._last_external_rng_indices.astype(int).tolist(), draws=b._external_rng_step_draws))
        return fired

    def gate(self, values, condition, admitted):
        result = gated(values, condition, self.tick, admitted)
        self.neural[-1]['raw'] = dict(values)
        self.neural[-1]['gated'] = result
        self.neural[-1]['previous'] = {n: ch['pipeline'].previous_physical_target for n, ch in self.channels.items()}
        return result

    def sample(self, brain, *, encoded_sensory=None):
        for ch in self.channels.values():
            observer = ch['observer']
            if not np.array_equal(observer.last_counts, brain.spike_counts[observer.used]):
                raise ValueError('motor observer readout mismatch')
        self.neural[-1]['readout_verified'] = True
        return {'motor_readout_verified': True}

    def observe(self, record):
        if 'neural_transition_index' not in record:
            return
        row = self.neural[-1]
        if int(record['neural_transition_index']) != self.tick:
            raise ValueError('neural telemetry clock mismatch')
        row['telemetry'] = native(record)
        row['pipeline'] = {}
        for n, ch in self.channels.items():
            pipeline = MatchedControlPipeline(True, ch['pipeline'].safety)
            pipeline.previous_physical_target = row['previous'][n]
            # Baseline is the fixed initial joint command, not the current target.
            baseline = self.baseline[ch['index']]
            result = pipeline.update(baseline, row['gated'][n], .0005)
            if result.actuator_command != record['commanded_joint_targets'][ch['index']]:
                raise ValueError('online safety replay mismatch')
            row['pipeline'][n] = asdict(result)
            pipeline.previous_physical_target = row['previous'][n]
            counterfactual = pipeline.update(baseline, row['raw'][n], .0005)
            row['pipeline'][n]['enabled_counterfactual_target'] = counterfactual.actuator_command
        row['applied'] = command_is_applied(self.tick)

    def state_boundary(self):
        """Read the suspended unchanged kernel; never write its locals/state."""
        state = self.session._state
        frame = self.session._kernel.gi_frame.f_locals
        if state['physics_transition'] == 0:
            self.baseline = list(map(float, frame['baseline_commands']))
            self.initial['baseline'] = self.baseline
        if state['neural_update']:
            self.neural[-1]['proprio_rng_state'] = {l: native(r.bit_generator.state) for l, r in frame['rngs'].items()}
            self.neural[-1]['encoder_state'] = {l: encoder_state(e) for l, e in frame['encoders'].items()}
        if state['physics_transition'] == 0:
            self.initial['encoder_state'] = {l: encoder_state(e) for l, e in frame['encoders'].items()}
            self.initial['proprio_rng_state'] = {l: native(r.bit_generator.state) for l, r in frame['rngs'].items()}
            self.initial['data_artifacts'] = data_identities()
        self.samples[-1]['proposed_commands'] = native(state['commands'])

    def detach(self):
        if self.brain is not None and hasattr(self, 'original_step'):
            self.brain.step = self.original_step


def encoder_state(encoder):
    # The existing encoder is stateless; record its exact immutable pathway.
    p = encoder.pathway
    if set(vars(encoder)) != {'pathway'}:
        raise ValueError('unexpected encoder state requires explicit review')
    return dict(actuator=p.actuator_name, body_ids=list(map(int, p.sensor.body_ids)),
                dense_indices=list(map(int, p.sensor.dense_indices)))


def create_session(trial, protocol, table):
    from ..embodiment import _windows_m7d_corrected_spontaneous_adapter as adapter
    from ..embodiment import _windows_m8_live_condition as kernel
    from ..embodiment import live_v3_motor_interface as v3
    trial.records = []
    def runtime(flygym, interfaces):
        sim, physics, obs, tid, sid = adapter._runtime(flygym, interfaces)
        try:
            trial.bind(sim, physics, obs)
        except BaseException:
            sim.close()
            raise
        return context.ObservedSimulation(sim, physics, trial), physics, obs, tid, sid
    # by_record is constructed before runtime_factory is invoked. Use the
    # frozen M5A records as identity leads; the native inventory
    # below verifies every ID/address before any kernel channel is constructed.
    from ..embodiment.full_leg_interface import DEFAULT_OUTPUT
    saved = json.loads(DEFAULT_OUTPUT.read_text(encoding='utf-8'))
    records = [dict(name=r['actuator_name'], index=r['actuator_index'], mujoco_metadata=r['mujoco_metadata'])
               for r in saved['actuator_records']]
    if len(records) != 42:
        raise ValueError('complete M5A record inventory required')
    original_runtime = runtime
    def verified_runtime(flygym, interfaces):
        result = original_runtime(flygym, interfaces)
        try:
            for saved, actual in zip(records, trial.records):
                if saved['name'] != actual['name'] or saved['index'] != actual['index'] or any(
                        saved['mujoco_metadata'][k] != actual['mujoco_metadata'][k]
                        for k in ('actuator_id', 'joint_id', 'qpos_range', 'dof_range', 'actuator_name', 'joint_name')):
                    raise ValueError('recorded/native motor ID or address disagreement')
        except BaseException:
            result[0].close()
            raise
        return result
    session = kernel.create_scientific_session(protocol=protocol, condition=trial.condition,
        condition_number=CONDITIONS.index(trial.condition) + 1, condition_names=CONDITIONS,
        progress=lambda *_: '', cached_admission_assertion=v3.assert_v3_physical_admission,
        cached_records=records, cached_table=table, contribution_gate=trial.gate,
        runtime_factory=verified_runtime, proprioception_only=True, fixed_initial_baseline=True,
        m8_extended_telemetry=False, continuous=True, external_force_by_transition=force,
        motor_channel_names=v3.V3_MOTOR, supplemental_motor_channels=v3.SUPPLEMENTAL_MOTOR_CHANNELS,
        telemetry_observer=trial.observe, motor_state_probe_factory=trial.attach)
    trial.session = session
    return session


def run_arm(condition, protocol, table, progress=print):
    trial = Trial(condition)
    result = dict(condition=condition, run_status='ERROR', samples=trial.samples, neural=trial.neural)
    session = None
    operations = Counter()
    try:
        session = create_session(trial, protocol, table)
        progress(f'{condition}: fresh physical/CNS initialization', flush=True)
        with initialization_operations() as operations:
            initial = session.initialize()
        if initial.time_ms != 0:
            raise ValueError('nonzero initial time')
        trial.state_boundary()
        last = time.monotonic()
        for i in range(1, STEPS + 1):
            state = session.step(lightweight=True)
            if state.physics_transitions != i or state.neural_transitions != i // STRIDE:
                raise ValueError('authoritative transition counters mismatch')
            trial.state_boundary()
            if time.monotonic() - last >= 15:
                progress(f'{condition}: {i}/{STEPS} physics transitions', flush=True)
                last = time.monotonic()
        result['run_status'] = 'COMPLETE'
    except (Exception, KeyboardInterrupt) as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
        if trial.brain is not None:
            result['neural_failure_snapshot'] = {k: native(getattr(trial.brain, k)) for k in (
                'v', 'g_exc', 'g_inh', 'refractory', 'spike_counts', 'external_drive', 'time_ms')}
    finally:
        if session is not None:
            try:
                session.close()
            except Exception as exc:
                result.update(run_status='ERROR', close_error=f'{type(exc).__name__}: {exc}')
        trial.detach()
        result.update(context=trial.context, initial=trial.initial,
            initialization_operations=dict(operations), initialization_accounting_scope='observed Python/C API entries; native internal calls unobservable')
    return result


def git(*args):
    return subprocess.check_output(['git', '-c', f'safe.directory={ROOT.as_posix()}', *args], cwd=ROOT)


def data_identities():
    """Require original committed bytes/LFS OIDs, not freshly accepted hashes."""
    from ..loader import ARTIFACTS, DEFAULT_DATA_DIR
    paths = [DEFAULT_DATA_DIR / p for p in (*ARTIFACTS, 'brain_params.json')]
    records = {}
    for p in paths:
        relative = p.relative_to(ROOT).as_posix()
        committed = git('show', f'{design()["baseline"]}:{relative}')
        raw = p.read_bytes()
        actual = hashlib.sha256(raw).hexdigest()
        if committed.startswith(b'version https://git-lfs.github.com/spec/v1\n'):
            fields = dict(line.split(' ', 1) for line in committed.decode().splitlines())
            expected = fields['oid'].removeprefix('sha256:')
            good = actual == expected and len(raw) == int(fields['size'])
        else:
            expected = hashlib.sha256(committed).hexdigest()
            # brain_params is an existing text source, not a raw binary lock.
            # Preserve/report both raw bytes and original canonical source hash.
            good = (raw.replace(b'\r\n', b'\n') == committed.replace(b'\r\n', b'\n')
                    if p.name == 'brain_params.json' else raw == committed)
        if not good:
            raise ValueError('original committed data identity mismatch: ' + relative)
        records[relative] = dict(sha256=actual, original_committed_sha256=expected, bytes=len(raw),
            comparison='canonical_LF_text' if p.name == 'brain_params.json' else 'raw_bytes')
    return records


def audit_commands(arm):
    """Replay the unchanged safety path, including unapplied terminal update."""
    initial, rows, samples = arm['initial'], arm['neural'], arm['samples']
    motors, baseline = initial['motors'], initial['baseline']
    if (len(baseline) != 42 or list(motors) != [r['name'] for r in design()['motors']]
            or {m['action_index'] for m in motors.values()} != {r['action_index'] for r in design()['motors']}):
        raise ValueError('exact20 motor inventory required')
    pipes = {n: MatchedControlPipeline(True, MotorSafety(**m['safety'])) for n, m in motors.items()}
    commands = list(baseline)
    proposals = {0: commands.copy()}
    first_raw = first_safe = first_outgoing = None
    for tick, row in enumerate(rows, 1):
        if row['tick'] != tick or row['applied'] != command_is_applied(tick):
            raise ValueError('terminal/update ownership mismatch')
        expected = gated(row['raw'], arm['condition'], tick, tuple(motors))
        if row['gated'] != expected:
            raise ValueError('pre-safety withdrawal mismatch')
        changed_raw = changed_safe = False
        for n, pipe in pipes.items():
            index = motors[n]['action_index']
            previous = pipe.previous_physical_target
            if (row['previous'][n] != previous or pipe.safety.max_velocity_rad_s != 4.
                    or not 0 <= pipe.safety.max_offset_rad <= .25):
                raise ValueError('safety history or inherited slew limit mismatch')
            counter = MatchedControlPipeline(True, pipe.safety)
            counter.previous_physical_target = previous
            enabled = counter.update(baseline[index], row['raw'][n], .0005)
            result = pipe.update(baseline[index], expected[n], .0005)
            recorded = dict(row['pipeline'][n])
            cf = recorded.pop('enabled_counterfactual_target')
            if asdict(result) != recorded or cf != enabled.actuator_command:
                raise ValueError('offline pipeline replay mismatch')
            changed_raw |= row['raw'][n] != expected[n]
            changed_safe |= enabled.actuator_command != result.actuator_command
            commands[index] = result.actuator_command
            if (arm['condition'].startswith('W') and tick >= 1126
                    and abs(commands[index] - baseline[index]) > 1e-12):
                raise ValueError('withdrawal baseline return bound exceeded')
        if (row['telemetry']['commanded_joint_targets'] != commands
                or row['telemetry'].get('raw_signed_contribution_rad') != row['raw']
                or row['telemetry'].get('final_contribution_rad') != expected):
            raise ValueError('42-command proposal/isolation mismatch')
        proposals[tick * STRIDE] = commands.copy()
        if changed_raw and first_raw is None:
            first_raw = tick
        if changed_safe and first_safe is None:
            first_safe = tick
        if changed_safe and command_is_applied(tick) and first_outgoing is None:
            first_outgoing = tick * STRIDE
    inventory = arm['context']['native_inventory']
    for i, sample in enumerate(samples):
        if sample['proposed_commands'] != proposals[(i // STRIDE) * STRIDE]:
            raise ValueError('proposal persistence mismatch')
        if i:
            applied = proposals[((i - 1) // STRIDE) * STRIDE]
            if sample['commanded_joints'] != applied or sample['adhesion'] != [0.] * 6:
                raise ValueError('actual outgoing command or adhesion mismatch')
            ctrl = np.zeros(len(sample['ctrl']))
            for m in inventory['rows']:
                ctrl[m['actuator_id']] = applied[m['action_index']]
            if ctrl.tolist() != sample['ctrl']:
                raise ValueError('actual full native ctrl mismatch')
    return dict(first_raw_gate_difference_tick=first_raw, first_safe_counterfactual_difference_tick=first_safe,
        first_exposed_counterfactual_outgoing_transition=first_outgoing,
        terminal_proposal_retained=True, terminal_proposal_applied=False)


def audit_arm(arm):
    if arm['run_status'] != 'COMPLETE' or len(arm['samples']) != STEPS + 1 or len(arm['neural']) != TICKS:
        raise ValueError('incomplete fixed budget')
    samples, neural, ctx, initial = arm['samples'], arm['neural'], arm['context'], arm['initial']
    context.validate_identity(ctx['identity'])
    if (ctx['adhesion_enabled'] or not ctx['inherited_surface_unchanged']
            or ctx['configuration']['timestep'] != .0001 or not arm['initialization_operations']
            or ctx['configuration_sha256'] != context.digest(ctx['configuration'])):
        raise ValueError('support context or initialization accounting missing')
    schedule = initial['external_schedule']
    if len(schedule) != 392 or schedule != sorted(set(schedule)):
        raise ValueError('392 unique common slots required')
    from .tactile_recovery import support_counts
    ground_counts = support_counts(arm)
    calibration_counts, unexpected, correspondence = [], [], []
    ground = ctx['identity']['ground_geom_ids']
    from ..embodiment.m8_contact_kinematics import namespace_component
    gid = next(g for g in ground if namespace_component(ctx['identity']['geom_names'][g]) == 'ground')
    sid = next(g for g in ground if g != gid)
    for i, s in enumerate(samples):
        inv = ctx['native_inventory']
        if (np.asarray(s['qpos']).shape != (inv['nq'],)
                or np.asarray(s['qvel']).shape != (inv['nv'],)
                or np.asarray(s['ctrl']).shape != (48,)
                or np.asarray(s['xfrc_applied']).shape != (len(ctx['identity']['body_names']), 6)
                or np.asarray(s['qfrc_applied']).shape != (inv['nv'],)):
            raise ValueError('incomplete native state/control/force array shape')
        if not np.isfinite(np.asarray(s['qpos'] + s['qvel'] + s['ctrl'], dtype=float)).all():
            raise ValueError('nonfinite physical evidence')
        if (abs(s['time_s'] - i * .0001) > 1e-10 or s['configuration_sha256'] != ctx['configuration_sha256']
                or s['observer_state_before_sha256'] != s['observer_state_after_sha256']):
            raise ValueError('physical clock/configuration/observer mismatch')
        xfrc = np.zeros(np.asarray(s['xfrc_applied']).shape)
        if i:
            xfrc[ctx['thorax_body_id'], :3] = force(arm['condition'], i - 1)
        if (not np.array_equal(s['xfrc_applied'], xfrc) or np.any(s['qfrc_applied'])
                or s['external_applied_max'] != float(np.max(np.abs(xfrc)))
                or s['generalized_applied_max'] != 0):
            raise ValueError('complete declared force arrays mismatch')
        summary = context.summarize_sample(s, ctx['identity'])
        if any(not v['reconstruction_matches'] or not v['telemetry_matches']
               for v in summary.values()):
            raise ValueError('force/contact reconstruction mismatch')
        calibration_counts.append(sum(np.linalg.norm(v['reconstructed_by_surface'][str(sid)]) > context.THRESHOLD
                                      for v in summary.values()))
        unexpected.append(sum(v['unselected_pairs'] for v in summary.values()))
        correspondence.append(sum(not v['correspondence'] for v in summary.values()))
    cns_rng = np.random.Generator(np.random.PCG64())
    cns_rng.bit_generator.state = copy.deepcopy(initial['rng_state'])
    from ..embodiment.proprioceptive_activation import sample_candidates
    local_rngs = {l: np.random.Generator(np.random.PCG64()) for l in context.LEGS}
    for l, r in local_rngs.items():
        r.bit_generator.state = copy.deepcopy(initial['proprio_rng_state'][l])
    for t, n in enumerate(neural, 1):
        if (abs(n['time_ms'] - t * .5) > 1e-8 or n['rng_indices'] != schedule or n['draws'] != 392
                or not n['readout_verified'] or set(n['offered']) - set(schedule)
                or set(n['delivered']) - set(n['offered']) or set(n['eligible']) - set(n['offered'])
                or n['telemetry']['scheduled_sensory_candidate_events'] != n['offered']
                or n['telemetry']['delivered_external_sensory_events'] != n['delivered']):
            raise ValueError('neural clock/RNG/input/readout boundary mismatch')
        uniforms = cns_rng.random(392)
        if array_digest(uniforms) != n['uniforms_sha256'] or cns_rng.bit_generator.state != n['rng_state']:
            raise ValueError('independent CNS common-slot replay mismatch')
        offered = []
        for l, r in local_rngs.items():
            rates = n['telemetry']['encoded_sensory_rates'][l]
            indices = initial['encoder_state'][l]['dense_indices']
            if len(rates) != len(indices):
                raise ValueError('per-leg encoded sensory inventory mismatch')
            offered.extend(indices[int(i)] for i in sample_candidates(rates, r))
            if r.bit_generator.state != n['proprio_rng_state'][l]:
                raise ValueError('independent per-leg candidate RNG replay mismatch')
        if sorted(set(offered)) != n['offered']:
            raise ValueError('independent candidate event replay mismatch')
    return dict(commands=audit_commands(arm), ground_support_counts=ground_counts,
                calibration_support_counts=calibration_counts, unexpected_distal_contact_counts=unexpected,
                contact_correspondence_mismatch_counts=correspondence)


def equal_prefix(a, b, stop, *, proposed=True):
    for i in range(stop + 1):
        x, y = a['samples'][i], b['samples'][i]
        if proposed:
            if x != y:
                raise ValueError(f'physical prefix mismatch at state {i}')
        elif {k: v for k, v in x.items() if k != 'proposed_commands'} != {
                k: v for k, v in y.items() if k != 'proposed_commands'}:
            raise ValueError(f'applied physical prefix mismatch at state {i}')


def behavior(arms, audits):
    traces = {c: metrics.trace(a, audits[c]['ground_support_counts']) for c, a in arms.items()}
    responses = {p: metrics.response(traces[p], traces[c]) for p, c in (('NP', 'NC'), ('WP', 'WC'))}
    posture, ups = {}, {}
    for c, tr in traces.items():
        q = tr['quaternion']
        ups[c] = metrics.angular_velocity_world(q, np.tile([0., 0., 1.], (len(q), 1)))
        tilt = np.degrees(np.arccos(np.clip(tr['up_z'], -1., 1.)))
        post = slice(5201, None)
        posture[c] = dict(world_tilt_peak_deg=float(np.max(tilt[post])),
            world_tilt_mean_deg=float(np.mean(tilt[post])),
            world_tilt_rms_deg=float(np.sqrt(np.mean(tilt[post] ** 2))),
            rollover_samples=int(np.count_nonzero(tr['up_z'][post] <= 0)),
            below_minimum_up_samples=int(np.count_nonzero(tr['up_z'][post] <= .5)),
            low_height_samples=int(np.count_nonzero(tr['position'][post, 2] <= tr['position'][0, 2] * .5)),
            below_three_ground_support_samples=int(np.count_nonzero(tr['supports'][post] < 3)))
    peak = posture['NP']['world_tilt_peak_deg'] - posture['WP']['world_tilt_peak_deg']
    mean = posture['NP']['world_tilt_mean_deg'] - posture['WP']['world_tilt_mean_deg']
    label = ('LOWER_PUSHED_WORLD_TILT_WITH_NEURAL_INPUT' if peak < -.25 and mean < -.25 else
             'HIGHER_PUSHED_WORLD_TILT_WITH_NEURAL_INPUT' if peak > .25 and mean > .25 else 'MIXED_OR_UNRESOLVED')
    def contrast(values):
        return (values['NP'] - values['NC']) - (values['WP'] - values['WC'])
    limits = ['ONE_SEED_ASSISTED_POSITION_CONTROL_NOT_INDEPENDENT_BALANCE_OR_GAIT']
    for c in CONDITIONS:
        if any(audits[c]['calibration_support_counts']):
            limits.append(c + '_CALIBRATION_SURFACE_CONTACT')
        if any(audits[c]['unexpected_distal_contact_counts']):
            limits.append(c + '_UNEXPECTED_DISTAL_CONTACT')
        if any(audits[c]['contact_correspondence_mismatch_counts']):
            limits.append(c + '_CONTACT_FORCE_CORRESPONDENCE_LIMIT')
    for c in ('NP', 'WP'):
        for field in ('baseline_qualified', 'resolved_perturbation', 'relative_band_exited'):
            if not responses[c][field]:
                limits.append(c + '_' + field.upper() + '_FALSE')
    for c in ('WC', 'WP'):
        if audits[c]['commands']['first_exposed_counterfactual_outgoing_transition'] is None:
            limits.append(c + '_NO_SAFE_COMMAND_WITHDRAWAL_EXPOSURE')
    # Full signed vectors are retained, not replaced by norms or a composite score.
    return dict(primary_label=label, posture=posture, responses=responses,
        pushed_peak_NP_minus_WP_deg=peak, pushed_mean_NP_minus_WP_deg=mean,
        factorial_root_vector=contrast({c: tr['position'] for c, tr in traces.items()}).tolist(),
        factorial_world_up_vector=contrast(ups).tolist(), interpretation_limits=limits,
        independent_balance_proven=False, gait_proven=False)


def evaluate(report):
    checks, audits = {}, {}
    try:
        checks['fixed_design'] = report['design'] == design()
        checks['prerequisites'] = report['preflight']['verified'] is True
        checks['unchanged_sources'] = (bool(report['sources_before'])
            and report['sources_before'] == report['sources_after'] == source_hashes())
        arms = report['arms']
        checks['four_fresh_arms_order'] = list(arms) == list(CONDITIONS)
        for c in CONDITIONS:
            if arms[c]['condition'] != c:
                raise ValueError('arm identity mismatch')
            audits[c] = audit_arm(arms[c])
        checks['per_arm_integrity'] = True
        ref = arms['NC']
        for c in CONDITIONS:
            a = arms[c]
            if a['initial'] != ref['initial'] or a['context'] != ref['context']:
                raise ValueError('initial neural/model/config/identity mismatch')
            equal_prefix(ref, a, 5000)
            if a['neural'][:1000] != ref['neural'][:1000]:
                raise ValueError('complete all-arm neural prefix mismatch')
            for x, y in zip(ref['neural'], a['neural']):
                for field in ('rng_state', 'uniforms_sha256', 'rng_indices', 'draws', 'proprio_rng_state'):
                    if x[field] != y[field]:
                        raise ValueError('full-run common RNG mismatch: ' + field)
        for n, w in (('NC', 'WC'), ('NP', 'WP')):
            equal_prefix(arms[n], arms[w], 5005, proposed=False)
            x, y = arms[n]['neural'][1000], arms[w]['neural'][1000]
            for field in ('pre_state_sha256', 'post_state_sha256', 'previous', 'raw', 'offered', 'eligible',
                          'delivered', 'fired', 'encoder_state'):
                if x[field] != y[field]:
                    raise ValueError('same-push pre-gate neural/safety prefix mismatch')
        checks['prefix_and_full_rng'] = True
        exposure = {}
        for n, w in (('NC', 'WC'), ('NP', 'WP')):
            first_action = next((i - 1 for i, (x, y) in enumerate(zip(arms[n]['samples'], arms[w]['samples']))
                                 if i and x['commanded_joints'] != y['commanded_joints']), None)
            first_physics = next((i for i, (x, y) in enumerate(zip(arms[n]['samples'], arms[w]['samples']))
                                  if x['qpos'] != y['qpos'] or x['qvel'] != y['qvel']), None)
            exposure[n + '_vs_' + w] = dict(first_actual_outgoing_command_difference=first_action,
                first_physical_difference_state=first_physics,
                first_actual_command_effect_state=None if first_action is None else first_action + 1)
        accepted = all(checks.values())
        return dict(accepted=accepted, status='INTEGRITY_ACCEPTED' if accepted else 'INCONCLUSIVE_INTEGRITY',
                    checks=checks, arms=audits, behavior=behavior(arms, audits) if accepted else None,
                    pair_exposure=exposure, unity_replay_eligible=accepted)
    except (KeyError, TypeError, ValueError, IndexError, OverflowError) as exc:
        return dict(accepted=False, status='INCONCLUSIVE_INTEGRITY', checks=checks, arms=audits,
                    reason=f'{type(exc).__name__}: {exc}', unity_replay_eligible=False, behavior=None)


def save(path, payload):
    """Exclusive publication; explicit nonfinite markers preserve failed values."""
    from ..embodiment.distal_tarsus_reference import json_safe
    data = json.dumps(json_safe(native(payload)), allow_nan=False, separators=(',', ':')).encode()
    with Path(path).open('xb') as stream:
        stream.write(gzip.compress(data, mtime=0) if str(path).endswith('.gz') else data + b'\n')
    return dict(path=Path(path).name, sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest())


def implementation_committed():
    path = 'malecns_backend/live/balance_contribution.py'
    committed = git('show', 'HEAD:' + path).replace(b'\r\n', b'\n')
    if committed != (ROOT / path).read_bytes().replace(b'\r\n', b'\n'):
        raise ValueError('commit tested implementation before scientific execution')
    return git('rev-parse', 'HEAD').decode().strip()


def execute(output, *, live=False):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    report = dict(schema=SCHEMA, design=design(), runner_implemented=True, arms={}, sources_before=source_hashes(),
                  scientific_experiment_started=False, run_status='NOT_RUN')
    report['preflight'] = preflight()
    save(output / 'preflight.json', report['preflight'])
    if live and report['preflight']['verified']:
        try:
            report['implementation_commit'] = implementation_committed()
            protocol, table = static_authority()
            report['scientific_experiment_started'] = True
            save(output / 'started.json', dict(commit=report['implementation_commit'], conditions=list(CONDITIONS)))
            for c in CONDITIONS:
                arm = run_arm(c, protocol, table)
                report['arms'][c] = arm
                save(output / f'{c}.json.gz', arm)
                gc.collect()
                if arm['run_status'] != 'COMPLETE':
                    break
            report['run_status'] = 'COMPLETE' if len(report['arms']) == 4 and all(
                a['run_status'] == 'COMPLETE' for a in report['arms'].values()) else 'INCOMPLETE'
        except (Exception, KeyboardInterrupt) as exc:
            report.update(run_status='ERROR', error=f'{type(exc).__name__}: {exc}')
    elif live:
        report['run_status'] = 'BLOCKED_PREREQUISITES'
    report['sources_after'] = source_hashes()
    report['evaluation'] = evaluate(report)
    # Store arm files once; the index locks every raw capture. No overwritten run.
    summary = {k: v for k, v in report.items() if k != 'arms'}
    summary['arm_artifacts'] = {c: dict(path=f'{c}.json.gz', sha256=hashlib.sha256(
        (output / f'{c}.json.gz').read_bytes()).hexdigest()) for c in report['arms']}
    save(output / 'report.json', summary)
    return summary


def load_run(directory):
    directory = Path(directory)
    report = json.loads((directory / 'report.json').read_text(encoding='utf-8'))
    report['arms'] = {}
    for c, artifact in report['arm_artifacts'].items():
        if c not in CONDITIONS or artifact['path'] != f'{c}.json.gz':
            raise ValueError('invalid raw artifact identity')
        raw = (directory / artifact['path']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != artifact['sha256']:
            raise ValueError('raw arm artifact hash mismatch')
        report['arms'][c] = json.loads(gzip.decompress(raw))
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--output', type=Path, help='new exclusive run directory; default is static preflight only')
    group.add_argument('--evaluate', type=Path, help='replay saved evaluation without native/CNS execution')
    parser.add_argument('--live', action='store_true', help='one fixed four-arm run, only after all prerequisites and committed implementation')
    args = parser.parse_args(argv)
    if args.evaluate and args.live:
        parser.error('--live cannot accompany --evaluate')
    if args.evaluate:
        result = evaluate(load_run(args.evaluate))
        print(json.dumps(result, allow_nan=False))
        return 0 if result['accepted'] else 1
    result = execute(args.output, live=args.live)
    print(json.dumps(dict(status=result['run_status'], preflight=result['preflight'],
                          integrity=result['evaluation']['status']), allow_nan=False))
    return 0 if result['preflight']['verified'] and (not args.live or result['evaluation']['accepted']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
