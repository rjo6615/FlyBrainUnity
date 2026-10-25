"""Static LF selective-actuation contract. No model construction or mutation."""
import argparse
import json
from pathlib import Path
import subprocess

from . import lf_activation_integrator_validation as activation
from . import lf_force_reference as force

ROOT = force.ROOT
DIRECTORY = 'docs/evidence/lf-actuation-contract-v1/'
SCHEMA = 'lf-actuation-contract-v1'
M5A = force.audit.BASE+'full_leg_interface_audit.json'
SIGNATURE = force.audit.BASE+'candidate_motor_channel_experiment/attempt_004/candidate_motor_channel_report.json'
INTEGRATOR = activation.DIRECTORY+'run/validation.json'
LOCKS = {M5A: '758850ea659e49fd93a36a9606bea07a1d329739fbf6be8089060ee6d706c52e',
         SIGNATURE: '0629d05f9bf4c21cd911ac5f43f8f4518db3be5706daaf4d2f23991463645199',
         INTEGRATOR: 'cd545ca6863b2d2468da067b258d9aac0ecb7f3ab8a953f15c0d6574f62eb49b'}
EXTRAS = ('docs/LF_ACTUATION_CONTRACT_V1.md',
          'malecns_backend/embodiment/lf_actuation_contract.py',
          'malecns_backend/embodiment/full_leg_interface.py',
          'malecns_backend/embodiment/tactile_motor_loop_audit.py',
          'malecns_backend/embodiment/_windows_m8_live_condition.py')
BLOCKERS = (
    'CURRENT_NATIVE_IDENTITY_AND_FULL_TRANSMISSION_FORCE_SUPPORT_TABLES_REQUIRED',
    'NATIVE_SELECTIVE_NEUTRALIZATION_AND_RETAINED_CONTROL_PRESERVATION_REQUIRED',
    'MOVING_BODY_SPLIT_INTEGRATION_AND_FORCE_TIMING_VALIDATION_REQUIRED',
    'PHYSICAL_UNITS_GEOMETRY_AND_VELOCITY_DEPENDENCE_REGISTRATION_REQUIRED',
    'ORIGINAL_RAW_SCIENTIFIC_PREREQUISITES_REMAIN_SEPARATE',
    'INDIVIDUAL_TENDON_BINDING_AND_NEURAL_TO_ACTIVATION_EVIDENCE_REQUIRED',
)


def sources():
    result = activation.sources()
    for path in (*LOCKS, *EXTRAS):
        raw = (ROOT/path).read_bytes()
        digest = force.audit.sha(raw if path == INTEGRATOR else raw.replace(b'\r\n', b'\n'))
        if path in LOCKS and digest != LOCKS[path]:
            raise ValueError('static input content/raw lock mismatch: '+path)
        result[path] = digest
    return result


