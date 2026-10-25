"""Read-only LF transfer evidence review; never constructs a body or decoder."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from . import lf_synthetic_coupling_v2 as coupling
from . import lf_force_static_reference as static
from . import lf_proximal_binding_review as binding

ROOT = coupling.ROOT
DIRECTORY = 'docs/evidence/lf-transfer-prerequisites-v1/'
CONTEXT = DIRECTORY+'source-context.json'
CONTEXT_SHA = 'cd229d0e78fde88e27127e2c6dedd4c3d35f0546d74ffe839f93f5ec369d0bf9'
RECORD = coupling.DIRECTORY+'run/validation.json'
RECORD_SHA = '49e7443266c0b2a40129cf2600a99a468f3242764afa1a94e48ce55e72a1d891'
SCHEMA = 'lf-transfer-prerequisites-v1'
CLASSIFICATION = 'TRANSFER_REVIEW_VERIFIED_PHYSICAL_ANATOMICAL_NEURAL_RAW_GATES_OPEN'
NEXT = 'Source-unit and parameter-conversion lineage audit; no moving-fly coupling.'
SOURCES = (CONTEXT, 'docs/LF_TRANSFER_PREREQUISITES_V1.md',
           'malecns_backend/embodiment/lf_transfer_prerequisites.py',
           'malecns_backend/embodiment/lf_force_static_reference.py',
           'docs/evidence/lf-native-isolation-v1/input-manifest.json')


def read(path):
    return json.loads((ROOT/path).read_text(encoding='utf-8'))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def source_hashes():
    result = coupling.sources()
    for path in SOURCES:
        result[path] = sha((ROOT/path).read_bytes().replace(b'\r\n', b'\n'))
    if result[CONTEXT] != CONTEXT_SHA:
        raise ValueError('transfer source-context snapshot changed')
    if sha((ROOT/RECORD).read_bytes()) != RECORD_SHA:
        raise ValueError('historical V2 coupling raw evidence changed')
    result[RECORD] = RECORD_SHA
    return result


def inspect_external_model(path, context):
    """Optional exact original-XML check, not a native model or mesh check."""
    raw = Path(path).read_bytes()
    model = context['source_model']
    inspected = binding.inspect_model(raw, binding.MODEL_HASH, coupling.v1.force.TENDONS)
    tree = ET.fromstring(raw)
    expected = dict(relative_path=model['relative_path'], bytes=len(raw),
        compiler=dict(tree.find('compiler').attrib), option=dict(tree.find('option').attrib),
        mesh_scales=sorted({n.get('scale', '1 1 1') for n in tree.findall('./asset/mesh')}), **inspected)
    if expected != model:
        raise ValueError('source XML differs from captured transfer context')


def selected_parameters(context, source_binding):
    """Read explicit parameters; do not infer force units from numeric magnitude."""
    model = context['source_model']
    if (model['raw_sha256'] != binding.MODEL_HASH
            or source_binding['source_xml_sha256'] != binding.MODEL_HASH
            or model['muscle_default'] != source_binding['muscle_default']):
        raise ValueError('source-binding identity/default mismatch')
    rows = model['bindings']
    if (len(source_binding['selected']) != 4
            or [r['tendon'] for r in rows] != list(coupling.v1.force.TENDONS)):
        raise ValueError('exact selected tendon order required')
    result = []
    for row, frozen in zip(rows, source_binding['selected']):
        attrs = row['actuator_attributes']
        if attrs != frozen['source_attributes'] or row['tendon'] != frozen['tendon']:
            raise ValueError('selected parameters differ from original binding')
        gain = [float(v) for v in attrs['gainprm'].split()]
        result.append(dict(tendon=row['tendon'], explicit_peak_force=gain[2],
            peak_force_semantics='EXPLICIT_SOURCE_MODEL_PARAMETER_NOT_AUTOMATIC_ACC0_SCALE',
            source_force_SI_unit=None, target_force_conversion=None,
            normalized_range=gain[:2], lengthrange=[float(v) for v in attrs['lengthrange'].split()],
            dynprm=[float(v) for v in attrs['dynprm'].split()],
            gainprm=gain, biasprm=[float(v) for v in attrs['biasprm'].split()],
            ctrlrange=[float(v) for v in attrs['ctrlrange'].split()],
            biological_force_calibration=False))
    if len(result) != 4:
        raise ValueError('four original source bindings required')
    return result


def build():
    before = source_hashes()
    context = read(CONTEXT)
    # Reuse saved-evidence evaluators. These paths do not execute their runners.
    ready = coupling.preflight()
    report = coupling.v1.upstream.load_report(ROOT/RECORD)
    evaluated = coupling.evaluate(report, ready)
    if (evaluated != report['evaluation'] or evaluated['classification'] !=
            'SYNTHETIC_COUPLING_V2_VERIFIED_TRANSFER_BLOCKED'):
        raise ValueError('original V2 saved-report evaluation failed')
    authority = static.load()
    populations = binding.reference_rows(authority['registration'],
        authority['candidates']['candidate_population_inventory'], authority['lf']['candidate_identities'])
    native_inputs = read('docs/evidence/lf-native-isolation-v1/input-manifest.json')
    if context['files']['flygym/simulation.py']['raw_sha256'] != native_inputs['files']['flygym/simulation.py']['sha256']:
        raise ValueError('FlyGym unit-context source differs from original native input lock')
    selected = selected_parameters(context, ready['binding'])
    gates = [
        dict(gate='software_coupling', status='VERIFIED_SYNTHETIC_ONLY',
             evidence=RECORD, limit='Constant reference coefficients and synthetic inertias; no physical transfer.'),
        dict(gate='units_and_parameter_lineage', status='UNRESOLVED', evidence=CONTEXT,
             limit='Source gravity -9801, mesh scale 1000 and target gravity -9810 are clues; mass/time/force conversion lineage is not established.'),
        dict(gate='finite_angle_target_registration', status='MODELED_NOT_TARGET_VALIDATED',
             evidence='docs/evidence/lf-pose-force-v1_1/run/validation.json',
             limit='15 source poses and modeled rotation/covector map; not actual target tendon attachment/length registration.'),
        dict(gate='moving_length_velocity_force', status='SOURCE_LAW_ONLY',
             evidence=coupling.v1.schedule.BINDING,
             limit='Source lengthrange/gain/bias are preserved; frozen-pose zero-velocity forces do not supply target moving lengths/velocities.'),
        dict(gate='population_to_tendon', status='UNRESOLVED',
             evidence='docs/evidence/lf-anatomical-crosswalk-v1/crosswalk.json',
             limit='13 exact neurons, 12 recorded MANC body matches; seven hypotheses including three promotor alternatives; no individual tendon assignments.'),
        dict(gate='neural_to_activation', status='UNRESOLVED',
             evidence='docs/evidence/lf-proximal-binding-review-v1/review.json',
             limit='No supported proximal spike-to-activation conversion; existing position-decoder scale does not establish it.'),
        dict(gate='original_raw_prerequisites', status='UNRESOLVED',
             evidence='docs/evidence/remaining-leg-admission-audit-v1_1/audit.json',
             limit='Original failed scientific raw locks are retained; canonical content correspondence is not a waiver.'),
    ]
    if source_hashes() != before:
        raise ValueError('source changed during transfer review')
    return dict(schema=SCHEMA, classification=CLASSIFICATION, source_hashes=before,
        execution_scope='STATIC_SAVED_EVIDENCE_REVIEW_NO_NATIVE_OR_SOLVER_OR_CNS_CALLS',
        current_motor_count=20, model_coordinates=42, new_admissions=0,
        physical_transitions=0, cns_transitions=0, production_transfer_enabled=False,
        synthetic_prerequisite=dict(classification=evaluated['classification'],
            cases=len(evaluated['cases']), historical_v1_classification='INTEGRITY_FAILURE'),
        current_original_raw_freezes_satisfied=authority['original_raw_freezes_satisfied'],
        source_context=CONTEXT, source_context_scope='PINNED_SNAPSHOT_NOT_LIVE_EXTERNAL_CLONE_CHECK',
        selected_parameters=selected, population_hypotheses=populations,
        dimensional_ledger=dict(source_base_length_SI=None, source_base_mass_SI=None,
            source_base_time_SI=None, target_base_length_SI=None, target_base_mass_SI=None,
            target_base_time_SI=1.0, force_conversion=None, torque_conversion=None,
            rule='F_unit=M_unit*L_unit/T_unit^2; torque_unit=M_unit*L_unit^2/T_unit^2',
            observation_division_by_1000_is_force_calibration=False),
        gates=gates, next_task=NEXT)


def verify(path):
    saved = json.loads(Path(path).read_text(encoding='utf-8'))
    now = build()
    raw = saved.get('current_original_raw_freezes_satisfied')
    if type(raw) is not bool:
        raise ValueError('recorded raw-prerequisite state required')
    # Preserve historical raw outcome across newline representations. Always
    # return/display the current one separately; this never admits transfer.
    if saved != dict(now, current_original_raw_freezes_satisfied=raw):
        raise ValueError('saved transfer review differs from reconstructed evidence')
    return saved, now


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--report', type=Path)
    modes.add_argument('--output-dir', type=Path)
    parser.add_argument('--source-model', type=Path)
    args = parser.parse_args(argv)
    if args.source_model:
        inspect_external_model(args.source_model, read(CONTEXT))
    if args.report:
        saved, now = verify(args.report)
    else:
        saved = now = build()
        args.output_dir.mkdir(parents=True, exist_ok=False)
        with (args.output_dir/'review.json').open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(saved, indent=2, allow_nan=False)+'\n')
    print('TRANSFER REVIEW VERIFIED: software prerequisite9/9; physical/anatomical/neural/raw gates OPEN.')
    for row in now['gates']:
        print(row['gate']+': '+row['status'])
    print('Original raw prerequisites recorded/current:', saved['current_original_raw_freezes_satisfied'],
          '/', now['current_original_raw_freezes_satisfied'])
    print('Roadmap:20/42; new admissions0; physics/CNS transitions0; no new Unity behavior.')
    print('Next:', NEXT)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
