"""V1.2 exact model-phase check without per-state full-model re-hashing.

The V1.1 adapter re-hashed every numeric model array (379 arrays, 108.75 MB of
BVH/texture/mesh data in the actual fly model, ~55 ms) twice per state, which
explains nearly all of its ~123 ms/step versus ~10 ms/step without it. Here the
recorded M0 and the independently derived MR are snapshotted once; each state
compares the live model's raw bytes (and option values and compiled name
buffer) exactly against the expected snapshot. Byte equality to a snapshot
whose full identity hashes to the recorded SHA256 is as strict as re-hashing:
no collision risk, NaN payloads and signed zeros included. The V1.1 live-data
guard and every other mechanical primitive are reused unchanged.
"""
import numpy as np

from . import assistance_native_v1_1 as guard
from .assistance_native import (require, digest, components, model_record, partition, write_rows,
    plan, FIELDS, array_identity)

CHECK = 'exact-byte-snapshot-of-recorded-M0-and-derived-MR-v1.2'


def _bytes(value):
    return np.ascontiguousarray(value).reshape(-1).view(np.uint8)


def options(model):
    """Same option selection/encoding as physics_model_identity."""
    option, values = model.opt, {}
    for name in dir(option):
        if name.startswith('_'):
            continue
        try:
            value = getattr(option, name)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            continue
        if isinstance(value, (bool, int, float, np.bool_, np.integer, np.floating)):
            values[name] = value.item() if isinstance(value, np.generic) else value
        elif isinstance(value, np.ndarray) and value.dtype.kind in 'biufc':
            values[name] = array_identity(value)
    return values


class ModelPhases:
    """Exact M0/MR snapshots of one actual model, built once at binding."""

    def __init__(self, model, data, selected_ids, original, neutral):
        model = getattr(model, 'ptr', model)
        require(digest(components(model, data)) == original['sha256'], 'snapshot requires the actual recorded M0')
        self.names = list(original['identity']['model_arrays'])
        m0 = {n: np.array(getattr(model, n), copy=True) for n in self.names}
        mr = {n: a.copy() for n, a in m0.items()}
        for name in FIELDS:
            mr[name][selected_ids] = 0.
        for phase, snapshot, record in (('M0', m0, original), ('MR', mr, neutral)):
            require(all(array_identity(snapshot[n]) == record['identity']['model_arrays'][n] for n in self.names),
                    'snapshot does not reproduce recorded '+phase+' identity')
        require(options(model) == original['identity']['options'] == neutral['identity']['options'],
                'recorded model options differ from actual model')
        self.options = original['identity']['options']
        self.name_buffer = bytes(_bytes(model.names))
        self.sha = dict(M0=original['sha256'], MR=neutral['sha256'])
        self.snapshots = dict(M0=m0, MR=mr)
        self.bytes = {phase: {n: _bytes(a) for n, a in snapshot.items()} for phase, snapshot in self.snapshots.items()}

    def phase_sha(self, model, phase):
        """Return the recorded SHA256 only if the live model is byte-identical to that phase."""
        model = getattr(model, 'ptr', model)
        require(phase in self.sha, 'declared model phase required')
        reference = self.bytes[phase]
        changed = [n for n in self.names if not np.array_equal(_bytes(getattr(model, n)), reference[n])]
        require(not changed, f'live model differs from {phase}: '+','.join(changed[:12]))
        require(options(model) == self.options, 'live model options changed')
        require(bytes(_bytes(model.names)) == self.name_buffer, 'live model name buffer changed')
        return self.sha[phase]


class Intervention(guard.Intervention):
    """V1.1 phase machine with the exact snapshot comparison at each boundary."""

    def __init__(self, arm_id, model, data, inv, original):
        super().__init__(arm_id, model, data, inv, original)
        self.phases = ModelPhases(model, data, [r['actuator_id'] for r in partition(inv)[1]],
                                  original, self.neutral)

    def boundary(self, index, protected_state):
        require(self.ready, 'native qualification required before scientific boundary')
        require(type(index) is int and index == self.last_boundary+1 and index <= 20000,
                'exact consecutive scientific boundary required')
        phase = plan.expected_model_phase(self.arm_id, index)
        expected = self.neutral if phase == 'MR' else self.original
        require(self.phases.phase_sha(self.model, phase) == expected['sha256'], 'unexpected sampled model phase')
        require(abs(float(self.data.time)-index*.0001) <= 1e-12, 'scientific boundary clock mismatch')
        if index == 5005:
            fields = guard.data_fields(self.data)
            before = dict(live=digest(fields), protected=protected_state())
            self.event = dict(state_index=index, time_s=float(self.data.time), before=self.original,
                              operation='ZERO_FULL_SELECTED_ROWS' if self.arm_id.startswith('R_') else 'OBSERVE_ONLY',
                              selected_actuator_ids=[r['actuator_id'] for r in partition(self.inventory)[1]],
                              protected_before=before, live_guard=guard.GUARD, model_phase_check=CHECK)
            if self.arm_id.startswith('R_'):
                write_rows(self.model, self.original, self.inventory, True)
            self.event['after'] = model_record(self.model, self.data)
            guard.require_unchanged(fields, self.data, 'boundary mutated live data')
            self.event['protected_after'] = dict(live=guard.data_digest(self.data), protected=protected_state())
            require(self.event['after'] == (self.neutral if self.arm_id.startswith('R_') else self.original),
                    'undeclared mechanical model change')
            require(self.event['protected_before'] == self.event['protected_after'], 'boundary mutated live/neural state')
        self.last_boundary = index
