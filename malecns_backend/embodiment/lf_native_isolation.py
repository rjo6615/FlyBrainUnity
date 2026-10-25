"""Native forward-only LF position-actuator isolation; no muscle/CNS coupling."""
import argparse
from contextlib import contextmanager
import importlib.metadata as packages
import json
from pathlib import Path
import subprocess

import numpy as np

from . import lf_actuation_contract as contract
from . import lf_pose_force as pose
from .candidate_motor_channel_experiment import physics_model_identity, _canonical_array_identity
from .m8_contact_kinematics import compiled_name, namespace_component
from .six_tibia_physics_diagnostic import resolve_dof

ROOT = contract.ROOT
DIRECTORY = 'docs/evidence/lf-native-isolation-v1/'
MANIFEST = DIRECTORY+'input-manifest.json'
PRIOR = contract.DIRECTORY+'audit.json'
SCHEMA = 'lf-native-isolation-v1'
ARMS = ('BASELINE', 'CTRL_ZERO_ONLY', 'NEUTRALIZED')
PROBES = ('CENTER', 'YAW_PLUS', 'YAW_MINUS', 'PITCH_PLUS', 'PITCH_MINUS',
          'ROLL_PLUS', 'ROLL_MINUS', 'VELOCITY_PLUS', 'VELOCITY_MINUS')
INTEGRATORS = ('mj_step', 'mj_step1', 'mj_step2', 'mj_Euler', 'mj_RungeKutta', 'mj_implicit')
ACT_FIELDS = ('trnid', 'trntype', 'gear', 'dyntype', 'gaintype', 'biastype', 'gainprm',
              'biasprm', 'dynprm', 'actadr', 'actnum', 'actearly', 'ctrllimited', 'ctrlrange',
              'forcelimited', 'forcerange')
STATE = ('qpos', 'qvel', 'act', 'ctrl', 'qfrc_applied', 'xfrc_applied')


def sources():
    result = contract.sources()
    for p in (MANIFEST, PRIOR, 'docs/LF_NATIVE_ISOLATION_V1.md',
              'malecns_backend/embodiment/lf_native_isolation.py',
              'malecns_backend/embodiment/candidate_motor_channel_experiment.py',
              'malecns_backend/embodiment/m8_contact_kinematics.py',
              'malecns_backend/embodiment/six_tibia_physics_diagnostic.py'):
        result[p] = contract.force.audit.sha((ROOT/p).read_bytes().replace(b'\r\n', b'\n'))
    if result[PRIOR] != '385c57724f1ec3a937ad35bd86cfe76d4cb004b92d7aa52335d010c83bd81fc4':
        raise ValueError('original static contract record changed')
    return result


def installed_inputs():
    manifest = json.loads((ROOT/MANIFEST).read_text(encoding='utf-8'))
    base = Path(packages.distribution('flygym').locate_file(''))
    for p, expected in manifest['files'].items():
        raw = (base/p).read_bytes()
        if len(raw) != expected['bytes'] or contract.force.audit.sha(raw) != expected['sha256']:
            raise ValueError('installed scientific file changed: '+p)
    if {p: packages.version(p) for p in manifest['versions']} != manifest['versions']:
        raise ValueError('validated installed package version changed')
    return manifest


def preflight():
    before = sources()
    old = json.loads((ROOT/PRIOR).read_text(encoding='utf-8'))
    actual = contract.build()
    if {k: v for k, v in old.items() if k != 'commit'} != actual:
        raise ValueError('prior static contract does not verify')
    inputs = installed_inputs()
    if sources() != before: raise ValueError('sources changed during preflight')
    return dict(sources=before, installed_inputs=inputs,
                original_raw_freezes_satisfied=actual['original_raw_freezes_satisfied'])


