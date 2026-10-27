"""Mechanical evidence primitives for the prospective assistance assay.

No experiment CLI, model factory, CNS constructor or integrator. The caller must
provide the actual initialized model and complete the campaign/source gates.
"""
import copy
from itertools import product

import numpy as np

from . import assistance_contribution_plan as plan
from .contact_context import digest
from ..embodiment import lf_native_isolation as isolation
from ..embodiment.lf_pose_force import dense_moments, saved_sparse_matrix
from ..embodiment.candidate_motor_channel_experiment import (
    physics_model_identity, _canonical_array_identity as array_identity,
)

SCHEMA = 'assistance-mechanical-evidence-v1'
FIELDS = ('actuator_gainprm', 'actuator_biasprm')
FORCE_FIELDS = ('actuator_force', 'qfrc_actuator', 'qfrc_passive', 'qfrc_bias',
                'qfrc_applied', 'xfrc_applied', 'ctrl')
ATOL, PROJECTION_ATOL = 1e-10, 1e-8


def require(value, message):
    if not value:
        raise ValueError(message)


def components(model, data):
    value = physics_model_identity(getattr(model, 'ptr', model), getattr(data, 'ptr', data))['components']
    del value['initial_state']  # model phase identity must not include body motion
    return value


def model_record(model, data):
    model = getattr(model, 'ptr', model)
    identity = components(model, data)
    return dict(identity=identity, sha256=digest(identity), arrays={
        name: isolation.encode_nonfinite(np.asarray(getattr(model, name)).tolist())
        for name in identity['model_arrays']})


def array_values(record, name):
    # Nonfinite native metadata use the existing lossless tagged representation.
    def decode(value):
        if isinstance(value, dict):
            return isolation.decode_nonfinite(value)
        return [decode(v) for v in value] if isinstance(value, list) else value
    spec = record['identity']['model_arrays'][name]
    return np.asarray(decode(record['arrays'][name]), dtype=spec['dtype']).reshape(spec['shape'])


def validate_model_record(record):
    require(set(record) == {'identity', 'sha256', 'arrays'}, 'complete model record required')
    require(set(record['arrays']) == set(record['identity']['model_arrays']), 'complete typed model arrays required')
    for name, expected in record['identity']['model_arrays'].items():
        require(array_identity(array_values(record, name)) == expected, 'typed model array mismatch: '+name)
    require(digest(record['identity']) == record['sha256'], 'model digest mismatch')


def partition(inv):
    """Resolve logical authority through explicit validated native rows."""
    admitted, selected = plan.coordinate_partition(plan.locked_json(plan.AUTHORITY, plan.AUTHORITY_SHA256))
    rows = inv['rows']
    require(len(rows) == 42, 'complete action inventory required')
    by_name = {row['coordinate']: row for row in rows}
    require(len(by_name) == 42, 'unique coordinate inventory required')
    for expected in admitted+selected:
        row = by_name[expected['coordinate']]
        require(type(row['action_index']) is int and row['action_index'] == expected['action_index'],
                'exact action index required')
    return ([by_name[r['coordinate']] for r in admitted], [by_name[r['coordinate']] for r in selected])


def validate_binding(inv, record):
    """Re-evaluable binding; no name-only/native-ID or action-ID inference."""
    validate_model_record(record)
    dims = record['identity']['dimensions']
    for row in inv['rows']+inv['adhesion']:
        for key, bound in (('actuator_id', dims['nu']), ('body_id', dims['nbody'])):
            require(type(row[key]) is int and 0 <= row[key] < bound, 'invalid native '+key)
        if 'joint_id' in row:
            require(type(row['joint_id']) is int and 0 <= row['joint_id'] < dims['njnt'], 'invalid joint ID')
            for key, bound in (('qpos_range', dims['nq']), ('dof_range', dims['nv'])):
                addresses = row[key]
                require(len(addresses) == 2 and all(type(i) is int for i in addresses)
                        and 0 <= addresses[0] < addresses[1] <= bound, 'invalid native addresses')
    isolation.validate_inventory(inv, dict(components=record['identity']))
    retained, selected = partition(inv)
    require(dims.get('nplugin', 0) == 0 and dims.get('nmocap', 0) == 0, 'plugin/mocap state unsupported')
    aids = [r['actuator_id'] for r in selected]
    jids = [r['joint_id'] for r in selected]
    for limited, ranges, ids in (('actuator_forcelimited', 'actuator_forcerange', aids),
                                  ('jnt_actfrclimited', 'jnt_actfrcrange', jids)):
        flags, limits = array_values(record, limited), array_values(record, ranges)
        require(all(not flags[i] or limits[i, 0] <= 0 <= limits[i, 1] for i in ids),
                'selected force limits must admit zero')
    require(not np.any(array_values(record, 'jnt_actgravcomp')[jids]), 'selected actuator gravity compensation unsupported')
    require(not np.any(array_values(record, 'body_gravcomp')), 'body gravity compensation unsupported')
    # Never change enable/disable bits or groups to satisfy this requirement.
    options = record['identity']['options']
    import mujoco
    require(not options['disableflags'] & int(mujoco.mjtDisableBit.mjDSBL_ACTUATION), 'actuation disabled')
    groups = array_values(record, 'actuator_group')
    require(all(not options.get('disableactuator', 0) & (1 << int(groups[r['actuator_id']]))
                for r in retained+selected), 'position actuator group disabled')
    return retained, selected


