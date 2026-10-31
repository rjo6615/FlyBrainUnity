"""V1.1 live-data guard for the assistance adapter; force mechanics unchanged.

Executed campaign run-desktop-01 stopped at A_NC binding because the V1 guard
hashed EVERY exposed numeric MjData buffer. Several arena-backed scratch
buffers (island and efc_AR descriptors) are not defined state and changed
between consecutive reads with no intervening MuJoCo call (standalone toy
MuJoCo 3.2.7 models). This module guards MuJoCo's documented complete
simulation state, mjSTATE_INTEGRATION (everything mj_step consumes), read
field by field without a native call, names any changed field, and otherwise
reuses every V1 mechanical primitive unchanged. The executed V1 module stays
immutable as the record of that attempt.
"""
from itertools import product

import numpy as np

from . import assistance_native as v1
from .assistance_native import (require, digest, components, model_record, validate_binding,
    neutral_record, write_rows, force_record, probe_inputs, evaluate_qualification, partition,
    FIELDS, plan, isolation, array_identity)

GUARD = 'mujoco-mjSTATE_INTEGRATION-fields-v1.1'
# mjSTATE_INTEGRATION component order (MuJoCo 3.2.7 mjtState bits 1..4096).
INTEGRATION_FIELDS = ('time', 'qpos', 'qvel', 'act', 'qacc_warmstart', 'ctrl', 'qfrc_applied',
                      'xfrc_applied', 'eq_active', 'mocap_pos', 'mocap_quat', 'userdata', 'plugin_state')


def data_fields(data):
    """Per-field identities of the complete integration state; derived buffers excluded."""
    data = getattr(data, 'ptr', data)
    return {name: array_identity(np.asarray(getattr(data, name))) for name in INTEGRATION_FIELDS}


def data_digest(data):
    return digest(data_fields(data))


def require_unchanged(before, data, message):
    after = data_fields(data)
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    require(not changed, message+': '+','.join(changed))


def qualify(native, model, live_data, inv, original, protected_state, report):
    """V1 bounded shadow qualification with the V1.1 live-data guard.

    Identical explicit API budget, probes, restoration and offline evaluation;
    only the before/after live-data identity definition differs.
    """
    require(not report, 'qualification is exclusive; no retry on existing evidence')
    report.update(schema=v1.SCHEMA, live_guard=GUARD, status='INCOMPLETE', inventory=inv, original=original,
                  cases=[], explicit_calls=dict(shadow_allocations=0, shadow_resets=0, shadow_forwards=0))
    try:
        validate_binding(inv, original)
        require(model_record(model, live_data) == original, 'original actual model required')
        for name in ('control', 'passive', 'act_dyn', 'act_gain', 'act_bias'):
            require(getattr(native, 'get_mjcb_'+name)() is None, 'native callback unsupported: '+name)
    except BaseException as exc:
        report['error'] = f'{type(exc).__name__}: {exc}'
        raise
    report.update(neutral=neutral_record(original, inv), center=np.asarray(live_data.qpos).tolist())
    live_before = data_fields(live_data)
    report['before'] = dict(live=digest(live_before), protected=protected_state())
    saved = {name: np.array(getattr(model, name), copy=True) for name in FIELDS}
    try:
        from .balance_contribution import initialization_operations
        with initialization_operations() as operations:
            report['explicit_calls']['shadow_allocations'] += 1
            shadow = native.MjData(model)
        require(shadow is not live_data, 'shadow data must not alias live data')
        report['constructor_observed_api_entries'] = dict(operations)
        for cs, vs in product((1, -1), repeat=2):
            qpos, qvel, ctrl = probe_inputs(inv, report['center'], cs, vs)
            for phase in ('M0', 'MR', 'RESTORED_M0'):
                write_rows(model, original, inv, phase == 'MR')
                report['explicit_calls']['shadow_resets'] += 1
                native.mj_resetData(model, shadow)
                shadow.qpos[:], shadow.qvel[:], shadow.ctrl[:] = qpos, qvel, ctrl
                shadow.qfrc_applied[:] = 0.; shadow.xfrc_applied[:] = 0.
                report['explicit_calls']['shadow_forwards'] += 1
                native.mj_forward(model, shadow)
                report['cases'].append(dict(probe=[cs, vs], phase=phase,
                    inputs=[np.asarray(getattr(shadow, name)).tolist() for name in ('qpos', 'qvel', 'ctrl')],
                    time_s=float(shadow.time), model_sha256=digest(components(model, live_data)),
                    **force_record(native, model, shadow)))
    except BaseException as exc:
        report['error'] = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        for name, values in saved.items():
            getattr(model, name)[:] = values
        report['restored'] = model_record(model, live_data)
        live_after = data_fields(live_data)
        report['after'] = dict(live=digest(live_after), protected=protected_state())
        report['live_fields_changed'] = sorted(k for k in set(live_before) | set(live_after)
                                               if live_before.get(k) != live_after.get(k))
    report['status'] = 'COMPLETE'
    try:
        report['evaluation'] = evaluate_qualification(report)
    except Exception as exc:
        report.update(status='FAILED_QUALIFICATION', error=f'{type(exc).__name__}: {exc}')
        raise
    return report


class Intervention(v1.Intervention):
    """V1 phase machine; only the boundary live-data guard definition differs."""

    def boundary(self, index, protected_state):
        require(self.ready, 'native qualification required before scientific boundary')
        require(type(index) is int and index == self.last_boundary+1 and index <= 20000,
                'exact consecutive scientific boundary required')
        phase = plan.expected_model_phase(self.arm_id, index)
        expected = self.neutral if phase == 'MR' else self.original
        require(digest(components(self.model, self.data)) == expected['sha256'], 'unexpected sampled model phase')
        require(abs(float(self.data.time)-index*.0001) <= 1e-12, 'scientific boundary clock mismatch')
        if index == 5005:
            fields = data_fields(self.data)
            before = dict(live=digest(fields), protected=protected_state())
            self.event = dict(state_index=index, time_s=float(self.data.time), before=self.original,
                              operation='ZERO_FULL_SELECTED_ROWS' if self.arm_id.startswith('R_') else 'OBSERVE_ONLY',
                              selected_actuator_ids=[r['actuator_id'] for r in partition(self.inventory)[1]],
                              protected_before=before, live_guard=GUARD)
            if self.arm_id.startswith('R_'):
                write_rows(self.model, self.original, self.inventory, True)
            self.event['after'] = model_record(self.model, self.data)
            require_unchanged(fields, self.data, 'boundary mutated live data')
            self.event['protected_after'] = dict(live=data_digest(self.data), protected=protected_state())
            require(self.event['after'] == (self.neutral if self.arm_id.startswith('R_') else self.original),
                    'undeclared mechanical model change')
            require(self.event['protected_before'] == self.event['protected_after'], 'boundary mutated live/neural state')
        self.last_boundary = index
