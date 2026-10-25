"""Synthetic constant-coefficient split coupling; no FlyGym/neural transfer."""
import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess

import numpy as np
from scipy.integrate import solve_ivp

from . import lf_native_isolation as upstream
from . import lf_activation_integrator as activation
from . import lf_activation_transient as schedule
from . import lf_force_reference as force
from .six_tibia_physics_diagnostic import resolve_dof

ROOT = force.ROOT
DIRECTORY = 'docs/evidence/lf-synthetic-coupling-v1/'
FIXTURE = 'docs/fixtures/lf-synthetic-coupling-v1.xml'
NATIVE_RECORD = upstream.DIRECTORY+'run/validation.json'
SCHEMA = 'lf-synthetic-coupling-v1'
INERTIA = np.array([1., 2., 3., 4.])
FOREIGN = np.array([.125, 0., 0., 0.])
FOREIGN_TOTAL = np.array([.375, 0., 0., 0.])
REFERENCE = dict(method='DOP853', rtol=1e-11, atol=1e-13, max_step=2.5e-6)


def sources():
    result = upstream.sources()
    for p in (FIXTURE, NATIVE_RECORD, 'docs/LF_SYNTHETIC_COUPLING_V1.md',
              'malecns_backend/embodiment/lf_synthetic_coupling.py'):
        raw = (ROOT/p).read_bytes()
        result[p] = force.audit.sha(raw if p == NATIVE_RECORD else raw.replace(b'\r\n', b'\n'))
    if result[NATIVE_RECORD] != 'ee3ddfe2e9d298d3b3f269ab04c114d7f3a332ebc68ea20c184deb7b1df2a628':
        raise ValueError('accepted native isolation record changed')
    return result


def preflight():
    before = sources()
    native = upstream.load_report(ROOT/NATIVE_RECORD)
    ready = upstream.preflight()
    evaluated = upstream.evaluate(native, ready)
    if not evaluated['passed'] or evaluated != native['evaluation']:
        raise ValueError('native isolation prerequisite failed')
    reference = force.load_reference()
    binding = json.loads((ROOT/schedule.BINDING).read_text(encoding='utf-8'))
    if sources() != before: raise ValueError('sources changed during static preflight')
    return dict(sources=before, reference=reference, binding=binding,
                original_raw_freezes_satisfied=ready['original_raw_freezes_satisfied'])


def foreign_body():
    result = np.zeros((5, 6))
    result[1, 5] = .25
    return result


def projected_torque(ready, a):
    binding = ready['binding']
    tension = -(np.asarray(binding['frozen_gain'])*a+binding['frozen_bias'])
    return np.asarray(ready['reference']['R_G'])@tension


def physical_state(data):
    return dict(time=float(data.time), qpos=data.qpos.tolist(), qvel=data.qvel.tolist(),
                act=data.act.tolist(), generalized=data.qfrc_applied.tolist(), body=data.xfrc_applied.tolist())