def inventory(model, fly):
    if list(fly.actuated_joints) != list(contract.force.audit.JOINT_NAMES):
        raise ValueError('public ordered action authority mismatch')
    if model.nu != 48 or model.na != 0: raise ValueError('48 stateless native actuators required')
    names = {kind: [compiled_name(model, kind, i) for i in range(int(getattr(model, count)))]
             for kind, count in (('joint', 'njnt'), ('actuator', 'nu'), ('body', 'nbody'), ('sensor', 'nsensor'))}
    def exact(kind, local):
        ids = [i for i, name in enumerate(names[kind]) if namespace_component(name) == local]
        if len(ids) != 1: raise ValueError('unique native identity required: '+local)
        return ids[0]
    rows = []
    for index, joint in enumerate(fly.actuated_joints):
        jid = exact('joint', joint)
        aid = exact('actuator', 'actuator_position_'+joint)
        observed = resolve_dof(model, int(model.jnt_dofadr[jid]))
        if (not observed['resolved'] or observed['joint_id'] != jid or observed['joint_type'] != 'hinge'
                or model.actuator_trntype[aid] != 0 or model.actuator_trnid[aid].tolist() != [jid, -1]
                or names['joint'][jid].rsplit('/', 1)[:-1] != names['actuator'][aid].rsplit('/', 1)[:-1]
                or model.actuator_gaintype[aid] != 0 or model.actuator_biastype[aid] != 1
                or model.actuator_dyntype[aid] != 0 or model.actuator_actadr[aid] != -1
                or model.actuator_actnum[aid] != 0
                or model.actuator_gear[aid].tolist() != [1., 0., 0., 0., 0., 0.]):
            raise ValueError('unsupported exact native position actuator: '+joint)
        rows.append(dict(coordinate=joint, action_index=index, actuator_id=aid,
            actuator_name=names['actuator'][aid], joint_id=jid, joint_name=names['joint'][jid],
            body_id=observed['body_id'], body_name=observed['body_name'],
            qpos_range=observed['qpos_address_range'], dof_range=observed['dof_address_range'],
            activation_address=int(model.actuator_actadr[aid]), activation_count=int(model.actuator_actnum[aid])))
    adhesion = []
    for leg in ('LF', 'LM', 'LH', 'RF', 'RM', 'RH'):
        aid = exact('actuator', leg+'Tarsus5_adhesion')
        bid = exact('body', leg+'Tarsus5')
        if model.actuator_trntype[aid] != 5 or model.actuator_trnid[aid, 0] != bid:
            raise ValueError('exact adhesion body transmission required')
        adhesion.append(dict(actuator_id=aid, actuator_name=names['actuator'][aid], body_id=bid, body_name=names['body'][bid]))
    return dict(rows=rows, adhesion=adhesion, names=names,
        actuators={k: np.asarray(getattr(model, 'actuator_'+k)).tolist() for k in ACT_FIELDS},
        joints={k: np.asarray(getattr(model, 'jnt_'+k)).tolist() for k in ('bodyid', 'type', 'qposadr', 'dofadr', 'axis', 'limited', 'range')},
        sensors={k: np.asarray(getattr(model, 'sensor_'+k)).tolist() for k in ('type', 'objtype', 'objid', 'dim', 'adr')})


def targets(inv):
    return [next(r for r in inv['rows'] if r['coordinate'] == n) for n in contract.force.BASIS]


