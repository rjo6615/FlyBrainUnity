"""Injection/lifecycle checks; all scientific sessions/models are synthetic."""
from dataclasses import dataclass
import json
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest

from malecns_backend.live import assistance_trial as t
from malecns_backend.live import controlled_live_balance as driver


def test_validated_native_api_surface_without_constructing_model_or_data():
    import mujoco
    for name in ('control','passive','act_dyn','act_gain','act_bias'):
        assert callable(getattr(mujoco,'get_mjcb_'+name))
    for name in ('jnt_actgravcomp','jnt_actfrclimited','jnt_actfrcrange','body_gravcomp','actuator_group'):
        assert hasattr(mujoco.MjModel,name)


def test_factory_policies_require_first_qualification_and_later_proof():
    assert t.Trial('A_NC').condition == 'NC'
    assert t.Trial('R_WP',{'pending':'offline validation at boundary'}).condition == 'WP'
    for arm,proof in [('A_NC',{}),('R_NC',None),('UNKNOWN',None)]:
        with pytest.raises(ValueError): t.Trial(arm,proof)


@pytest.mark.parametrize('arm',['A_NC','R_WP'])
def test_boundary_hook_follows_original_neural_gate_and_does_not_advance_session(arm):
    trial = t.Trial(arm,None if arm == 'A_NC' else {'proof':'provided'})
    events=[]
    trial.session = SimpleNamespace(_state={'physics_transition':0})
    trial.physics = SimpleNamespace(model=object(),data=object())
    trial.inventory = {'native':'inventory'}
    trial.intervention = SimpleNamespace(original={'model':'M0'},
        accept_qualification=lambda proof:events.append('accept'),
        boundary=lambda index,guard:events.append(('boundary',index)))
    trial.mechanical_samples = [{}]
    def qualify(*args):
        events.append('qualify'); args[-1].update(passed=True)
    with (patch.object(t.base.Trial,'state_boundary',lambda self:events.append('original gate')),
          patch.object(t.mechanical,'qualify',qualify)):
        trial.state_boundary()
        assert events == (['original gate','qualify','accept',('boundary',0)] if arm == 'A_NC'
                          else ['original gate','accept',('boundary',0)])
        events.clear(); trial.session._state['physics_transition']=5005
        trial.mechanical_samples=[None]*5006
        trial.state_boundary()
        assert events == ['original gate',('boundary',5005)]


@dataclass
class Safety:
    bound: float = .1


def test_protected_state_uses_brain_digest_and_value_session_fields_without_serializing_brain():
    trial=t.Trial('A_NC')
    brain=SimpleNamespace(weights=np.ones(1),pre_sign=np.ones(1),indices=np.zeros(1,dtype=int),indptr=np.zeros(1,dtype=int))
    trial.brain=brain
    trial.channels={'motor':dict(pipeline=SimpleNamespace(safety=Safety(),previous_physical_target=.1),
        observer=SimpleNamespace(filtered_hz=np.ones(1),last_counts=np.zeros(1)),index=0,positive=[0],negative=[],
        sign=1,decoder_mode='test',bound=.1,populations=['fixture'])}
    rng=np.random.default_rng(1)
    trial.session=SimpleNamespace(_state={'brain':brain,'physics_transition':0,'commands':[0.]*42},
        _kernel=SimpleNamespace(gi_frame=SimpleNamespace(f_locals={'rngs':{'LF':rng},'encoders':{}})))
    with patch.object(t.base,'neural_state_digest',return_value='separate brain digest'):
        before=trial.protected_state()
        trial.channels['motor']['pipeline'].previous_physical_target=.2
        assert trial.protected_state() != before
        trial.session._state['brain']=object()
        with pytest.raises(ValueError,match='brain binding'): trial.protected_state()


def test_capture_preserves_full_mechanical_state_and_handles_initial_binding():
    trial=t.Trial('A_NC')
    with patch.object(t.base.Trial,'capture') as original, patch.object(trial,'_capture_mechanical') as capture:
        trial.capture('physics','obs',None)
        original.assert_called_once_with('physics','obs',None); capture.assert_not_called()
        trial.intervention=object()
        trial.capture('physics','obs','action')
        capture.assert_called_once_with('physics')


def test_original_driver_failures_return_mechanical_partial_without_global_patches(tmp_path):
    original_factory=driver.base.Trial
    def run(condition,protocol,table,stop,*,trial_factory,**kwargs):
        trial=trial_factory(condition)
        assert type(trial) is t.Trial and trial.arm_id == 'R_WP'
        trial.mechanical_samples.append({'partial':'evidence'})
        trial.qualification['partial']='preserved'
        return {'run_status':'ERROR','condition':condition}, {'display':'partial'}
    with patch.object(driver,'run_arm',run):
        result,display=t.run_arm('R_WP',{},[],tmp_path/'STOP.json',qualification={'prior':'proof'})
    assert result['assistance']['samples']==[{'partial':'evidence'}]
    assert result['assistance']['qualification']['partial']=='preserved'
    assert result['schema']=='assistance-arm-adapter-v1' and result['arm_id']=='R_WP'
    assert not result['full_scientific_audit_completed'] and result['run_status']=='ERROR'
    assert display=={'display':'partial'} and driver.base.Trial is original_factory


def test_trial_factory_override_is_not_a_hidden_campaign_option(tmp_path):
    with patch.object(driver,'run_arm',side_effect=AssertionError('must not run')):
        with pytest.raises(ValueError):
            t.run_arm('A_NC',{},[],tmp_path/'stop',trial_factory=lambda c:None)


def test_source_check_is_static_and_rejects_changed_or_missing_source_manifest(tmp_path):
    import mujoco
    from malecns_backend import neural,loader
    forbidden=AssertionError('no native/CNS construction in source check')
    with (patch.object(mujoco,'MjModel',side_effect=forbidden),patch.object(mujoco,'MjData',side_effect=forbidden),
          patch.object(neural.MaleCNSBrain,'__init__',side_effect=forbidden),
          patch.object(loader,'load_malecns',side_effect=forbidden)):
        value=t.implementation_record()
        path=tmp_path/'implementation.json';path.write_text(json.dumps(value))
        assert t.source_check(path)==value
        value['sources_canonical_lf_sha256'].pop(t.SOURCES[0])
        path.write_text(json.dumps(value))
        with pytest.raises(ValueError,match='source checkpoint'): t.source_check(path)


def test_cli_check_only_never_exposes_live_or_execution_options(capsys):
    with patch.object(t,'source_check') as check:
        assert t.main(['--check'])==0
        check.assert_called_once_with()
        assert 'campaign launcher/evaluator pending' in capsys.readouterr().out
        for args in ([],['--live'],['--execute'],['--check','--live']):
            with pytest.raises(SystemExit): t.main(args)
