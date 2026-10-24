"""Read-only remaining-coordinate evidence matrix; never admits a motor channel."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np

from ..codec import decode_neurons
from ..live.protocol import JOINT_NAMES
from . import whole_leg_motor_mapping_audit as m6a
from . import coxa_yaw_anatomical_sign_bridge as bridge
from . import live_v2_motor_interface as v2,live_v3_motor_interface as v3

ROOT=Path(__file__).resolve().parents[2]
BASE='malecns_backend/embodiment/interface_output/'
PATHS=dict(mapping=BASE+'whole_leg_motor_mapping_audit.json',interface='malecns_backend/interface_map.json',
    bodymap='fly-brain-main/public/data/bodymap.json',neurons='fly-brain-main/public/data/neurons.flyn',
    mechanical=BASE+'coxa_yaw_sign_validation/coxa_yaw_sign_validation_result.json',
    mechanical_freeze=BASE+'coxa_yaw_sign_validation/COXA_YAW_SIGN_VALIDATION_FREEZE.json',
    bridge=BASE+'coxa_yaw_anatomical_sign_bridge/coxa_yaw_anatomical_sign_bridge_result.json',
    bridge_freeze=BASE+'coxa_yaw_anatomical_sign_bridge/COXA_YAW_ANATOMICAL_SIGN_BRIDGE_FREEZE.json',
    registration=BASE+'flymimic_flygym_proximal_registration/flymimic_flygym_proximal_registration_result.json',
    registration_manifest=BASE+'flymimic_flygym_proximal_registration/flymimic_flygym_proximal_registration_manifest.json',
    candidates=BASE+'lf_proximal_candidate_mapping_review/lf_proximal_candidate_mapping_review_preregistration.json',
    activity=BASE+'lf_proximal_candidate_mapping_review/lf_proximal_candidate_activity_evidence_addendum.json',
    recruitment=BASE+'lf_proximal_motor_recruitment/lf_proximal_motor_recruitment_result.json')
SOURCES=('docs/REMAINING_LEG_ADMISSION_AUDIT_V1.md',
    'malecns_backend/embodiment/remaining_leg_admission_audit.py',
    'malecns_backend/codec.py','malecns_backend/live/protocol.py',
    'malecns_backend/embodiment/live_v3_motor_interface.py',
    'malecns_backend/embodiment/live_v2_motor_interface.py',
    'malecns_backend/embodiment/whole_leg_motor_mapping_audit.py',
    'malecns_backend/embodiment/coxa_yaw_anatomical_sign_bridge.py')
SCHEMA='remaining-leg-admission-audit-v1'


def sha(raw): return hashlib.sha256(raw).hexdigest()


def snapshot():
    result={}
    for p in (*PATHS.values(),*SOURCES):
        raw=(ROOT/p).read_bytes()
        normalized=raw.replace(b'\r\n',b'\n') if Path(p).suffix in ('.py','.md','.json') else raw
        result[p]=dict(raw_sha256=sha(raw),canonical_content_sha256=sha(normalized))
    return result


def frozen_record(path,expected):
    raw=(ROOT/path).read_bytes()
    canonical=raw.replace(b'\r\n',b'\n')
    raw_ok=sha(raw)==expected
    if not raw_ok:
        git=subprocess.check_output(['git','show','HEAD:'+path],cwd=ROOT)
        if sha(canonical)!=expected or git!=canonical:
            raise ValueError('substantive frozen artifact mismatch: '+path)
    return dict(path=path,expected_sha256=expected,actual_raw_sha256=sha(raw),raw_lock_passed=raw_ok,
        canonical_content_verified=True,
        interpretation='ORIGINAL_RAW_LOCK_PASSED' if raw_ok else 'RAW_LOCK_FAILED_CHECKOUT_CRLF_ONLY; original prerequisite has NOT passed')


def resolve_population(name,expected_ids,populations,muscles,body_ids):
    p=populations[name]
    source=muscles[name]
    ids=p['body_ids']; dense=p['dense_indices']
    checks=dict(exact_body_ids=ids==expected_ids,count=p['count']==len(ids)==len(dense)>0,
        body_integer=all(type(b) is int for b in ids),
        unique=len(ids)==len(set(ids)) and len(dense)==len(set(dense)),
        dense_integer=all(type(i) is int and 0<=i<len(body_ids) for i in dense),
        metadata=p['bodymap_metadata']=={k:source[k] for k in ('name','actuator','dir')},
        exact_bodymap_indices=dense==source['idx'])
    checks['body_id_dense_inversion']=checks['dense_integer'] and all(int(body_ids[i])==b for b,i in zip(ids,dense))
    if not all(checks.values()): raise ValueError('population identity mismatch: '+name)
    return dict(name=name,body_ids=ids,dense_indices=dense,count=p['count'],direction=source['dir'],
        annotation_actuator=source['actuator'],checks=checks)


def row_record(row,admission,populations,muscles,body_ids,geometric):
    name,index=row['actuator'],row['global_action_index']
    if name!=JOINT_NAMES[index] or admission['actuator']!=name or admission['action_index']!=index or admission['neural_motor_admission']:
        raise ValueError('remaining-row admission identity mismatch')
    candidates=[resolve_population(c['population'],c['body_ids'],populations,muscles,body_ids) for c in row['candidates']]
    positive={b for c in candidates if c['direction']==1 for b in c['body_ids']}
    negative={b for c in candidates if c['direction']==-1 for b in c['body_ids']}
    if positive&negative: raise ValueError('opposing candidate pools overlap')
    joint=row['joint_class']
    extra={}
    if joint in ('Coxa','Coxa_roll'):
        if not row['unresolved_shared_population_conflict']: raise ValueError('expected shared-axis evidence changed')
        status='SHARED_AXIS_BINDING_REQUIRED'
        blockers=['Shared population-to-Coxa/Coxa_roll decomposition unresolved.',
                  'Unique anatomical action/sign and validated multi-axis decoder/admission unavailable.']
    elif joint=='Coxa_yaw':
        leg=geometric['legs'][row['leg']]
        actual=bridge.classify_leg(leg)
        if actual!=leg['classification'] or leg['action_index']!=index or leg['joint']!=name:
            raise ValueError('frozen geometric classifier/identity mismatch')
        extra=dict(recorded_mechanical_valid=leg['mechanical_valid'],recorded_geometry_identity=leg['geometry_identity_valid'],
            anatomical_classification=actual,positive_anterior_projection=leg['positive']['projected_anterior_displacement'],
            negative_anterior_projection=leg['negative']['projected_anterior_displacement'],
            anterior_coordinate_sign=leg['derived_anterior_coordinate_sign'],historical_active_motors=11)
        if actual!='ANATOMICAL_SIGN_GEOMETRICALLY_UNRESOLVED' or extra['anterior_coordinate_sign'] is not None:
            raise ValueError('frozen unresolved sign was strengthened or changed')
        status='ANATOMICAL_ACTION_SIGN_BRIDGE_REQUIRED'
        blockers=['Mechanical coordinate rotation recorded; biological anterior/posterior-to-coordinate sign unresolved.',
                  'Frozen anterior-projection null must not be reinterpreted with a favorable metric.',
                  'Current-context decoder/causal admission prerequisites not satisfied.']
    elif joint=='Tarsus1':
        actuator=f"tarsus_{row['segment']}_{row['side']}"
        exact=[p for p in muscles.values() if p.get('actuator')==actuator]
        related=[p['name'] for p in muscles.values() if p.get('actuator')==f"tarsus2_{row['segment']}_{row['side']}"]
        if candidates or exact: raise ValueError('missing Tarsus1 annotation evidence changed; re-audit required')
        status='EXACT_TARGET_POPULATION_MAPPING_REQUIRED'
        blockers=['No exact current tarsus_T2/T3 population mapping for this Tarsus1 target.',
                  'Tarsus2 annotations/front-leg pools cannot substitute for this coordinate.',
                  'Identity, opposing pools, sign, decoder and mechanical/causal admission remain prerequisites.']
        extra=dict(exact_annotation_actuator=actuator,exact_population_count=0,related_tarsus2_not_candidates=related)
    else: raise ValueError('unexpected remaining coordinate group')
    return dict(actuator=name,action_index=index,leg=row['leg'],joint_class=joint,
        current_admission=dict(admission),historical_mapping_status=row['motor_mapping_status'],
        historical_decoder_readiness=row['decoder_readiness'],unique_mapping=row['unique_physical_mapping'],
        candidate_physical_axes=row['candidate_physical_axes'],shared_axis_conflict=row['unresolved_shared_population_conflict'],
        candidates=candidates,opposing_pool_overlap=[],evidence=extra,status=status,blockers=blockers,
        admission_ready=False,coordinate_sign_assigned_by_audit=None)


def inspect_lf(registration,candidates,recruitment,populations,muscles,body_ids):
    matrix=np.asarray(registration['local_differential_registration']['J_GM_inverse_transpose'],dtype=float)
    jacobian=np.asarray(registration['local_differential_registration']['J_GM'],dtype=float)
    if matrix.shape!=(3,3) or not np.allclose(matrix,np.linalg.inv(jacobian).T,atol=1e-12,rtol=0):
        raise ValueError('frozen differential registration inverse-transpose mismatch')
    transforms=[]
    for row in registration['muscle_mechanics']:
        if (row['flymimic_covector']['basis_order']!=['yaw','pitch','roll'] or
                row['flygym_covector']['basis_order']!=['joint_LFCoxa_yaw','joint_LFCoxa','joint_LFCoxa_roll']):
            raise ValueError('frozen local covector basis order mismatch')
        rm=np.asarray(row['flymimic_covector']['values'],dtype=float)
        rg=np.asarray(row['flygym_covector']['values'],dtype=float)
        error=float(np.max(np.abs(matrix@rm-rg)))
        if error>1e-12 or not np.isfinite(error): raise ValueError('frozen covector mismatch')
        transforms.append(dict(tendon=row['flymimic_tendon'],max_absolute_error=error))
    identities=[resolve_population(r['repository_population_name'],r['mapped_neuron_ids'],populations,muscles,body_ids)
                for r in candidates['candidate_population_inventory']]
    decisions=recruitment['decisions']
    if set(decisions)!={p['name'] for p in identities}: raise ValueError('LF recruitment population inventory mismatch')
    for result in decisions.values():
        if any(r['label']!='NOT_RECRUITED_UNDER_TEST_CONDITION' or r['per_seed_response']!=[False]*3
               or r['event_count_crosscheck']!=[True]*3 for r in result.values()):
            raise ValueError('recorded LF recruitment null changed')
    return dict(registration_verdict=registration['registration_verdict'],scope=registration['scientific_scope'],
        covector_transform_checks=transforms,candidate_identities=identities,
        historical_recruitment_decisions=decisions,historical_context='11 admitted motors; seeds 1,2,3; LF_MIN_BOUND/LF_MAX_BOUND sensory replay',
        interpretation='Recorded older-context nulls, not evidence of inevitable silence in current v3/tactile context.',
        remaining=['LF-only local differential mechanics are not population activation signs or decoder weights.',
                   'Broad promotor maps to three tendon hypotheses; no unsupported averaging or dominant-axis selection.',
                   'Independent population-to-muscle activation/binding and sign/decoder/admission validation still required.'])


def build():
    before=snapshot()
    read=lambda key:json.loads((ROOT/PATHS[key]).read_text(encoding='utf-8'))
    data={key:read(key) for key in PATHS if key!='neurons'}
    # Reuse the actual data-only current-v3 projection and its original locks.
    from . import _windows_m7d_corrected_spontaneous_adapter as adapter
    protocol,records,table=adapter._protocol()
    protocol,records,table=v2.derive_v2(protocol,records,table)
    protocol,records,table=v3.derive_v3(protocol,records,table)
    if [r['actuator'] for r in table]!=list(JOINT_NAMES): raise ValueError('ordered 42-coordinate table mismatch')
    if data['mapping']['classification']!='WHOLE_LEG_MOTOR_AUDIT_COMPLETE': raise ValueError('M6A incomplete')
    if sha((ROOT/PATHS['mapping']).read_bytes())!='722ee9b3b1d6a0fad2bf8ef0f02fc63f49277c5f44e3bccf27898e6c4ea673d9':
        raise ValueError('original M6A raw lock mismatch')
    freezes=[]
    for key,freeze_key in (('mechanical','mechanical_freeze'),('bridge','bridge_freeze')):
        relative=PATHS[key]; name=Path(relative).name
        freezes.append(frozen_record(relative,data[freeze_key]['artifacts'][name]['sha256']))
    freezes.append(frozen_record(PATHS['registration'],data['registration_manifest']['result']['sha256']))
    count,body_ids,*_=decode_neurons(ROOT/PATHS['neurons'])
    if count!=len(body_ids) or len(set(body_ids))!=count: raise ValueError('neuron body-ID index not unique')
    populations={p['name']:p for p in data['interface']['populations']}
    muscles={p['name']:p for p in data['bodymap']['muscles']}
    if len(populations)!=len(data['interface']['populations']) or len(muscles)!=len(data['bodymap']['muscles']):
        raise ValueError('duplicate exact population names')
    mapping={r['actuator']:r for r in data['mapping']['per_actuator']}
    rows=[row_record(mapping[r['actuator']],r,populations,muscles,body_ids,data['bridge']) for r in table if not r['neural_motor_admission']]
    if len(rows)!=22 or sum(r['neural_motor_admission'] for r in table)!=20: raise ValueError('20/22 partition mismatch')
    lf=inspect_lf(data['registration'],data['candidates'],data['recruitment'],populations,muscles,body_ids)
    after=snapshot()
    return dict(schema=SCHEMA,audit_integrity_passed=before==after,scientific_transitions=0,new_admissions=0,
        current_motor_count=20,model_coordinates=42,remaining_count=22,
        source_hashes_before=before,source_hashes_after=after,legacy_frozen_checks=freezes,
        all_original_raw_freezes_satisfied=all(r['raw_lock_passed'] for r in freezes),
        counts=dict(Counter(r['status'] for r in rows)),rows=rows,lf_reference=lf,
        next_workstream='Reference-backed LF proximal activation/sign and multi-axis population-to-muscle binding prerequisites; no admission or rerun of frozen zero-projection assay.',
        limitations=['No current admission gate passed merely because historical content can be read.',
                     'Canonical Git-content correspondence does not satisfy failed original raw-byte prerequisites.',
                     'No activity-based ranking, new signs, weights, gains, neural drive or stimulation.'])


def markdown(report):
    lines=['# Remaining leg admission evidence matrix','',
        'Current 20/42 motors; 22 audited; 0 newly admitted. Read-only, zero scientific transitions.','',
        '| Index | Coordinate | Candidate populations / neurons | Blocker |','|---:|---|---:|---|']
    for r in report['rows']:
        lines.append(f"| {r['action_index']} | {r['actuator']} | {len(r['candidates'])} / {sum(p['count'] for p in r['candidates'])} | {r['status']} |")
    lines+=['','Historical raw freeze checks: '+str(report['all_original_raw_freezes_satisfied']),
        'See JSON for exact IDs, dense indices, metadata, nulls, raw-lock failures and LF-only reference limits.','']
    return '\n'.join(lines)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args(argv)
    args.output_dir.mkdir(parents=True,exist_ok=False)
    try: report=build()
    except Exception as exc:
        report=dict(schema=SCHEMA,audit_integrity_passed=False,scientific_transitions=0,new_admissions=0,error=f'{type(exc).__name__}: {exc}')
    with (args.output_dir/'audit.json').open('x',encoding='utf-8') as stream:
        json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')
    if report['audit_integrity_passed']:
        (args.output_dir/'matrix.md').write_text(markdown(report),encoding='utf-8')
        print('AUDIT VERIFIED: current 20/42; remaining 22; newly admitted 0; CNS/physics transitions 0.')
        print(json.dumps(report['counts'],indent=2))
        print('Original historical raw freeze checks:',report['all_original_raw_freezes_satisfied'])
    else: print(report['error'])
    return 0 if report['audit_integrity_passed'] else 1


if __name__=='__main__': raise SystemExit(main())
