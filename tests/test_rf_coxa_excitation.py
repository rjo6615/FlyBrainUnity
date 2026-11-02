"""Synthetic checks for the RF coxa excitation analysis; no connectome or physics."""
import math

import numpy as np

from malecns_backend.embodiment import coxa_drive_asymmetry as d
from malecns_backend.embodiment import rf_coxa_excitation as e
from malecns_backend.neural import MaleCNSBrain, ModelConfig
from test_coxa_drive_asymmetry import tiny


def test_attribution_sums_to_replayed_excitation():
    data = tiny()
    config = ModelConfig.calibrated()
    brain = MaleCNSBrain(data, config); brain.reset(5)
    driven = list(range(6))
    brain.set_external_drive(driven, 400.)
    fired = [tuple(int(x) for x in brain.step()) for _ in range(800)]
    mns = list(range(data.neuron_count - 8, data.neuron_count))
    window = (200, 799)
    indptr, indices = np.asarray(data.row_ptr, np.int64), np.asarray(data.target_indices, np.int64)
    _, means = d.replay(fired, mns, brain.weights, indptr, indices, brain.pre_sign, config, brain.delay_steps,
                        set(driven), window)
    contrib, edges = e.attribute(fired, set(mns), brain.weights, indptr, indices, brain.pre_sign, config,
                                 brain.delay_steps, window)
    for i, m in enumerate(mns):
        ref = means['hair'][i] + means['other'][i]
        got = sum(contrib[m].values())
        assert abs(got - ref) <= max(1e-6*abs(ref), 1e-9)
        hair = sum(v for p, v in contrib[m].items() if p in driven)
        assert math.isclose(hair, means['hair'][i], rel_tol=1e-6, abs_tol=1e-9)
    assert all(brain.pre_sign[p] > 0 for p in edges)


def test_kernel_sum_closed_form():
    decay = .9
    brute = sum(decay**(t - dd) for dd in (3, 8, 20) for t in range(max(dd, 5), 16) if dd <= 15)
    assert math.isclose(e.kernel_sum([3, 8, 20], (5, 15), decay), brute)


def test_wiring_activity_identity_and_q2():
    w, a = e.split_terms(10., 20., 1., 8.)
    assert math.isclose(w + a, math.log(1/8))
    assert e.q2_label(w, a, 10.) == 'ACTIVITY_GAP'          # log .5 vs log .25
    w, a = e.split_terms(2., 20., 1., 4.)
    assert e.q2_label(w, a, 2.) == 'WIRING_GAP'
    assert e.q2_label(-1., -.95, 1.) == 'MIXED'
    assert e.q2_label(.1, .2, 1.) == 'NO_GAP'
    assert e.q2_label(-1., None, 1.) == 'ACTIVITY_GAP'
    assert e.q2_label(None, None, 0.) == 'WIRING_GAP'


def test_q1_q3_rules():
    assert e.q1_label(.6, .5) == 'HAIR_EVOKED'
    assert e.q1_label(.2, .49) == 'BASELINE'
    assert e.q1_label(.6, .2) == 'MIXED_LEGS'
    assert e.q3_label(1., 1., .2, 1.) == 'CONSEQUENCE_OF_HAIR_PLATES'
    assert e.q3_label(.5, 1., .2, 1.) == 'PRE_EXISTING_ASYMMETRY'
    assert e.q3_label(1., 1., .5, 1.) == 'NOT_DETERMINED'


def test_labels_end_to_end():
    best = dict(RF=1, LF=2, LH=3)
    g = dict(A_OFF={1: 1., 2: 1., 3: 4.}, A_ON={1: .2, 2: 8., 3: 20.})
    out = e.labels(best, g, {1: 10., 2: 12., 3: 30.})
    assert out['Q1']['label'] == 'HAIR_EVOKED'
    assert out['Q2']['label'] == 'ACTIVITY_GAP' and out['Q3']['label'] == 'CONSEQUENCE_OF_HAIR_PLATES'
    assert math.isclose(out['Q2']['wiring'] + out['Q2']['activity'], out['Q2']['total'])
