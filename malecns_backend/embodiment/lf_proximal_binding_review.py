"""Static LF muscle-reference semantics; never builds a decoder or simulation."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np

from . import remaining_leg_admission_audit as audit
from . import remaining_leg_admission_review as admission

ROOT = audit.ROOT
SCHEMA = 'lf-proximal-binding-review-v1'
UPSTREAM = 'docs/evidence/remaining-leg-admission-audit-v1_1/audit.json'
MODEL_HASH = 'a72d4a3167a6f6382d31936d32f2481db5895441a0cc2d02cdbd0452a6209a81'
SOURCES = (UPSTREAM, 'docs/LF_PROXIMAL_BINDING_REVIEW_V1.md',
           'malecns_backend/embodiment/lf_proximal_binding_review.py',
           'malecns_backend/embodiment/remaining_leg_admission_review.py',
           'malecns_backend/embodiment/motor.py',
           'malecns_backend/embodiment/_windows_m8_live_condition.py')


def source_hashes():
    return {p: hashlib.sha256((ROOT/p).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
            for p in SOURCES}


def inspect_model(raw, expected_hash, tendons):
    """Check the exact source before interpreting this narrow XML contract."""
    if expected_hash != MODEL_HASH or hashlib.sha256(raw).hexdigest() != expected_hash:
        raise ValueError('original FlyMimic source-model raw hash mismatch')
    tree = ET.fromstring(raw)
    defaults = tree.findall(".//default[@class='muscle']/general")
    if len(defaults) != 1:
        raise ValueError('unique muscle default required')
    default = dict(defaults[0].attrib)
    if any(default.get(k) != 'muscle' for k in ('dyntype', 'gaintype', 'biastype')):
        raise ValueError('muscle activation/force semantics required')
    bindings = []
    for name in tendons:
        actuators = [e for e in tree.findall('./actuator/general') if e.get('tendon') == name]
        routes = [e for e in tree.findall('./tendon/spatial') if e.get('name') == name]
        if len(actuators) != 1 or len(routes) != 1:
            raise ValueError('unique actuator and spatial tendon required: '+name)
        attrs = dict(actuators[0].attrib)
        effective = default | attrs
        gear = [float(x) for x in effective.get('gear', '1 0 0 0 0 0').split()]
        control = [float(x) for x in effective['ctrlrange'].split()]
        gain = [float(x) for x in effective['gainprm'].split()]
        if (attrs.get('class') != 'muscle' or any(effective.get(k) != 'muscle'
                for k in ('dyntype', 'gaintype', 'biastype')) or gear != [1, 0, 0, 0, 0, 0]
                or len(control) != 2 or not 0 <= control[0] < control[1] <= 1
                or len(gain) != 10 or not np.isfinite(gain).all() or gain[2] <= 0):
            raise ValueError('unsupported static muscle/gear/control/peak-force contract')
        bindings.append(dict(tendon=name, actuator_attributes=attrs,
                             tendon_sites=[dict(e.attrib) for e in routes[0]]))
    return dict(raw_sha256=expected_hash, muscle_default=default, bindings=bindings,
                inspection='XML_ONLY_NOT_COMPILED_OR_SIMULATED')


def reference_rows(registration, inventory, identities):
    """Preserve the old hypotheses without creating neuron/decoder signs."""
    rows = registration['muscle_mechanics']
    by_tendon = {r['flymimic_tendon']: r for r in rows}
    if len(rows) != len(by_tendon) or len(rows) != 7:
        raise ValueError('seven unique registered tendon references required')
    result = []
    covered = []
    if len(inventory) != 5 or len(identities) != 5:
        raise ValueError('five exact population identities required')
    if len({p['name'] for p in identities}) != 5:
        raise ValueError('duplicate population identity')
    identity_by_name = {p['name']: p for p in identities}
    for candidate in inventory:
        identity = identity_by_name[candidate['repository_population_name']]
        if identity['body_ids'] != candidate['mapped_neuron_ids']:
            raise ValueError('candidate identity mismatch')
        hypotheses = []
        for old in candidate['mechanical_hypothesis']['external_reference_covectors']:
            name = old['flymimic_tendon']
            row = by_tendon[name]
            vec = np.asarray(row['flygym_covector']['values'], dtype=float)
            if (row['moment_arm_convention'] != 'R = -dL/dq'
                    or old['moment_arm_convention'] != row['moment_arm_convention']
                    or row['flygym_covector']['basis_order'] != ['joint_LFCoxa_yaw', 'joint_LFCoxa', 'joint_LFCoxa_roll']
                    or old['external_reference_covector'] != row['flygym_covector']
                    or vec.shape != (3,) or not np.isfinite(vec).all()):
                raise ValueError('reference convention/basis/covector mismatch')
            hypotheses.append(dict(tendon=name, tensile_torque_coefficient=vec.tolist(),
                                   conditional_positive_tension_component_signs=np.sign(vec).astype(int).tolist()))
            covered.append(name)
        result.append(dict(identity=identity, tendon_hypotheses=hypotheses,
            binding_status='MULTIPLE_TENDON_HYPOTHESES_UNRESOLVED' if len(hypotheses) > 1 else 'SINGLE_CLASS_HYPOTHESIS_NOT_INDEPENDENT_CROSSWALK',
            per_neuron_tendon_assignments=[dict(body_id=b, dense_index=d, tendon=None)
                for b, d in zip(identity['body_ids'], identity['dense_indices'])],
            spike_to_activation=None, activation_to_force=None, force_to_position_target=None,
            decoder_vector=None, gain=None, admission_ready=False))
    if len(covered) != 7 or set(covered) != set(by_tendon):
        raise ValueError('all seven hypotheses must be retained exactly once')
    return result


def build(model):
    before = source_hashes()
    saved, now = admission.verify(ROOT/UPSTREAM)
    registration = json.loads((ROOT/audit.PATHS['registration']).read_text(encoding='utf-8'))
    candidates = json.loads((ROOT/audit.PATHS['candidates']).read_text(encoding='utf-8'))
    raw = Path(model).read_bytes()
    model_record = inspect_model(raw, registration['provenance']['flymimic']['source_model_sha256'],
                                 [r['flymimic_tendon'] for r in registration['muscle_mechanics']])
    populations = reference_rows(registration, candidates['candidate_population_inventory'],
                                 now['lf_reference']['candidate_identities'])
    if source_hashes() != before or Path(model).read_bytes() != raw:
        raise ValueError('source changed during reference inspection')
    return dict(schema=SCHEMA, status='REFERENCE_SEMANTICS_ONLY_ADMISSION_BLOCKED',
        current_motor_count=20, model_coordinates=42, new_admissions=0, scientific_transitions=0,
        source_hashes=before, source_model=model_record, populations=populations,
        upstream_recorded_raw_freezes_satisfied=saved['all_original_raw_freezes_satisfied'],
        current_original_raw_freezes_satisfied=now['all_original_raw_freezes_satisfied'],
        conditional_equation='tau_G = T * R_G; T >= 0; R = -dL/dq',
        scope='LF_ONLY_LOCAL_REFERENCE; no neuron-to-tendon or force-to-position transfer established')


def verify(report, model):
    saved = json.loads(Path(report).read_text(encoding='utf-8'))
    now = build(model)
    # Current checkout raw representation may differ; never rewrite the recorded one.
    historical_current_raw = saved.get('current_original_raw_freezes_satisfied')
    if type(historical_current_raw) is not bool:
        raise ValueError('recorded raw-freeze state required')
    comparison = dict(now, current_original_raw_freezes_satisfied=historical_current_raw)
    if saved != comparison:
        raise ValueError('saved reference review mismatch')
    return saved, now


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--report', type=Path)
    mode.add_argument('--output-dir', type=Path)
    args = parser.parse_args(argv)
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=False)
        try:
            saved = now = build(args.model)
        except Exception as exc:
            failure = dict(schema=SCHEMA, status='INTEGRITY_ERROR', scientific_transitions=0,
                           new_admissions=0, error=f'{type(exc).__name__}: {exc}')
            (args.output_dir/'review.json').write_text(json.dumps(failure, indent=2)+'\n', encoding='utf-8')
            print(failure['error'])
            return 1
        with (args.output_dir/'review.json').open('x', encoding='utf-8') as stream:
            json.dump(saved, stream, indent=2, allow_nan=False)
            stream.write('\n')
    else:
        saved, now = verify(args.report, args.model)
    print('REFERENCE REVIEW VERIFIED: 7 tendon hypotheses; 5 populations; current 20/42.')
    print('Newly admitted 0; CNS/physics transitions 0; admission BLOCKED.')
    print('Original raw-freeze checks at review:', saved['current_original_raw_freezes_satisfied'])
    print('Original raw-freeze checks in current checkout:', now['current_original_raw_freezes_satisfied'])
    print('Tensile torque coefficients are not neuron-to-position decoder signs or gains.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
