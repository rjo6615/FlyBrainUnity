"""Synthetic force-law fixtures only: no native model, CNS or physics run."""
import copy
import json
from types import SimpleNamespace

import numpy as np
import pytest

from malecns_backend.live import assistance_native as m


class Model(SimpleNamespace):
    def id2name(self, index, kind):
        return self._names[kind][index]


class Data(SimpleNamespace):
    def __init__(self, model):
        super().__init__(time=0., qpos=np.zeros(model.nq), qvel=np.zeros(model.nv),
            act=np.zeros(0), ctrl=np.zeros(model.nu), qfrc_applied=np.zeros(model.nv),
            xfrc_applied=np.zeros((model.nbody, 6)), actuator_force=np.zeros(model.nu),
            qfrc_actuator=np.zeros(model.nv), qfrc_passive=np.zeros(model.nv),
            qfrc_bias=np.zeros(model.nv), qacc_warmstart=np.zeros(model.nv))


def sparse(matrix):
    values, columns, starts, counts = [], [], [], []
    for row in matrix:
        cols = np.flatnonzero(row)
        starts.append(len(values)); counts.append(len(cols))
        values.extend(row[cols].tolist()); columns.extend(cols.tolist())
    return dict(values=values, rownnz=counts, rowadr=starts, colind=columns)


class API:
    def __init__(self):
        self.calls = []; self.fail_at = None; self.on_forward = None

    def MjData(self, model):
        self.calls.append('allocate')
        return Data(model)

    def mj_resetData(self, model, data):
        self.calls.append('reset')
        data.__dict__.update(Data(model).__dict__)

    def mj_forward(self, model, data):
        self.calls.append('forward')
        if self.calls.count('forward') == self.fail_at:
            raise RuntimeError('injected forward failure')
        forces = np.zeros(48)
        matrix = np.zeros((48, model.nv))
        for aid, (jid, _) in enumerate(model.actuator_trnid):
            if model.actuator_trntype[aid] != 0:
                # Adhesion structurally supports a selected DOF, with zero force.
                matrix[aid, 6] = .5
                continue
            q, v = data.qpos[model.jnt_qposadr[jid]], data.qvel[model.jnt_dofadr[jid]]
            forces[aid] = (model.actuator_gainprm[aid, 0]*data.ctrl[aid]
                           +model.actuator_biasprm[aid, 0]+model.actuator_biasprm[aid, 1]*q
                           +model.actuator_biasprm[aid, 2]*v)
            matrix[aid, model.jnt_dofadr[jid]] = 1.
        data.actuator_force[:] = forces
        data.qfrc_actuator[:] = matrix.T @ forces
        data.qfrc_passive[:] = -.1*data.qvel
        data._matrix = matrix
        if self.on_forward:
            self.on_forward(model, data)

    def __getattr__(self, name):
        if name.startswith('get_mjcb_'):
            return lambda: None
        raise AssertionError('undeclared native API: '+name)


