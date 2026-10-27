"""Static prospective assistance plan. No runtime, model mutation or experiment."""
import argparse
import hashlib
import json
from pathlib import Path

from .protocol import JOINT_NAMES

ROOT = Path(__file__).resolve().parents[2]
AUTHORITY = 'docs/evidence/balance-contribution-v1/protocol.json'
AUTHORITY_SHA256 = '2ea0a8b94476cdc4a1c7040dfa3d5a40048e4242491ec42bb4af3761be998a20'
REFERENCE = 'docs/evidence/controlled-live-balance-v1_1/run-desktop-01/report.json'
REFERENCE_SHA256 = 'eaf95d2b8b4b270e8368db3025919cc438054bdc93382f4987f12edfffb138f2'
SOURCE_PATHS = (
    'malecns_backend/live/assistance_contribution_plan.py',
    'docs/ASSISTANCE_CONTRIBUTION_V1.md',
    'malecns_backend/live/protocol.py',
    'malecns_backend/live/controlled_live_balance_v1_1.py',
    'malecns_backend/live/controlled_live_balance.py',
    'malecns_backend/live/balance_contribution.py',
    'malecns_backend/live/balance_source_prerequisites.py',
    'malecns_backend/embodiment/lf_native_isolation.py',
    'malecns_backend/embodiment/lf_actuation_contract.py',
    'malecns_backend/embodiment/_windows_m8_live_condition.py',
    'malecns_backend/live/contact_context.py',
    'malecns_backend/live/tactile_recovery_metrics.py',
)
BASE_CONDITIONS = ('NC','WC','NP','WP')
ARM_IDS = tuple(m+'_'+c for m in ('A','R') for c in BASE_CONDITIONS)


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


def read_json(path):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result: raise ValueError('duplicate JSON key: '+key)
            result[key]=value
        return result
    def constant(value):
        raise ValueError('nonfinite JSON constant: '+value)
    return json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=pairs,parse_constant=constant)


def locked_json(path,expected):
    if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=expected:
        raise ValueError('original reference bytes changed: '+path)
    return read_json(ROOT/path)


def coordinate_partition(authority):
    """Logical action authority only. No action-index/native-ID equivalence."""
    admitted,baseline=authority['motors'],authority['unadmitted_baseline_only']
    if len(admitted)!=20 or len(baseline)!=22:
        raise ValueError('frozen20/22partition required')
    rows=admitted+baseline
    if (len(JOINT_NAMES)!=42 or len({r['name'] for r in rows})!=42
            or len({r['action_index'] for r in rows})!=42):
        raise ValueError('complete disjoint coordinate/action authority required')
    for row in rows:
        index=row['action_index']
        if type(index) is not int or not 0<=index<42 or JOINT_NAMES[index]!=row['name']:
            raise ValueError('exact canonical coordinate/action identity required')
    project=lambda values:[dict(coordinate=r['name'],action_index=r['action_index'],
        native_actuator_id=None,native_joint_id=None,native_body_id=None,qpos_range=None,dof_range=None)
        for r in sorted(values,key=lambda row:row['action_index'])]
    return project(admitted),project(baseline)


def expected_model_phase(arm_id,state_index):
    """Expected sampled phase, not an actuator mutation/force implementation."""
    if arm_id not in ARM_IDS or type(state_index) is not int or not 0<=state_index<=20000:
        raise ValueError('declared arm and exact scientific state index required')
    return 'MR' if arm_id.startswith('R_') and state_index>=5006 else 'M0'