class SyntheticSplitAdapter:
    """Only this four-rotor fixture; one body call and external state commit."""
    def __init__(self, native, model, data, ready, initial_activation):
        self.native, self.model, self.data, self.ready = native, model, data, ready
        self.dt = float(model.opt.timestep)
        self._activation = np.array(initial_activation, dtype=float, copy=True)
        self.transitions, self.failed, self.owned = 0, False, None
        self.last_attempt = None
        self.metadata = []
        for name, body in zip(force.BASIS, ('synthetic_yaw', 'synthetic_pitch', 'synthetic_roll')):
            jid = int(model.joint(name).id)
            row = resolve_dof(model, int(model.jnt_dofadr[jid]))
            if (not row['resolved'] or row['joint_name'] != name or row['body_name'] != body
                    or row['joint_type'] != 'hinge' or row['actuators']):
                raise ValueError('exact synthetic joint/body ownership required')
            self.metadata.append(row)
        if ([r['dof_index'] for r in self.metadata] != [1, 2, 3]
                or [r['qpos_address_range'] for r in self.metadata] != [[1, 2], [2, 3], [3, 4]]):
            raise ValueError('synthetic addresses differ from fixture contract')
        self.guard()

    @property
    def activation(self): return self._activation.copy()

    def guard(self):
        m, d = self.model, self.data
        if (self.failed or self.owned is not None or m.nq != 4 or m.nv != 4 or m.nu or m.na
                or m.ngeom or m.neq or m.nbody != 5 or m.ntendon or m.opt.integrator != 0
                or float(m.opt.timestep) != self.dt or self.dt not in schedule.DTS
                or np.any(m.opt.gravity) or np.any(m.dof_damping) or np.any(m.dof_frictionloss)
                or np.any(m.dof_armature) or np.any(m.jnt_stiffness) or np.any(m.body_ipos)
                or not np.array_equal(m.body_inertia[1:], INERTIA[:, None]*np.ones((4, 3)))
                or not np.array_equal(m.body_mass[1:], np.ones(4))
                or not np.array_equal(m.jnt_axis, [[0, 0, 1], [1, 0, 0], [0, 1, 0], [0, 0, 1]])
                or not np.array_equal(m.body_parentid, np.zeros(5))
                or not np.array_equal(m.jnt_bodyid, [1, 2, 3, 4])
                or abs(d.time-self.transitions*self.dt) > 1e-12
                or self._activation.shape != (4,) or not np.isfinite(self._activation).all()
                or not np.array_equal(d.qfrc_applied, FOREIGN) or not np.array_equal(d.xfrc_applied, foreign_body())):
            raise ValueError('synthetic context, ownership, time or foreign force changed')

    def apply(self, torque):
        self.guard()
        if np.asarray(torque).shape != (3,) or not np.isfinite(torque).all():
            raise ValueError('three finite projected torques required')
        expected = FOREIGN.copy()
        expected[1:] = torque
        self.data.qfrc_applied[:] = expected
        self.owned = expected

    def clear(self):
        if (self.owned is None or not np.array_equal(self.data.qfrc_applied, self.owned)
                or not np.array_equal(self.data.xfrc_applied, foreign_body())):
            raise ValueError('owned or foreign buffer was modified')
        self.data.qfrc_applied[1:] = 0.
        self.owned = None

    def advance(self, condition):
        self.guard()
        index, dt = self.transitions, self.dt
        raw = schedule.raw_control(condition, index, dt)
        limits = np.asarray(self.ready['binding']['ctrlrange'])
        effective = np.clip(np.full(4, raw), *limits.T)
        before = self.activation
        row = dict(index=index, before=physical_state(self.data), activation_before=before.tolist(),
                   raw_control=raw, effective_control=effective.tolist(), phase='BEFORE_SOLVE')
        self.last_attempt = row
        try:
            solved = activation.integrate_interval(self.native, before, effective,
                self.ready['binding']['dynprm'], dt, [dt])
            torque = projected_torque(self.ready, before)
            self.apply(torque)
            row.update(torque=torque.tolist(), applied=physical_state(self.data), solver=solved, phase='BEFORE_BODY')
            self.native.mj_step(self.model, self.data)
            row.update(after_body=physical_state(self.data), native_acceleration=self.data.qacc.tolist(), phase='AFTER_BODY')
            self.clear()
            self.native.mj_forward(self.model, self.data)
            self._activation = np.asarray(solved['after']).copy()
            self.transitions += 1
            row.update(after_clear=physical_state(self.data), activation_after=self.activation.tolist(),
                       commit_index=self.transitions, phase='COMMITTED')
            return row
        except Exception as exc:
            self.failed = True
            row.update(error=f'{type(exc).__name__}: {exc}', failure_state=physical_state(self.data),
                       activation_at_failure=self.activation.tolist())
            # Do not roll back body state or pretend that a native step did not run.
            if self.owned is not None:
                try: self.clear()
                except Exception as clear_exc: row['clear_error'] = str(clear_exc)
            raise