def validate_inventory(inv, identity):
    """Bind explicit native values to the reused model identity and exact rows."""
    components = identity['components']
    dims, arrays = components['dimensions'], components['model_arrays']
    if (dims['nu'] != 48 or dims['na'] != 0 or inv['nv'] != dims['nv'] or inv['nq'] != dims['nq']
            or len(inv['rows']) != 42 or len(inv['adhesion']) != 6):
        raise ValueError('complete stateless 48-actuator native inventory required')
    for group, prefix in (('actuators', 'actuator_'), ('joints', 'jnt_'), ('sensors', 'sensor_')):
        required = ACT_FIELDS if group == 'actuators' else (
            ('bodyid', 'type', 'qposadr', 'dofadr', 'axis', 'limited', 'range') if group == 'joints'
            else ('type', 'objtype', 'objid', 'dim', 'adr'))
        if set(inv[group]) != set(required): raise ValueError('incomplete explicit native tables')
        for key, values in inv[group].items():
            expected = arrays[prefix+key]
            actual = np.asarray(values, dtype=expected['dtype'])
            if _canonical_array_identity(actual) != expected:
                raise ValueError('native table/hash mismatch: '+prefix+key)
    for kind, names in inv['names'].items():
        if [namespace_component(n) for n in names] != components['inventories'][kind]:
            raise ValueError('native name inventory mismatch')
    for index, (row, joint) in enumerate(zip(inv['rows'], contract.force.audit.JOINT_NAMES)):
        jid, aid, bid = row['joint_id'], row['actuator_id'], row['body_id']
        a, j = inv['actuators'], inv['joints']
        qend = j['qposadr'][jid+1] if jid+1 < dims['njnt'] else dims['nq']
        dend = j['dofadr'][jid+1] if jid+1 < dims['njnt'] else dims['nv']
        if (row['coordinate'] != joint or row['action_index'] != index
                or namespace_component(row['joint_name']) != joint
                or namespace_component(row['actuator_name']) != 'actuator_position_'+joint
                or row['joint_name'] != inv['names']['joint'][jid]
                or row['actuator_name'] != inv['names']['actuator'][aid]
                or row['joint_name'].rsplit('/', 1)[:-1] != row['actuator_name'].rsplit('/', 1)[:-1]
                or row['body_name'] != inv['names']['body'][bid] or j['bodyid'][jid] != bid
                or j['type'][jid] != 3 or a['trntype'][aid] != 0 or a['trnid'][aid] != [jid, -1]
                or a['gaintype'][aid] != 0 or a['biastype'][aid] != 1 or a['dyntype'][aid] != 0
                or a['gear'][aid] != [1., 0., 0., 0., 0., 0.]
                or row['activation_address'] != a['actadr'][aid] or a['actadr'][aid] != -1
                or row['activation_count'] != a['actnum'][aid] or a['actnum'][aid] != 0
                or row['qpos_range'] != [j['qposadr'][jid], qend] or qend-j['qposadr'][jid] != 1
                or row['dof_range'] != [j['dofadr'][jid], dend] or dend-j['dofadr'][jid] != 1):
            raise ValueError('native joint/body/actuator/address association mismatch: '+joint)
    for row, leg in zip(inv['adhesion'], ('LF', 'LM', 'LH', 'RF', 'RM', 'RH')):
        aid, bid = row['actuator_id'], row['body_id']
        if (row['actuator_name'] != inv['names']['actuator'][aid]
                or namespace_component(row['actuator_name']) != leg+'Tarsus5_adhesion'
                or row['body_name'] != inv['names']['body'][bid]
                or namespace_component(row['body_name']) != leg+'Tarsus5'
                or inv['actuators']['trntype'][aid] != 5 or inv['actuators']['trnid'][aid][0] != bid):
            raise ValueError('native adhesion body association mismatch')
    if len({r['actuator_id'] for r in inv['rows']+inv['adhesion']}) != 48:
        raise ValueError('native actuator partition is not unique and complete')
    return True


def probe_inputs(inv, center, name, arm):
    qpos = np.array(center, copy=True)
    # The actual nv is passed in the recorded dimensions, not inferred from IDs.
    qvel = np.zeros(inv['nv'])
    selected = targets(inv)
    if name not in PROBES or arm not in ARMS: raise ValueError('undeclared probe/arm')
    if name.startswith('VELOCITY'):
        sign = 1 if name.endswith('PLUS') else -1
        for r, value in zip(selected, (.1, -.1, .1)): qvel[r['dof_range'][0]] = sign*value
    elif name != 'CENTER':
        axis = ('YAW', 'PITCH', 'ROLL').index(name.split('_')[0])
        qpos[selected[axis]['qpos_range'][0]] += .05 if name.endswith('PLUS') else -.05
    ctrl = np.zeros(48)
    for r in inv['rows']:
        ctrl[r['actuator_id']] = qpos[r['qpos_range'][0]]+(.01 if r['action_index'] % 2 == 0 else -.01)
    if arm == 'CTRL_ZERO_ONLY': ctrl[[r['actuator_id'] for r in selected]] = 0.
    return qpos, qvel, ctrl