def bind(model, data, fly):
    inv = isolation.inventory(model, fly)
    inv.update(nq=int(model.nq), nv=int(model.nv))
    record = model_record(model, data)
    validate_binding(inv, record)
    return inv, record


def neutral_record(original, inv):
    validate_binding(inv, original)
    expected = copy.deepcopy(original)
    _, selected = partition(inv)
    ids = [r['actuator_id'] for r in selected]
    for name in FIELDS:
        values = array_values(original, name).copy()
        values[ids] = 0.
        expected['arrays'][name] = isolation.encode_nonfinite(values.tolist())
        expected['identity']['model_arrays'][name] = array_identity(values)
    expected['sha256'] = digest(expected['identity'])
    return expected


def write_rows(model, original, inv, neutral):
    """Exactly the predeclared two sets of rows; no control/live-data writes."""
    ids = [r['actuator_id'] for r in partition(inv)[1]]
    for name in FIELDS:
        getattr(model, name)[ids] = 0. if neutral else array_values(original, name)[ids]


def data_digest(data):
    """Guard all exposed numeric MjData arrays/scalars, including warm starts."""
    data = getattr(data, 'ptr', data)
    values = {}
    for name in dir(data):
        if name.startswith('_') or name == 'ptr':
            continue
        value = getattr(data, name)
        if isinstance(value, np.ndarray) and value.dtype.kind in 'biufc':
            values[name] = array_identity(value)
        elif isinstance(value, (int, float, np.integer, np.floating)):
            values[name] = isolation.encode_nonfinite(value)
    return digest(values)


def force_record(native, model, data):
    _, sparse = dense_moments(native, model, data)
    return dict(moments=sparse, **{name: np.asarray(getattr(data, name)).tolist() for name in FORCE_FIELDS})


def audit_force(record, inv, neutral, selection=None):
    nu, nv = 48, inv['nv']
    shape = dict(actuator_force=(nu,), qfrc_actuator=(nv,), qfrc_passive=(nv,),
                 qfrc_bias=(nv,), qfrc_applied=(nv,), ctrl=(nu,))
    vectors = {name: np.asarray(record[name], dtype=float) for name in FORCE_FIELDS}
    for name, values in vectors.items():
        require(np.isfinite(values).all(), 'nonfinite force evidence: '+name)
        if name in shape:
            require(values.shape == shape[name], 'force evidence shape: '+name)
    require(vectors['xfrc_applied'].shape == (len(inv['names']['body']), 6),
            'full external body forces required')
    matrix = saved_sparse_matrix(record['moments'], nu, nv)
    retained, selected = selection if selection is not None else partition(inv)
    for row in retained+selected:
        expected = np.zeros(nv); expected[row['dof_range'][0]] = 1.
        require(np.array_equal(matrix[row['actuator_id']], expected), 'joint transmission force support changed')
    adhesion = [r['actuator_id'] for r in inv['adhesion']]
    require(not np.any(vectors['ctrl'][adhesion]) and not np.any(vectors['actuator_force'][adhesion]),
            'adhesion control/force must stay exactly zero')
    require(np.max(np.abs(matrix.T @ vectors['actuator_force']-vectors['qfrc_actuator'])) <= PROJECTION_ATOL,
            'actuator force projection mismatch')
    if neutral:
        aids = [r['actuator_id'] for r in selected]
        dofs = [r['dof_range'][0] for r in selected]
        require(np.max(np.abs(vectors['actuator_force'][aids])) <= ATOL
                and np.max(np.abs(vectors['qfrc_actuator'][dofs])) <= ATOL, 'neutralized force remains')
    return matrix