def continuous_reference(native, ready, condition):
    binding = ready['binding']
    floor = np.asarray(binding['ctrlrange'])[:, 0]
    initial = np.r_[np.zeros(4) if condition == 'RELAX_ZERO' else floor, np.zeros(8)]
    times = np.arange(401)*schedule.DTS[-1]
    result = np.empty((401, 12))
    segments = []
    for start, end in ((0., .002), (.002, .005), (.005, .01)):
        control = np.ones(4) if condition == 'PULSE' and start == .002 else floor
        def rhs(t, state):
            da = [native.mju_muscleDynamics(float(c), float(a), np.asarray(p[:3]))
                  for c, a, p in zip(control, state[:4], binding['dynprm'])]
            torque = FOREIGN_TOTAL.copy()
            torque[1:] += projected_torque(ready, state[:4])
            return np.r_[da, state[8:], torque/INERTIA]
        solved = solve_ivp(rhs, (start, end), initial, **REFERENCE, dense_output=True)
        segments.append(dict(start=start, end=end, success=bool(solved.success), message=solved.message,
            nfev=int(solved.nfev), times=solved.t.tolist(), states=solved.y.T.tolist()))
        if not solved.success: raise ValueError('continuous synthetic reference failed')
        mask = (times >= start-1e-14)&(times <= end+1e-14)
        result[mask] = solved.sol(times[mask]).T
        initial = solved.y[:, -1]
    return dict(settings=REFERENCE, times=times.tolist(), states=result.tolist(), segments=segments)


@contextmanager
def accounting(native):
    counts = dict(mj_forward=0, mj_step=0, mj_resetData=0,
                  **{k: 0 for k in upstream.INTEGRATORS if k != 'mj_step'})
    originals = {k: getattr(native, k) for k in counts}
    for key, original in originals.items():
        def call(*args, _key=key, _original=original, **kwargs):
            counts[_key] += 1
            if _key not in ('mj_forward', 'mj_step'): raise ValueError('unexpected explicit native operation: '+_key)
            return _original(*args, **kwargs)
        setattr(native, key, call)
    try: yield counts
    finally:
        for key, original in originals.items(): setattr(native, key, original)


def execute(ready):
    import mujoco as native
    report = dict(schema=SCHEMA, status='COMPLETE', ready=ready, cases=[], calibrations=[],
        current_motor_count=20, new_admissions=0, neural_transitions=0, synthetic_only=True,
        activation_settings=activation.SETTINGS, models_constructed=0,
        commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip())
    with accounting(native) as counts:
        try:
            report['references'] = {c: continuous_reference(native, ready, c) for c in schedule.CONDITIONS}
            for dt in schedule.DTS:
                model = native.MjModel.from_xml_path(str(ROOT/FIXTURE))
                report['models_constructed'] += 1
                model.opt.timestep = dt
                check = native.MjData(model)
                native.mj_forward(model, check)
                mass = np.zeros((4, 4))
                native.mj_fullM(model, mass, check.qM)
                report['calibrations'].append(dict(dt=dt, mass=mass.tolist(), nq=int(model.nq), nv=int(model.nv),
                    nu=int(model.nu), na=int(model.na), ngeom=int(model.ngeom)))
                for condition in schedule.CONDITIONS:
                    case = dict(dt=dt, condition=condition, steps=[])
                    report['cases'].append(case)
                    data = native.MjData(model)
                    data.qfrc_applied[:] = FOREIGN
                    data.xfrc_applied[:] = foreign_body()
                    native.mj_forward(model, data)
                    a0 = np.zeros(4) if condition == 'RELAX_ZERO' else np.asarray(ready['binding']['ctrlrange'])[:, 0]
                    adapter = SyntheticSplitAdapter(native, model, data, ready, a0)
                    case.update(initial=physical_state(data), activation_initial=a0.tolist(), metadata=adapter.metadata)
                    try:
                        for _ in range(round(schedule.DURATION/dt)): case['steps'].append(adapter.advance(condition))
                    except Exception as exc:
                        case.update(error=str(exc), last_attempt=adapter.last_attempt)
                        report['status'] = 'INCOMPLETE'
        except Exception as exc:
            report.update(status='INCOMPLETE', error=f'{type(exc).__name__}: {exc}')
        report['api_calls'] = counts
    report['sources_after'] = sources()
    return report


