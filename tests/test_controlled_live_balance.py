"""Engineering tests only: synthetic sessions/registries, real OS and sockets."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from malecns_backend.live import controlled_live_balance as c
from malecns_backend.live import balance_live_observer as o
from malecns_backend.live.protocol import JOINT_NAMES, decode


def pose_arm():
    q = [0., 1., 2., 1., 0., 0., 0.] + [i/100 for i in range(42)]
    return dict(context=dict(free_root=dict(qpos_address=0, dof_address=0), native_inventory=dict(nq=49,
        rows=[dict(coordinate=n, action_index=i, qpos_range=[48-i,49-i]) for i,n in enumerate(JOINT_NAMES)])),
        samples=[dict(time_s=i*.0001, qpos=q) for i in range(20001)])


def test_original_spec_and_sources_remain_valid():
    assert c.specification()['conditions'] == list(c.base.CONDITIONS)
    assert set(c.original.sources()).issubset(c.sources())
    assert c.original.base.create_session is c.base.create_session


def test_live_projection_matches_existing_replay_with_permuted_native_addresses():
    from malecns_backend.live.balance_contribution_replay import pose_only
    a = pose_arm()
    a['run_status'] = 'COMPLETE'
    saved = pose_only(a)
    for index in (0, 5000, 5005, 5006, 5201, 20000):
        snapshot = o.sample_snapshot(a['context'], a['samples'][index], index)
        assert snapshot.joint_positions == tuple(saved[index]['joint_positions'])
        assert snapshot.root_quaternion_wxyz == (1.,0.,0.,0.)
        assert snapshot.diagnostics['neural_transition_count'] == index//5
    assert snapshot.joint_positions == tuple(i/100 for i in range(41,-1,-1))


@pytest.mark.parametrize('corruption', ['address','duplicate','name','root','clock','finite','quaternion'])
def test_bad_live_pose_is_rejected(corruption):
    a = pose_arm(); sample = dict(a['samples'][5005]); context = a['context']
    if corruption == 'address': context['native_inventory']['rows'][0]['qpos_range'] = [0,1]
    if corruption == 'duplicate': context['native_inventory']['rows'][0]['qpos_range'] = [47,48]
    if corruption == 'name': context['native_inventory']['rows'][0]['coordinate'] = 'unknown'
    if corruption == 'root': context['free_root']['qpos_address'] = 1
    if corruption == 'clock': sample['time_s'] = .5
    if corruption == 'finite': sample['qpos'] = [float('nan')]*49
    if corruption == 'quaternion': sample['qpos'] = sample['qpos'][:3]+[0.]*4+sample['qpos'][7:]
    with pytest.raises(ValueError): o.sample_snapshot(context, sample, 5005)


def real_observer():
    return o.LiveObserver(server_factory=lambda:o.CheckedPoseServer(port=0))


def test_real_no_client_live_offers_match_raw_and_do_not_claim_receipt():
    a = pose_arm(); observer = real_observer(); observer.start()
    try:
        observer.observe(a['context'], a['samples'][0], 0)
    finally:
        record = observer.close()
    check = o.audit_display(a, record)
    assert check['projection_status'] == 'VERIFIED' and check['status'] == 'UNCONFIRMED'
    assert check['sent_frames'] == 0 and check['visual_review'] == 'UNCONFIRMED'
    assert record['offers'][0]['wire_packet']['joint_positions'] == [i/100 for i in range(41,-1,-1)]


def test_real_client_bytes_and_disconnect_cannot_modify_scientific_input():
    a = pose_arm(); before = copy.deepcopy(a['samples'][0]); observer = real_observer(); observer.start()
    try:
        observer.observe(a['context'], a['samples'][0], 0)
        with socket.create_connection(('127.0.0.1', observer.server.bound_port), timeout=2) as client:
            reader = client.makefile('rb')
            assert decode(reader.readline())['type'] == 'hello'
            assert decode(reader.readline())['type'] == 'pose'
            client.sendall(b'{"force":999,"reset":true}\n')
            try:
                assert reader.readline() == b''
            except ConnectionResetError:
                pass  # Windows resets a socket closed with unread rejected bytes.
        assert a['samples'][0] == before
        assert not observer.disabled
    finally:
        record = observer.close()
    assert o.audit_display(a, record)['projection_status'] == 'VERIFIED'


def test_bind_failure_is_surfaced_without_waiting_for_science():
    with socket.socket() as held:
        held.bind(('127.0.0.1',0)); held.listen(1)
        server = o.CheckedPoseServer(port=held.getsockname()[1])
        with pytest.raises(RuntimeError): server.start()
        assert server.serve_error


def test_midrun_transport_fault_disables_only_observation():
    a = pose_arm(); observer = real_observer(); observer.start()
    with patch.object(observer.server, 'publish', side_effect=OSError('synthetic transport fault')):
        observer.observe(a['context'], a['samples'][0], 0)
    assert observer.disabled
    observer.observe({}, {}, 1)  # Does not touch later science or try reconnect.
    record = observer.close()
    assert o.audit_display(a, record)['status'] == 'FAILED'
    assert len(record['faults']) == 1


@pytest.mark.parametrize('corruption', ['packet','wire','clock','sequence','index','rate','fault'])
def test_display_audit_catches_corruption_separately(corruption):
    a = pose_arm(); observer = real_observer(); observer.start()
    try:
        observer.observe(a['context'], a['samples'][0], 0)
    finally: record = observer.close()
    row = record['offers'][0]
    if corruption == 'packet': row['packet']['joint_positions'][0] += .1
    if corruption == 'wire': row['wire_packet']['root_position'][0] += .1
    if corruption == 'clock': row['packet']['sim_time_seconds'] = 1.
    if corruption == 'sequence': row['packet']['sequence'] = 5
    if corruption == 'index': row['state_index'] = 20001
    if corruption == 'fault': record['faults'] = ['thread stopped']
    if corruption == 'rate':
        second = copy.deepcopy(row); second['state_index'] = 1
        second['wall_monotonic_s'] += .001
        second['packet'] = o.packet_for(o.sample_snapshot(a['context'],a['samples'][1],1),record['session_id'],1)
        second['wire_packet'] = copy.deepcopy(second['packet']); record['offers'].append(second)
    assert o.audit_display(a, record)['status'] == 'FAILED'


class SyntheticTrial:
    def __init__(self, condition):
        self.samples, self.neural, self.initial, self.brain = [], [], {}, None
        self.context = pose_arm()['context']
        self.index = 0
    def state_boundary(self):
        self.samples.append(dict(time_s=self.index*.0001,qpos=[0.,0.,1.,1.,0.,0.,0.]+[0.]*42))
        if self.index and self.index%5 == 0: self.neural.append(dict(tick=self.index//5))
    def detach(self): pass


class SyntheticSession:
    def __init__(self, trial): self.trial,self.closed = trial,False
    def initialize(self): return SimpleNamespace(time_ms=0.)
    def step(self, **kwargs):
        assert kwargs == dict(lightweight=True)
        self.trial.index += 1
        return SimpleNamespace(physics_transitions=self.trial.index,neural_transitions=self.trial.index//5)
    def close(self): self.closed=True


def quiet(*args,**kwargs): pass


def test_driver_full_budget_no_client_original_factory_unchanged(tmp_path):
    factory = c.base.create_session
    sessions=[]
    def session(trial,*args):
        s=SyntheticSession(trial); sessions.append(s); return s
    arm, display = c.run_arm('WP',{},[],tmp_path/'STOP.json',trial_factory=SyntheticTrial,
        session_factory=session,observer_factory=real_observer,progress=quiet)
    assert arm['run_status']=='COMPLETE' and len(arm['samples'])==20001 and len(arm['neural'])==4000
    assert arm['neural'][-1]['tick']==4000 and arm['samples'][-1]['time_s']==2.
    assert sessions[0].closed and c.base.create_session is factory
    assert o.audit_display(arm,display)['projection_status']=='VERIFIED'


def test_driver_bind_failure_prevents_native_factory(tmp_path):
    class Observer:
        def start(self): raise RuntimeError('port occupied')
        def close(self): return dict(faults=['port occupied'])
    arm,display=c.run_arm('NC',{},[],tmp_path/'STOP.json',trial_factory=SyntheticTrial,
        session_factory=lambda *a:pytest.fail('native factory called'),observer_factory=Observer,progress=quiet)
    assert arm['run_status']=='ERROR' and not arm['samples'] and 'port occupied' in arm['error']


def test_midrun_display_failure_still_keeps_every_scientific_transition(tmp_path):
    class FaultingObserver(o.LiveObserver):
        def __init__(self): super().__init__(server_factory=lambda:o.CheckedPoseServer(port=0))
        def observe(self,context,sample,index):
            if index==10: self.fault(OSError('synthetic publication failure'))
            super().observe(context,sample,index)
    arm,display=c.run_arm('NP',{},[],tmp_path/'STOP.json',trial_factory=SyntheticTrial,
        session_factory=lambda trial,*a:SyntheticSession(trial),observer_factory=FaultingObserver,progress=quiet)
    assert arm['run_status']=='COMPLETE' and len(arm['samples'])==20001 and len(arm['neural'])==4000
    assert o.audit_display(arm,display)['status']=='FAILED'


def test_stop_retains_partial_and_does_not_take_next_transition(tmp_path):
    stop=tmp_path/'STOP.json'; sessions=[]
    class Session(SyntheticSession):
        def step(self,**kw):
            result=super().step(**kw)
            if self.trial.index==5005: stop.write_text('{}')
            return result
    def factory(trial,*a):
        s=Session(trial);sessions.append(s);return s
    arm,display=c.run_arm('WC',{},[],stop,trial_factory=SyntheticTrial,
        session_factory=factory,observer_factory=real_observer,progress=quiet)
    assert arm['run_status']=='ERROR' and len(arm['samples'])==5006 and len(arm['neural'])==1001
    assert sessions[0].closed and 'KeyboardInterrupt' in arm['error']


def test_stop_before_init_has_no_socket_or_native_construction(tmp_path):
    stop=tmp_path/'STOP.json';stop.write_text('{}')
    arm,display=c.run_arm('NC',{},[],stop,trial_factory=SyntheticTrial,
        observer_factory=lambda:pytest.fail('socket created'),session_factory=lambda *a:pytest.fail('constructed'),progress=quiet)
    assert arm['run_status']=='ERROR' and not arm['samples'] and display is None


def test_stop_after_session_creation_still_prevents_initialize(tmp_path):
    stop=tmp_path/'STOP.json';closed=[]
    def factory(*args):
        stop.write_text('{}')
        return SimpleNamespace(initialize=lambda:pytest.fail('initialized after stop'),close=lambda:closed.append(True))
    arm,_=c.run_arm('NC',{},[],stop,trial_factory=SyntheticTrial,session_factory=factory,
        observer_factory=real_observer,progress=quiet)
    assert arm['run_status']=='ERROR' and not arm['samples'] and closed==[True]


def test_detach_error_cannot_discard_raw_partial_or_display_journal(tmp_path):
    class Trial(SyntheticTrial):
        def detach(self): raise RuntimeError('synthetic detach fault')
    class Session(SyntheticSession):
        def step(self,**kw): raise KeyboardInterrupt('fixture interruption')
    arm,display=c.run_arm('NC',{},[],tmp_path/'STOP.json',trial_factory=Trial,
        session_factory=lambda trial,*a:Session(trial),observer_factory=real_observer,progress=quiet)
    assert arm['run_status']=='ERROR' and len(arm['samples'])==1 and 'detach fault' in arm['detach_error']
    assert display is not None


def test_default_execute_checks_only_and_refuses_overwrite(tmp_path):
    with patch.object(c.base,'preflight',return_value=dict(verified=False)):
        r=c.execute(tmp_path/'check',child_runner=lambda *a:pytest.fail('child started'))
    assert r['run_status']=='NOT_RUN' and not r['scientific_experiment_started']
    with pytest.raises(FileExistsError): c.execute(tmp_path/'check')


def test_missing_review_or_failed_prerequisite_never_launches(tmp_path):
    with patch.object(c.base,'preflight',return_value=dict(verified=True)):
        r=c.execute(tmp_path/'review',live=True,child_runner=lambda *a:pytest.fail('child'))
    assert not r['scientific_experiment_started'] and 'review' in r['error']
    with patch.object(c.base,'preflight',return_value=dict(verified=False)):
        r=c.execute(tmp_path/'prereq',live=True,review_note='Actual user confirmation',child_runner=lambda *a:pytest.fail('child'))
    assert not r['scientific_experiment_started'] and 'prerequisites' in r['error']


def test_uncommitted_implementation_prevents_worker(tmp_path):
    with patch.object(c.base,'preflight',return_value=dict(verified=True)),patch.object(c,'committed',side_effect=ValueError('not committed')):
        r=c.execute(tmp_path/'source',live=True,review_note='confirmed',child_runner=lambda *a:pytest.fail('child'))
    assert not r['scientific_experiment_started'] and 'not committed' in r['error']


def test_controller_stops_after_one_failed_arm_without_retry(tmp_path):
    calls=[]
    def child(folder,condition,*args):
        calls.append(condition)
        return dict(run_status='ERROR',artifact=dict(path='NC.json.gz',sha256='fixture'),
                    display_artifact=dict(path='NC.display.json.gz',sha256='fixture')),False
    with patch.object(c.base,'preflight',return_value=dict(verified=True)),patch.object(c,'committed',return_value='fixture'):
        r=c.execute(tmp_path/'failure',live=True,review_note='confirmed',child_runner=child)
    assert calls==['NC'] and r['run_status']=='INCOMPLETE' and not r['evaluation']['scientific']['accepted']


@pytest.fixture(scope='module')
def synthetic_evaluation():
    spec=importlib.util.spec_from_file_location('live_old_fixture',c.ROOT/'tests/test_balance_contribution_process.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    old=module.fixture_module().null_report(); source=c.sources(); arms={}
    report=dict(schema=c.SCHEMA,specification=c.specification(),design=c.base.design(),run_status='COMPLETE',
        preflight=dict(verified=True),sources_before=source,sources_after=source,controller_pid=100,
        implementation_commit='synthetic',prior_full_body_review_note='synthetic attestation; not a human review',
        arm_artifacts={k:dict(path=k+'.json.gz',sha256='synthetic') for k in c.base.CONDITIONS},
        display_artifacts={k:dict(path=k+'.display.json.gz',sha256='synthetic') for k in c.base.CONDITIONS})
    for i,k in enumerate(c.base.CONDITIONS):
        arms[k]=dict(old['arms'][k],worker_sources_before=source,worker_sources_after=source,
            process_boundary=dict(pid=200+i,parent_pid=100,launch_pid=200+i,controller_pid=100,
                launcher_parent_pid=100,mode='direct',commit='synthetic',fresh_registry=dict(existing_names=[],default_name=0)))
    return old,report,arms


def test_new_schema_delegates_full_original_audit_and_behavior(synthetic_evaluation):
    old,report,arms=synthetic_evaluation
    expected=c.base.evaluate(old)
    actual=c.evaluate(report,'.',loader=lambda f,k,a:arms[k],
        display_loader=lambda *a:None,reference_comparator=lambda *a:dict(status='NOT_AVAILABLE_IN_SYNTHETIC_TEST'))
    scientific=actual['scientific']
    assert scientific['accepted'],scientific.get('reason')
    for field in ('arms','behavior','pair_exposure','unity_replay_eligible'): assert scientific[field]==expected[field]
    assert all(v['status']=='FAILED' for v in actual['display'].values())
    assert not actual['scientific']['behavior']['independent_balance_proven']


def test_source_corruption_rejects_before_loading_or_auditing(synthetic_evaluation):
    report=dict(synthetic_evaluation[1],sources_after={'bad':'identity'})
    result=c.evaluate(report,'.',loader=lambda *a:pytest.fail('loaded'))
    assert not result['scientific']['accepted']


def test_incomplete_never_loads_and_cli_cannot_start_with_evaluate(synthetic_evaluation):
    report=dict(synthetic_evaluation[1],run_status='INCOMPLETE')
    assert not c.evaluate(report,'.',loader=lambda *a:pytest.fail('loaded'))['scientific']['accepted']
    with pytest.raises(SystemExit): c.main(['--evaluate','.','--live'])
    with pytest.raises(SystemExit): c.main(['--output','x','--live'])


def test_missing_child_receipt_not_fabricated_or_retried(tmp_path):
    process=SimpleNamespace(pid=1234,poll=lambda:9)
    with patch.object(c.subprocess,'Popen',return_value=process) as launch:
        with pytest.raises(RuntimeError,match='no retry'): c.run_child(tmp_path,'NC','lock')
    assert launch.call_count==1 and not (tmp_path/'NC.done.json').exists()


def test_actual_os_worker_smoke_is_fresh_and_uses_injected_science_only(tmp_path):
    """Actual child+redirector+socket, fixture registry; no native body/full CNS."""
    script=tmp_path/'smoke.py'
    script.write_text('''import sys,os
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, ROOT_VALUE)
from malecns_backend.live import controlled_live_balance as c
class FixtureFly:
    _existing_fly_names=set()
    _default_fly_name=0
sys.modules['flygym']=SimpleNamespace(Fly=FixtureFly)
c.committed=lambda:'synthetic'
c.base.environment=lambda:{'verified':True}
c.base.static_authority=lambda:({},[])
c.base.data_identities=lambda:{}
def arm(condition,*a):
    assert FixtureFly._existing_fly_names==set()
    FixtureFly._existing_fly_names.add('fixture-used')
    from malecns_backend.live.balance_live_observer import CheckedPoseServer
    with CheckedPoseServer(port=0): pass
    return dict(condition=condition,run_status='COMPLETE',samples=[{'synthetic':True}],neural=[]),None
c.run_arm=arm
raise SystemExit(c.worker(sys.argv[1]))
'''.replace('ROOT_VALUE',repr(str(c.ROOT))),encoding='utf-8')
    source=c.sources()
    control=c.base.save(tmp_path/'controller.json',dict(schema=c.SCHEMA,specification=c.specification(),
        sources=source,commit='synthetic',prior_full_body_review_note='synthetic only'))
    real_popen=c.subprocess.Popen
    def launch(command,**kw):
        return real_popen([sys.executable,'-u',str(script),command[-1]],**kw)
    receipts=[]
    with patch.object(c.subprocess,'Popen',side_effect=launch):
        for condition in ('NC','WC'):
            receipt,interrupted=c.run_child(tmp_path,condition,control['sha256'])
            assert receipt['run_status']=='COMPLETE' and not interrupted
            assert receipt['process_boundary']['fresh_registry']==dict(existing_names=[],default_name=0)
            receipts.append(receipt)
    assert receipts[0]['pid']!=receipts[1]['pid']


def test_slow_client_display_has_one_pending_slot_and_no_scientific_pacing():
    a=pose_arm(); observer=real_observer();observer.start()
    client=socket.create_connection(('127.0.0.1',observer.server.bound_port),timeout=2)
    try:
        # Wall times are explicit; no sleeping to pace the science/session.
        for index in range(10):
            with patch.object(observer,'clock',return_value=index*.04):
                observer.observe(a['context'],a['samples'][index],index)
        assert observer.server.pending_capacity==1 and observer.server._sequence==10
    finally:
        client.close();record=observer.close()
    assert o.audit_display(a,record)['projection_status']=='VERIFIED'