@pytest.fixture
def fixture(monkeypatch):
    names = list(m.plan.JOINT_NAMES)
    native_joints = list(reversed(names))  # native joints also differ from action order
    actuator_names = ['']*48
    ids = [(i*5+7) % 48 for i in range(48)]
    body_names = ['world', 'Thorax']+[n.removeprefix('joint_') for n in native_joints]
    body_names += [leg+'Tarsus5' for leg in ('LF','LM','LH','RF','RM','RH')]
    model = Model(nu=48, na=0, nq=49, nv=48, njnt=43, nbody=50, nsensor=0,
        ngeom=1, nsite=0, nplugin=0, nmocap=0,
        opt=SimpleNamespace(disableflags=0, enableflags=0, disableactuator=0, gravity=np.array([0.,0.,-9810.]), timestep=.0001),
        _names=dict(joint=['root']+native_joints, actuator=actuator_names,
                    body=body_names, sensor=[], geom=['ground'], site=[]),
        jnt_bodyid=np.arange(1,44), jnt_type=np.array([0]+[3]*42),
        jnt_qposadr=np.array([0]+list(range(7,49))), jnt_dofadr=np.array([0]+list(range(6,48))),
        jnt_axis=np.tile([1.,0.,0.],(43,1)), jnt_limited=np.zeros(43,dtype=int), jnt_range=np.zeros((43,2)),
        jnt_actfrclimited=np.zeros(43,dtype=int), jnt_actfrcrange=np.zeros((43,2)),
        jnt_actgravcomp=np.zeros(43,dtype=int), body_gravcomp=np.zeros(50),
        geom_friction=np.ones((1,3)), actuator_group=np.zeros(48,dtype=int))
    for name in m.isolation.ACT_FIELDS:
        if name in ('gainprm','biasprm','dynprm'):
            array = np.zeros((48,10))
        elif name == 'gear':
            array = np.zeros((48,6)); array[:,0] = 1.
        elif name in ('ctrlrange','forcerange'):
            array = np.tile([-2.,2.],(48,1))
        elif name == 'trnid':
            array = np.tile([-1,-1],(48,1))
        else:
            array = np.zeros(48,dtype=int)
        setattr(model,'actuator_'+name,array)
    model.actuator_gainprm[:,0] = 2.
    model.actuator_biasprm[:,1] = -2.; model.actuator_biasprm[:,2] = -.1
    model.actuator_biastype[:] = 1; model.actuator_actadr[:] = -1
    model.actuator_ctrllimited[:] = 1
    for i, name in enumerate(names):
        aid, jid = ids[i], native_joints.index(name)+1
        actuator_names[aid] = 'actuator_position_'+name
        model.actuator_trnid[aid,0] = jid
    for i, leg in enumerate(('LF','LM','LH','RF','RM','RH')):
        aid = ids[42+i]
        actuator_names[aid] = leg+'Tarsus5_adhesion'
        model.actuator_trntype[aid] = 5; model.actuator_trnid[aid,0] = 44+i
    for name in ('type','objtype','objid','dim','adr'):
        setattr(model,'sensor_'+name,np.zeros(0,dtype=int))
    api, data = API(), Data(model)
    api.mj_forward(model,data); api.calls.clear()
    monkeypatch.setattr(m,'dense_moments',lambda native,model,data:(data._matrix.copy(),sparse(data._matrix)))
    inv, original = m.bind(model,data,SimpleNamespace(actuated_joints=names))
    return model, data, api, inv, original


def qualification(fixture):
    model, data, api, inv, original = fixture
    report = {}
    m.qualify(api,model,data,inv,original,lambda:'protected',report)
    return report


def test_actual_inventory_helpers_bind_permuted_ids_and_typed_empty_arrays(fixture):
    model, data, api, inv, original = fixture
    retained, selected = m.partition(inv)
    assert len(retained) == 20 and len(selected) == 22
    assert any(r['action_index'] != r['actuator_id'] for r in selected)
    assert any(r['joint_id'] != r['actuator_id'] for r in selected)
    assert not set(r['actuator_id'] for r in retained)&set(r['actuator_id'] for r in selected)
    m.validate_model_record(json.loads(json.dumps(original)))
    assert not api.calls
    assert m.model_record(SimpleNamespace(ptr=model),SimpleNamespace(ptr=data)) == original


def test_qualification_exact_budget_restores_everything_without_live_or_cns_calls(fixture):
    model, data, api, inv, original = fixture
    before = m.data_digest(data)
    report = qualification(fixture)
    assert report['evaluation']['passed'] and report['evaluation']['minimum_baseline_exposure'] > 1e-8
    assert api.calls == ['allocate']+['reset','forward']*12
    assert report['before'] == report['after']
    assert before == m.data_digest(data) and m.model_record(model,data) == original
    assert len(report['cases']) == 12
    assert m.evaluate_qualification(json.loads(json.dumps(report)))['passed']
    with pytest.raises(ValueError,match='no retry'):
        m.qualify(api,model,data,inv,original,lambda:'protected',report)


@pytest.mark.parametrize('field,value', [('joint_id',-1),('actuator_id',True),('body_id',999),('action_index',0.0)])
def test_invalid_native_ids_never_alias_or_wrap(fixture,field,value):
    *_,inv,original = fixture
    broken = copy.deepcopy(inv); broken['rows'][0][field] = value
    with pytest.raises(ValueError): m.validate_binding(broken,original)


