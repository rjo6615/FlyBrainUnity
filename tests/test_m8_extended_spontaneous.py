"""Dependency-free/static M8 tests. No scientific transition is executed."""
from malecns_backend.embodiment import m8_extended_spontaneous as m8
from malecns_backend.embodiment import m7d_corrected_spontaneous as m7d
from malecns_backend.embodiment import _windows_m8_extended_spontaneous_adapter as adapter
from malecns_backend.embodiment import m8_contact_kinematics as contacts


def test_only_duration_and_telemetry_extend_m7d():
    p=m8.protocol(); m8.validate_protocol(p)
    assert (m8.DURATION_MS,m8.EXPECTED_PHYSICS_TRANSITIONS,m8.EXPECTED_PHYSICS_STATES,m8.EXPECTED_NEURAL_UPDATES)==(10_000,100_000,100_001,20_000)
    assert p['physical_initialization']==m7d.protocol()['physical_initialization']
    assert (m8.SEED,m8.CONDITIONS,m8.ADMITTED_MOTOR,m8.ADMITTED_SENSORY)==(m7d.SEED,m7d.CONDITIONS,m7d.ADMITTED_MOTOR,m7d.ADMITTED_SENSORY)
    assert not any(p['hidden_assistance'].values()) and p['walking'] is p['tripod_gait_classification'] is None


def test_disabled_gate_is_exact_m7d_gate():
    values={n:.25 for n in m8.ADMITTED_MOTOR}
    assert adapter.gate_contributions(values,m8.CONDITIONS[0],m8.ADMITTED_MOTOR)==values
    assert set(adapter.gate_contributions(values,m8.CONDITIONS[1],m8.ADMITTED_MOTOR).values())=={0.}


def test_preflight_is_two_fresh_zero_transition_initializations(monkeypatch,tmp_path):
    monkeypatch.setattr(m8,'OUTPUT_DIR',tmp_path); monkeypatch.setattr(m8,'RAW_PATH',tmp_path/'raw'); monkeypatch.setattr(m8,'MANIFEST_PATH',tmp_path/'manifest'); monkeypatch.setattr(m8,'ANALYSIS_PATH',tmp_path/'analysis'); monkeypatch.setattr(m8,'REPORT_PATH',tmp_path/'report'); monkeypatch.setattr(m8,'REPLAY_MANIFEST_PATH',tmp_path/'replay')
    monkeypatch.setattr(m7d,'verify_b4',lambda:{'raw':{'sha256':'b4'}}); monkeypatch.setattr(m7d,'verify_m7',lambda:{'raw':{'sha256':'m7'}})
    monkeypatch.setattr(adapter.m7da,'_environment',lambda:{'flygym':'1.2.1','mujoco':'3.2.7'})
    monkeypatch.setattr(adapter.m7da,'_protocol',lambda:({'admitted_motor_interfaces':list(m8.ADMITTED_MOTOR)},[],[]))
    monkeypatch.setattr(adapter.m6c,'pre_intervention_equivalent',lambda *x:True)
    calls=[]
    def runner(**kw):
        calls.append(kw); return {'physics_steps':0,'neural_steps':0,'pre_intervention_state':{},'initial_physical_state_audit':{'body_position':list(m8.SPAWN_POS),'m8_contact_identity':{'available':True,'method':'compiled IDs'}},'telemetry_schema':{}}
    result=adapter.windows_preflight(runner)
    assert len(calls)==2 and all(x['initialize_only'] and x['duration_ms']==10_000 for x in calls)
    assert result['physics_transitions']==result['neural_transitions']==0 and result['contact_identity']['available']


def test_authoritative_identity_uses_names_and_ids(monkeypatch):
    class Obj:
        def __init__(self,name): self.name=name
    class Model:
        nbody=8; ngeom=8
        geom_bodyid=[0,2,3,4,5,6,7,1]
        def body(self,i): return Obj(('world','ground','LFTarsus5','LMTarsus5','LHTarsus5','RFTarsus5','RMTarsus5','RHTarsus5')[i])
        def geom(self,i): return Obj(('ground','LFTarsus','LMTarsus','LHTarsus','RFTarsus','RMTarsus','RHTarsus','other')[i])
    identity=contacts.resolve(Model())
    assert identity['available'] and identity['ground_geom_ids']==(0,)
    assert identity['tarsus5_body_ids']['LF']==2 and identity['tarsal_geom_ids']['RH']==(6,)


def test_raw_and_replay_names_are_new_m8_namespace():
    assert 'm8_extended_spontaneous' in str(m8.RAW_PATH)
    assert all('m7d_corrected_spontaneous' not in str(x) for x in (m8.RAW_PATH,m8.MANIFEST_PATH,m8.ANALYSIS_PATH,m8.REPLAY_MANIFEST_PATH))