def project_inventory(records, signature, admissions):
    """Project recorded metadata without treating two snapshots as one model."""
    names = list(force.audit.JOINT_NAMES)
    if (len(records) != 42 or [r['actuator_name'] for r in records] != names
            or [r['actuator_index'] for r in records] != list(range(42))
            or [r['actuator'] for r in admissions] != names
            or [r['action_index'] for r in admissions] != list(range(42))
            or sum(r['neural_motor_admission'] is True for r in admissions) != 20
            or any(type(r['neural_motor_admission']) is not bool for r in admissions)):
        raise ValueError('exact authoritative 42-coordinate order and 20 admissions required')
    rows = []
    for record, admission in zip(records, admissions):
        m = record['mujoco_metadata']
        joint = record['actuator_name']
        if (m['joint_name'] != '0/'+joint or m['actuator_name'] != '0/actuator_position_'+joint
                or type(m['joint_id']) is not int or m['joint_id'] < 0
                or type(m['actuator_id']) is not int or m['actuator_id'] < 0
                or m['joint_type'] != 3 or m['actuator_transmission_type'] != 0
                or m['actuator_transmission_ids'] != [m['joint_id'], -1]
                or any(len(m[k]) != 2 or any(type(x) is not int or x < 0 for x in m[k])
                       or m[k][1]-m[k][0] != 1 for k in ('qpos_range', 'dof_range'))):
            raise ValueError('exact M5A hinge/transmission/address metadata required: '+joint)
        rows.append(dict(coordinate=joint, action_index=record['actuator_index'],
            identity_scope='M5A_RECORDED_COMPILED_MODEL_ONLY', compiled=dict(m),
            body_id=None, activation_address=None,
            missing_native_fields=['body_id', 'actuator_actadr', 'actuator_actnum', 'full_force_support'],
            current_neural_admission=admission['neural_motor_admission'],
            policy='REPLACE_IF_SEPARATELY_APPROVED' if joint in force.BASIS else 'PRESERVE'))
    for key in ('actuator_id', 'joint_id'):
        if len({r['compiled'][key] for r in rows}) != 42:
            raise ValueError('native IDs must be unique within the recorded model')
    for key in ('qpos_range', 'dof_range'):
        if len({tuple(r['compiled'][key]) for r in rows}) != 42:
            raise ValueError('coordinate address ranges overlap')
    targets = [next(r for r in rows if r['coordinate'] == n) for n in force.BASIS]
    if any(r['current_neural_admission'] for r in targets):
        raise ValueError('do not replace currently admitted coordinates in this contract')
    dimensions = signature['dimensions']
    actuator_names = signature['inventories']['actuator']
    expected_names = ['actuator_position_'+n for n in names]
    adhesion_names = [leg+'Tarsus5_adhesion' for leg in ('LF', 'LM', 'LH', 'RF', 'RM', 'RH')]
    if (dimensions['nu'] != 48 or dimensions['na'] != 0 or len(actuator_names) != 48
            or actuator_names != expected_names+adhesion_names):
        raise ValueError('separate 48-name historical inventory must include all six adhesion actuators')
    arrays = signature['model_arrays']
    for key, shape in (('actuator_actadr', [48]), ('actuator_actnum', [48]),
                       ('actuator_trnid', [48, 2]), ('actuator_trntype', [48]),
                       ('actuator_gainprm', [48, 10]), ('actuator_biasprm', [48, 10])):
        if arrays[key]['shape'] != shape or len(arrays[key]['sha256']) != 64:
            raise ValueError('recorded array identity/shape missing')
    retained = [r for r in rows if r['policy'] == 'PRESERVE']
    return dict(target_basis=list(force.BASIS), targets=targets, retained_joint_controls=retained,
                retained_admitted_count=sum(r['current_neural_admission'] for r in retained),
                retained_baseline_count=sum(not r['current_neural_admission'] for r in retained),
                separate_signature=dict(identity_scope='CANDIDATE_ATTEMPT004_RECORDED_MODEL_ONLY',
                    path='candidates/joint_LFTarsus1/initialization/ENABLED/physics_model_identity/components',
                    dimensions={k: dimensions[k] for k in ('nq', 'nv', 'nu', 'na', 'njnt', 'nbody')},
                    actuator_names=actuator_names,
                    adhesion=[dict(recorded_name_id=i, name=n, policy='PRESERVE_DISABLED_CONSTANT_ZERO',
                                   transmission_values=None) for i, n in enumerate(actuator_names) if i >= 42],
                    array_hashes={k: arrays[k] for k in ('actuator_actadr', 'actuator_actnum',
                        'actuator_trnid', 'actuator_trntype', 'actuator_gainprm', 'actuator_biasprm')},
                    values_available=False, equivalent_to_m5a_model=False, current_native_capture=False))


def proposed_plan(inventory):
    return dict(target_m5a_actuator_ids=[r['compiled']['actuator_id'] for r in inventory['targets']],
                patch_fields=['actuator_gainprm', 'actuator_biasprm'], patch_operation='ZERO_FULL_SELECTED_ROWS_AFTER_NATIVE_SEMANTICS_CHECK',
                preserved_action_indices=[r['action_index'] for r in inventory['retained_joint_controls']],
                adhesion_policy='PRESERVE_DISABLED_CONSTANT_ZERO', remove_actuators=False,
                global_actuation_disable=False, control_zero_only=False,
                activation_owner='EXTERNAL_SOURCE_STATE_VECTOR_ONLY', native_muscle_states_added=0,
                body_owner='EXISTING_NATIVE_BODY_PATH_ONLY', external_body_time_writes=0,
                native_body_intervals_per_transition=1, external_activation_commits_per_transition=1,
                force_phase='LEFT_ENDPOINT_TOTAL_TENSION_HELD_FOR_BODY_INTERVAL',
                force_buffer_policy='CLEAR_ONLY_OWN_CONTRIBUTION_PRESERVE_FOREIGN_OUTSIDE_TARGET',
                production_enabled=False, coupling_ready=False)