def probe_inputs(inv, center, control_sign, velocity_sign):
    require(control_sign in (1, -1) and velocity_sign in (1, -1), 'undeclared probe')
    qpos = np.array(center, copy=True)
    qvel, ctrl = np.zeros(inv['nv']), np.zeros(48)
    _, selected = partition(inv)
    for row in inv['rows']:
        aid = row['actuator_id']
        ctrl[aid] = qpos[row['qpos_range'][0]]+control_sign*.01*(-1)**row['action_index']
        limits = inv['actuators']['ctrlrange'][aid]
        require(not inv['actuators']['ctrllimited'][aid] or limits[0] <= ctrl[aid] <= limits[1],
                'declared probe control out of original range; do not clip')
    for row in selected:
        qvel[row['dof_range'][0]] = velocity_sign*.1*(-1)**row['action_index']
    return qpos, qvel, ctrl


def evaluate_qualification(report):
    """Offline force-law check. Not a campaign/biological acceptance predicate."""
    require(report['schema'] == SCHEMA and report['status'] == 'COMPLETE', 'qualification incomplete')
    inv, original = report['inventory'], report['original']
    validate_binding(inv, original)
    neutral = neutral_record(original, inv)
    require(report['neutral'] == neutral and report['restored'] == original, 'qualification model restoration/patch mismatch')
    require(report['before'] == report['after'], 'qualification changed live/neural state')
    require(report['explicit_calls'] == dict(shadow_allocations=1, shadow_resets=12, shadow_forwards=12),
            'qualification explicit API budget mismatch')
    require(len(report['cases']) == 12, 'all fixed qualification cases required')
    retained, selected = partition(inv)
    aids = [r['actuator_id'] for r in selected]
    keep = [r['actuator_id'] for r in retained]
    outside = sorted(set(range(inv['nv']))-{r['dof_range'][0] for r in selected})
    exposure = np.zeros(22)
    for probe, (cs, vs) in enumerate(product((1, -1), repeat=2)):
        cases = report['cases'][probe*3:probe*3+3]
        expected_inputs = [a.tolist() for a in probe_inputs(inv, report['center'], cs, vs)]
        for case, phase in zip(cases, ('M0', 'MR', 'RESTORED_M0')):
            require(case['probe'] == [cs, vs] and case['phase'] == phase, 'qualification case order mismatch')
            require(case['inputs'] == expected_inputs and case['time_s'] == 0., 'qualification probe/reset mismatch')
            require(case['model_sha256'] == (neutral if phase == 'MR' else original)['sha256'], 'qualification phase mismatch')
            require(not np.any(case['qfrc_applied']) and not np.any(case['xfrc_applied']), 'probe applied force changed')
            audit_force(case, inv, phase == 'MR')
        b, r, restored = cases
        exposure = np.maximum(exposure, np.abs(np.asarray(b['actuator_force'])[aids]))
        require(b == dict(restored, phase='M0'), 'baseline restoration changed force evidence')
        require(b['moments'] == r['moments'] and b['qfrc_passive'] == r['qfrc_passive'], 'moment/passive probe mismatch')
        for field, indices in (('actuator_force', keep), ('qfrc_actuator', outside)):
            require(np.max(np.abs(np.asarray(b[field])[indices]-np.asarray(r[field])[indices])) <= ATOL,
                    'nonselected probe force changed')
    require(np.min(exposure) > 1e-8, 'vacuous selected baseline forces')
    return dict(passed=True, cases=12, minimum_baseline_exposure=float(np.min(exposure)),
                scope='INSTANTANEOUS_FORCE_LAW_ONLY_NOT_MOVING_CAMPAIGN')