@pytest.mark.parametrize('defect', ['retained_gain','selected_limit','joint_gravity','body_gravity','disabled','plugin'])
def test_unsupported_semantics_and_typed_record_tampering_fail(fixture,defect):
    model, data, api, inv, original = fixture
    selected = m.partition(inv)[1][0]
    if defect == 'retained_gain':
        original['arrays']['actuator_gainprm'][0][0] += 1.
        with pytest.raises(ValueError): m.validate_model_record(original)
        return
    if defect == 'selected_limit':
        model.actuator_forcelimited[selected['actuator_id']] = 1
        model.actuator_forcerange[selected['actuator_id']] = [1.,2.]
    if defect == 'joint_gravity': model.jnt_actgravcomp[selected['joint_id']] = 1
    if defect == 'body_gravity': model.body_gravcomp[1] = .1
    if defect == 'disabled': model.opt.disableactuator = 1
    if defect == 'plugin': model.nplugin = 1
    inv = m.isolation.inventory(model,SimpleNamespace(actuated_joints=m.plan.JOINT_NAMES))
    inv.update(nq=model.nq,nv=model.nv)
    with pytest.raises(ValueError): m.validate_binding(inv,m.model_record(model,data))


def test_forward_failure_retains_partial_evidence_and_restores_model(fixture):
    model, data, api, inv, original = fixture
    api.fail_at = 2
    report = {}
    with pytest.raises(RuntimeError,match='injected'):
        m.qualify(api,model,data,inv,original,lambda:'protected',report)
    assert report['status'] == 'INCOMPLETE' and len(report['cases']) == 1
    assert report['explicit_calls']['shadow_forwards'] == 2
    assert report['restored'] == original and report['before'] == report['after']
    with pytest.raises(ValueError): m.evaluate_qualification(report)


@pytest.mark.parametrize('fault', ['live_state','unrelated_model','silent_baseline','retained_force','passive','callback','range'])
def test_qualification_faults_fail_without_tuning_or_retry(fixture,fault):
    model, data, api, inv, original = fixture
    keep, selected = m.partition(inv)
    aid = keep[0]['actuator_id']
    def alter(model, shadow):
        if fault == 'live_state': data.qacc_warmstart[0] = 1.
        if fault == 'unrelated_model': model.geom_friction[0,0] = 2.
        if fault == 'silent_baseline': shadow.actuator_force[[r['actuator_id'] for r in selected]] = 0.
        if fault == 'retained_force' and not model.actuator_gainprm[selected[0]['actuator_id'],0]:
            shadow.actuator_force[aid] += .1
        if fault == 'passive' and not model.actuator_gainprm[selected[0]['actuator_id'],0]:
            shadow.qfrc_passive[0] += 1.
    api.on_forward = alter
    if fault == 'callback': api.get_mjcb_control = lambda: object()
    if fault == 'range':
        aid = selected[0]['actuator_id']; model.actuator_ctrlrange[aid] = [0.,0.]
        inv['actuators']['ctrlrange'][aid] = [0.,0.]
        original = m.model_record(model,data)
    report = {}
    with pytest.raises(ValueError): m.qualify(api,model,data,inv,original,lambda:'protected',report)
    assert not api.calls or len(api.calls) <= 25
    if report:
        assert report['status'] != 'COMPLETE'
        if fault not in ('unrelated_model','callback'): assert report['restored'] == original


@pytest.mark.parametrize('fault', ['drop','order','count','input','force','restore','protection'])
def test_saved_qualification_is_independently_checked(fixture,fault):
    report = qualification(fixture)
    if fault == 'drop': report['cases'].pop()
    if fault == 'order': report['cases'].reverse()
    if fault == 'count': report['explicit_calls']['shadow_forwards'] = 13
    if fault == 'input': report['cases'][0]['inputs'][1][0] = .2
    if fault == 'force': report['cases'][1]['actuator_force'][0] = 1.
    if fault == 'restore': report['restored'] = report['neutral']
    if fault == 'protection': report['after']['protected'] = 'changed'
    with pytest.raises(ValueError): m.evaluate_qualification(report)