def validate_plan(plan, inventory):
    """Reject unsafe declarations; this verifies no physical intervention."""
    expected = proposed_plan(inventory)
    if set(plan) != set(expected):
        raise ValueError('complete explicit replacement/ownership declaration required')
    failed = [key for key, value in expected.items() if plan[key] != value or type(plan[key]) is not type(value)]
    if failed:
        raise ValueError('unsafe or out-of-scope proposed contract: '+', '.join(failed))
    return True


def build():
    before = sources()
    read = lambda p: json.loads((ROOT/p).read_text(encoding='utf-8'))
    upstream = read(INTEGRATOR)
    ready = activation.preflight()
    evaluation = activation.evaluate(upstream, ready)
    if (not evaluation['integrity_passed'] or not evaluation['all_numerically_accepted']
            or evaluation != upstream['evaluation']):
        raise ValueError('accepted source activation evidence required')
    verified = force.static.load()
    signature = read(SIGNATURE)['candidates']['joint_LFTarsus1']['initialization']['ENABLED']['physics_model_identity']['components']
    inventory = project_inventory(read(M5A)['actuator_records'], signature, verified['static_admission_table'])
    plan = proposed_plan(inventory)
    validate_plan(plan, inventory)
    source = upstream['compiled'][0]
    binding = ready['prior_ready']['binding']
    if not activation.valid_metadata(source, binding):
        raise ValueError('exact source fixture metadata required')
    states = [dict(external_state_index=i, source_fixture_actuator_id=i,
                   source_fixture_actuator_name=source['actuator_names'][i],
                   source_fixture_tendon_id=i, source_fixture_tendon=source['tendon_names'][i],
                   source_fixture_activation_address=source['actadr'][i],
                   identity_scope='ZERO_DOF_SOURCE_FIXTURE_ONLY', flygym_activation_address=None,
                   individual_neuron_assignment=None) for i in range(4)]
    after = sources()
    if before != after:
        raise ValueError('sources changed during static audit')
    return dict(schema=SCHEMA, classification='STATIC_CONTRACT_VERIFIED_COUPLING_BLOCKED',
                source_hashes_before=before, source_hashes_after=after,
                source_hash_modes='canonical LF for static text; exact raw LFS evidence; no raw-lock waiver',
                inventory=inventory, proposed_plan=plan, source_activation_states=states,
                source_integrator_classification=evaluation['classification'],
                original_raw_freezes_satisfied=verified['original_raw_freezes_satisfied'],
                coupling_ready=False, blockers=list(BLOCKERS), current_motor_count=20, new_admissions=0,
                execution=dict(model_constructions=0, mj_forward=0, mj_step=0, solver_calls=0,
                               cns_transitions=0, model_or_state_mutations=0),
                roadmap=dict(completed='Static selective LF actuation partition and state-ownership design',
                    next='Separately specify current native inventory and no-integration neutralization/preservation audit',
                    later='Physical registration/units, coupled numerics, binding and neural conversion before moving-fly coupling'))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--build', action='store_true')
    group.add_argument('--report', type=Path)
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args(argv)
    if args.build:
        if args.output_dir is None: parser.error('--build requires a fresh --output-dir')
        args.output_dir.mkdir(parents=True, exist_ok=False)
        try:
            report = build()
            report['commit'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        except Exception as exc:
            report = dict(schema=SCHEMA, classification='STATIC_AUDIT_FAILED', error=f'{type(exc).__name__}: {exc}')
        with (args.output_dir/'audit.json').open('x', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write('\n')
        if report['classification'] == 'STATIC_AUDIT_FAILED':
            print('STATIC AUDIT FAILED; evidence retained:', report['error'])
            return 1
    else:
        report = json.loads(args.report.read_text(encoding='utf-8'))
        actual = build()
        if {k: v for k, v in report.items() if k != 'commit'} != actual:
            raise ValueError('saved static contract/source verification failed')
    print('STATIC CONTRACT VERIFIED; coupling BLOCKED; no model construction, forward, integration or CNS.')
    for row in report['inventory']['targets']:
        m = row['compiled']
        print(f"M5A {row['coordinate']}: action{row['action_index']}, actuator{m['actuator_id']}, joint{m['joint_id']}, qpos{m['qpos_range']}, DOF{m['dof_range']}")
    print('Preserved design: 39 joint controls (20 admitted +19 baseline), plus6 separately scoped adhesion actuators.')
    print('Current20/42; new admissions0; original raw prerequisites:', report['original_raw_freezes_satisfied'])
    print('Roadmap next:', report['roadmap']['next'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