def qualify(native, model, live_data, inv, original, protected_state, report):
    """One bounded shadow qualification; partial report survives any exception.

    No module-global API patches. Only supplied native MjData/reset/forward APIs
    are called. Integration/live reset/forward and CNS advancement are absent.
    """
    require(not report, 'qualification is exclusive; no retry on existing evidence')
    report.update(schema=SCHEMA, status='INCOMPLETE', inventory=inv, original=original,
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
    report['before'] = dict(live=data_digest(live_data), protected=protected_state())
    saved = {name: np.array(getattr(model, name), copy=True) for name in FIELDS}
    try:
        # Constructor entries recorded separately; no claim about invisible native internals.
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
        # Restore even after failure, without resetting/forwarding live data.
        for name, values in saved.items():
            getattr(model, name)[:] = values
        report['restored'] = model_record(model, live_data)
        report['after'] = dict(live=data_digest(live_data), protected=protected_state())
    report['status'] = 'COMPLETE'
    try:
        report['evaluation'] = evaluate_qualification(report)
    except Exception as exc:
        report.update(status='FAILED_QUALIFICATION', error=f'{type(exc).__name__}: {exc}')
        raise
    return report


class Intervention:
    """Instance-local phase machine. Qualification must precede integration."""
    def __init__(self, arm_id, model, data, inv, original):
        require(arm_id in plan.ARM_IDS, 'declared arm required')
        validate_binding(inv, original)
        self.arm_id, self.model, self.data, self.inventory = arm_id, model, data, inv
        self.original, self.neutral = original, neutral_record(original, inv)
        self.event, self.ready, self.last_boundary = None, False, -1

    def accept_qualification(self, report):
        require(not self.ready and self.last_boundary == -1, 'qualification already bound')
        evaluate_qualification(report)
        require(report['original'] == self.original, 'actual model differs from qualified M0')
        require(model_record(self.model, self.data) == self.original, 'model changed before qualification binding')
        self.ready = True

    def boundary(self, index, protected_state):
        require(self.ready, 'native qualification required before scientific boundary')
        require(type(index) is int and index == self.last_boundary+1 and index <= 20000,
                'exact consecutive scientific boundary required')
        phase = plan.expected_model_phase(self.arm_id, index)
        expected = self.neutral if phase == 'MR' else self.original
        require(digest(components(self.model, self.data)) == expected['sha256'], 'unexpected sampled model phase')
        require(abs(float(self.data.time)-index*.0001) <= 1e-12, 'scientific boundary clock mismatch')
        if index == 5005:
            before = dict(live=data_digest(self.data), protected=protected_state())
            self.event = dict(state_index=index, time_s=float(self.data.time), before=self.original,
                              operation='ZERO_FULL_SELECTED_ROWS' if self.arm_id.startswith('R_') else 'OBSERVE_ONLY',
                              selected_actuator_ids=[r['actuator_id'] for r in partition(self.inventory)[1]],
                              protected_before=before)
            if self.arm_id.startswith('R_'):
                write_rows(self.model, self.original, self.inventory, True)
            self.event['after'] = model_record(self.model, self.data)
            self.event['protected_after'] = dict(live=data_digest(self.data), protected=protected_state())
            require(self.event['after'] == (self.neutral if self.arm_id.startswith('R_') else self.original),
                    'undeclared mechanical model change')
            require(self.event['protected_before'] == self.event['protected_after'], 'boundary mutated live/neural state')
        self.last_boundary = index


def audit_trace(arm_id, inv, original, event, samples):
    """Mechanical-only offline audit; never masquerades as full scientific audit."""
    require(arm_id in plan.ARM_IDS and len(samples) == 20001, 'complete declared mechanical trace required')
    neutral = neutral_record(original, inv)
    released = arm_id.startswith('R_')
    expected = dict(state_index=5005, time_s=5005*.0001, before=original,
        after=neutral if released else original,
        operation='ZERO_FULL_SELECTED_ROWS' if released else 'OBSERVE_ONLY',
        selected_actuator_ids=[r['actuator_id'] for r in partition(inv)[1]])
    require({k: event[k] for k in expected} == expected, 'mechanical boundary journal mismatch')
    require(event['protected_before'] == event['protected_after'], 'boundary changed protected state')
    selection = partition(inv)
    for index, sample in enumerate(samples):
        require(type(sample['state_index']) is int and sample['state_index'] == index, 'mechanical trace index mismatch')
        require(abs(sample['time_s']-index*.0001) <= 1e-12, 'mechanical trace clock mismatch')
        phase = plan.expected_model_phase(arm_id, index)
        require(sample['model_sha256'] == (neutral if phase == 'MR' else original)['sha256'], 'mechanical sample phase mismatch')
        audit_force(sample, inv, phase == 'MR', selection)
    return dict(passed=True, states=20001, scope='MECHANICAL_ONLY_FULL_SCIENTIFIC_EVALUATOR_STILL_REQUIRED')
