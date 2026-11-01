"""Synthetic checks for the Stage 1 DNg100 rhythm test; no connectome or CNS run."""
import math
from types import SimpleNamespace

import numpy as np
import pytest

from malecns_backend.embodiment import dng100_rhythm as r


def test_rhythmicity_scores_periodic_waveforms_high_and_noise_low():
    t = np.arange(2750)
    sine, period = r.rhythmicity(np.sin(2*np.pi*t/100))
    assert sine == pytest.approx(1, abs=1e-6) and period == 100
    saw, _ = r.rhythmicity((t % 80)/80.)
    assert saw > .8
    noise, _ = r.rhythmicity(np.random.default_rng(0).normal(size=2750))
    assert noise < .3
    assert r.rhythmicity(np.zeros(100)) == (0., None)


def spec():
    return dict(readout=dict(analysis_window_ms=[250, 3000]), stimulus=dict(duration_ms=3000))


def test_simulation_score_uses_active_mns_and_reports_frequency():
    dt = .5
    rhythmic = [int(k*100/dt) + j for k in range(30) for j in range(0, 20, 2)]  # 10 Hz bursts
    result, freq, detail = r.score_simulation({1: rhythmic, 2: [10, 20], 3: []}, spec(), dt)
    assert set(detail) == {1} and result > .8 and freq == pytest.approx(10, rel=.02)
    assert math.isnan(r.score_simulation({1: [1, 2]}, spec(), dt)[0])


def level(rate, score, freq=10.):
    return dict(rate_hz=rate, score=score, frequency_hz=freq)


def test_verdict_rules_follow_protocol():
    dng = [level(25, .2), level(50, .7, 9.), level(100, .6, 11.), level(200, math.nan, math.nan)]
    controls = {str(i): [level(25, .1*i/20)] for i in range(20)}
    ok = {'E1': level(50, .1), 'E2': level(50, math.nan)}
    result, d = r.verdict(dng, controls, ok, None)
    assert result == 'REPRODUCED' and d['dng100_best_rate_hz'] == 50 and all(d['checks'].values())
    assert r.verdict(dng, controls, {'E1': level(50, .6), 'E2': level(50, .1)}, None)[0] == 'PARTIAL'
    strong = {str(i): [level(25, .9)] for i in range(20)}
    assert r.verdict(dng, strong, ok, None)[0] == 'NOT_REPRODUCED'
    assert r.verdict([level(25, math.nan)], controls, ok, None)[0] == 'INCONCLUSIVE'
    slow = [level(50, .7, 3.)]
    assert r.verdict(slow, controls, ok, None)[0] == 'PARTIAL'


def test_copy_selection_and_control_sampling_are_deterministic():
    data = SimpleNamespace(types=['E', 'E', 'X', 'M'], row_ptr=[0, 1, 3, 3, 3], target_indices=[3, 3, 2],
                           synapse_counts=[4, 9, 50])
    chosen, totals = r.select_copy(data, 'E', [3])
    assert chosen == 1 and totals == {0: 4, 1: 9}


class Brain:
    def __init__(self):
        self.config = SimpleNamespace(dt=.5); self.drive = {}; self.withheld = None
    def reset(self, seed): self.t = 0; self.seed = seed
    def clear_external_drive(self): self.drive = {}
    def set_external_drive(self, idx, rate): self.drive.update({i: rate for i in idx})
    def step(self):
        self.t += 1
        return np.array([7]) if self.drive and self.t % 10 == 0 else np.array([], dtype=int)


def test_simulate_records_watched_spikes_and_applies_silencing():
    b = Brain()
    spikes = r.simulate(b, 5, 100, 3, [7, 8], 100, silenced=[9])
    assert len(spikes[7]) == 20 and spikes[8] == [] and list(b.transmission_withheld_indices) == [9]
    assert b.drive == {}


def test_protocol_lock_and_front_left_selection():
    assert r.protocol()['stimulus']['rates_hz'] == [25, 50, 100, 200]
    bm = dict(muscles=[dict(name='Ti flexor MN T1 left', idx=[3, 1]), dict(name='Ti flexor MN T1 right', idx=[9]),
                       dict(name='Tr flexor MN T1 left', idx=[1, 5])])
    assert r.front_left_mns(bm) == [1, 3, 5]
