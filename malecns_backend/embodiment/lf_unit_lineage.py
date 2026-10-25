"""Static source-unit/conversion-lineage audit; no converter or physics execution."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from . import lf_transfer_prerequisites as transfer

ROOT = transfer.ROOT
DIRECTORY = 'docs/evidence/lf-unit-lineage-v1/'
SNAPSHOT = DIRECTORY+'source-extracts.json'
SNAPSHOT_SHA = 'cb945fca39d5952aee7d16aa32bae808da0b2a5f468aa80c15de41fe50df66c4'
UPSTREAM = transfer.DIRECTORY+'run/review.json'
SCHEMA = 'lf-unit-lineage-v1'
NAMES = tuple(t.removesuffix('_tendon') for t in transfer.coupling.v1.force.TENDONS)
MUSCLE_FIELDS = ('max_isometric_force', 'optimal_fiber_length', 'tendon_slack_length',
                 'max_contraction_velocity', 'activation_time_constant', 'deactivation_time_constant')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def extract_osim(raw):
    model = ET.fromstring(raw).find('Model')
    if model is None:
        raise ValueError('OpenSim Model required')
    muscles = model.findall('./ForceSet/objects/*')
    selected = []
    for name in NAMES:
        found = [n for n in muscles if n.get('name') == name]
        if len(found) != 1 or found[0].tag != 'Millard2012EquilibriumMuscle':
            raise ValueError('unique exact Millard muscle required: '+name)
        selected.append(dict(name=name, model=found[0].tag,
            parameters={k: float(found[0].findtext(k)) for k in MUSCLE_FIELDS}))
    bodies = model.findall('./BodySet/objects/Body')
    if len({b.get('name') for b in bodies}) != len(bodies):
        raise ValueError('duplicate OpenSim body')
    return dict(model=model.get('name'), declared_length_units=model.findtext('length_units'),
        declared_force_units=model.findtext('force_units'),
        gravity=[float(v) for v in model.findtext('gravity').split()],
        body_count=len(bodies), raw_body_mass_sum=sum(float(b.findtext('mass')) for b in bodies),
        representative_bodies=[dict(name=b.get('name'), mass=float(b.findtext('mass')),
            inertia=[float(v) for v in b.findtext('inertia').split()])
            for b in bodies if b.get('name') in ('Thorax', 'LFCoxa')], selected=selected)


def extract_source(raw):
    inspected = transfer.binding.inspect_model(raw, transfer.binding.MODEL_HASH,
        transfer.coupling.v1.force.TENDONS)
    tree = ET.fromstring(raw)
    return dict(binding=inspected, option=dict(tree.find('option').attrib),
        raw_body_mass_sum=sum(float(n.get('mass')) for n in tree.findall('.//inertial')),
        representative_bodies=[dict(name=b.get('name'), inertial=dict(b.find('inertial').attrib))
            for b in tree.findall('.//body') if b.get('name') in ('Thorax', 'LFCoxa')])


def extract_target(raw):
    tree = ET.fromstring(raw)
    geoms = [g for g in tree.findall('.//geom') if g.get('mass') is not None]
    return dict(compiler=dict(tree.find('compiler').attrib), raw_geom_mass_sum=sum(float(g.get('mass')) for g in geoms),
        representative_geoms=[dict(g.attrib) for g in geoms if g.get('name') in ('Thorax', 'LFCoxa')],
        scope='RAW_XML_GEOM_MASSES_NOT_COMPILED_BODY_MASS_OR_UNIT_CALIBRATION')


def analyse(snapshot):
    osim = snapshot['files']['opensim']['extract']
    full = snapshot['files']['opensim_full']['extract']
    source = snapshot['files']['source_mjcf']['extract']
    comparisons = []
    if [n['name'] for n in osim['selected']] != list(NAMES) or [n['name'] for n in full['selected']] != list(NAMES):
        raise ValueError('exact OpenSim muscle identities/order required')
    if [r['tendon'] for r in source['binding']['bindings']] != [n+'_tendon' for n in NAMES]:
        raise ValueError('exact original MJCF tendon identities/order required')
    for old, other, mjc in zip(osim['selected'], full['selected'], source['binding']['bindings']):
        attrs = mjc['actuator_attributes']
        peak = float(attrs['gainprm'].split()[2])
        params = old['parameters']
        comparisons.append(dict(muscle=old['name'], opensim_parameters=params,
            full_model_parameters_equal=params == other['parameters'], mjcf_peak_force=peak,
            numeric_peak_ratio_not_unit_conversion=peak/params['max_isometric_force'],
            mjcf_lengthrange=[float(v) for v in attrs['lengthrange'].split()],
            mjcf_normalized_length_range=[float(v) for v in attrs['gainprm'].split()[:2]],
            mjcf_vmax_parameter=float(attrs['gainprm'].split()[6]),
            mjcf_activation_constants=[float(v) for v in attrs['dynprm'].split()[:2]],
            activation_constants_numerically_equal=[float(v) for v in attrs['dynprm'].split()[:2]] ==
                [params['activation_time_constant'], params['deactivation_time_constant']],
            interpretation='MODEL_PARAMETER_COMPARISON_NOT_ONE_TO_ONE_PHYSIOLOGY_OR_PROVEN_CONVERSION'))
    tracked = snapshot['repository']['tracked_paths']
    patterns = dict(conversion_log=r'(^|/)[^/]*conversion[^/]*\.log$',
        intermediate_xml=r'(^|/)[^/]*_cvt[12]\.xml$',
        converter_revision_or_config=r'(^|/)(myoconverter|conversion_config|converter_config)(/|\.)',
        step_validation_inputs=r'(^|/)Step[123]_[^/]+/')
    available = {key: [p for p in tracked if re.search(pattern, p, re.I)] for key, pattern in patterns.items()}
    ratios = [r['numeric_peak_ratio_not_unit_conversion'] for r in comparisons]
    return dict(classification='LINEAGE_AUDIT_VERIFIED_CONVERSION_AND_PHYSICAL_SCALE_UNRESOLVED',
        comparisons=comparisons, numeric_peak_ratios_all_identical=all(v == ratios[0] for v in ratios),
        tracked_conversion_records=available,
        absence_scope='RECORDED_LOCAL_TRACKED_TREE_ONLY_NOT_GLOBAL_OR_UPSTREAM_ABSENCE',
        conversion_pdf=dict(file=snapshot['files']['conversion_pdf']['path'],
            raw_sha256=snapshot['files']['conversion_pdf']['raw_sha256'],
            inspection=snapshot['pdf_inspection'], exact_locked_xml_hash_link=False,
            establishes_locked_xml_validation=False),
        unit_ledger=dict(opensim_declared_length=osim['declared_length_units'],
            opensim_declared_force=osim['declared_force_units'], opensim_gravity=osim['gravity'],
            source_mjcf_gravity=source['option']['gravity'], target_clock_seconds=1.0,
            resolved_source_length_SI=None, resolved_source_mass_SI=None, resolved_source_time_SI=None,
            resolved_target_length_SI=None, resolved_target_mass_SI=None,
            physical_force_conversion=None, physical_torque_conversion=None,
            source_to_target_moment_arm_conversion=None, source_to_target_velocity_conversion=None,
            rule='F=M*L/T^2; torque=M*L^2/T^2; inertia=M*L^2; length=L; velocity=L/T',
            note='Declarations preserved literally; scaled gravity needs lineage. No factor inferred from names, force ratios, masses or printed PDF units.'),
        converter_revision=None, converter_configuration=None, post_conversion_edit_history=None,
        original_OpenSim_input_to_locked_XML_proven=False, production_transfer_enabled=False,
        next_task='Predeclare non-actuating native target orientation-registration assay; force scaling remains blocked pending authoritative conversion lineage.')


def source_hashes():
    result = {}
    for path in (SNAPSHOT, UPSTREAM, 'docs/LF_UNIT_LINEAGE_V1.md',
                 'malecns_backend/embodiment/lf_unit_lineage.py',
                 'docs/evidence/lf-native-isolation-v1/input-manifest.json'):
        result[path] = sha((ROOT/path).read_bytes().replace(b'\r\n', b'\n'))
    if result[SNAPSHOT] != SNAPSHOT_SHA:
        raise ValueError('unit-lineage source snapshot changed')
    return result


def inspect_external(root, snapshot):
    root = Path(root)
    for key, record in snapshot['files'].items():
        if record['location'] != 'FlyMimic':
            continue
        raw = (root/record['path']).read_bytes()
        if sha(raw) != record['raw_sha256'] or len(raw) != record['bytes']:
            raise ValueError('original external source raw identity mismatch: '+record['path'])
        extractor = extract_osim if key in ('opensim', 'opensim_full') else extract_source if key == 'source_mjcf' else None
        if extractor and extractor(raw) != record['extract']:
            raise ValueError('source extract differs from original XML: '+key)


def build():
    before = source_hashes()
    _, upstream = transfer.verify(ROOT/UPSTREAM)
    snapshot = transfer.read(SNAPSHOT)
    context = transfer.read(transfer.CONTEXT)
    if (snapshot['files']['source_mjcf']['raw_sha256'] != transfer.binding.MODEL_HASH
            or snapshot['files']['source_mjcf']['extract']['binding'] !=
            {k: context['source_model'][k] for k in ('raw_sha256', 'muscle_default', 'bindings', 'inspection')}):
        raise ValueError('original source-model binding context differs')
    manifest = transfer.read('docs/evidence/lf-native-isolation-v1/input-manifest.json')
    target = snapshot['files']['target_mjcf']
    if target['raw_sha256'] != manifest['files'][target['path']]['sha256']:
        raise ValueError('target source differs from original native manifest')
    result = dict(schema=SCHEMA, source_hashes=before, current_motor_count=20, model_coordinates=42,
        new_admissions=0, physics_transitions=0, cns_transitions=0,
        execution_scope='STATIC_SOURCE_AND_SAVED_REPORT_AUDIT_NO_NATIVE_SOLVER_CONVERTER_OR_CNS',
        current_original_raw_freezes_satisfied=upstream['current_original_raw_freezes_satisfied'],
        source_repository=snapshot['repository'], source_files=snapshot['files'], **analyse(snapshot))
    if source_hashes() != before:
        raise ValueError('audit sources changed during reconstruction')
    return result


def verify(path):
    saved = json.loads(Path(path).read_text(encoding='utf-8'))
    now = build()
    recorded = saved.get('current_original_raw_freezes_satisfied')
    if type(recorded) is not bool or saved != dict(now, current_original_raw_freezes_satisfied=recorded):
        raise ValueError('saved unit-lineage audit differs from reconstructed sources')
    return saved, now


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--report', type=Path)
    mode.add_argument('--output-dir', type=Path)
    parser.add_argument('--source-root', type=Path)
    args = parser.parse_args(argv)
    if args.source_root:
        inspect_external(args.source_root, transfer.read(SNAPSHOT))
    if args.report:
        saved, now = verify(args.report)
    else:
        saved = now = build()
        args.output_dir.mkdir(parents=True, exist_ok=False)
        with (args.output_dir/'audit.json').open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(saved, indent=2, allow_nan=False)+'\n')
    print('UNIT/LINEAGE AUDIT VERIFIED; physical conversion UNRESOLVED; coupling BLOCKED.')
    for row in now['comparisons']:
        print(row['muscle']+': numeric peak ratio '+format(row['numeric_peak_ratio_not_unit_conversion'], '.8g')+' (not a unit conversion)')
    print('Converter revision/configuration and exact PDF-to-locked-XML link: unresolved.')
    print('Original raw prerequisites recorded/current:', saved['current_original_raw_freezes_satisfied'], '/', now['current_original_raw_freezes_satisfied'])
    print('Roadmap:20/42; new admissions0; physics/CNS transitions0; no new Unity behavior.')
    print('Next:', now['next_task'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