def state(data):
    return dict(time=float(data.time), **{k: np.asarray(getattr(data, k)).tolist() for k in STATE})


def observe(native, model, inv, center, probe, arm):
    data = native.MjData(model)
    data.qpos[:], data.qvel[:], data.ctrl[:] = probe_inputs(inv, center, probe, arm)
    before = state(data)
    native.mj_forward(model, data)
    dense, sparse = pose.dense_moments(native, model, data)
    return dict(probe=probe, arm=arm, before=before, after=state(data), sparse_moments=sparse,
        dense_moment_hash=_canonical_array_identity(dense),
        force_support=[np.flatnonzero(row).tolist() for row in dense],
        outputs={k: np.asarray(getattr(data, k)).tolist() for k in ('actuator_force', 'actuator_length',
            'actuator_velocity', 'qfrc_actuator', 'qfrc_passive', 'qfrc_constraint', 'qacc', 'sensordata')})


@contextmanager
def native_accounting(native):
    counts = {phase: dict(mj_forward=0, mj_resetData=0, **{k: 0 for k in INTEGRATORS}) for phase in ('initialization', 'probes')}
    phase = ['initialization']
    originals = {k: getattr(native, k) for k in ('mj_forward', 'mj_resetData', *INTEGRATORS)}
    for key, original in originals.items():
        def call(*args, _key=key, _original=original, **kwargs):
            counts[phase[0]][_key] += 1
            if _key in INTEGRATORS: raise ValueError('integration prohibited: '+_key)
            return _original(*args, **kwargs)
        setattr(native, key, call)
    try: yield counts, phase
    finally:
        for key, original in originals.items(): setattr(native, key, original)


def execute(ready):
    import mujoco as native
    import flygym
    from .tactile_motor_loop_audit import _make_live
    report = dict(schema=SCHEMA, status='INCOMPLETE', ready=ready, cases=[], models={},
        current_motor_count=20, new_admissions=0, neural_transitions=0, body_transitions=0,
        initializer_calls=0, commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip())
    sim, model, saved = None, None, None
    with native_accounting(native) as (counts, phase):
        try:
            report['initializer_calls'] += 1
            sim, physics, *_ = _make_live(flygym, {})
            model, initial = physics.model.ptr, physics.data
            inv = inventory(physics.model, sim.flies[0])
            inv.update(nv=int(model.nv), nq=int(model.nq))
            report['inventory'] = inv
            report['center'] = np.asarray(initial.qpos).tolist()
            report['models']['BASELINE'] = physics_model_identity(physics.model, initial)
            validate_inventory(inv, report['models']['BASELINE'])
            selected = [r['actuator_id'] for r in targets(inv)]
            saved = (model.actuator_gainprm.copy(), model.actuator_biasprm.copy())
            phase[0] = 'probes'
            for arm in ARMS:
                if arm == 'NEUTRALIZED':
                    model.actuator_gainprm[selected] = 0.
                    model.actuator_biasprm[selected] = 0.
                    report['models'][arm] = physics_model_identity(physics.model, initial)
                    report['neutralized_parameters'] = dict(gainprm=model.actuator_gainprm.tolist(), biasprm=model.actuator_biasprm.tolist())
                for probe in PROBES:
                    report['cases'].append(observe(native, model, inv, report['center'], probe, arm))
            report['status'] = 'COMPLETE'
        except Exception as exc:
            report['error'] = f'{type(exc).__name__}: {exc}'
        finally:
            if model is not None and saved is not None:
                model.actuator_gainprm[:], model.actuator_biasprm[:] = saved
                report['models']['RESTORED'] = physics_model_identity(physics.model, initial)
            if sim is not None: sim.close()
            report['api_calls'] = counts
    report['sources_after'] = sources()
    report['installed_inputs_after'] = installed_inputs()
    return report


