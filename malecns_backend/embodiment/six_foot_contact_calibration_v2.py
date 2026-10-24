"""Separately versioned collision-isolation assay; see docs/SIX_FOOT_NEGATIVE_CONTROL_V2.md."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import math
from pathlib import Path

import numpy as np

from . import six_foot_contact_calibration as v1

single = v1.single
SCHEMA = 'six-foot-contact-calibration-v2.1'
REMOTE_POSITION = (1000000., 0., 0.)
PROTOCOL = {
    'schema': SCHEMA, 'duration_s': v1.DURATION_S, 'timestep_s': v1.TIMESTEP_S,
    'seed': 0, 'engineering_threshold': single.ENGINEERING_THRESHOLD,
    'leg_order': list(v1.LEGS), 'conditions': ['control', 'contact'],
    'negative_surface_position': list(REMOTE_POSITION), 'automatic_retries': 0,
    'male_cns_used': False, 'tactile_delivery_enabled': False,
    'collision_context': 'isolated selected Tarsus5 and surface only; no explicit pairs',
}


def collision_masks(count, tarsus, surface, contact):
    if not (0 <= tarsus < count and 0 <= surface < count and tarsus != surface):
        raise ValueError('distinct exact geometry IDs required')
    masks = np.zeros((count, 2), dtype=int)
    masks[tarsus] = (1, 2)
    if contact:
        masks[surface] = (2, 1)
    return masks


def clearance(tarsus_position, surface_position, radii):
    """Positive bounding-sphere clearance is sufficient geometric separation."""
    return float(np.linalg.norm(np.asarray(tarsus_position) - surface_position) - sum(radii))


def _sample(sim, leg, condition):
    physics = single._physics(sim)
    obs = sim.get_observation()  # refresh after placement/forward, including reset
    tid, sid = condition['tarsus_geom']['id'], condition['surface_geom']['id']
    vector = np.asarray(obs['contact_forces'], dtype=np.float64)[v1.LEGS.index(leg) * 6 + single.DISTAL_OFFSET]
    metadata = single.contact_metadata(single._pairs(physics), tid, sid)
    positions = np.asarray(physics.data.geom_xpos)[[tid, sid]].copy()
    radii = np.asarray(physics.model.geom_rbound)[[tid, sid]].copy()
    return {
        'simulation_time_s': float(physics.data.time),
        'raw_tarsus5_vector': vector.tolist(), 'magnitude': float(np.linalg.norm(vector)),
        'selected_pair_present': metadata['selected_pair_present'], 'contact_metadata': metadata,
        'geom_positions': positions.tolist(), 'geom_radii': radii.tolist(),
        'sphere_clearance': clearance(*positions, radii),
        'collision_masks': np.column_stack((physics.model.geom_contype,
                                          physics.model.geom_conaffinity)).tolist(),
        'explicit_pair_count': int(physics.model.npair),
    }


def run_condition(flygym, leg, *, contact):
    """Fresh physics, existing observers and held-joint calibration schedule."""
    evidence = {'run_status': 'ERROR', 'samples': []}
    sim = None
    try:
        placements = [f'{l}{s}' for l in v1.LEGS for s in
                      ('Tibia', 'Tarsus1', 'Tarsus2', 'Tarsus3', 'Tarsus4', 'Tarsus5')]
        fly = flygym.Fly(name='calibration', enable_adhesion=False, control='position',
                         floor_collisions=[], self_collisions=[],
                         contact_sensor_placements=placements)
        arena = single._make_arena(flygym)
        # Configure before compilation: MuJoCo caches body collision bitmasks.
        # Changing only compiled geom masks could leave those caches stale.
        for geom in fly.model.find_all('geom'):
            geom.contype, geom.conaffinity = (1, 2) if geom.name == f'{leg}Tarsus5' else (0, 0)
        for geom in arena.root_element.find_all('geom'):
            geom.contype, geom.conaffinity = ((2, 1) if contact and geom.name == single.SURFACE_NAME else (0, 0))
        simulation_type = getattr(flygym, 'SingleFlySimulation', None)
        if simulation_type is None:
            simulation_type = importlib.import_module('flygym.simulation').SingleFlySimulation
        sim = simulation_type(fly=fly, arena=arena,
                              cameras=[], timestep=v1.TIMESTEP_S)
        sim.reset(seed=PROTOCOL['seed'])
        physics = single._physics(sim)
        tid, tname = single.resolve_exact_geom(physics.model, f'{leg}Tarsus5')
        sid, sname = single.resolve_exact_geom(physics.model, single.SURFACE_NAME)
        if int(physics.model.npair) != 0:
            raise RuntimeError('explicit collision pairs would bypass isolation masks')
        masks = collision_masks(int(physics.model.ngeom), tid, sid, contact)
        if not (np.array_equal(physics.model.geom_contype, masks[:, 0])
                and np.array_equal(physics.model.geom_conaffinity, masks[:, 1])):
            raise RuntimeError('compiled collision masks differ from prescribed isolation')
        qpos = np.asarray(physics.data.qpos).copy()
        qvel = np.asarray(physics.data.qvel).copy()
        initial_pos = np.asarray(physics.data.geom_xpos[tid]).copy()
        radius = float(physics.model.geom_rbound[tid])
        position = (single.surface_position(initial_pos, radius, contact=True)
                    if contact else np.asarray(REMOTE_POSITION))
        physics.model.geom_pos[sid] = position
        single._forward(physics)
        obs = sim.get_observation()
        joints = np.asarray(obs['joints'])
        held = (joints[0] if joints.ndim == 2 else joints).copy()
        evidence.update({
            'tarsus_geom': {'id': tid, 'name': tname},
            'surface_geom': {'id': sid, 'name': sname},
            'geom_names': [single._geom_name(physics.model, i) for i in range(int(physics.model.ngeom))],
            'reset_qvel': qvel.tolist(), 'held_joints': held.tolist(),
            'pose_proof': {'qpos_before': qpos.tolist(),
                           'qpos_after_surface_placement': np.asarray(physics.data.qpos).tolist(),
                           'exactly_equal': bool(np.array_equal(qpos, physics.data.qpos))},
            'placement': {'surface_position': position.tolist(),
                          'surface_half_size': list(single.SURFACE_HALF_SIZE),
                          'tarsus_world_position': initial_pos.tolist(),
                          'tarsus_conservative_radius': radius,
                          'gap': None if not contact else 0.,
                          'penetration': single.CONTACT_PENETRATION if contact else 0.},
        })
        for step in range(round(v1.DURATION_S / v1.TIMESTEP_S) + 1):
            evidence['samples'].append(_sample(sim, leg, evidence))
            if step < round(v1.DURATION_S / v1.TIMESTEP_S):
                sim.step({'joints': held.copy(), 'adhesion': np.zeros(6)})
        evidence['run_status'] = 'COMPLETE'
    except Exception as exc:
        evidence['reason'] = f'{type(exc).__name__}: {exc}'
    finally:
        if sim is not None:
            try:
                sim.close()
            except Exception as exc:
                evidence.update(run_status='ERROR', close_error=f'{type(exc).__name__}: {exc}')
    return evidence


def evaluate_leg(report, leg):
    """Reuse v1 strict measurement checks, replacing its versioned surface rule."""
    try:
        if any(report[c]['run_status'] != 'COMPLETE' for c in PROTOCOL['conditions']):
            return {'accepted': False, 'status': 'INCOMPLETE', 'checks': {}}
        legacy = v1.evaluate_leg(report, leg)
        if not legacy['checks']:
            return legacy
        checks = dict(legacy['checks'])
        del checks['fixed_surface_rule']  # v1 gap design is explicitly superseded
        checks['versioned_protocol'] = report['protocol'] == PROTOCOL
        control, positive = report['control'], report['contact']
        checks['matched_reset_velocity_and_commands'] = all(
            bool(control[k]) and control[k] == positive[k]
            and all(math.isfinite(float(x)) for x in control[k])
            for k in ('reset_qvel', 'held_joints'))
        checks['fixed_schedule_origin_and_steps'] = all(
            all(math.isclose(s['simulation_time_s'], i * v1.TIMESTEP_S,
                             rel_tol=0, abs_tol=1e-12)
                for i, s in enumerate(report[c]['samples'])) for c in PROTOCOL['conditions'])
        identities = isolation = separation = placement = force = True
        for label, arm in (('control', control), ('contact', positive)):
            tid, sid = arm['tarsus_geom']['id'], arm['surface_geom']['id']
            names = arm['geom_names']
            identities &= (names == control['geom_names'] and names[tid] == arm['tarsus_geom']['name']
                           and names[sid] == arm['surface_geom']['name']
                           and sum(n is not None and n.rsplit('/', 1)[-1] == f'{leg}Tarsus5' for n in names) == 1
                           and sum(n is not None and n.rsplit('/', 1)[-1] == single.SURFACE_NAME for n in names) == 1)
            expected_masks = collision_masks(len(names), tid, sid, label == 'contact').tolist()
            p = arm['placement']
            expected_pos = (single.surface_position(p['tarsus_world_position'],
                            p['tarsus_conservative_radius'], contact=True).tolist()
                            if label == 'contact' else list(REMOTE_POSITION))
            placement &= (p['surface_position'] == expected_pos
                          and p['surface_half_size'] == list(single.SURFACE_HALF_SIZE)
                          and p['penetration'] == (single.CONTACT_PENETRATION if label == 'contact' else 0.))
            for s in arm['samples']:
                isolation &= s['collision_masks'] == expected_masks and s['explicit_pair_count'] == 0
                positions, radii = np.asarray(s['geom_positions']), np.asarray(s['geom_radii'])
                geometry_valid = (positions.shape == (2, 3) and radii.shape == (2,)
                                  and np.isfinite(positions).all() and np.isfinite(radii).all()
                                  and (radii > 0).all())
                separation &= bool(geometry_valid)
                if geometry_valid:
                    distance = clearance(*positions, radii)
                    separation &= (math.isclose(s['sphere_clearance'], distance, rel_tol=1e-12, abs_tol=1e-12)
                                   and (label == 'contact' or distance > 0))
                    placement &= positions[1].tolist() == expected_pos
                for pair in s['contact_metadata']['all_contact_pairs']:
                    ids = (pair['geom1_id'], pair['geom2_id'])
                    identities &= all(0 <= i < len(names) for i in ids)
                    identities &= all(names[i] == pair[key] for i, key in
                                      zip(ids, ('geom1_name', 'geom2_name')))
                    isolation &= label == 'contact' and set(ids) == {tid, sid}
                force &= ((s['magnitude'] > single.ENGINEERING_THRESHOLD)
                          if s['selected_pair_present'] else (s['magnitude'] <= single.ENGINEERING_THRESHOLD))
        checks.update(exact_identity_table=bool(identities), collision_isolation=bool(isolation),
                      independently_verified_separation=bool(separation), fixed_v2_surface_rule=bool(placement),
                      full_sample_force_correspondence=bool(force))
        return {'accepted': all(checks.values()), 'checks': checks,
                'status': 'ISOLATED_CALIBRATION_ACCEPTED' if all(checks.values()) else 'CALIBRATION_INCONCLUSIVE_OR_DISAGREEMENT'}
    except (KeyError, IndexError, TypeError, ValueError, OverflowError) as exc:
        return {'accepted': False, 'checks': {}, 'status': 'INVALID_REPORT', 'reason': str(exc)}


def build_report(*, live=False, progress=print):
    flygym, unavailable = None, None
    if live:
        try:
            flygym = importlib.import_module('flygym')
        except ImportError as exc:
            unavailable = f'{type(exc).__name__}: {exc}'
    results = {}
    for leg in v1.LEGS:
        evidence = {'protocol': PROTOCOL.copy(), 'run_status': 'COMPLETE',
                    'selected_leg': leg, 'selected_segment': 'Tarsus5', 'male_cns_used': False,
                    'duration_s': v1.DURATION_S, 'timestep_s': v1.TIMESTEP_S}
        for label in PROTOCOL['conditions']:
            progress(f'{leg} {label}: collision-isolation v2; no CNS or tactile delivery.')
            evidence[label] = (run_condition(flygym, leg, contact=label == 'contact') if flygym else
                               {'run_status': 'UNAVAILABLE' if live else 'NOT_RUN',
                                'reason': unavailable, 'samples': []})
        invalid = []
        safe = v1.finite_evidence(evidence, invalid=invalid)
        evaluation = evaluate_leg(evidence, leg)
        if invalid:
            evaluation.update(accepted=False, status='INVALID_NONFINITE_EVIDENCE')
        results[leg] = {'evidence': safe, 'evaluation': evaluation, 'nonfinite_measurement_paths': invalid}
    accepted = [l for l, r in results.items() if r['evaluation']['accepted']]
    complete = all(r['evidence'][c]['run_status'] == 'COMPLETE'
                   for r in results.values() for c in PROTOCOL['conditions'])
    sources = [Path(__file__), Path(single.__file__), Path(v1.__file__),
               Path(__file__).with_name('tactile_contact.py'),
               Path(__file__).parents[2] / 'docs/SIX_FOOT_NEGATIVE_CONTROL_V2.md',
               Path(__file__).parents[2] / 'docs/SIX_FOOT_NEGATIVE_CONTROL_V2_1.md']
    return {'schema': SCHEMA, 'protocol': PROTOCOL.copy(), 'legs': results,
            'run_status': 'COMPLETE' if complete else 'INCOMPLETE',
            'accepted_legs': accepted, 'all_six_accepted': len(accepted) == 6,
            'source_sha256_lf': {p.name: hashlib.sha256(p.read_bytes().replace(b'\r\n', b'\n')).hexdigest() for p in sources},
            'interpretation': 'Isolated engineering assay only; no live-v3 sensory admission, biological validation, balance or gait claim.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Reserve exclusively before physics; never overwrite historical evidence.
    with args.output.open('x', encoding='utf-8') as stream:
        report = build_report(live=args.live, progress=lambda m: print(m, flush=True))
        stream.write(single.serialized_report(report))
    print(f"Saved {args.output}; accepted={report['accepted_legs']}", flush=True)
    return 0 if report['all_six_accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
