"""V1.2 saved-JSON decoding and campaign gates. Synthetic/retained files only; no fly or CNS."""
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from malecns_backend.live import assistance_campaign_v1_2 as v

base, mechanical = v.base, v.mechanical
RETAINED = v.ROOT/'docs/evidence/assistance-campaign-v1_1/run-desktop-01'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, v.ROOT/path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


v11_fixture = load('assistance_campaign_v1_1_fixture', 'tests/test_assistance_campaign_v1_1.py')
v1_fixture = v11_fixture.campaign_fixture
checked, boundary, receipt = v1_fixture.checked, v1_fixture.boundary, v1_fixture.receipt


def test_decoder_is_exact_inverse_of_existing_save(tmp_path):
    payload = dict(forcerange=[[-math.inf, math.inf], [0., 1.]], nested={'x': [math.nan, 2.5]},
                   other={'__arrow_nonfinite_float__': 'NaN', 'extra': 1}, single={'native_nonfinite': '+inf'})
    made = v.save(tmp_path/'probe.json.gz', payload)
    raw = json.loads(__import__('gzip').decompress((tmp_path/'probe.json.gz').read_bytes()))
    assert raw['forcerange'][0] == [{'__arrow_nonfinite_float__': '-Infinity'}, {'__arrow_nonfinite_float__': '+Infinity'}]
    loaded = v.read_artifact(tmp_path, made, 'probe.json.gz')
    assert loaded['forcerange'] == [[-math.inf, math.inf], [0., 1.]]
    assert math.isnan(loaded['nested']['x'][0]) and loaded['nested']['x'][1] == 2.5
    assert loaded['other'] == {'__arrow_nonfinite_float__': 'NaN', 'extra': 1}
    assert loaded['single'] == {'native_nonfinite': '+inf'}  # isolation markers stay for array_values


@pytest.fixture(scope='module')
def retained_qualification():
    receipt_ = json.loads((RETAINED/'A_NC.done.json').read_text())
    artifact = receipt_['qualification_artifact']
    if not (RETAINED/artifact['path']).exists() or (RETAINED/artifact['path']).stat().st_size < 1_000_000:
        pytest.skip('retained V1.1 qualification raw file unavailable (LFS not hydrated)')
    return artifact


def test_retained_v1_1_qualification_fails_old_reader_and_passes_exact_decoding(retained_qualification):
    with pytest.raises(TypeError, match="not 'dict'"):
        v.prior.read_qualification(RETAINED, retained_qualification)
    report = v.read_qualification(RETAINED, retained_qualification)
    forcerange = report['inventory']['actuators']['forcerange']
    adhesion = [a['actuator_id'] for a in report['inventory']['adhesion']]
    assert sorted(i for i, row in enumerate(forcerange) if not all(map(math.isfinite, row))) == adhesion
    result = mechanical.evaluate_qualification(report)
    assert result['passed'] and result['cases'] == 12 and result['minimum_baseline_exposure'] > 1e-8
    assert report['live_guard'] == v.guard.GUARD and report['live_fields_changed'] == []


def test_amendment_locks_both_failures_and_unchanged_science():
    spec = v.specification()
    a = spec['amendment']
    assert [f['executed_commit'] for f in a['failed_attempts']] == [
        '953b607877ee9b790bda73429f4ab2d64e677362', '92652b5f9cbd74244367e0c4f175703a739f7c1f']
    assert not a['reuse_retained_arms'] and not a['live_guard_changed'] and a['automatic_retries'] == 0
    assert spec['scientific'] == v.v1.specification() and spec['amendment_v1_1'] == v.prior.amendment()
    assert {k: x for k, x in v.CAMPAIGN.items() if k not in ('schema', 'amendment', 'saved_json_reader')} == {
        k: x for k, x in v.prior.CAMPAIGN.items() if k not in ('schema', 'amendment')}
    assert set(v.prior.sources()) <= set(v.sources())
    v.prior.source_check(); v.v1.source_check()


def test_retained_attempt_stays_inconclusive_without_loading_raw():
    report = json.loads((RETAINED/'report.json').read_text())
    assert report['run_status'] == 'ERROR' and list(report['arm_artifacts']) == ['A_NC']
    assert not v.prior.evaluate(report, RETAINED, loader=lambda *a: pytest.fail('raw loaded'))['scientific']['accepted']
    done = json.loads((RETAINED/'A_NC.done.json').read_text())
    assert (done['run_status'], done['states'], done['neural_updates'], done['mechanical_states']) == (
        'COMPLETE', 20001, 4000, 20001)


@pytest.fixture(scope='module')
def world():
    w = v11_fixture.world.__wrapped__()
    report = dict(w['report'], schema=v.SCHEMA, campaign=v.CAMPAIGN, specification=v.specification(),
                  sources_before=v.sources(), sources_after=v.sources())
    for arm in w['arms'].values():
        arm.update(worker_sources_before=report['sources_before'], worker_sources_after=report['sources_after'])
    return dict(w, report=report)


