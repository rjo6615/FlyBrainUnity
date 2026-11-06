"""Synthetic tests for rhythm Step R1 (no maleCNS data, no protocol run)."""
import json
import math
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from malecns_backend.embodiment import dng100_rate_model as rm

ROOT = Path(__file__).resolve().parents[1]
NTS = ['unknown', 'acetylcholine', 'gaba', 'glutamate', 'dopamine', 'serotonin', 'octopamine', 'histamine']


def fake_data(edges, nt, sup, sizes, n):
    """edges: list of (pre, post, count). CSR by presynaptic neuron, like the maleCNS cache."""
    edges = sorted(edges)
    row_ptr = np.zeros(n + 1, np.int64)
    for pre, _, _ in edges:
        row_ptr[pre + 1] += 1
    return SimpleNamespace(
        neuron_count=n, row_ptr=np.cumsum(row_ptr), target_indices=np.array([e[1] for e in edges], np.int64),
        synapse_counts=np.array([e[2] for e in edges], np.int64), neurotransmitters=NTS,
        neurotransmitter_ids=np.array([NTS.index(x) for x in nt]), superclasses=['vnc_intrinsic', 'descending_neuron',
                                                                                   'vnc_motor'],
        superclass_ids=np.array(sup), neuron_sizes=np.array(sizes, np.float32), body_ids=np.arange(100, 100 + n),
        bodymap={'muscles': []})


def test_ratenet_fidelity_one_euler_step(tmp_path):
    """I2: Python RHS (signs, 5-synapse floor, size scaling, silencing) equals one ratenet.js Euler step."""
    node = shutil.which('node')
    if node is None:
        pytest.fail('node is required for the I2 reference-fidelity test')
    rng = np.random.default_rng(3)
    n = 7
    nt = ['acetylcholine', 'gaba', 'glutamate', 'acetylcholine', 'serotonin', 'histamine', 'acetylcholine']
    edges = [(pre, post, int(rng.integers(1, 30))) for pre in range(n) for post in range(n)
             if pre != post and rng.random() < .6]
    sizes = rng.uniform(.3, 3., n)*5e8
    data = fake_data(edges, nt, [0]*n, sizes, n)
    net = list(range(n))
    W, _, _ = rm.signed_matrix(data, net)
    p = dict(a_star=rng.uniform(.8, 1.2, n), theta_star=rng.uniform(6, 9, n), tau=rng.uniform(16, 24, n),
             rmax=rng.uniform(180, 220, n))
    size_ref = 5.4e8
    a, theta, _ = rm.scale(p, data.neuron_sizes.astype(np.float64), size_ref)
    r = rng.uniform(0, 80, n)
    r[2] = 0.
    I = rng.uniform(0, 300, n)
    sil = np.zeros(n, bool)
    sil[4] = True
    dt = 1.
    expected = r + dt*rm.rhs(r, W, I, a, theta, p['tau'], p['rmax'], sil)
    indptr = np.asarray(data.row_ptr).tolist()
    fixture = dict(N=n, indptr=indptr, indices=data.target_indices.tolist(), weights=data.synapse_counts.tolist(),
                   nt=data.neurotransmitter_ids.tolist(), size=data.neuron_sizes.tolist(), sizeRef=size_ref,
                   dt=dt, b=rm.B, minSyn=rm.FLOOR, r=r.tolist(), I=I.tolist(), silenced=sil.astype(int).tolist(),
                   **{k: v.tolist() for k, v in p.items()})
    path = tmp_path/'fixture.json'
    path.write_text(json.dumps(fixture))
    out = subprocess.run([node, str(ROOT/'tests/js/ratenet_step_fixture.mjs'), str(path)], capture_output=True,
                         text=True, check=True, cwd=ROOT)
    got = np.array(json.loads(out.stdout)['r_next'])
    assert np.allclose(got, expected, rtol=2e-4, atol=1e-3), (got, expected)
    assert (W.toarray() != 0).sum() == sum(c >= rm.FLOOR for _, _, c in edges)


def test_solver_matches_closed_form():
    """I3: unconnected neurons approach the tanh target exponentially from the stimulus onset."""
    W = rm.sparse.csr_matrix((2, 2))
    a, theta = np.array([1.1, 1.]), np.array([7., 7.5])
    tau, rmax = np.array([20., 18.]), np.array([200., 205.])
    rates = rm.simulate(W, a, theta, tau, rmax, 0, 250., [], duration=200.)
    target = rmax[0]*np.tanh(a[0]/rmax[0]*(250. - theta[0]))
    t = np.arange(200.)
    closed = np.where(t < 20, 0., target*(1 - np.exp(-(t - 20)/tau[0])))
    assert np.max(np.abs(rates[:, 0] - closed)) < 1e-6*target + 1e-6
    assert np.all(rates[:, 1] == 0)


