"""Fixed passive attribution audit in the unchanged supported live-v3 session."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import time

import numpy as np

from .contact_readiness import LEGS, THRESHOLD
from ..embodiment import m8_contact_kinematics as identities
from ..embodiment import six_foot_contact_calibration as batch

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'live-contact-context-v1'
STEPS = 20000
DT = .0001
RTOL, ATOL = 1e-10, 1e-14
PROTOCOL = dict(schema=SCHEMA, physics_steps=STEPS, physics_dt_s=DT,
                duration_s=2., neural_seed=1, engineering_threshold=THRESHOLD,
                reconstruction_rtol=RTOL, reconstruction_atol=ATOL,
                tactile_delivery_enabled=False, automatic_retries=0,
                runtime='create_live_v3_session + unchanged adapter._runtime')
MODEL_FIELDS = (
    'geom_bodyid', 'geom_type', 'geom_pos', 'geom_quat', 'geom_size',
    'geom_contype', 'geom_conaffinity', 'geom_friction', 'geom_solref', 'geom_solimp',
    'geom_margin', 'geom_gap', 'pair_geom1', 'pair_geom2', 'pair_friction',
    'pair_solref', 'pair_solimp', 'pair_margin', 'pair_gap',
    'body_pos', 'body_quat', 'body_mass', 'body_inertia', 'jnt_type', 'jnt_range',
    'dof_damping', 'actuator_gainprm', 'actuator_biasprm', 'actuator_ctrlrange',
    'eq_type', 'eq_obj1id', 'eq_obj2id', 'eq_data',
)
SOURCE_PATHS = (
    'docs/LIVE_CONTACT_CONTEXT_V1.md', 'malecns_backend/live/contact_context.py',
    'malecns_backend/live/headless.py', 'malecns_backend/neural.py',
    'malecns_backend/embodiment/_windows_m8_live_condition.py',
    'malecns_backend/embodiment/_windows_m7d_corrected_spontaneous_adapter.py',
    'malecns_backend/embodiment/m7c_b4_stability.py',
    'malecns_backend/embodiment/tactile_contact.py',
    'malecns_backend/embodiment/live_v3_motor_interface.py',
)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def source_hashes():
    return {p: hashlib.sha256((ROOT / p).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
            for p in SOURCE_PATHS}


def prerequisite():
    """Recheck the actual archived isolated calibration; never refresh its locks."""
    from ..embodiment import six_foot_contact_calibration_v2 as isolated
    folder = ROOT / 'docs/evidence'
    checkpoint = json.loads((folder / 'six-foot-contact-v2-checkpoint.json').read_text())
    run = next(r for r in checkpoint['runs'] if r['schema'] == 'six-foot-contact-calibration-v2.1')
    packed = (folder / run['raw_artifact']).read_bytes()
    raw = gzip.decompress(packed)
    if (hashlib.sha256(packed).hexdigest() != run['gzip_sha256']
            or hashlib.sha256(raw).hexdigest() != run['raw_json_sha256']):
        raise RuntimeError('isolated calibration evidence hash mismatch')
    report = json.loads(raw)
    if (report['all_six_accepted'] is not True or report['accepted_legs'] != list(LEGS)
            or not all(isolated.evaluate_leg(report['legs'][l]['evidence'], l)['accepted'] for l in LEGS)):
        raise RuntimeError('isolated calibration prerequisite rejected')
    for name, expected in report['source_sha256_lf'].items():
        path = ROOT / ('docs' if name.endswith('.md') else 'malecns_backend/embodiment') / name
        if hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest() != expected:
            raise RuntimeError(f'isolated calibration source mismatch: {name}')
    return dict(verified=True, schema=report['schema'], raw_sha256=run['raw_json_sha256'],
                gzip_sha256=run['gzip_sha256'], accepted_legs=report['accepted_legs'])


def configuration(model):
    """Record the support/contact/dynamics settings guarded at every sample."""
    return dict(arrays={name: np.asarray(getattr(model, name)).tolist() for name in MODEL_FIELDS},
                gravity=np.asarray(model.opt.gravity).tolist(), timestep=float(model.opt.timestep),
                disableflags=int(model.opt.disableflags), enableflags=int(model.opt.enableflags),
                integrator=int(model.opt.integrator), solver=int(model.opt.solver),
                iterations=int(model.opt.iterations), tolerance=float(model.opt.tolerance))


def resolve(sim, physics):
    model = physics.model
    authority = identities.resolve(model)
    bodies = [identities.compiled_name(model, 'body', i) for i in range(int(model.nbody))]
    geoms = [identities.compiled_name(model, 'geom', i) for i in range(int(model.ngeom))]
    placements = list(sim.fly.contact_sensor_placements)
    placement_ids = []
    for name in placements:
        candidates = [i for i, n in enumerate(bodies) if n == name]
        if len(candidates) != 1:
            raise ValueError('ambiguous actual sensor placement body')
        placement_ids.append(candidates[0])
    return dict(body_names=bodies, geom_names=geoms,
                geom_bodyid=np.asarray(model.geom_bodyid).astype(int).tolist(),
                sensor_placement_names=placements, sensor_body_ids=placement_ids,
                tarsus5_body_ids=authority['tarsus5_body_ids'],
                ground_geom_ids=list(authority['ground_geom_ids']))


def validate_identity(table):
    bodies, geoms, owners = table['body_names'], table['geom_names'], table['geom_bodyid']
    if len(geoms) != len(owners) or len(table['sensor_body_ids']) != 36:
        raise ValueError('invalid model/sensor identity table shape')
    if any(type(i) is not int or not 0 <= i < len(bodies) for i in owners):
        raise ValueError('invalid geometry body ownership')
    expected_sensors = [f'{leg}{seg}' for leg in LEGS for seg in
                        ('Tibia', 'Tarsus1', 'Tarsus2', 'Tarsus3', 'Tarsus4', 'Tarsus5')]
    for row, expected in enumerate(expected_sensors):
        bid = table['sensor_body_ids'][row]
        if (type(bid) is not int or not 0 < bid < len(bodies)
                or bodies[bid] != table['sensor_placement_names'][row]
                or identities.namespace_component(bodies[bid]) != expected
                or sum(identities.namespace_component(n) == expected for n in bodies) != 1):
            raise ValueError('exact actual force-row body identity mismatch')
    ground = table['ground_geom_ids']
    expected_ground = {'ground', batch.single.SURFACE_NAME}
    if (len(ground) != 2 or len(set(ground)) != 2
            or any(type(i) is not int or not 0 <= i < len(geoms) for i in ground)
            or {identities.namespace_component(geoms[i]) for i in ground} != expected_ground
            or any(owners[i] != 0 for i in ground)
            or sum(identities.namespace_component(n) in expected_ground for n in geoms) != 2):
        raise ValueError('support must be the two exact unique static world geometries')
    for position, leg in enumerate(LEGS):
        bid = table['tarsus5_body_ids'][leg]
        selected = [i for i, n in enumerate(geoms) if identities.namespace_component(n) == f'{leg}Tarsus5']
        if (bid != table['sensor_body_ids'][position * 6 + 5] or len(selected) != 1
                or owners[selected[0]] != bid):
            raise ValueError('exact distal geometry/body mismatch')


def summarize_sample(sample, table):
    """Replay numerical attribution solely from recorded identities and contacts."""
    owners, names = table['geom_bodyid'], table['geom_names']
    ground = set(table['ground_geom_ids'])
    totals = {l: np.zeros(3) for l in LEGS}
    support = {l: np.zeros(3) for l in LEGS}
    pair_counts = {l: [0, 0] for l in LEGS}  # exact support, unselected direct contacts
    by_body = {table['tarsus5_body_ids'][l]: l for l in LEGS}
    by_surface = {l: {str(i): np.zeros(3) for i in ground} for l in LEGS}
    for pair in sample['contacts']:
        a, b = pair['geom1_id'], pair['geom2_id']
        if (type(a) is not int or type(b) is not int or a == b
                or not 0 <= a < len(owners) or not 0 <= b < len(owners)
                or names[a] != pair['geom1_name'] or names[b] != pair['geom2_name']):
            raise ValueError('invalid exact contact identities')
        frame = np.asarray(pair['frame'], dtype=float).reshape(3, 3)
        wrench = np.asarray(pair['local_force_torque'], dtype=float)
        if (wrench.shape != (6,) or not np.isfinite(wrench).all() or not np.isfinite(frame).all()
                or not np.allclose(frame @ frame.T, np.eye(3), rtol=RTOL, atol=ATOL)
                or not math.isclose(float(np.linalg.det(frame)), 1., rel_tol=RTOL, abs_tol=ATOL)):
            raise ValueError('invalid contact frame/wrench')
        world = frame.T @ wrench[:3] if pair['efc_address'] >= 0 else np.zeros(3)
        for geom, other, sign in ((a, b, -1), (b, a, 1)):
            leg = by_body.get(owners[geom])
            if leg is None:
                continue
            selected = identities.namespace_component(names[geom]) == f'{leg}Tarsus5' and other in ground
            pair_counts[leg][0 if selected else 1] += 1
            totals[leg] += sign * world
            if selected:
                support[leg] += sign * world
                by_surface[leg][str(other)] += sign * world
    result = {}
    raw, telemetry = np.asarray(sample['body_forces'], dtype=float), np.asarray(sample['telemetry_forces'], dtype=float)
    if raw.shape != (6, 3) or telemetry.shape != (6, 3) or not np.isfinite(raw).all() or not np.isfinite(telemetry).all():
        raise ValueError('invalid distal force vectors')
    for i, leg in enumerate(LEGS):
        positive, other = pair_counts[leg]
        force = float(np.linalg.norm(telemetry[i]))
        result[leg] = dict(support_pairs=positive, unselected_pairs=other,
            force_magnitude=force, reconstructed_total=totals[leg].tolist(),
            reconstructed_support=support[leg].tolist(),
            reconstructed_by_surface={k: v.tolist() for k, v in by_surface[leg].items()},
            reconstruction_matches=bool(np.allclose(totals[leg], raw[i], rtol=RTOL, atol=ATOL)),
            telemetry_matches=bool(np.array_equal(raw[i].astype(np.float32).astype(float), telemetry[i])),
            correspondence=(bool(positive) == (force > THRESHOLD)))
    return result


class PassiveRecorder:
    """Reads physics only. Never sees brain, encoders, RNGs or motor decoders."""
    def __init__(self):
        self.context = None
        self.samples = []

    def bind(self, sim, physics, obs):
        from ..embodiment.candidate_motor_channel_experiment import physics_model_identity
        from ..embodiment import m7c_b4_stability as b4
        table = resolve(sim, physics)
        validate_identity(table)
        config = configuration(physics.model)
        self.context = dict(identity=table, configuration=config, configuration_sha256=digest(config),
            physics_model_identity=physics_model_identity(physics.model, physics.data),
            inherited_surface_unchanged=b4._calibration_unchanged(sim, np, __import__('mujoco'), b4._surface()),
            adhesion_enabled=bool(sim.fly.enable_adhesion))
        self.capture(physics, obs, None)

    def capture(self, physics, obs, action):
        import mujoco
        model, data = physics.model, physics.data
        table = self.context['identity']
        def guard():
            h = hashlib.sha256()
            for value in (data.qpos, data.qvel, data.qacc, data.ctrl, data.cfrc_ext,
                          data.xfrc_applied, data.qfrc_applied, data.efc_force, obs['contact_forces']):
                h.update(np.asarray(value).tobytes())
            h.update(str(float(data.time)).encode())
            if action is not None:
                h.update(np.asarray(action['joints']).tobytes())
                h.update(np.asarray(action['adhesion']).tobytes())
            return h.hexdigest()
        before = guard()
        contacts = []
        for i, pair in enumerate(batch.single._pairs(physics)):
            contact = data.contact[i]
            wrench = np.zeros(6)
            mujoco.mj_contactForce(getattr(model, 'ptr', model), getattr(data, 'ptr', data), i, wrench)
            contacts.append(dict(geom1_id=pair.geom1_id, geom1_name=pair.geom1_name,
                                 geom2_id=pair.geom2_id, geom2_name=pair.geom2_name,
                                 frame=np.asarray(contact.frame).tolist(), efc_address=int(contact.efc_address),
                                 local_force_torque=wrench.tolist()))
        bids = [table['tarsus5_body_ids'][l] for l in LEGS]
        forces = np.asarray(obs['contact_forces'], dtype=float)
        if forces.shape != (36, 3):
            raise ValueError('invalid actual force telemetry shape')
        record = dict(time_s=float(data.time), contacts=contacts,
            body_forces=np.asarray(data.cfrc_ext)[bids, 3:].tolist(),
            telemetry_forces=forces[[i * 6 + 5 for i in range(6)]].tolist(),
            qpos=np.asarray(data.qpos).tolist(), qvel=np.asarray(data.qvel).tolist(),
            commanded_joints=None if action is None else np.asarray(action['joints']).tolist(),
            adhesion=None if action is None else np.asarray(action['adhesion']).tolist(),
            external_applied_max=float(np.max(np.abs(data.xfrc_applied))),
            generalized_applied_max=float(np.max(np.abs(data.qfrc_applied))),
            configuration_sha256=digest(configuration(model)), observer_state_before_sha256=before)
        record['observer_state_after_sha256'] = guard()
        self.samples.append(record)


class ObservedSimulation:
    def __init__(self, sim, physics, recorder):
        self.sim, self.physics, self.recorder = sim, physics, recorder

    def __getattr__(self, name):
        return getattr(self.sim, name)

    def step(self, action):
        result = self.sim.step(action)
        self.recorder.capture(self.physics, result[0], action)
        return result


def evaluate(report):
    checks = dict(fixed_protocol=report.get('protocol') == PROTOCOL,
                  completed=report.get('run_status') == 'COMPLETE',
                  prerequisite=report.get('prerequisite', {}).get('verified') is True,
                  source_integrity=report.get('sources_before') == report.get('sources_after')
                                   and bool(report.get('sources_before')))
    rows = {l: dict(positive_samples=0, negative_samples=0, ambiguous_samples=0,
                   force_disagreements=0, reconstruction_disagreements=0, telemetry_disagreements=0,
                   ground_positive_samples=0, calibration_surface_positive_samples=0) for l in LEGS}
    try:
        context, samples = report['context'], report['samples']
        table = context['identity']
        validate_identity(table)
        checks['exact_identity'] = True
        config = context['configuration']
        expected_digest = digest(config)
        checks['supported_context'] = (context['inherited_surface_unchanged'] is True
            and context['adhesion_enabled'] is False and config['timestep'] == DT
            and bool(config['arrays']['pair_geom1'])
            and all(t not in (0, 1, 4) for t in config['arrays']['eq_type']))
        checks['complete_fixed_schedule'] = (len(samples) == STEPS + 1 and all(
            math.isclose(s['time_s'], i * DT, rel_tol=0, abs_tol=1e-10) for i, s in enumerate(samples)))
        checks['immutable_context'] = context['configuration_sha256'] == expected_digest and all(
            s['configuration_sha256'] == expected_digest for s in samples)
        checks['passive_observer'] = bool(samples) and all(
            s['observer_state_before_sha256'] == s['observer_state_after_sha256'] for s in samples)
        checks['no_external_forcing'] = bool(samples) and all(
            s['external_applied_max'] == 0 and s['generalized_applied_max'] == 0 for s in samples)
        checks['finite_physics_and_zero_adhesion'] = bool(samples) and all(
            bool(s['qpos']) and bool(s['qvel']) and np.isfinite(s['qpos']).all() and np.isfinite(s['qvel']).all()
            and (i == 0 and s['commanded_joints'] is None and s['adhesion'] is None or
                 i > 0 and np.asarray(s['commanded_joints']).shape == (42,)
                 and np.isfinite(s['commanded_joints']).all() and s['adhesion'] == [0.] * 6)
            for i, s in enumerate(samples))
        for sample in samples:
            values = summarize_sample(sample, table)
            for leg, v in values.items():
                r = rows[leg]
                r['positive_samples'] += bool(v['support_pairs']) and not v['unselected_pairs'] and v['force_magnitude'] > THRESHOLD
                r['negative_samples'] += not v['support_pairs'] and not v['unselected_pairs'] and v['force_magnitude'] <= THRESHOLD
                r['ambiguous_samples'] += bool(v['unselected_pairs'])
                r['force_disagreements'] += not v['correspondence']
                r['reconstruction_disagreements'] += not v['reconstruction_matches']
                r['telemetry_disagreements'] += not v['telemetry_matches']
                for gid in table['ground_geom_ids']:
                    name = identities.namespace_component(table['geom_names'][gid])
                    label = 'ground_positive_samples' if name == 'ground' else 'calibration_surface_positive_samples'
                    r[label] += int(np.linalg.norm(v['reconstructed_by_surface'][str(gid)]) > THRESHOLD)
    except (KeyError, IndexError, TypeError, ValueError, OverflowError) as exc:
        checks['valid_evidence'] = False
        return dict(accepted=False, status='INVALID_OR_INCOMPLETE', checks=checks, legs=rows, reason=str(exc))
    accepted = []
    for leg, row in rows.items():
        good = all(checks.values()) and not any(row[k] for k in (
            'ambiguous_samples', 'force_disagreements', 'reconstruction_disagreements', 'telemetry_disagreements'))
        coverage = row['positive_samples'] > 0 and row['negative_samples'] > 0
        row.update(accepted=bool(good and coverage), status='OBSERVATIONAL_CONTEXT_ACCEPTED' if good and coverage
                   else 'INCONCLUSIVE_COVERAGE' if good else 'REJECTED')
        if row['accepted']:
            accepted.append(leg)
    return dict(accepted=len(accepted) == 6, accepted_legs=accepted, checks=checks, legs=rows,
                status='OBSERVATIONAL_CONTEXT_ACCEPTED' if len(accepted) == 6 else 'NOT_ADMITTED')


def build_report(*, live=False, progress=print):
    recorder = PassiveRecorder()
    report = dict(schema=SCHEMA, protocol=PROTOCOL.copy(), run_status='NOT_RUN',
                  context=None, samples=recorder.samples, sources_before=source_hashes())
    session = None
    try:
        report['prerequisite'] = prerequisite()
        if live:
            from .headless import create_live_v3_session
            from ..embodiment import _windows_m7d_corrected_spontaneous_adapter as adapter
            adapter._environment()
            def runtime(flygym, interfaces):
                sim, physics, obs, tid, sid = adapter._runtime(flygym, interfaces)
                try:
                    recorder.bind(sim, physics, obs)
                except BaseException:
                    sim.close()
                    raise
                return ObservedSimulation(sim, physics, recorder), physics, obs, tid, sid
            report['environment'] = {p: importlib.metadata.version(p) for p in ('flygym', 'mujoco', 'numpy')}
            session = create_live_v3_session(runtime_factory=runtime)
            progress('Initializing unchanged live-v3 CNS and supported body; no tactile delivery.')
            state = session.initialize()
            if state.time_ms != 0.:
                raise RuntimeError('unexpected live initialization time')
            last = time.monotonic()
            for step in range(1, STEPS + 1):
                state = session.step(lightweight=True)
                if state.physics_transitions != step or state.neural_transitions != step // 5:
                    raise RuntimeError('unexpected authoritative transition counters')
                if time.monotonic() - last >= 15:
                    progress(f'Observed {step}/{STEPS} physics states after reset.')
                    last = time.monotonic()
            report['run_status'] = 'COMPLETE'
    except (Exception, KeyboardInterrupt) as exc:
        report.update(run_status='ERROR', error=f'{type(exc).__name__}: {exc}')
    finally:
        if session is not None:
            try:
                session.close()
            except Exception as exc:
                report.update(run_status='ERROR', close_error=f'{type(exc).__name__}: {exc}')
        report['context'] = recorder.context
        report['sources_after'] = source_hashes()
    invalid = []
    safe = batch.finite_evidence(report, invalid=invalid)
    safe['nonfinite_measurement_paths'] = invalid
    safe['evaluation'] = evaluate(safe)
    if invalid:
        safe['evaluation'].update(accepted=False, accepted_legs=[], status='INVALID_NONFINITE_EVIDENCE')
        for row in safe['evaluation'].get('legs', {}).values():
            row.update(accepted=False, status='INVALID_NONFINITE_EVIDENCE')
    safe['interpretation'] = 'Passive sampled-context attribution only; no causal intervention, sensory admission, biological validation, balance or gait claim.'
    return safe


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('xb') as stream:  # reserve before initialization
        report = build_report(live=args.live, progress=lambda m: print(m, flush=True))
        with gzip.GzipFile(filename='', mode='wb', fileobj=stream, mtime=0) as archive:
            archive.write(json.dumps(report, allow_nan=False, separators=(',', ':')).encode())
    print(f"Saved {args.output}; status={report['evaluation']['status']}", flush=True)
    return 0 if report['evaluation']['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