def test_v1_2_synthetic_eight_arms_accepted_with_unchanged_evaluator(world):
    def missing(*args):
        raise OSError('synthetic fixture has no display journal')
    result = v.evaluate(world['report'], '.', loader=lambda folder, a, artifact: world['arms'][a],
        display_loader=missing, qualification_loader=lambda folder, artifact: world['qualification'],
        reference_comparator=lambda *a: dict(status='SYNTHETIC'))['scientific']
    assert result['accepted'], result.get('reason')
    assert len(result['behavior']['comparisons']) == 8 and not result['behavior']['independent_balance_proven']


def test_transfer_requires_v1_1_guard_and_fixed_path(tmp_path, world):
    old = v.save(tmp_path/v.QUALIFICATION, dict(world['qualification'], live_guard=None))
    with pytest.raises(ValueError, match='V1.1 live-data guard'):
        v.read_qualification(tmp_path, old)
    other = v.save(tmp_path/('x-'+v.QUALIFICATION), world['qualification'])
    with pytest.raises(ValueError, match='path'):
        v.read_qualification(tmp_path, other)


def run_controller(tmp_path, child, *, verified=True):
    with patch.object(v, 'preflight', return_value=dict(checked(), verified=verified)), \
            patch.object(v, 'committed', return_value='commit'), \
            patch.object(v, 'evaluate', return_value=dict(scientific=dict(accepted=False, status='INCONCLUSIVE_INTEGRITY'))):
        return v.execute(tmp_path/'campaign', live=True, review_note='user reviewed', child_runner=child)


def test_controller_transfer_failed_first_and_refusal(tmp_path, world):
    calls = []
    def child(folder, arm_id, lock, transfer):
        calls.append(transfer)
        made = v.save(folder/v.QUALIFICATION, world['qualification']) if arm_id == v.FIRST else None
        return receipt(arm_id, qualification=made), False
    report = run_controller(tmp_path/'ok', child)
    assert report['run_status'] == 'COMPLETE' and calls[0] is None and len(calls) == 8
    assert all(c == report['qualification_artifact'] for c in calls[1:])
    def failing(folder, arm_id, lock, transfer):
        return receipt(arm_id, 'ERROR', v.save(folder/v.QUALIFICATION, None)), False
    stopped = run_controller(tmp_path/'fail', failing)
    assert stopped['run_status'] == 'INCOMPLETE' and list(stopped['arm_artifacts']) == ['A_NC']
    refused = run_controller(tmp_path/'refused', lambda *a: pytest.fail('launched'), verified=False)
    assert refused['run_status'] == 'ERROR' and not refused['scientific_experiment_started']


def test_worker_decodes_transfer_and_uses_v1_1_adapter(tmp_path, world):
    made = v.save(tmp_path/v.QUALIFICATION, world['qualification'])
    control = v.save(tmp_path/'controller.json', dict(schema=v.SCHEMA, campaign=v.CAMPAIGN, specification=v.specification(),
        sources=v.sources(), commit='fixture', prior_full_body_review_note='synthetic fixture only',
        complete_preflight=checked()))
    request = tmp_path/'R_WC.request.json'
    v.save(request, dict(arm_id='R_WC', controller_sha256=control['sha256'], qualification=made))
    seen = []
    def run(arm_id, protocol, table, stop, *, qualification):
        seen.append(qualification)
        return dict(arm_id=arm_id, condition='WC', run_status='COMPLETE', samples=[], neural=[], assistance=None), None
    assert v.adapter is v.prior.adapter
    with patch.object(v, 'committed', return_value='fixture'), \
            patch.object(v.original, 'process_boundary', return_value=boundary(300)), \
            patch.object(v, 'preflight', return_value=checked()), \
            patch.object(base, 'static_authority', return_value=({}, [])), \
            patch.dict(sys.modules, {'flygym': SimpleNamespace(Fly=v1_fixture.FixtureFly)}), \
            patch.object(v.adapter, 'run_arm', side_effect=run):
        assert v.worker(request) == 0
    assert seen == [world['qualification']]


