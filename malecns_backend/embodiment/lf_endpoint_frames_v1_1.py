"""V1.1 exact mesh namespace bookkeeping; all V1 geometry/state budgets retained."""
import argparse
import json
from pathlib import Path
import subprocess

import numpy as np

from . import lf_endpoint_frames as v1

n, o, route, ROOT = v1.n, v1.o, v1.route, v1.ROOT
DIRECTORY = 'docs/evidence/lf-endpoint-frames-v1_1/'
SCHEMA = 'lf-endpoint-frames-v1.1'
OLD = v1.DIRECTORY+'run/validation.json'
OLD_SHA = '4de986daefb60a8528f7fb361cc0dfe0d7120af109140ace52bf4804ca28d598'


def sources():
    result = v1.sources()
    if o.lineage.sha((ROOT/OLD).read_bytes()) != OLD_SHA: raise ValueError('original V1 failed raw record changed')
    result[OLD] = OLD_SHA
    for p in ('docs/LF_ENDPOINT_FRAMES_V1_1.md', 'malecns_backend/embodiment/lf_endpoint_frames_v1_1.py'):
        result[p] = o.lineage.sha((ROOT/p).read_bytes().replace(b'\r\n', b'\n'))
    return result


def preflight(model_path=None):
    before = sources(); ready = v1.preflight(model_path)
    old = n.load_report(ROOT/OLD)
    if (old['evaluation']['classification'] != 'ENDPOINT_FRAME_INTEGRITY_FAILURE'
            or old['cases'] != [] or old['ready']['sources'] != v1.sources()
            or any(old['api_calls']['probes'].values())):
        raise ValueError('original setup failure scope differs')
    ready.update(sources=before, expected_source_model=old['source']['identity'], historical_v1=dict(raw_sha256=OLD_SHA,
        classification='ENDPOINT_FRAME_INTEGRITY_FAILURE', kinematics_probes=0))
    if sources() != before: raise ValueError('sources changed during V1.1 preflight')
    return ready


def mesh_namespace_links(meta, bodies):
    raw = meta['raw_mesh_names']; names, arrays = meta['names'], meta['arrays']
    if [n.namespace_component(name) for name in raw] != names['mesh']:
        raise ValueError('raw/terminal mesh name inventory differs')
    for row, gid, bid in zip(bodies, meta['geom_ids'], meta['body_ids']):
        mid = arrays['geom_dataid'][gid]
        if (names['mesh'][mid] != row['mesh']['name'] or arrays['geom_bodyid'][gid] != bid
                or raw[mid].rsplit('/', 1)[:-1] != names['geom'][gid].rsplit('/', 1)[:-1]):
            raise ValueError('exact geom/body/mesh attachment namespace differs')
    return True


def metadata(model, data, bodies):
    identity = n.physics_model_identity(model, data)
    names = {kind: [n.compiled_name(model, kind, i) for i in range(int(getattr(model, count)))]
        for kind, count in [('body', 'nbody'), ('geom', 'ngeom'), ('site', 'nsite'), ('mesh', 'nmesh'),
                            ('joint', 'njnt'), ('actuator', 'nu'), ('tendon', 'ntendon')]}
    raw_mesh_names = names['mesh']; names['mesh'] = [n.namespace_component(name) for name in raw_mesh_names]
    def exact(kind, name):
        found = [i for i, value in enumerate(names[kind]) if n.namespace_component(value) == name]
        if len(found) != 1: raise ValueError('unique compiled identity required: '+name)
        return found[0]
    result = dict(identity=identity, names=names, raw_mesh_names=raw_mesh_names,
        arrays={key: np.asarray(getattr(model, key)).tolist() for key in v1.ARRAYS},
        body_ids=[exact('body', row['body']['name']) for row in bodies],
        geom_ids=[exact('geom', row['geom']['name']) for row in bodies])
    v1.validate_metadata(result, bodies); mesh_namespace_links(result, bodies)
    return result


