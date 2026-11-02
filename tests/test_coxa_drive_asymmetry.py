"""Synthetic checks for the coxa drive asymmetry analysis; no connectome or physics."""
import math

import numpy as np
import pytest

from malecns_backend.embodiment import coxa_drive_asymmetry as d
from malecns_backend.loader import MaleCNSData
from malecns_backend.neural import MaleCNSBrain, ModelConfig


def tiny(n=40, seed=3):
    rng = np.random.default_rng(seed)
    rows, targets, counts = [0], [], []
    for i in range(n):
        t = np.sort(rng.choice(n, size=rng.integers(4, 12), replace=False))
        t = t[t != i]
        targets += t.tolist(); counts += rng.integers(1, 40, len(t)).tolist(); rows.append(len(targets))
    supers = ['vnc_motor', 'sensory_leg', 'vnc_interneuron']
    sup = np.array([1 if i < 6 else 0 if i >= n - 8 else 2 for i in range(n)], np.int32)
    signs = np.array([rng.choice([1., 1., .5, -1.]) for _ in range(n)], np.float32)
    types = [('OA-x' if i == 7 else f't{i}') for i in range(n)]
    return MaleCNSData(n, np.arange(100, 100 + n), {100 + i: i for i in range(n)}, np.zeros(n), np.zeros(n, np.int32),
                       np.zeros(n, np.int32), sup, np.zeros(n, np.int32), types, types, ['x'], supers, ['acetylcholine'],
                       np.array(rows, np.int64), np.array(targets, np.int32), np.array(counts, np.float32),
                       rng.uniform(.2, 8., n).astype(np.float32), signs, {}, (), {})


def test_rule_weights_equal_engine():
    data = tiny()
    config = ModelConfig.calibrated()
    brain = MaleCNSBrain(data, config)
    pre, post, pos = d.edges_into(data, set(range(data.neuron_count)))
    _, _, w, sign = d.rule_weights(data, config, pre, post, pos)
    assert np.array_equal(w, brain.weights[pos]) and np.array_equal(sign[pre], brain.pre_sign[pre])
    assert len(pos) == data.edge_count


def test_replay_reproduces_engine_spikes_exactly():
    data = tiny()
    config = ModelConfig.calibrated()
    brain = MaleCNSBrain(data, config); brain.reset(5)
    driven = list(range(6))  # 'sensory' neurons forced at high rate
    brain.set_external_drive(driven, 400.)
    fired = [tuple(int(x) for x in brain.step()) for _ in range(800)]
    mns = list(range(data.neuron_count - 8, data.neuron_count))
    recorded = [[t for t, f in enumerate(fired) if m in f] for m in mns]
    assert sum(map(len, recorded)) > 20  # the fixture actually drives the targets
    predicted, means = d.replay(fired, mns, brain.weights, np.asarray(data.row_ptr), np.asarray(data.target_indices),
                                brain.pre_sign, config, brain.delay_steps, set(driven), (0, 799))
    assert predicted == recorded
    status, rows = d.compare_spikes(predicted, recorded, (0, 799))
    assert status == 'REPLAY_EXACT'
    total = np.array(means['hair']) + np.array(means['other'])
    assert np.allclose(total, means['total_exc'], rtol=1e-4, atol=1e-6)


def test_compare_spikes_close_and_inconclusive():
    rec = [[10, 20, 30, 40, 50]]
    assert d.compare_spikes([[11, 20, 30, 40, 50]], rec, (0, 100))[0] == 'REPLAY_CLOSE'
    assert d.compare_spikes([[15, 25, 35, 45, 55]], rec, (0, 100))[0] == 'INCONCLUSIVE_REPLAY'


def terms(N, R, F, S, G):
    return dict(N_s=N, R=R, F=F, S=S, G=G)


def test_factor_identity_and_largest_loss():
    x, y = terms(5, 200, 190, 100, 100), terms(7, 900, 830, 500, 500)
    logs, total = d.factors(x, y)
    assert math.isclose(sum(logs.values()), total) and set(logs) == set(d.FACTORS)
    assert d.largest_loss(logs) == 'SYNAPSES_PER_SOURCE'
    assert d.largest_loss(dict(A=-1., B=-.95, C=.2)) == 'MIXED'
    assert d.largest_loss(dict(A=-1., B=-.5)) == 'A'
    assert d.largest_loss(dict(A=0., B=.3)) == 'NO_DEFICIT'


def test_q1_q3_and_g_star():
    config = ModelConfig.calibrated()
    gs = d.g_star(config)
    v = (config.v_rest*(config.e_exc - config.v_rest) + gs*config.e_exc)/((config.e_exc - config.v_rest) + gs)
    assert math.isclose(v, config.v_threshold)  # steady COBA potential at g* equals threshold
    assert d.q1(dict(RF=1., LF=gs + 1, LH=0.), gs) == 'RF_DIRECT_SUBTHRESHOLD'
    assert d.q1(dict(RF=gs, LF=0., LH=0.), gs) == 'RF_DIRECT_SUFFICIENT'
    assert d.q1(dict(RF=1., LF=1., LH=1.), gs) == 'ALL_SUBTHRESHOLD'
    assert d.q3(.4, .2) == 'INHIBITION_CONTRIBUTES' and d.q3(.39, .2) == 'INHIBITION_NOT_DECISIVE'


def test_mean_field_matches_simulated_conductance():
    config = ModelConfig.calibrated()
    w, r = .7, 120.
    p = r*config.dt/1000.
    rng = np.random.default_rng(0)
    g, acc = 0., []
    decay = math.exp(-config.dt/config.tau_syn)
    for _ in range(400000):
        if rng.random() < p:
            g += w
        acc.append(g); g *= decay
    assert d.mean_field(w, r, config) == pytest.approx(np.mean(acc), rel=.02)


def test_structural_terms_on_fixture():
    data = tiny()
    config = ModelConfig.calibrated()
    sets = {leg: {0, 1, 2} for leg in ('RF', 'LF', 'LH')}
    pools = {leg: dict(posterior={34, 35, 36}, anterior=set()) for leg in sets}
    s = d.structural(data, config, sets, pools, 120., config.min_synapses)
    t = s['RF']['terms']
    assert t['N_s'] == 3 and t['R'] >= t['F'] >= 0
    brain = MaleCNSBrain(data, config)
    W = sum(float(brain.weights[k])*float(brain.pre_sign[p_])*config.psp_scale
            for p_ in (0, 1, 2) for k in range(data.row_ptr[p_], data.row_ptr[p_+1]) if data.target_indices[k] in (34, 35, 36))
    assert math.isclose(sum(v['W'] for v in s['RF']['per_mn'].values()), W, rel_tol=1e-6)