def evaluate(report, ready):
    checks = dict(schema=report.get('schema') == SCHEMA, complete=report.get('status') == 'COMPLETE',
        ready=report.get('ready') == ready, sources=report.get('sources_after') == ready['sources'],
        installed=report.get('installed_inputs_after') == ready['installed_inputs'],
        scope=all(report.get(k) == v for k, v in dict(current_motor_count=20, new_admissions=0,
            neural_transitions=0, body_transitions=0, initializer_calls=1).items()),
        inventory=[(r.get('arm'), r.get('probe')) for r in report.get('cases', [])] == [(a, p) for a in ARMS for p in PROBES])
    results = []
    try:
        counts = report['api_calls']
        checks['accounting'] = all(counts[p] == dict(mj_forward=f, mj_resetData=r, **{k: 0 for k in INTEGRATORS})
            for p, f, r in (('initialization', 7, 3), ('probes', 27, 0)))
        inv = report['inventory']
        checks['native_identity_tables'] = validate_inventory(inv, report['models']['BASELINE'])
        aids = [r['actuator_id'] for r in targets(inv)]
        dofs = [r['dof_range'][0] for r in targets(inv)]
        retained = [i for i in range(48) if i not in aids]
        outside = [i for i in range(inv['nv']) if i not in dofs]
        base = report['models']['BASELINE']['components']
        changed = report['models']['NEUTRALIZED']['components']
        checks['aggregate_model_identities'] = all(record['sha256'] == contract.force.audit.sha(
            json.dumps(record['components'], sort_keys=True, separators=(',', ':'), allow_nan=False).encode())
            for record in report['models'].values())
        checks['model_restore'] = report['models']['BASELINE'] == report['models']['RESTORED']
        checks['only_model_fields'] = (set(base) == set(changed) and all(base[k] == changed[k] for k in base if k != 'model_arrays')
            and set(base['model_arrays']) == set(changed['model_arrays']) and all(base['model_arrays'][k] == changed['model_arrays'][k]
                for k in base['model_arrays'] if k not in ('actuator_gainprm', 'actuator_biasprm')))
        checks['parameter_rows'] = True
        for key in ('gainprm', 'biasprm'):
            old = np.asarray(inv['actuators'][key])
            new = np.asarray(report['neutralized_parameters'][key])
            checks['parameter_rows'] &= (old.shape == new.shape == (48, 10) and np.isfinite(new).all()
                and np.array_equal(old[retained], new[retained]) and not np.any(new[aids])
                and _canonical_array_identity(old) == base['model_arrays']['actuator_'+key]
                and _canonical_array_identity(new) == changed['model_arrays']['actuator_'+key])
        checks['parameter_rows'] = bool(checks['parameter_rows'])
        matrices = {}
        for row in report['cases']:
            rc = {}
            q, v, u = probe_inputs(inv, report['center'], row['probe'], row['arm'])
            s = row['before']
            rc['state'] = (row['before'] == row['after'] and s['qpos'] == q.tolist() and s['qvel'] == v.tolist()
                and s['ctrl'] == u.tolist() and s['act'] == [] and s['time'] == 0
                and not np.any(s['qfrc_applied']) and not np.any(s['xfrc_applied']))
            ranges = np.asarray(inv['actuators']['ctrlrange'])
            limited = np.asarray(inv['actuators']['ctrllimited'], dtype=bool)
            rc['control_ranges'] = bool(np.all(u[limited] >= ranges[limited, 0]) and np.all(u[limited] <= ranges[limited, 1]))
            moments = pose.saved_sparse_matrix(row['sparse_moments'], 48, inv['nv'])
            matrices[(row['arm'], row['probe'])] = moments
            output = row['outputs']
            rc['finite'] = all(np.isfinite(value).all() for value in output.values()) and np.isfinite(q).all() and np.isfinite(v).all()
            rc['moment_identity'] = (_canonical_array_identity(moments) == row['dense_moment_hash']
                and row['force_support'] == [np.flatnonzero(x).tolist() for x in moments])
            rc['force_projection'] = np.max(np.abs(moments.T@output['actuator_force']-output['qfrc_actuator'])) <= 1e-8
            result = dict(arm=row['arm'], probe=row['probe'], checks={k: bool(v) for k, v in rc.items()})
            results.append(result)
        comparisons = []
        for probe in PROBES:
            rows = {a: next(r for r in report['cases'] if r['arm'] == a and r['probe'] == probe) for a in ARMS}
            b, n, z = [rows[a]['outputs'] for a in ('BASELINE', 'NEUTRALIZED', 'CTRL_ZERO_ONLY')]
            bf, nf = np.asarray(b['actuator_force']), np.asarray(n['actuator_force'])
            delta = np.asarray(n['qfrc_actuator'])-b['qfrc_actuator']
            cc = dict(selected_force_zero=float(np.max(np.abs(nf[aids]))) <= 1e-10,
                target_generalized_zero=float(np.max(np.abs(np.asarray(n['qfrc_actuator'])[dofs]))) <= 1e-10,
                retained_force_equal=float(np.max(np.abs(nf[retained]-bf[retained]))) <= 1e-10,
                outside_force_equal=float(np.max(np.abs(delta[outside]))) <= 1e-10,
                passive_equal=b['qfrc_passive'] == n['qfrc_passive'],
                moment_equal=np.array_equal(matrices[('BASELINE', probe)], matrices[('NEUTRALIZED', probe)]))
            comparisons.append(dict(probe=probe, checks={k: bool(v) for k, v in cc.items()},
                maximum_selected_force=float(np.max(np.abs(nf[aids]))),
                maximum_retained_force_difference=float(np.max(np.abs(nf[retained]-bf[retained]))),
                control_zero_selected_forces=np.asarray(z['actuator_force'])[aids].tolist()))
        checks['nonvacuous_baseline'] = all(any(abs(r['outputs']['actuator_force'][aid]) > 1e-8 for r in report['cases'] if r['arm'] == 'BASELINE') for aid in aids)
        checks['control_zero_comparison_informative'] = any(abs(x) > 1e-8 for r in comparisons for x in r['control_zero_selected_forces'])
        checks['comparisons'] = all(all(r['checks'].values()) for r in comparisons)
    except Exception as exc:
        checks['evaluation_complete'] = False
        checks['error'] = str(exc)
        comparisons = []
    passed = all(v is True for v in checks.values()) and len(results) == 27 and all(all(r['checks'].values()) for r in results)
    return dict(checks=checks, cases=results, comparisons=comparisons, passed=passed,
                classification='NATIVE_ISOLATION_VERIFIED_COUPLING_BLOCKED' if passed else 'NATIVE_ISOLATION_FAILED')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--execute', action='store_true')
    group.add_argument('--preflight', action='store_true')
    group.add_argument('--report', type=Path)
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args(argv)
    if args.execute:
        if args.output_dir is None: parser.error('--execute requires fresh --output-dir')
        args.output_dir.mkdir(parents=True, exist_ok=False)
        try:
            report = execute(preflight())
            report['evaluation'] = evaluate(report, report['ready'])
        except Exception as exc:
            report = dict(schema=SCHEMA, status='ERROR', error=f'{type(exc).__name__}: {exc}')
        with (args.output_dir/'validation.json').open('x', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2, allow_nan=False); stream.write('\n')
        if not report.get('evaluation', {}).get('passed'):
            print('NATIVE ISOLATION FAILED; evidence retained.', report.get('error', report.get('evaluation')))
            return 1
    elif args.report:
        report = json.loads(args.report.read_text(encoding='utf-8'))
        actual = evaluate(report, preflight())
        if not actual['passed'] or actual != report['evaluation']:
            raise ValueError('saved native isolation/source verification failed')
    else:
        preflight(); print('PREFLIGHT VERIFIED: no native model or forward/integration.'); return 0
    print('NATIVE ISOLATION EVIDENCE VERIFIED:', report['evaluation']['classification'])
    print('27 forward-only probes; initialization7+probe27 forwards;3 resets;0 integration or CNS transitions.')
    print('Roadmap: current20/42, new admissions0; selective suppression verified only at declared instantaneous probes.')
    print('Next: separately specified synthetic coupled-state ownership/convergence; physical/neural/raw gates remain.')
    print('Original raw prerequisites:', report['ready']['original_raw_freezes_satisfied'])
    return 0


if __name__ == '__main__': raise SystemExit(main())
