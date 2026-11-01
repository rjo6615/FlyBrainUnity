# Stage 1 — DNg100 front-leg motor rhythm in our engine (V1)

Preregistered 2026-11-01: `evidence/dng100-rhythm-v1/protocol.json` (SHA-256 locked in
`malecns_backend/embodiment/dng100_rhythm.py`). Protocol, code and tests are committed
before the single run.

Question: does our existing calibrated whole-CNS LIF engine, untuned, reproduce the
published prediction (Pugliese et al. 2025 preprint) that tonic left DNg100 drive
makes front-leg motor neurons fire rhythmically through the E1 (IN17A001) and E2
(INXXX466) core interneurons?

Design: Poisson drive to DNg100_L at 25/50/100/200 Hz, 3 s, 16 seeds; front-left
leg MN spikes smoothed (1 ms bins, 5 ms Gaussian) and scored with the preprint's
autocorrelation rhythmicity score over 0.25-3 s (trace demeaned before the
autocorrelation). Controls: no-drive baseline and 20 seeded random cholinergic
descending neurons at the same rates (4 seeds). Necessity: silence the
front-left E1 or E2 copy (most synapses onto front-left MNs) by withholding its
output at DNg100's best rate. A silenced condition with no active MN counts as
abolished.

Verdict: REPRODUCED needs best-rate score >= 0.5 and above the controls' 80th
percentile (C1), frequency 5-20 Hz (C2), and both silencings < 0.5 (C3). PARTIAL
if C1 holds but C2 or C3 fails; NOT_REPRODUCED if C1 fails. Drive-frequency
scaling is reported, not gated.

Limits: neural activity only, no body; whole-CNS spiking engine with fixed
parameters versus the preprint's isolated rate network with sampled parameters.
Results: `DNG100_RHYTHM_RESULTS.md`.
