"""Eight-arm campaign gates/evaluator. Synthetic models/sessions only; no native assay."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest

from malecns_backend.live import assistance_campaign as v

mechanical, base = v.mechanical, v.base


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, v.ROOT/path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


native_fixture = load('assistance_native_fixture', 'tests/test_assistance_native.py')
balance_fixture = load('balance_v1_reference_fixture', 'tests/test_balance_contribution.py')


def checked():
    expected = v.guard.specification()['source_graph_authority']
    return dict(verified=True, checks={k: True for k in ('design', 'original_authorities', 'original_neural_data')},
        errors={}, scientific_transitions=0, native_constructions=0, cns_initializations=0,
        environment=dict(verified=True, observed={k: value for k, value in base.design()['expected_environment'].items()
                                                if k != 'dependency_changes_allowed'}, mismatches={}),
        complete_source_schema='balance-loader-source-prerequisites-v1',
        orientation_source=dict(verified=True, path=v.guard.source_guard.GRAPH, expected=expected,
                                observed={k: expected[k] for k in ('sha256', 'bytes')}))


def boundary(pid):
    return dict(pid=pid, parent_pid=100, launch_pid=pid, controller_pid=100, launcher_parent_pid=100,
                mode='direct', commit='synthetic', fresh_registry=dict(existing_names=[], default_name=0))


@pytest.fixture(scope='module')
def world():
    """Synthetic 160,008-state campaign; never claimed as simulated physics."""
    with pytest.MonkeyPatch.context() as mp:
        model, data, api, inv, record = native_fixture.fixture.__wrapped__(mp)
        qualification = native_fixture.qualification((model, data, api, inv, record))
        neutral = mechanical.neutral_record(record, inv)
        selected = [r['actuator_id'] for r in mechanical.partition(inv)[1]]
        api.mj_forward(model, data)
        m0_force = mechanical.force_record(api, model, data)
        mechanical.write_rows(model, record, inv, True)
        api.mj_forward(model, data)
        mr_force = mechanical.force_record(api, model, data)
        mechanical.write_rows(model, record, inv, False)
    null = balance_fixture.null_report()['arms']
    ctx = null['NC']['context']  # one shared actual context, as in all real arms
    ctx['identity']['body_names'] += [f'fly/Extra{i}' for i in range(12)]
    gain, bias = np.array(model.actuator_gainprm), np.array(model.actuator_biasprm)
    config = dict(timestep=.0001, arrays=dict(actuator_gainprm=gain.tolist(), actuator_biasprm=bias.tolist()))
    gain[selected], bias[selected] = 0., 0.
    released = dict(timestep=.0001, arrays=dict(actuator_gainprm=gain.tolist(), actuator_biasprm=bias.tolist()))
    ctx.update(configuration=config, configuration_sha256=base.context.digest(config), native_inventory=inv)
    digests = dict(M0=base.context.digest(config), MR=base.context.digest(released))
    source = v.sources()
    arms = {}
    for pid, arm_id in enumerate(v.ARM_IDS, 200):
        condition = arm_id.split('_')[1]
        samples, mech = [], []
        for i, s in enumerate(null[condition]['samples']):
            phase = v.plan.expected_model_phase(arm_id, i)
            xfrc = [[0.]*6 for _ in range(50)]
            if condition.endswith('P') and 5001 <= i <= 5200:
                xfrc[37][1] = 1.024
            samples.append(dict(s, xfrc_applied=xfrc, configuration_sha256=digests[phase]))
            force = mr_force if phase == 'MR' else m0_force
            mech.append(dict(force, state_index=i, time_s=s['time_s'], ctrl=s['ctrl'], xfrc_applied=xfrc,
                             model_sha256=(neutral if phase == 'MR' else record)['sha256']))
        event = dict(state_index=5005, time_s=5005*.0001, before=record, selected_actuator_ids=selected,
            after=neutral if arm_id.startswith('R_') else record,
            operation='ZERO_FULL_SELECTED_ROWS' if arm_id.startswith('R_') else 'OBSERVE_ONLY',
            protected_before={'live': 'same', 'protected': 'same'}, protected_after={'live': 'same', 'protected': 'same'})
        arms[arm_id] = dict(null[condition], samples=samples, arm_id=arm_id, schema='assistance-arm-adapter-v1',
            full_scientific_audit_completed=False, assistance=dict(event=event, samples=mech, qualification=qualification,
                context=dict(schema=mechanical.SCHEMA, arm_id=arm_id, inventory=inv, original=record, neutral=neutral)),
            worker_sources_before=source, worker_sources_after=source, complete_preflight_before=checked(),
            complete_preflight_after=checked(), process_boundary=boundary(pid),
            transferred_qualification=None if arm_id == v.FIRST else dict(path=v.QUALIFICATION, sha256='synthetic'))
    report = dict(schema=v.SCHEMA, campaign=v.CAMPAIGN, specification=v.specification(), design=base.design(),
        run_status='COMPLETE', preflight=checked(), preflight_after=checked(), sources_before=source,
        sources_after=source, prior_full_body_review_note='synthetic fixture only', controller_pid=100,
        implementation_commit='synthetic', qualification_artifact=dict(path=v.QUALIFICATION, sha256='synthetic'),
        arm_artifacts={a: dict(path=a+'.json.gz', sha256='synthetic') for a in v.ARM_IDS},
        display_artifacts={a: dict(path=a+'.display.json.gz', sha256='synthetic') for a in v.ARM_IDS})
    return dict(arms=arms, report=report, qualification=qualification, digests=digests, selected=selected)


def evaluate(world, arms=None, report=None, qualification=None):
    arms = arms or world['arms']
    def missing_display(*args):
        raise OSError('synthetic fixture has no display journal')
    return v.evaluate(report or world['report'], '.', loader=lambda folder, a, artifact: arms[a],
        display_loader=missing_display, qualification_loader=lambda folder, artifact: qualification or world['qualification'],
        reference_comparator=lambda *args: dict(status='SYNTHETIC_NOT_COMPARED'))['scientific']


@pytest.fixture(scope='module')
def accepted(world):
    return evaluate(world)


def changed(world, arm_id, index=None, **fields):
    arms = dict(world['arms'])
    arms[arm_id] = dict(arms[arm_id], samples=list(arms[arm_id]['samples']))
    if index is not None:
        arms[arm_id]['samples'][index] = dict(arms[arm_id]['samples'][index], **fields)
    return arms


def test_protocol_policy_and_frozen_sources_are_locked():
    p = v.specification()
    assert [a['id'] for a in p['arms']] == list(v.ARM_IDS) == v.CAMPAIGN['arm_order']
    assert v.CAMPAIGN['automatic_retries'] == 0 and not v.CAMPAIGN['resume'] and not v.CAMPAIGN['stop_on_fall']
    s = v.sources()
    for path in (v.PROTOCOL, v.MODULE, v.adapter.MANIFEST, *v.adapter.SOURCES, *v.plan.SOURCE_PATHS,
                 'malecns_backend/live/balance_source_prerequisites.py', 'malecns_backend/live/controlled_live_balance.py'):
        assert path in s
    assert v.preflight is v.guard.preflight and v.verified_preflight(checked())


def test_synthetic_eight_arms_accepted_with_explicit_piecewise_context(accepted):
    assert accepted['accepted'], accepted.get('reason')
    assert all(accepted['checks'].values()) and accepted['qualification']['passed']
    for arm_id, audit in accepted['arms'].items():
        assert audit['model_context'] == ('M0_CONSTANT_FROZEN_AUDITOR_ACCEPTED' if arm_id.startswith('A_')
                                          else 'PIECEWISE_M0_0_5005_MR_5006_20000')
        assert accepted['mechanical'][arm_id]['states'] == 20001
    assert set(accepted['pair_exposure']) == {'A_NC_vs_A_WC', 'A_NP_vs_A_WP', 'R_NC_vs_R_WC', 'R_NP_vs_R_WP',
                                              'A_NC_vs_R_NC', 'A_WC_vs_R_WC', 'A_NP_vs_R_NP', 'A_WP_vs_R_WP'}
    assert accepted['same_policy_mechanical_prefix_diagnostic'] == dict.fromkeys(base.CONDITIONS, 'EXACT_MATCH')
    b = accepted['behavior']
    assert set(b['comparisons']) == {'A_NC_vs_R_NC', 'A_WC_vs_R_WC', 'A_NP_vs_R_NP', 'A_WP_vs_R_WP',
                                     'A_NC_vs_A_WC', 'R_NC_vs_R_WC', 'A_NP_vs_A_WP', 'R_NP_vs_R_WP'}
    assert all(c['tilt_label'] == 'MIXED_OR_UNRESOLVED' for c in b['comparisons'].values())
    # Synthetic arms have zero foot contacts, so the declared support-loss qualifier must appear.
    assert all(r['qualifiers'] == ['CONTROL_POSTURE_LOSS_CONFOUNDS_RECOVERY'] for r in b['own_control_recovery'].values())
    assert not b['independent_balance_proven'] and not b['gait_proven'] and b['motor_coverage'] == [20, 42]
    assert accepted['unity_replay_entry_point'] == 'NOT_IMPLEMENTED_FOR_THIS_SCHEMA'


def test_frozen_constant_model_auditor_still_rejects_released_arm(world):
    with pytest.raises(ValueError, match='configuration'):
        base.audit_arm(world['arms']['R_NC'])
    base.audit_arm(world['arms']['A_NC'])


@pytest.mark.parametrize('arm_id,index,phase', [('R_WC', 5006, 'M0'), ('R_NP', 20000, 'M0'),
                                                ('R_NC', 5005, 'MR'), ('A_WP', 5006, 'MR')])
def test_piecewise_phase_violations_are_integrity_failures(world, arm_id, index, phase):
    arms = changed(world, arm_id, index, configuration_sha256=world['digests'][phase])
    with pytest.raises(ValueError, match='configuration'):
        v.audit_scientific(arms[arm_id], arm_id)


def mechanical_change(world, arm_id, index, field, value):
    arms = dict(world['arms'])
    evidence = dict(arms[arm_id]['assistance'], samples=list(arms[arm_id]['assistance']['samples']))
    sample = dict(evidence['samples'][index])
    sample[field] = copy.deepcopy(sample[field])
    value(sample[field])
    evidence['samples'][index] = sample
    arms[arm_id] = dict(arms[arm_id], assistance=evidence)
    return arms


def test_selected_force_after_release_including_terminal_state_is_rejected(world):
    aid = world['selected'][0]
    dof = next(r['dof_range'][0] for r in world['arms']['R_WP']['context']['native_inventory']['rows']
               if r['actuator_id'] == aid)
    arms = mechanical_change(world, 'R_WP', 20000, 'actuator_force', lambda f: f.__setitem__(aid, f[aid]+1.))
    arms = dict(arms, R_WP=mechanical_change(dict(world, arms=arms), 'R_WP', 20000, 'qfrc_actuator',
                                             lambda f: f.__setitem__(dof, f[dof]+1.))['R_WP'])
    with pytest.raises(ValueError, match='neutralized force'):
        v.audit_mechanical(arms['R_WP'], 'R_WP', world['qualification'])


def test_mechanical_and_scientific_states_must_be_the_same_samples(world):
    arms = mechanical_change(world, 'A_NP', 7000, 'xfrc_applied', lambda f: f[37].__setitem__(1, 1e-6))
    with pytest.raises(ValueError, match='different states'):
        v.audit_mechanical(arms['A_NP'], 'A_NP', world['qualification'])


def test_later_arm_must_carry_the_transferred_first_model_qualification(world):
    arms = dict(world['arms'])
    other = copy.deepcopy(world['qualification']); other['center'][7] += 1e-3
    arms['R_NC'] = dict(arms['R_NC'], assistance=dict(arms['R_NC']['assistance'], qualification=other))
    with pytest.raises(ValueError, match='qualified first M0'):
        v.audit_mechanical(arms['R_NC'], 'R_NC', world['qualification'])
    arms = dict(world['arms'])
    arms['A_WC'] = dict(arms['A_WC'], transferred_qualification=None)
    assert 'identity' in evaluate(world, arms)['reason']


def test_failed_saved_qualification_is_not_promoted(world):
    failed = dict(world['qualification'], status='FAILED_QUALIFICATION')
    def loader(folder, artifact):
        mechanical.evaluate_qualification(failed)
    result = v.evaluate(world['report'], '.', loader=lambda *a: pytest.fail('arm loaded after failed qualification'),
                        qualification_loader=loader)['scientific']
    assert not result['accepted'] and 'qualification' in result['reason']


@pytest.fixture(scope='module')
def proofs(world):
    return {a: v.proof(arm) for a, arm in world['arms'].items()}


@pytest.mark.parametrize('arm_id,field,index', [('R_WP', 'same_push_prefix', 5004), ('R_NC', 'physical_prefix', 4999),
    ('A_WC', 'neural_prefix', 999), ('R_NP', 'rng', 3999), ('R_WC', 'pre_gate', None), ('R_NC', 'physics', 5005)])
def test_declared_cross_arm_prefixes_and_rng_are_exact(proofs, arm_id, field, index):
    assert v.compare_all(proofs)['A_NC_vs_R_NC']['first_physical_difference_state'] is None
    altered = dict(proofs)
    altered[arm_id] = dict(proofs[arm_id])
    if index is None:
        altered[arm_id][field] = 'corrupt'
    else:
        altered[arm_id][field] = list(proofs[arm_id][field]); altered[arm_id][field][index] = 'corrupt'
    with pytest.raises(ValueError):
        v.compare_all(altered)


def test_mechanical_pair_exposure_begins_at_first_affected_state(proofs):
    altered = dict(proofs)
    altered['R_WP'] = dict(proofs['R_WP'], physics=list(proofs['R_WP']['physics']),
                           actions=list(proofs['R_WP']['actions']))
    altered['R_WP']['physics'][5006] = altered['R_WP']['actions'][5007] = 'diverged'
    assert v.compare_all(altered)['A_WP_vs_R_WP'] == dict(first_actual_outgoing_command_difference=5006,
        first_physical_difference_state=5006, first_actual_command_effect_state=5007)


def test_full_run_rng_mismatch_is_rejected_per_arm(world):
    neural = list(world['arms']['R_WP']['neural'])
    neural[3999] = dict(neural[3999], draws=391)
    with pytest.raises(ValueError, match='RNG'):
        v.audit_scientific(dict(world['arms']['R_WP'], neural=neural), 'R_WP')


@pytest.mark.parametrize('field,value', [('run_status', 'INCOMPLETE'), ('preflight_after', {'verified': True}),
    ('arm_artifacts', {}), ('qualification_artifact', None), ('prior_full_body_review_note', ' ')])
def test_incomplete_or_unguarded_controller_never_loads_or_accepts(world, field, value):
    report = dict(world['report'], **{field: value})
    result = v.evaluate(report, '.', loader=lambda *a: pytest.fail('loaded unaccepted campaign'))['scientific']
    assert not result['accepted'] and not result['unity_replay_eligible']


def test_duplicate_worker_process_is_rejected(world):
    arms = dict(world['arms'])
    arms['A_WC'] = dict(arms['A_WC'], process_boundary=boundary(200))
    assert 'distinct' in evaluate(world, arms)['reason']


def pose(z=1., angle=0.):
    q = [np.cos(np.radians(angle)/2), np.sin(np.radians(angle)/2), 0., 0.]
    return np.array([0., 0., z]+q+[0.]*42)


def test_tilt_labels_contrasts_and_posture_loss_qualifier_follow_declared_rules(world):
    audits = {a: dict(ground_support_counts=[6]*20001, calibration_support_counts=[0]*20001,
                      unexpected_distal_contact_counts=[0]*20001, contact_correspondence_mismatch_counts=[0]*20001,
                      commands=dict(first_exposed_counterfactual_outgoing_transition=5005)) for a in v.ARM_IDS}
    poses = {}
    for arm_id in v.ARM_IDS:
        rows = []
        for i in range(20001):
            z = .4 if arm_id == 'R_NC' and i >= 6000 else 1.
            tilt = 10. if arm_id == 'A_NP' and i >= 5100 else 0.
            rows.append(dict(qpos=pose(z, tilt), qvel=np.zeros(48)))
        poses[arm_id] = dict(samples=rows)
    result = v.behavior(poses, audits, v.specification())
    c = result['comparisons']
    assert c['A_NP_vs_R_NP']['tilt_label'] == 'HIGHER_WORLD_TILT_IN_A_NP'
    assert c['A_NP_vs_A_WP']['tilt_label'] == 'HIGHER_WORLD_TILT_IN_A_NP'
    assert c['R_NC_vs_R_WC']['tilt_label'] == 'MIXED_OR_UNRESOLVED'
    assert result['own_control_recovery']['R_NP']['qualifiers'] == ['CONTROL_POSTURE_LOSS_CONFOUNDS_RECOVERY']
    assert result['own_control_recovery']['A_NP']['qualifiers'] == []
    assert c['R_NC_vs_R_WC']['qualifiers'] == [] and c['R_NP_vs_R_WP']['qualifiers'] == [
        'R_NP_CONTROL_POSTURE_LOSS_CONFOUNDS_RECOVERY']
    root = result['signed_contrasts']['root_position']
    # (R_NP-R_NC)-(A_NP-A_NC) at fixed neural input: height drop in R_NC enters with negative sign.
    assert root['mechanical_push_at_neural']['N'][-1] == [0., 0., .6]
    assert root['neural_push_R_minus_A'][-1] == [0., 0., .6]
    assert result['levels']['A']['primary_label'] == 'HIGHER_PUSHED_WORLD_TILT_WITH_NEURAL_INPUT'


# ---- controller lifecycle -------------------------------------------------

def run_controller(tmp_path, child, *, note='user reviewed V1.1 saved replay', verified=True):
    with patch.object(v, 'preflight', return_value=dict(checked(), verified=verified)), \
            patch.object(v, 'committed', return_value='commit'), \
            patch.object(v, 'evaluate', return_value=dict(scientific=dict(accepted=False, status='INCONCLUSIVE_INTEGRITY'))):
        return v.execute(tmp_path/'campaign', live=True, review_note=note, child_runner=child)


def receipt(arm_id, status='COMPLETE', qualification=None):
    return dict(arm_id=arm_id, run_status=status, artifact=dict(path=arm_id+'.json.gz', sha256='synthetic'),
                display_artifact=dict(path=arm_id+'.display.json.gz', sha256='synthetic'),
                qualification_artifact=qualification)


@pytest.mark.parametrize('note,verified', [('', True), ('reviewed', False)])
def test_controller_refuses_before_any_worker_or_commit(tmp_path, note, verified):
    report = run_controller(tmp_path, lambda *a: pytest.fail('worker launched'), note=note, verified=verified)
    assert report['run_status'] == 'ERROR' and not report['scientific_experiment_started']
    assert report['preflight_after']['verified'] is verified and not (tmp_path/'campaign/controller.json').exists()


def test_failed_first_qualification_stops_campaign_and_keeps_partial(tmp_path):
    calls = []
    def child(folder, arm_id, lock, transfer):
        calls.append((arm_id, transfer))
        partial = v.save(folder/v.QUALIFICATION, dict(status='FAILED_QUALIFICATION', cases=[{'retained': True}]))
        return receipt(arm_id, 'ERROR', partial), False
    report = run_controller(tmp_path, child)
    assert calls == [('A_NC', None)] and report['run_status'] == 'INCOMPLETE'
    assert report['qualification_artifact'] is None and list(report['arm_artifacts']) == ['A_NC']
    saved = json.loads((tmp_path/'campaign/A_NC.controller-receipt.json').read_text())
    assert saved['qualification_artifact']['path'] == v.QUALIFICATION
    assert not (tmp_path/'campaign/qualification-transfer.json').exists()


def test_valid_qualification_is_transferred_unchanged_to_every_later_arm(tmp_path, world):
    calls = []
    def child(folder, arm_id, lock, transfer):
        calls.append((arm_id, transfer))
        made = v.save(folder/v.QUALIFICATION, world['qualification']) if arm_id == v.FIRST else None
        return receipt(arm_id, qualification=made), False
    report = run_controller(tmp_path, child)
    assert [a for a, _ in calls] == list(v.ARM_IDS) and report['run_status'] == 'COMPLETE'
    transfer = report['qualification_artifact']
    assert calls[0][1] is None and all(t == transfer for _, t in calls[1:])
    saved = json.loads((tmp_path/'campaign/qualification-transfer.json').read_text())
    assert saved['artifact'] == transfer and saved['evaluation']['passed']


def test_corrupt_transfer_stops_before_second_arm(tmp_path, world):
    calls = []
    def child(folder, arm_id, lock, transfer):
        calls.append(arm_id)
        made = v.save(folder/v.QUALIFICATION, world['qualification'])
        return receipt(arm_id, qualification=dict(made, sha256='0'*64)), False
    report = run_controller(tmp_path, child)
    assert calls == ['A_NC'] and report['run_status'] == 'ERROR' and 'SHA256' in report['error']


def test_stop_preserves_completed_receipts_and_never_starts_later_arms(tmp_path, world):
    calls = []
    def child(folder, arm_id, lock, transfer):
        calls.append(arm_id)
        made = v.save(folder/v.QUALIFICATION, world['qualification']) if arm_id == v.FIRST else None
        if arm_id == 'A_NP':
            v.save(folder/'STOP.json', dict(reason='synthetic user stop'))
            return receipt(arm_id, 'ERROR'), True
        return receipt(arm_id, qualification=made), False
    report = run_controller(tmp_path, child)
    assert calls == ['A_NC', 'A_WC', 'A_NP'] and report['run_status'] == 'INCOMPLETE'
    assert list(report['arm_artifacts']) == ['A_NC', 'A_WC', 'A_NP']


def test_default_output_is_construction_free_and_exclusive(tmp_path):
    with patch.object(v, 'preflight', return_value=checked()), \
            patch.object(v, 'run_child', side_effect=AssertionError('launched')), \
            patch.object(v, 'committed', side_effect=AssertionError('commit gate reached')):
        report = v.execute(tmp_path/'check')
        assert report['run_status'] == 'NOT_RUN' and not report['evaluation']['scientific']['accepted']
        with pytest.raises(FileExistsError):
            v.execute(tmp_path/'check')


# ---- worker lifecycle -----------------------------------------------------

class FixtureFly:
    _existing_fly_names = set()
    _default_fly_name = 0


def controller(folder, arm_id, transfer=None):
    folder.mkdir(exist_ok=True)
    made = v.save(folder/'controller.json', dict(schema=v.SCHEMA, campaign=v.CAMPAIGN, specification=v.specification(),
        sources=v.sources(), commit='fixture', prior_full_body_review_note='synthetic fixture only',
        complete_preflight=checked()))
    request = folder/f'{arm_id}.request.json'
    v.save(request, dict(arm_id=arm_id, controller_sha256=made['sha256'], qualification=transfer))
    return request


def run_worker(request, *, run=None, after=None):
    states = iter([checked(), after or checked()])
    with patch.object(v, 'committed', return_value='fixture'), \
            patch.object(v.original, 'process_boundary', return_value=boundary(300)), \
            patch.object(v, 'preflight', side_effect=lambda: next(states)), \
            patch.object(base, 'static_authority', return_value=({}, [])), \
            patch.dict(sys.modules, {'flygym': SimpleNamespace(Fly=FixtureFly)}), \
            patch.object(v.adapter, 'run_arm', side_effect=run or AssertionError('scientific arm reached')):
        return v.worker(request)


def done(folder, arm_id):
    return json.loads((folder/f'{arm_id}.done.json').read_text())


def test_worker_prerequisite_failure_never_reaches_authority_and_keeps_receipts(tmp_path):
    request = controller(tmp_path, 'A_NC')
    with patch.object(v, 'committed', return_value='fixture'), \
            patch.object(v.original, 'process_boundary', return_value=boundary(300)), \
            patch.object(v, 'preflight', return_value=dict(checked(), verified=False)), \
            patch.object(base, 'static_authority', side_effect=AssertionError('authority reached')):
        assert v.worker(request) == 1
    receipt_ = done(tmp_path, 'A_NC')
    arm = v.read_arm(tmp_path, 'A_NC', receipt_['artifact'])
    assert arm['run_status'] == 'ERROR' and 'before initialization' in arm['worker_error']
    assert receipt_['qualification_artifact']['path'] == v.QUALIFICATION


def test_initialization_failure_inside_adapter_is_saved_not_retried(tmp_path):
    request = controller(tmp_path, 'A_NC')
    assert run_worker(request, run=ValueError('Trial binding refused')) == 1
    arm = v.read_arm(tmp_path, 'A_NC', done(tmp_path, 'A_NC')['artifact'])
    assert 'Trial binding refused' in arm['worker_error'] and arm['samples'] == []


def test_failed_first_qualification_partial_is_published_separately(tmp_path):
    request = controller(tmp_path, 'A_NC')
    def run(arm_id, protocol, table, stop, *, qualification):
        assert arm_id == 'A_NC' and qualification is None
        partial = dict(status='FAILED_QUALIFICATION', cases=[{'case': 1}], error='ValueError: vacuous')
        return dict(arm_id=arm_id, condition='NC', run_status='ERROR', samples=[{'state': 0}], neural=[],
                    assistance=dict(qualification=partial, samples=[{'mechanical': 0}])), {'display': 'partial'}
    assert run_worker(request, run=run) == 1
    receipt_ = done(tmp_path, 'A_NC')
    assert receipt_['mechanical_states'] == 1 and receipt_['states'] == 1
    saved = v.read_artifact(tmp_path, receipt_['qualification_artifact'], v.QUALIFICATION)
    assert saved['status'] == 'FAILED_QUALIFICATION' and saved['cases'] == [{'case': 1}]
    assert v.read_display(tmp_path, 'A_NC', receipt_['display_artifact']) == {'display': 'partial'}


def test_worker_rejects_tampered_transfer_before_native_authority(tmp_path, world):
    made = v.save(tmp_path/v.QUALIFICATION, world['qualification'])
    request = controller(tmp_path, 'R_WP', dict(made, sha256='1'*64))
    assert run_worker(request) == 1
    assert 'SHA256' in v.read_arm(tmp_path, 'R_WP', done(tmp_path, 'R_WP')['artifact'])['worker_error']


def test_worker_passes_reevaluated_transfer_and_detects_changed_post_prerequisites(tmp_path, world):
    made = v.save(tmp_path/v.QUALIFICATION, world['qualification'])
    request = controller(tmp_path, 'R_NC', made)
    seen = []
    def run(arm_id, protocol, table, stop, *, qualification):
        seen.append(qualification)
        return dict(arm_id=arm_id, condition='NC', run_status='COMPLETE', samples=[{'kept': True}], neural=[]), None
    assert run_worker(request, run=run, after=dict(checked(), errors={'late': 'changed'})) == 1
    assert seen == [world['qualification']]
    arm = v.read_arm(tmp_path, 'R_NC', done(tmp_path, 'R_NC')['artifact'])
    assert arm['samples'] == [{'kept': True}] and 'after acquisition' in arm['worker_error']
    assert arm['transferred_qualification'] == made and done(tmp_path, 'R_NC')['qualification_artifact'] is None


@pytest.mark.parametrize('arm_id,transfer,extra', [('A_NC', {'path': 'x'}, {}), ('R_NC', None, {}),
                                                   ('A_WC', {'path': 'x'}, {'resume': True}), ('B_NC', None, {})])
def test_invalid_worker_requests_are_refused_before_claim(tmp_path, arm_id, transfer, extra):
    request = tmp_path/f'{arm_id}.request.json'
    request.write_text(json.dumps(dict(arm_id=arm_id, controller_sha256='x', qualification=transfer, **extra)))
    with pytest.raises(ValueError, match='request'):
        v.worker(request)
    assert not (tmp_path/f'{arm_id}.claim.json').exists()


def test_real_child_processes_transfer_first_qualification_with_verified_ancestry(tmp_path, world):
    """Actual OS launches with a synthetic adapter; zero native/CNS construction."""
    script = tmp_path/'synthetic_worker.py'
    script.write_text('''import sys
from types import SimpleNamespace
sys.path.insert(0, ROOT_VALUE)
from malecns_backend.live import assistance_campaign as v
class FixtureFly:
    _existing_fly_names = set()
    _default_fly_name = 0
sys.modules['flygym'] = SimpleNamespace(Fly=FixtureFly)
v.committed = lambda: 'synthetic-commit'
v.preflight = lambda: CHECKED
v.base.static_authority = lambda: ({}, [])
v.read_qualification = lambda folder, artifact: v.read_artifact(folder, artifact, v.QUALIFICATION)
def run(arm_id, protocol, table, stop, *, qualification):
    FixtureFly._existing_fly_names.add('0')
    q = qualification if qualification is not None else {'synthetic': 'first-model qualification'}
    return dict(arm_id=arm_id, condition=arm_id[2:], run_status='COMPLETE', samples=[], neural=[],
                assistance=dict(qualification=q, samples=[])), None
v.adapter.run_arm = run
raise SystemExit(v.worker(sys.argv[1]))
'''.replace('ROOT_VALUE', repr(str(v.ROOT))).replace('CHECKED', repr(checked())), encoding='utf-8')
    made = v.save(tmp_path/'controller.json', dict(schema=v.SCHEMA, campaign=v.CAMPAIGN, specification=v.specification(),
        sources=v.sources(), commit='synthetic-commit', prior_full_body_review_note='synthetic fixture only',
        complete_preflight=checked()))
    actual = v.subprocess.Popen
    def popen(command, **kwargs):
        assert command[0] == sys.executable and command[3] == 'malecns_backend.live.assistance_campaign'
        return actual([sys.executable, str(script), command[-1]], **kwargs)
    pids = []
    with patch.object(v.subprocess, 'Popen', side_effect=popen):
        first, interrupted = v.run_child(tmp_path, 'A_NC', made['sha256'], None)
        assert first['run_status'] == 'COMPLETE' and not interrupted
        transfer = first['qualification_artifact']
        second, _ = v.run_child(tmp_path, 'A_WC', made['sha256'], transfer)
        for r in (first, second):
            assert v.original.valid_boundary(r['process_boundary'], os.getpid())
            assert r['process_boundary']['fresh_registry'] == dict(existing_names=[], default_name=0)
            pids.append(r['pid'])
    later = v.read_arm(tmp_path, 'A_WC', second['artifact'])
    assert later['assistance']['qualification'] == {'synthetic': 'first-model qualification'}
    assert later['transferred_qualification'] == transfer and len(set(pids)) == 2
    with pytest.raises(FileExistsError):
        v.run_child(tmp_path, 'A_WC', made['sha256'], transfer)


# ---- static entry points --------------------------------------------------

def test_cli_never_lets_worker_or_evaluation_request_live_execution(capsys):
    for args in (['--live'], ['--evaluate', 'x', '--live'], ['--check', '--review-note', 'x'],
                 ['--output', 'x', '--live'], ['--worker-request', 'x', '--live', '--review-note', 'n']):
        with pytest.raises(SystemExit):
            v.main(args)
    with patch.object(v, 'source_check') as check:
        assert v.main(['--check']) == 0 and check.called
    assert 'not run by this check' in capsys.readouterr().out


def test_source_checkpoint_is_static_and_detects_changes(tmp_path):
    import mujoco
    from malecns_backend import loader, neural
    forbidden = AssertionError('no native/CNS construction in source check')
    with (patch.object(mujoco, 'MjModel', side_effect=forbidden), patch.object(mujoco, 'MjData', side_effect=forbidden),
          patch.object(neural.MaleCNSBrain, '__init__', side_effect=forbidden),
          patch.object(loader, 'load_malecns', side_effect=forbidden)):
        value = v.implementation_record()
        path = tmp_path/'implementation.json'; path.write_text(json.dumps(value))
        assert v.source_check(path) == value
        value['campaign'] = dict(value['campaign'], automatic_retries=1)
        path.write_text(json.dumps(value))
        with pytest.raises(ValueError, match='checkpoint'):
            v.source_check(path)


def test_uncommitted_campaign_source_blocks_execution():
    with patch.object(v.guard, 'committed', return_value='head'), patch.object(base, 'git', return_value=b'changed'):
        with pytest.raises(ValueError, match='commit campaign'):
            v.committed()