def test_adjust_rule_doubles_halves_and_gives_up():
    def runner(counts):
        seq = iter(counts)

        def run(i):
            n = next(seq)
            rates = np.zeros((1000, 600))
            rates[300, :n] = 1.
            return rates
        return run
    _, info = rm.adjust(runner([2, 3, 10]))
    assert info['status'] == 'FEASIBLE' and info['i_stim'] == 1000. and info['adjustments'] == 2
    _, info = rm.adjust(runner([600, 40]))
    assert info['status'] == 'FEASIBLE' and info['i_stim'] == 125.
    _, info = rm.adjust(runner([0]*11))
    assert info['status'] == 'INFEASIBLE' and len(info['history']) == 11


def test_score_rhythmic_vs_tonic():
    t = np.arange(1000)
    rates = np.zeros((1000, 3))
    rates[:, 0] = 50 + 40*np.sin(2*np.pi*t/100)
    rates[:, 1] = 30.
    score, freq, detail = rm.score_rates(rates, {10: 0, 11: 1, 12: 2}, {10: 'Ti flexor MN T1 left'})
    assert detail[10]['score'] > .9 and detail[11]['score'] == 0 and 12 not in detail
    assert math.isclose(freq, 10., rel_tol=.02)


def test_tibia_phase_antiphase():
    t = np.arange(1000)
    rates = np.stack([50 + 40*np.sin(2*np.pi*t/100), 50 - 40*np.sin(2*np.pi*t/100)], axis=1)
    ph = rm.tibia_phase(rates, {1: 0, 2: 1}, {1: 'Ti flexor MN T1 left', 2: 'Ti extensor MN T1 left'})
    assert ph['corr_at_zero'] < -.9 and abs(abs(ph['peak_lag_ms']) - 50) <= 1


def test_network_rule_keeps_mns_and_drops_unknown_premotor():
    # 0,1 MNs (1 unknown); 2 premotor ACh; 3 premotor unknown; 4 DN onto 2; 5 DN onto MN only; 6 weak premotor
    nt = ['glutamate', 'unknown', 'acetylcholine', 'unknown', 'acetylcholine', 'acetylcholine', 'gaba']
    sup = [2, 2, 0, 0, 1, 1, 0]
    edges = [(2, 0, 9), (3, 1, 7), (4, 2, 6), (5, 0, 8), (6, 0, 4), (1, 2, 20)]
    data = fake_data(edges, nt, sup, [1.]*7, 7)
    net, counts = rm.build_network(data, mns=[0, 1])
    assert net == [0, 1, 2, 4, 5]
    assert counts['unknown_removed'] == 1 and counts['premotor_dns'] == 1
    W, _, _ = rm.signed_matrix(data, net)
    assert W[2, 1] == 0                                    # unknown MN sends no input
    assert W[0, 2] == 9 and W[2, 3] == 6                   # local indices: 2 -> 0, 4 (pos 3) -> 2


def test_verdict_rules():
    s = lambda score, f=10.: dict(score=score, frequency_hz=f)
    ctl = {str(k): s(.1*k/10) for k in range(10)}
    sil = {'E1': s(.2), 'E2': s(math.nan), 'I1': s(.1)}
    assert rm.verdict(s(.7), ctl, sil)[0] == 'RATE_RHYTHM_REPRODUCED'
    assert rm.verdict(s(.7, 30.), ctl, sil)[0] == 'RATE_RHYTHM_PARTIAL'
    assert rm.verdict(s(.7), ctl, {**sil, 'I1': s(.6)})[0] == 'RATE_RHYTHM_PARTIAL'
    assert rm.verdict(s(.4), ctl, sil)[0] == 'RATE_RHYTHM_NOT_REPRODUCED'
    assert rm.verdict(s(.7), {**ctl, **{f'h{k}': s(.9) for k in range(5)}}, sil)[0] == 'RATE_RHYTHM_NOT_REPRODUCED'
    assert rm.verdict(s(math.nan), ctl, sil)[0] == 'INCONCLUSIVE'