def build():
    authority=locked_json(AUTHORITY,AUTHORITY_SHA256)
    reference=locked_json(REFERENCE,REFERENCE_SHA256)
    if (reference['run_status']!='COMPLETE' or reference['schema']!='controlled-live-balance-execution-v1.1'
            or reference['evaluation']['scientific']['accepted'] is not True
            or reference['design']!=authority):
        raise ValueError('unchanged accepted scientific reference required')
    retained,selected=coordinate_partition(authority)
    arms=[dict(id=arm,base_condition=arm.split('_')[1],
        baseline22_policy='NEUTRALIZE_AFTER_STATE_5005' if arm.startswith('R_') else 'HOLD_ORIGINAL',
        neural20_policy='WITHDRAW_BEFORE_SAFETY_TICK_1001' if arm.split('_')[1].startswith('W') else 'CONTINUE',
        pulse=arm.endswith('P')) for arm in ARM_IDS]
    return dict(schema='assistance-contribution-design-v1',status='DESIGN_ONLY_NOT_IMPLEMENTED_NOT_RUN',
        question='Contribution of22baseline-only position servos and existing20decoder inputs under fixed push/no-push',
        authority=dict(path=AUTHORITY,raw_sha256=AUTHORITY_SHA256),
        reference=dict(path=REFERENCE,raw_sha256=REFERENCE_SHA256,
            scope='READ_RECORDED_ACCEPTANCE_NOT_REEVALUATED_IN_THIS_DESIGN',
            known_behavior=reference['evaluation']['scientific']['behavior']['primary_label']),
        arms=arms,seed=1,physics_dt_s=.0001,neural_dt_ms=.5,duration_s_per_arm=2,
        planned_physics_transitions_per_arm=20000,planned_states_per_arm=20001,planned_neural_updates_per_arm=4000,
        planned_physics_transitions_total=160000,planned_states_total=160008,planned_neural_updates_total=32000,
        retained_neural20=retained,selected_baseline22=selected,
        runtime_native_bindings='UNBOUND_ACTUAL_MODEL_VALIDATION_REQUIRED',
        mechanical_event=dict(after_recorded_state=5005,before_outgoing_transition=5005,
            first_affected_state=5006,fields=['actuator_gainprm','actuator_biasprm'],operation='ZERO_FULL_SELECTED_ROWS',
            mutate_controls=False,mutate_retained20_parameters=False,mutate_passive_mechanics=False,
            live_forward_reset_or_extra_step=False,release_is_all_assistance_removed=False),
        qualification=dict(scope='FIRST_ACTUAL_MODEL_SHADOW_DATA_ONLY_BEFORE_SCIENTIFIC_STEPS',
            additional_flygym_models=0,additional_cns_initializations=0,shadow_mjdata_allocations=1,
            control_signs=[1,-1],velocity_signs=[1,-1],control_offset_rad=.01,velocity_rad_s=.1,
            sign_by_action_index='(-1)^index',all42_ctrl_in_original_ranges_required=True,
            phases=['BASELINE','NEUTRALIZED','RESTORED_BASELINE'],explicit_shadow_resets=12,
            explicit_shadow_forwards=12,live_forwards=0,live_resets=0,integration=0,cns_updates=0,
            constructor_internals='MEASURE_SEPARATELY_NOT_INFERRED_ABSENT',
            force_zero_preservation_atol=1e-10,force_projection_atol=1e-8,baseline_exposure_floor=1e-8,
            evidence_reused='LF_ISOLATION_MECHANISM_NOT_22COORDINATE_VALIDATION'),
        inherited_science=dict(authority_path=AUTHORITY,neural_gains_weights_drive_signs_unchanged=True,
            proprioceptive_neurons=392,fixed_cns_rng_slots=392,tactile_enabled=False,
            decoder_withdrawal_tick=1001,force_world=[0,1.024,0],force_outgoing_start=5000,
            force_outgoing_stop_exclusive=5200,terminal_update_retained_unapplied=True,
            baseline_states_inclusive=[4000,5000],cleared_window_states_inclusive=[5201,20000],
            original_bands_dwell_resolution_unchanged=True,contact_force_rtol=1e-10,contact_force_atol=1e-14),
        comparisons=dict(mechanical_pairs=[[f'A_{c}',f'R_{c}'] for c in BASE_CONDITIONS],
            neural_pairs=[[m+'_NC',m+'_WC'] for m in ('A','R')]+[[m+'_NP',m+'_WP'] for m in ('A','R')],
            report_all_pairs=True,posture_label_requires_peak_and_mean_difference_deg=.25,
            control_posture_loss_qualifier='CONTROL_POSTURE_LOSS_CONFOUNDS_RECOVERY',
            additive_balance_fraction_claim=False),
        automatic_retries=0,reuse_previous_controls=False,resume=False,stop_on_fall=False,
        native_execution_in_this_update=False,runner_implemented=False,native_binding_completed=False,
        native_qualification_passed=False,execution_prerequisites_verified=False,
        independent_balance_proven=False,gait_proven=False,new_motor_admissions=0,motor_coverage=[20,42],
        source_canonical_lf_sha256={p:hashlib.sha256((ROOT/p).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
                                     for p in SOURCE_PATHS})


def verify(path):
    if canonical(read_json(path))!=canonical(build()):
        raise ValueError('saved prospective plan differs from versioned design/authorities')
    return True


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    choice=parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--output',type=Path,help='exclusive new plan JSON; no experiment')
    choice.add_argument('--verify',type=Path,help='read-only static design check')
    args=parser.parse_args(argv)
    if args.verify:
        verify(args.verify)
    else:
        if args.output.exists():parser.error('output exists; never overwrite a saved plan')
        value=build();args.output.parent.mkdir(parents=True,exist_ok=True)
        with args.output.open('x',encoding='utf-8',newline='\n') as stream:
            json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')
    print('STATIC DESIGN VERIFIED:8planned arms;22baseline servos selected;20neural servos retained;'
          '160000physics/32000neural PLANNED;no native or CNS experiment executed.')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