@pytest.mark.parametrize('arm_id', ['A_NC','R_WP'])
def test_boundary_exact_order_no_early_patch_and_partial_trace_rejected(fixture,arm_id):
    model, data, api, inv, original = fixture
    report = qualification(fixture)
    gate = m.Intervention(arm_id,model,data,inv,original)
    with pytest.raises(ValueError,match='qualification'): gate.boundary(0,lambda:'protected')
    gate.accept_qualification(report)
    for index in range(5006):
        data.time = index*.0001
        gate.boundary(index,lambda:'protected')
        if index == 5004: assert m.model_record(model,data) == original
    assert gate.event['before'] == original
    assert gate.event['protected_before'] == gate.event['protected_after']
    assert gate.event['after'] == (gate.neutral if arm_id.startswith('R_') else original)
    # Patch is outside sample5005; first affected force record is5006.
    data.time = .5006; gate.boundary(5006,lambda:'protected')
    with pytest.raises(ValueError): gate.boundary(5006,lambda:'protected')
    with pytest.raises(ValueError): gate.boundary(5008,lambda:'protected')
    assert api.calls == ['allocate']+['reset','forward']*12
    with pytest.raises(ValueError): m.audit_trace(arm_id,inv,original,gate.event,[])


def test_phase_guard_detects_unrelated_model_write(fixture):
    model,data,api,inv,original = fixture
    gate = m.Intervention('R_NC',model,data,inv,original)
    gate.accept_qualification(qualification(fixture))
    model.geom_friction[0,0] += 1.
    with pytest.raises(ValueError,match='phase'): gate.boundary(0,lambda:'protected')


def test_control_zero_alone_leaves_bias_force_and_cannot_pass_neutralization(fixture):
    model,data,api,inv,original = fixture
    selected=m.partition(inv)[1][0]
    data.qpos[selected['qpos_range'][0]]=.1
    api.mj_forward(model,data)
    assert data.ctrl[selected['actuator_id']] == 0.
    assert data.actuator_force[selected['actuator_id']] != 0.
    with pytest.raises(ValueError,match='force remains'):
        m.audit_force(m.force_record(api,model,data),inv,True)


def test_shadow_alias_refused_before_live_reset_and_partial_retained(fixture):
    model,data,api,inv,original = fixture
    api.MjData=lambda model:data
    before=m.data_digest(data)
    report={}
    with pytest.raises(ValueError,match='alias'):
        m.qualify(api,model,data,inv,original,lambda:'protected',report)
    assert not api.calls and not report['cases']
    assert report['explicit_calls']['shadow_resets']==0
    assert report['restored']==original and before==m.data_digest(data)


def test_a_later_initialized_model_must_match_qualified_original(fixture):
    model,data,api,inv,original = fixture
    proof=qualification(fixture)
    model.geom_friction[0,0]+=1.
    changed=m.model_record(model,data)
    gate=m.Intervention('R_NP',model,data,inv,changed)
    with pytest.raises(ValueError,match='qualified M0'): gate.accept_qualification(proof)


def test_full_synthetic_trace_checks_terminal_force_and_cached_boundary(fixture):
    model,data,api,inv,original = fixture
    neutral = m.neutral_record(original,inv)
    samples = []
    for index in range(20001):
        if index in (0,5006):
            if index: m.write_rows(model,original,inv,True)
            api.mj_forward(model,data)
            force = m.force_record(api,model,data)
        samples.append(dict(state_index=index,time_s=index*.0001,
            model_sha256=(original if index <= 5005 else neutral)['sha256'],**force))
    event = dict(state_index=5005,time_s=5005*.0001,before=original,after=neutral,
        operation='ZERO_FULL_SELECTED_ROWS', selected_actuator_ids=[r['actuator_id'] for r in m.partition(inv)[1]],
        protected_before={'live':'same','protected':'same'}, protected_after={'live':'same','protected':'same'})
    assert m.audit_trace('R_NC',inv,original,event,samples)['passed']
    samples[-1] = copy.deepcopy(samples[-1])
    samples[-1]['actuator_force'][m.partition(inv)[1][0]['actuator_id']] = 1.
    with pytest.raises(ValueError): m.audit_trace('R_NC',inv,original,event,samples)