def test_real_child_process_launches_v1_2_worker(tmp_path):
    script = tmp_path/'synthetic_worker.py'
    script.write_text('''import sys
from types import SimpleNamespace
sys.path.insert(0, ROOT_VALUE)
from malecns_backend.live import assistance_campaign_v1_2 as v
class FixtureFly:
    _existing_fly_names = set()
    _default_fly_name = 0
sys.modules['flygym'] = SimpleNamespace(Fly=FixtureFly)
v.committed = lambda: 'synthetic-commit'
v.preflight = lambda: CHECKED
v.base.static_authority = lambda: ({}, [])
def run(arm_id, protocol, table, stop, *, qualification):
    return dict(arm_id=arm_id, condition=arm_id[2:], run_status='COMPLETE', samples=[], neural=[],
                assistance=dict(qualification={'synthetic': float('inf')}, samples=[])), None
v.adapter.run_arm = run
raise SystemExit(v.worker(sys.argv[1]))
'''.replace('ROOT_VALUE', repr(str(v.ROOT))).replace('CHECKED', repr(checked())), encoding='utf-8')
    made = v.save(tmp_path/'controller.json', dict(schema=v.SCHEMA, campaign=v.CAMPAIGN, specification=v.specification(),
        sources=v.sources(), commit='synthetic-commit', prior_full_body_review_note='synthetic fixture only',
        complete_preflight=checked()))
    actual = v.subprocess.Popen
    def popen(command, **kwargs):
        assert command[3] == 'malecns_backend.live.assistance_campaign_v1_2'
        return actual([sys.executable, str(script), command[-1]], **kwargs)
    with patch.object(v.subprocess, 'Popen', side_effect=popen):
        first, _ = v.run_child(tmp_path, 'A_NC', made['sha256'], None)
    assert first['run_status'] == 'COMPLETE' and v.original.valid_boundary(first['process_boundary'], os.getpid())
    saved = v.read_artifact(tmp_path, first['qualification_artifact'], v.QUALIFICATION)
    assert saved == {'synthetic': math.inf}


def test_audit_retained_requires_v1_1_attempt_and_stops_on_bad_qualification(tmp_path):
    (tmp_path/'report.json').write_text(json.dumps(dict(schema='other')))
    with pytest.raises(ValueError, match='V1.1'):
        v.audit_retained(tmp_path)
    (tmp_path/'report.json').write_text(json.dumps(dict(schema=v.prior.SCHEMA, run_status='ERROR',
        evaluation=dict(scientific=dict(status='INCONCLUSIVE_INTEGRITY')), arm_artifacts={'A_NC': {}})))
    (tmp_path/'A_NC.done.json').write_text(json.dumps(dict(qualification_artifact=dict(path=v.QUALIFICATION, sha256='0'))))
    result = v.audit_retained(tmp_path)
    assert result['qualification']['passed'] is False and result['arms'] == {}
    assert result['scope'].startswith('OFFLINE_RETAINED_ARM_INTEGRITY_DIAGNOSTIC') and result['native_constructions'] == 0


def test_cli_and_source_checkpoint(tmp_path, capsys):
    for args in (['--live'], ['--audit-retained', 'x'], ['--check', '--receipt', 'x'], ['--output', 'x', '--live']):
        with pytest.raises(SystemExit):
            v.main(args)
    value = v.implementation_record()
    path = tmp_path/'implementation.json'; path.write_text(json.dumps(value))
    assert v.source_check(path) == value
    value['campaign'] = dict(value['campaign'], saved_json_reader='none'); path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match='checkpoint'):
        v.source_check(path)
    with patch.object(v, 'committed', return_value='head'), patch.object(v, 'audit_retained',
            return_value=dict(qualification=dict(passed=True), arms={'A_NC': dict(receipt_status='COMPLETE', passed=True)})):
        assert v.main(['--audit-retained', str(tmp_path), '--receipt', str(tmp_path/'r.json')]) == 0
        with pytest.raises(FileExistsError):
            v.main(['--audit-retained', str(tmp_path), '--receipt', str(tmp_path/'r.json')])
    with patch.object(v.v1.guard, 'committed', return_value='head'), patch.object(base, 'git', return_value=b'changed'):
        with pytest.raises(ValueError, match='commit V1.2'):
            v.committed()


@pytest.mark.parametrize('offset,accepted', [(-3.885780586188048e-14, True), (0., True), (2e-12, False), (-2e-12, False)])
def test_event_journal_clock_uses_runtime_bound_and_keeps_other_checks(world, offset, accepted):
    arm = dict(world['arms']['R_NP'])
    event = dict(arm['assistance']['event'], time_s=5005*.0001+offset)
    arm['assistance'] = dict(arm['assistance'], event=event)
    if accepted:
        result = v.audit_mechanical(arm, 'R_NP', world['qualification'])
        assert result['passed'] and result['states'] == 20001 and result['journal_clock_offset_s'] == event['time_s']-5005*.0001
    else:
        with pytest.raises(ValueError, match='journal clock'):
            v.audit_mechanical(arm, 'R_NP', world['qualification'])
    wrong = dict(arm['assistance'], event=dict(event, operation='OBSERVE_ONLY'))
    with pytest.raises(ValueError):
        v.audit_mechanical(dict(arm, assistance=wrong), 'R_NP', world['qualification'])