def evaluate(report, ready):
    checks = dict(schema=report.get('schema') == SCHEMA, complete=report.get('status') == 'COMPLETE',
        ready=report.get('ready') == ready, sources=report.get('sources_after') == ready['sources'],
        activation_settings=report.get('activation_settings') == activation.SETTINGS,
        models_constructed=report.get('models_constructed') == 3,
        scope=all(report.get(k) == v for k, v in dict(current_motor_count=20, new_admissions=0,
            neural_transitions=0, synthetic_only=True).items()),
        inventory=[(c.get('dt'), c.get('condition')) for c in report.get('cases', [])] ==
            [(dt, c) for dt in schedule.DTS for c in schedule.CONDITIONS],
        api_calls=report.get('api_calls') == dict(mj_forward=2112, mj_step=2100, mj_resetData=0,
            **{k: 0 for k in upstream.INTEGRATORS if k != 'mj_step'}))
    results, refinement = [], []
    try:
        checks['mass_calibration'] = len(report['calibrations']) == 3 and all(
            r['dt'] == dt and np.array_equal(r['mass'], np.diag(INERTIA))
            and all(r[k] == v for k, v in dict(nq=4, nv=4, nu=0, na=0, ngeom=0).items())
            for r, dt in zip(report['calibrations'], schedule.DTS))
        checks['reference_inventory'] = set(report['references']) == set(schedule.CONDITIONS)
        for condition, ref in report['references'].items():
            rc = (ref['settings'] == REFERENCE and np.array_equal(ref['times'], np.arange(401)*schedule.DTS[-1])
                and np.asarray(ref['states']).shape == (401, 12) and np.isfinite(ref['states']).all()
                and [(s['start'], s['end']) for s in ref['segments']] == [(0., .002), (.002, .005), (.005, .01)])
            for segment in ref['segments']:
                t, y = np.asarray(segment['times']), np.asarray(segment['states'])
                rc = rc and segment['success'] is True and segment['nfev'] > 0 and t[0] == segment['start'] and t[-1] == segment['end']
                rc = rc and y.shape == (len(t), 12) and np.isfinite(y).all() and np.all(np.diff(t) > 0)
            checks['reference_'+condition] = bool(rc)
        for case in report['cases']:
            result = dict(dt=case['dt'], condition=case['condition'], checks={})
            results.append(result)
            try:
                dt, condition, rows = case['dt'], case['condition'], case['steps']
                count, stride = round(schedule.DURATION/dt), round(dt/schedule.DTS[-1])
                if case.get('error') or len(rows) != count: raise ValueError('incomplete native trajectory')
                a0 = np.zeros(4) if condition == 'RELAX_ZERO' else np.asarray(ready['binding']['ctrlrange'])[:, 0]
                expected_initial = dict(time=0., qpos=[0.]*4, qvel=[0.]*4, act=[],
                    generalized=FOREIGN.tolist(), body=foreign_body().tolist())
                rc = result['checks']
                rc['initial'] = case['initial'] == expected_initial and case['activation_initial'] == a0.tolist()
                meta = case['metadata']
                rc['metadata'] = len(meta) == 3 and all(r['resolved'] and r['joint_name'] == name
                    and r['body_name'] == body and r['joint_type'] == 'hinge' and r['joint_id'] == i
                    and r['body_id'] == i+1 and r['dof_index'] == i and r['dof_address_range'] == [i, i+1]
                    and r['qpos_address_range'] == [i, i+1] and r['actuators'] == []
                    for i, (r, name, body) in enumerate(zip(meta, force.BASIS,
                        ('synthetic_yaw', 'synthetic_pitch', 'synthetic_roll')), start=1))
                a = np.vstack((a0, [r['activation_after'] for r in rows]))
                q = np.vstack((np.zeros(4), [r['after_clear']['qpos'] for r in rows]))
                v = np.vstack((np.zeros(4), [r['after_clear']['qvel'] for r in rows]))
                nodes = np.vstack([r['solver']['solver']['activations'] for r in rows])
                rc['finite'] = all(np.isfinite(x).all() for x in (a, q, v, nodes))
                rc['transitions'] = True
                rc['force_ownership'] = True
                rc['native_euler'] = True
                rc['solver'] = True
                previous = case['initial']
                for i, row in enumerate(rows):
                    before, applied, after_body, cleared = [row[k] for k in ('before', 'applied', 'after_body', 'after_clear')]
                    raw = schedule.raw_control(condition, i, dt)
                    effective = np.clip(np.full(4, raw), *np.asarray(ready['binding']['ctrlrange']).T)
                    rc['transitions'] &= (row['index'] == i and row['commit_index'] == i+1 and row['phase'] == 'COMMITTED'
                        and before == previous and row['activation_before'] == a[i].tolist()
                        and row['raw_control'] == raw and row['effective_control'] == effective.tolist()
                        and abs(before['time']-i*dt) <= 1e-12 and abs(cleared['time']-(i+1)*dt) <= 1e-12
                        and all(s['act'] == [] for s in (before, applied, after_body, cleared)))
                    torque = projected_torque(ready, a[i])
                    expected = FOREIGN.copy(); expected[1:] = torque
                    rc['force_ownership'] &= (np.array_equal(row['torque'], torque)
                        and before['generalized'] == cleared['generalized'] == FOREIGN.tolist()
                        and applied['generalized'] == after_body['generalized'] == expected.tolist()
                        and all(s['body'] == foreign_body().tolist() for s in (before, applied, after_body, cleared))
                        and all(applied[k] == before[k] and cleared[k] == after_body[k] for k in ('qpos', 'qvel', 'time')))
                    total = FOREIGN_TOTAL.copy(); total[1:] += torque
                    acceleration = total/INERTIA
                    expected_v = v[i]+dt*acceleration
                    expected_q = q[i]+dt*expected_v
                    rc['native_euler'] &= (np.max(np.abs(np.asarray(row['native_acceleration'])*INERTIA-total)) <= 1e-9
                        and np.max(np.abs(v[i+1]-expected_v)) <= 1e-9 and np.max(np.abs(q[i+1]-expected_q)) <= 1e-9)
                    solved = row['solver']; internal = solved['solver']
                    t = np.asarray(internal['times']); y = np.asarray(internal['activations'])
                    rc['solver'] &= (solved['after'] == a[i+1].tolist() and solved['samples'] == [a[i+1].tolist()]
                        and solved['sample_offsets'] == [dt] and internal['success'] is True and internal['status'] == 0
                        and t[0] == 0 and t[-1] == dt and len(t) == len(y) and np.all(np.diff(t) > 0)
                        and np.array_equal(y[0], a[i]) and np.array_equal(y[-1], a[i+1])
                        and all(internal[k] > 0 for k in ('nfev', 'njev', 'nlu')))
                    previous = cleared
                ref = np.asarray(report['references'][condition]['states'])[::stride]
                if ref.shape != (count+1, 12): raise ValueError('reference sampling mismatch')
                ae = float(np.max(np.abs(a-ref[:, :4])))
                qe = float(np.max(np.abs(q-ref[:, 4:8])))
                ve = float(np.max(np.abs(v-ref[:, 8:])))
                minimum, maximum = float(min(a.min(), nodes.min())), float(max(a.max(), nodes.max()))
                result.update(maximum_activation_error=ae, maximum_position_error=qe, maximum_velocity_error=ve,
                    endpoint_position_error=float(np.max(np.abs(q[-1]-ref[-1, 4:8]))),
                    endpoint_velocity_error=float(np.max(np.abs(v[-1]-ref[-1, 8:]))),
                    minimum_activation=minimum, maximum_activation=maximum, normalized_error=max(qe/1e-5, ve/1e-3),
                    numerical_checks=dict(activation=ae <= .01 and minimum >= -1e-12 and maximum <= 1+1e-12,
                                          position=qe <= 1e-5, velocity=ve <= 1e-3))
                result['numerical_acceptance'] = all(result['numerical_checks'].values())
            except Exception as exc:
                result['checks']['complete'] = False
                result.update(error=str(exc), numerical_acceptance=False)
            result['checks'] = {k: bool(v) for k, v in result['checks'].items()}
            result['integrity_passed'] = bool(result['checks']) and all(result['checks'].values())
        for dt in schedule.DTS:
            baseline, pulse = [next(c for c in report['cases'] if c['dt'] == dt and c['condition'] == name)
                               for name in ('FLOOR_BASELINE', 'PULSE')]
            end = round(.002/dt)
            checks['matched_prefix_'+str(dt)] = baseline['initial'] == pulse['initial'] and all(
                b['after_clear'] == p['after_clear'] and b['activation_after'] == p['activation_after']
                for b, p in zip(baseline['steps'][:end], pulse['steps'][:end]))
        pulse = [next(r for r in results if r['dt'] == dt and r['condition'] == 'PULSE') for dt in schedule.DTS]
        refinement = [dict(coarse=coarse['dt'], fine=fine['dt'], coarse_error=coarse['normalized_error'],
            fine_error=fine['normalized_error'], passed=fine['normalized_error'] <= .75*coarse['normalized_error']+1e-12)
            for coarse, fine in zip(pulse, pulse[1:])]
    except Exception as exc:
        checks['evaluation_complete'] = False; checks['error'] = str(exc)
    integrity = all(v is True for v in checks.values()) and len(results) == 9 and all(r['integrity_passed'] for r in results)
    numerical = len(results) == 9 and all(r['numerical_acceptance'] for r in results)
    convergence = len(refinement) == 2 and all(r['passed'] for r in refinement)
    return dict(checks=checks, cases=results, refinement=refinement, integrity_passed=integrity,
        numerical_accepted=numerical, refinement_accepted=convergence,
        classification='SYNTHETIC_COUPLING_VERIFIED_TRANSFER_BLOCKED' if integrity and numerical and convergence
            else 'NUMERICAL_LIMITS_OBSERVED' if integrity else 'INTEGRITY_FAILURE')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--execute', action='store_true')
    group.add_argument('--preflight', action='store_true')
    group.add_argument('--report', type=Path)
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args(argv)
    if args.execute:
        if args.output_dir is None: parser.error('--execute requires a new --output-dir')
        args.output_dir.mkdir(parents=True, exist_ok=False)
        try:
            report = execute(preflight())
            report['evaluation'] = evaluate(report, report['ready'])
        except Exception as exc:
            report = dict(schema=SCHEMA, status='ERROR', error=f'{type(exc).__name__}: {exc}')
        text = json.dumps(upstream.encode_nonfinite(report), indent=2, allow_nan=False)+'\n'
        with (args.output_dir/'validation.json').open('x', encoding='utf-8') as stream: stream.write(text)
        if not report.get('evaluation', {}).get('integrity_passed'):
            print('SYNTHETIC INTEGRITY FAILED; evidence retained.', report.get('error', report.get('evaluation')))
            return 1
    elif args.report:
        report = upstream.load_report(args.report)
        actual = evaluate(report, preflight())
        if not actual['integrity_passed'] or actual != report['evaluation']:
            raise ValueError('saved synthetic coupling/source verification failed')
    else:
        preflight(); print('PREFLIGHT VERIFIED: no native model, stepping or reference integration.'); return 0
    print('SYNTHETIC COUPLING EVIDENCE VERIFIED:', report['evaluation']['classification'])
    for r in report['evaluation']['cases']:
        print(f"{r['dt']*1e6:g}us {r['condition']}: {'PASS' if r['numerical_acceptance'] else 'FAIL'}; q error{r['maximum_position_error']:.8g}, v error{r['maximum_velocity_error']:.8g}")
    print('Roadmap: production20/42, new admissions0; synthetic body steps2100, CNS0; no FlyGym force transfer.')
    print('Next: physical-unit/geometry/velocity/length transfer prerequisite review; biological/raw/neural gates remain.')
    print('Original raw prerequisites:', report['ready']['original_raw_freezes_satisfied'])
    return 0


if __name__ == '__main__': raise SystemExit(main())