def execute(model_path, ready):
    import mujoco as mj
    import flygym
    from .tactile_motor_loop_audit import _make_live
    report = dict(schema=SCHEMA, status='INCOMPLETE', ready=ready, cases=[],
        physics_transitions=0, cns_transitions=0, current_motor_count=20, new_admissions=0,
        source_compilations=0, target_initializers=0,
        commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip())
    sim = None
    with o.accounting(mj) as (counts, phase):
        try:
            report['source_compilations'] += 1
            source = mj.MjModel.from_xml_path(str(Path(model_path).resolve())); source_data = mj.MjData(source)
            report['source'] = sm = metadata(source, source_data, ready['source_bodies'])
            if sm['identity'] != ready['expected_source_model']:
                raise ValueError('source model/state differs from original V1 compilation')
            ids = v1.resolve_sites(source, ready, sm); report['source_site_ids'] = ids
            report['target_initializers'] += 1
            sim, physics, *_ = _make_live(flygym, {})
            target, initial = physics.model.ptr, physics.data
            report['target'] = tm = metadata(physics.model, initial, ready['target_bodies'])
            inv = n.inventory(physics.model, sim.flies[0]); inv.update(nq=int(target.nq), nv=int(target.nv))
            n.validate_inventory(inv, tm['identity'])
            if tm['identity'] != ready['expected_target_model'] or tm['body_ids'] != [3, 13]:
                raise ValueError('original native target context differs')
            phase[0] = 'probes'
            q = np.asarray(ready['target_center']).copy(); q[[7, 8, 9]] = 0
            report['target_reference'] = v1.observe(mj, target, q, tm)
            for plan in ready['plans']:
                case = dict(offset=plan['offset'], samples=[]); report['cases'].append(case)
                for sample in plan['samples']:
                    q = np.asarray(ready['target_center']).copy(); q[[7, 8, 9]] = sample['target_angles']
                    case['samples'].append(dict(source=v1.observe(mj, source, sample['source_qpos'], sm, ids),
                                              target=v1.observe(mj, target, q, tm)))
            report['source_after'] = n.physics_model_identity(source, source_data)
            report['target_after'] = n.physics_model_identity(physics.model, initial)
            report['status'] = 'COMPLETE'
        except Exception as exc: report['error'] = f'{type(exc).__name__}: {exc}'
        finally:
            if sim is not None: sim.close()
            report['api_calls'] = counts
    try:
        report['sources_after'] = sources(); report['installed_after'] = n.installed_inputs()
        report['source_inputs_after'] = n.pose.manifest(model_path)
    except Exception as exc: report.update(status='INCOMPLETE', postflight_error=f'{type(exc).__name__}: {exc}')
    return report


def evaluate(report, ready):
    actual = v1.evaluate(report, ready)
    checks = {k: value for k, value in actual['checks'].items() if k != 'schema'}
    checks['schema_v1_1'] = report.get('schema') == SCHEMA
    checks['source_baseline_same_as_v1'] = report.get('source', {}).get('identity') == ready.get('expected_source_model')
    try:
        checks['raw_mesh_namespace_links'] = all(mesh_namespace_links(report[key], ready[key+'_bodies']) for key in ('source', 'target'))
    except Exception as exc: checks['raw_mesh_namespace_links'] = False; checks['namespace_error'] = str(exc)
    integrity = all(value is True for value in checks.values()) and len(actual['cases']) == 15
    classification = ('ENDPOINT_FRAME_INTEGRITY_FAILURE' if not integrity else 'ENDPOINT_FRAME_OUTSIDE_LIMITS_TRANSFER_BLOCKED'
        if not actual['all_samples_in_range'] else 'ENDPOINT_FRAME_V1_1_OBSERVER_VERIFIED_TRANSFER_BLOCKED'
        if actual['numerical_passed'] else 'ENDPOINT_FRAME_DISAGREEMENT_TRANSFER_BLOCKED')
    return dict(actual, checks=checks, integrity_passed=integrity, classification=classification)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--execute', action='store_true'); group.add_argument('--report', type=Path)
    parser.add_argument('--model', type=Path); parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args(argv)
    if args.execute:
        if args.model is None or args.output_dir is None: parser.error('--execute requires original --model and fresh --output-dir')
        args.output_dir.mkdir(parents=True, exist_ok=False)
        try:
            ready = preflight(args.model); report = execute(args.model, ready); report['evaluation'] = evaluate(report, ready)
        except Exception as exc: report = dict(schema=SCHEMA, status='ERROR', error=f'{type(exc).__name__}: {exc}')
        with (args.output_dir/'validation.json').open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(n.encode_nonfinite(report), indent=2, allow_nan=False)+'\n')
    else:
        report = n.load_report(args.report); ready = preflight(args.model)
        ready['original_raw_freezes_satisfied'] = report['ready']['original_raw_freezes_satisfied']
        if evaluate(report, ready) != report['evaluation']: raise ValueError('saved V1.1 endpoint evidence differs')
    evaluated = report.get('evaluation', {})
    if not evaluated.get('integrity_passed'):
        print('ENDPOINT V1.1 INTEGRITY FAILED; evidence retained.', report.get('error', evaluated)); return 1
    print('ENDPOINT V1.1 EVIDENCE VERIFIED:', evaluated['classification'])
    print('Historical V1 remains setup INTEGRITY_FAILURE,0probes; all raw mesh names retained.')
    print('105source/106target recorded kinematics;0 probe forwards/integration/CNS. Saved review executes none.')
    print('Maximum errors:', {k: max(r['metrics'][k] for r in evaluated['cases']) for k in ('endpoint', 'length', 'derivative', 'orientation', 'geom')})
    print('Roadmap:20/42;new admissions0;target attachments/units/neural/raw gates remain open;no new Unity behavior.')
    return 0


if __name__ == '__main__': raise SystemExit(main())
