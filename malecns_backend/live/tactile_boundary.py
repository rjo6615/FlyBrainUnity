"""Versioned, instance-local experimental input boundary over the locked kernel."""
from __future__ import annotations

import copy
from dataclasses import asdict
import hashlib
from collections.abc import Mapping

import numpy as np

from . import contact_context as context
from ..embodiment.tactile_contact import TactileContactEncoder, load_tactile_populations
from ..embodiment.tactile_propagation import rng_digest
from ..embodiment.tactile_motor_loop_audit import _joint_positions

LEGS = context.LEGS


def native(value):
    if isinstance(value, Mapping):
        return {k: native(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [native(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    return value.item() if isinstance(value, np.generic) else value


def array_digest(*arrays):
    h = hashlib.sha256()
    for value in arrays:
        a = np.asarray(value)
        h.update(str((a.shape, a.dtype.str)).encode())
        h.update(a.tobytes())
    return h.hexdigest()


def neural_state_digest(brain):
    arrays = array_digest(*(getattr(brain, k) for k in (
        'v', 'g_exc', 'g_inh', 'refractory', 'activity_trace', 'adaptation',
        'depression_resource', 'spike_counts', 'bias', 'threshold_offset', 'external_drive')))
    return context.digest(dict(arrays=arrays, ring=native(brain._ring), head=int(brain._head),
                               time_ms=float(brain.time_ms), rng=brain.rng.bit_generator.state))


class Trial(context.PassiveRecorder):
    """Experimental factory callback, not a passive neural diagnostic probe.

    Only the supplied brain instance's external-input boundaries are adapted.
    The original neural step, kernel, motor pipeline and encoder stay in use.
    """
    def __init__(self, condition, populations=None):
        super().__init__()
        if condition not in ('WITHHELD', 'ENABLED'):
            raise ValueError('unknown experimental condition')
        self.condition = condition
        self.populations = populations or load_tactile_populations()
        self.encoder = TactileContactEncoder(populations=self.populations)
        self.pending = {l: set() for l in LEGS}
        self.neural = []
        self.initial = None
        self.brain = None
        self.original_step = self.original_trials = None

    def capture(self, physics, obs, action):
        super().capture(physics, obs, action)
        sample = self.samples[-1]
        sample['joint_positions'] = _joint_positions(obs).tolist()
        sample['ctrl'] = np.asarray(physics.data.ctrl).tolist()
        frames = self.encoder.encode(obs['contact_forces'], sample['time_s'] * 1000, context.DT * 1000)
        sample['tactile'] = {}
        for leg, frame in frames.items():
            self.pending[leg].update(frame.generated_dense_indices)
            sample['tactile'][leg] = dict(contact=frame.contact, onset_time_ms=frame.onset_time_ms,
                modeled_rate_hz=frame.modeled_rate_hz, offered=list(frame.generated_dense_indices),
                rng_sha256=rng_digest(self.encoder.rng[leg]))

    def attach(self, brain, channels, *, sensory_sources):
        if self.brain is not None or self.context is None:
            raise RuntimeError('input adapter must attach once after physical reset')
        self.brain, self.channels = brain, channels
        self.proprio = np.asarray(sorted({int(i) for indices in sensory_sources.values() for i in indices}), dtype=np.intp)
        self.tactile = np.asarray(sorted({int(i) for p in self.populations.values() for i in p.dense_indices}), dtype=np.intp)
        if len(self.proprio) != 392 or len(self.tactile) != 1877 or np.intersect1d(self.proprio, self.tactile).size:
            raise RuntimeError('complete disjoint sensory inventories required')
        for population in self.populations.values():
            for body, index in zip(population.body_ids, population.dense_indices):
                if brain.data.body_id_to_index[int(body)] != int(index) or int(brain.data.body_ids[index]) != int(body):
                    raise RuntimeError('tactile body-ID/dense-index mismatch')
        self.schedule = np.union1d(self.proprio, self.tactile).astype(np.intp)
        self.non_input = np.ones(brain.n, dtype=bool)
        self.non_input[self.schedule] = False
        motor = {}
        for name, channel in channels.items():
            indices = list(map(int, channel['observer'].used))
            if any(i in self.schedule for i in indices):
                raise RuntimeError('motor readout overlaps externally driven sensory inventory')
            for i in indices:
                if brain.data.body_id_to_index[int(brain.data.body_ids[i])] != i:
                    raise RuntimeError('motor body-ID/dense-index mismatch')
            motor[name] = dict(dense_indices=indices, body_ids=[int(brain.data.body_ids[i]) for i in indices],
                populations=native(channel['populations']), action_index=channel['index'],
                sign=channel['sign'], decoder_mode=channel['decoder_mode'],
                observer_filtered_hz=channel['observer'].filtered_hz.tolist(),
                observer_counts=channel['observer'].last_counts.tolist(),
                decoder_previous_target=channel['pipeline'].previous_physical_target)
        self.initial = dict(neural_state_sha256=neural_state_digest(brain), neural_config=asdict(brain.config),
            neural_model_sha256=array_digest(brain.weights, brain.pre_sign, brain.indices, brain.indptr),
            motor_inventory=native(motor), external_schedule=self.schedule.tolist(),
            external_schedule_body_ids=[int(brain.data.body_ids[i]) for i in self.schedule],
            tactile_inventory={l: dict(body_ids=list(p.body_ids), dense_indices=list(p.dense_indices))
                               for l, p in self.populations.items()},
            encoder_state=dict(contact=copy.deepcopy(self.encoder._contact), onset=copy.deepcopy(self.encoder._onset),
                               rng={l: rng_digest(self.encoder.rng[l]) for l in LEGS}))
        self.expected_rng = copy.deepcopy(brain.rng.bit_generator.state)
        self.original_withheld = brain.external_drive_withheld_indices.copy()
        self.original_step, self.original_trials = brain.step, brain._external_event_trials
        brain.step = self.step
        brain._external_event_trials = self.event_trials
        return self

    def event_trials(self, candidate_available, parameters):
        """Same Bernoulli equation; fixed common slots and actual availability."""
        brain = self.brain
        if context.digest(brain.rng.bit_generator.state) != context.digest(self.expected_rng):
            raise RuntimeError('unexpected CNS RNG consumption')
        uniforms = brain.rng.random(len(self.schedule))
        self.expected_rng = copy.deepcopy(brain.rng.bit_generator.state)
        driven = np.flatnonzero(brain.external_drive > 0)
        if np.setdiff1d(driven, self.schedule).size:
            raise RuntimeError('unauthorized external input neuron')
        # The existing withheld-input shadow clock is deliberately not used:
        # actual pre-step refractory eligibility is the same rule in both arms.
        eligible = self.available[self.schedule] & (brain.external_drive[self.schedule] > 0)
        selected = eligible & (uniforms < brain.external_drive[self.schedule] * parameters.dt / 1000.)
        forced = np.zeros(brain.n, dtype=bool)
        forced[self.schedule[selected]] = True
        brain._last_external_rng_indices = self.schedule.astype(np.int32)
        brain._last_external_rng_uniforms = uniforms.copy()
        brain._external_rng_step_draws = len(self.schedule)
        self.current_sampling = dict(uniforms_sha256=array_digest(uniforms),
            rng_after_sha256=context.digest(self.expected_rng), draws=len(uniforms),
            eligible_indices=np.flatnonzero(forced).astype(int).tolist())
        return forced

    def step(self):
        brain = self.brain
        proprio = np.flatnonzero(brain.external_drive > 0)
        if (np.setdiff1d(proprio, self.proprio).size
                or not np.all(brain.external_drive[proprio] == 1000. / brain.config.dt)):
            raise RuntimeError('unexpected kernel proprioceptive input boundary')
        offered = {l: sorted(self.pending[l]) for l in LEGS}
        for pending in self.pending.values():
            pending.clear()
        tactile = sorted({i for indices in offered.values() for i in indices})
        if tactile:
            brain.set_external_drive(tactile, 1000. / brain.config.dt)
        before = neural_state_digest(brain)
        self.available = brain.refractory <= 0
        brain.external_drive_withheld_indices = (self.tactile.copy() if self.condition == 'WITHHELD'
                                                 else np.empty(0, dtype=np.intp))
        mask = context.digest(brain.external_drive_withheld_indices.astype(int).tolist())
        fired = self.original_step()  # exactly one canonical neural transition
        eligible = list(map(int, brain._last_external_candidates))
        delivered = list(map(int, brain._last_external_delivered))
        self.neural.append(dict(time_ms=float(brain.time_ms), pre_state_sha256=before,
            post_state_sha256=neural_state_digest(brain),
            downstream_state_sha256=array_digest(*(getattr(brain, k)[self.non_input]
                for k in ('v', 'g_exc', 'g_inh', 'spike_counts'))),
            offered_proprio=proprio.astype(int).tolist(), offered_tactile=offered,
            eligible=eligible, delivered=delivered, withheld_mask_sha256=mask,
            sampling=self.current_sampling.copy(), fired=list(map(int, fired)),
            non_input_fired=[int(i) for i in fired if self.non_input[i]], motor_readout_verified=False))
        return fired

    def sample(self, brain, *, encoded_sensory=None):
        for channel in self.channels.values():
            observer = channel['observer']
            if not np.array_equal(observer.last_counts, brain.spike_counts[observer.used]):
                raise RuntimeError('actual motor observer readout mismatch')
        self.neural[-1]['motor_readout_verified'] = True
        return {'experimental_input_adapter': self.condition}

    def observe(self, record):
        if 'neural_transition_index' in record:
            if int(record['neural_transition_index']) != len(self.neural):
                raise RuntimeError('neural telemetry boundary mismatch')
            fields = ('per_neuron_spike_increments', 'per_neuron_filtered_rate_hz',
                      'raw_signed_contribution_rad', 'final_contribution_rad', 'commanded_joint_targets',
                      'encoded_sensory_rates', 'scheduled_sensory_candidate_events',
                      'delivered_external_sensory_events')
            self.neural[-1]['motor_telemetry'] = {k: native(record[k]) for k in fields}

    def detach(self):
        if self.brain is not None and self.original_step is not None:
            self.brain.step, self.brain._external_event_trials = self.original_step, self.original_trials
            self.brain.external_drive_withheld_indices = self.original_withheld.copy()


def create_session(trial):
    """Same factory arguments as live-v3, with the explicit instance installer."""
    from ..embodiment import _windows_m7d_corrected_spontaneous_adapter as adapter
    from ..embodiment import _windows_m8_live_condition as kernel
    from ..embodiment import live_v2_motor_interface as v2, live_v3_motor_interface as v3
    from ..embodiment import m7d_corrected_spontaneous as m7d
    v1_protocol, records, v1_table = adapter._protocol()
    v2_protocol, records, v2_table = v2.derive_v2(v1_protocol, records, v1_table)
    protocol, records, table = v3.derive_v3(v2_protocol, records, v2_table)
    def runtime(flygym, interfaces):
        sim, physics, obs, tid, sid = adapter._runtime(flygym, interfaces)
        try:
            trial.bind(sim, physics, obs)
        except BaseException:
            sim.close()
            raise
        return context.ObservedSimulation(sim, physics, trial), physics, obs, tid, sid
    return kernel.create_scientific_session(
        protocol=protocol, condition=m7d.CONDITIONS[0], condition_number=1,
        progress=lambda *_: '', cached_admission_assertion=v3.assert_v3_physical_admission,
        cached_records=records, cached_table=table, condition_names=m7d.CONDITIONS,
        contribution_gate=v3.gate_contributions, compact_telemetry=False, runtime_factory=runtime,
        proprioception_only=True, fixed_initial_baseline=True, m8_extended_telemetry=False,
        continuous=True, motor_channel_names=v3.V3_MOTOR,
        supplemental_motor_channels=v3.SUPPLEMENTAL_MOTOR_CHANNELS,
        telemetry_observer=trial.observe, motor_state_probe_factory=trial.attach)
