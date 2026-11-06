# Rhythm, Step R1: the preprint's DNg100 rate model on our connectome (design)

Designed 2026-11-06. Design only: no protocol, code or run yet.

## Why this step

Walking needs a rhythm. Stage 1 (`DNG100_RHYTHM_V1.md`, results `DNG100_RHYTHM_RESULTS.md`,
2026-11-01) asked whether our calibrated whole-CNS LIF engine reproduces the prediction of
Pugliese, Tuthill, Brunton et al. 2025 (bioRxiv 10.1101/2025.09.12.675944, a preprint): that
tonic DNg100 drive makes front-leg motor neurons fire rhythmically through a core of E1
(IN17A001), E2 (INXXX466) and I1 (IN16B036). The answer was **NOT_REPRODUCED**:
- DNg100_L recruits the same 12 of 68 front-left MNs in every seed, but tonically;
- best rhythmicity was 0.196 against a required 0.5;
- tibia flexor and extensor were co-active.

V1 listed possible reasons but did not test them. The biggest unknown is whether the problem
is our **wiring** or our **engine**. V1 changed two things at once relative to the preprint:
1. the connectome (our maleCNS, not MANC);
2. the dynamics and context (a calibrated spiking whole-CNS engine, not a rate model of an
   isolated front-leg network with sampled parameters).

R1 holds the dynamics fixed to the preprint's own model and changes only the connectome. It
asks:

> **Does the preprint's rate model, built by the preprint's rules from our maleCNS wiring,
> produce the DNg100 front-left motor rhythm?**

- **If yes:** our wiring supports the rhythm, and V1's tonic output comes from our engine or
  its whole-CNS context. That points to a separately versioned bridge step (for example, the
  same isolated network in our LIF engine). It does not point to tuning.
- **If no:** the preprint's rhythm does not transfer to our wiring even under its own model,
  so changing the engine is not expected to produce it.

Nothing here changes the live engine, the calibration, mappings, gains or the body. It is a
neural-only reference-model test. No engine parameter is searched.

## Evidence gathered for this design (structure only; no simulation)

**The preprint's method.** From its Methods text, read 2026-11-06:
- **Units:** positive-rectified tanh rate units.
- **Sampled parameters** (normal, truncated at zero, redrawn per replicate):
  - a* ~ N(1, 0.1) and θ* ~ N(7.5, 0.6);
  - r_max ~ N(200, 10) Hz and τ ~ N(20, 2) ms.
- **Size scaling:** a = a*/s and θ = θ*·s, with s = neuron size / dataset median.
- **Weights:** |w| = synapse count, with a floor of 5. Acetylcholine is +, GABA and glutamate
  are −.
- **Network:** front-left-leg MNs, their premotor neurons, and the DNs onto those premotor
  neurons. Neurons need a neurotransmitter prediction.
- **Stimulus and solver:**
  - DNg100 is driven by I_stim = 250 (MANC), from 20 ms.
  - I_stim is doubled if fewer than 5 neurons are recruited and halved if more than 500 are,
    for up to 10 iterations; otherwise the replicate is NaN.
  - 1 s per replicate, Dopri5 with rtol 2e-6 and atol 5e-9.
- **Score:** the rhythmicity score V1 already implements, from 250 ms. An MN is included if
  r > 0.01 at any time after 250 ms.
- **What the text does not give** (it is in an equation image):
  - the global synaptic scale **b**;
  - the exact form of the nonlinearity.

**The repository already implements this model.** `fly-brain-main/src/ratenet.js` (checked in
since cd735e8) gives:
- the form `tau dr/dt = max(r_max tanh((a/r_max)(I + b Σ w r − θ)), 0) − r`;
- **b = 0.03**;
- the same parameter distributions;
- a VNC-region size median.

R1 takes b and the functional form from ratenet.js. That is declared provenance; the preprint
text does not confirm it. ratenet.js itself differs from the preprint in ways R1 does **not**
copy:
- it runs the whole CNS;
- it uses Euler integration at 1 ms;
- it snaps rates below 0.05 Hz to zero;
- it caps size ratios at 20.

**Our front-left network by the preprint's rule** (maleCNS cache, floor 5 synapses):

| Part | Count |
|---|---|
| Front-left MNs (`bodymap.json` ' T1 left', as V1) | 68 |
| Premotor (≥5 synapses onto those MNs, not MNs) | 1,280 (137 of them DNs) |
| DNs onto the non-DN premotor neurons | 924 |
| **Network** | **2,136 neurons, 65,462 edges, 1,381,218 synapses** |

For comparison, the preprint's MANC network has 4,604 neurons, 144 of them MNs.

- **Transmitters** (counts before the unknown-transmitter filter below): acetylcholine 1,311,
  GABA 441, glutamate 336, unknown 46, serotonin 2.
- **Core cells:** exactly one copy of each is in the network.

  | Cell | Index | Body ID | Transmitter |
  |---|---|---|---|
  | DNg100_L (stimulated) | 36 | 10045 | ACh |
  | DNg100_R (also in the network) | 46 | 10056 | ACh |
  | E1 IN17A001_L | 142920 | 800173 | ACh |
  | E2 INXXX466_L | 143429 | 800863 | ACh |
  | I1 IN16B036_L | 144200 | 801884 | glutamate |

  The E1 and E2 copies are the ones V1 silenced.

## Method

**Network.** Built as above from the maleCNS cache:
- the 68 V1 front-left MNs;
- every non-MN neuron with ≥5 synapses onto them;
- every descending neuron with ≥5 synapses onto a non-DN premotor neuron.

Following the preprint's filter, neurons with transmitter `unknown` are excluded, and only
edges with ≥5 synapses among the remaining neurons are kept. The two serotonergic neurons take
sign +1 (ratenet.js `modulatorySign`); the preprint states no rule for them.

**Model.** For every neuron i:

    τ_i dr_i/dt = max(r_max,i · tanh((a_i / r_max,i) · (I_i + b Σ_j w_ij r_j − θ_i)), 0) − r_i

- b = 0.03, and w_ij = sign(j) × synapse count.
- a_i = a*/s_i and θ_i = θ*·s_i, where s_i = size_i / median size of the VNC-region neurons.
  That median is the positive sizes of vnc_/descending/ascending/sensory_ascending/
  sensory_descending/efferent superclasses, taking the upper-middle element; the existing
  `region_scales` / `regionSizeRef` rule gives 542,747,200.
- s_i is not capped. The number of neurons with s > 20 is reported.
- a*, θ*, τ and r_max are drawn per replicate from the preprint's distributions with
  `numpy.random.default_rng(seed)`, redrawing non-positive values.
- Integration: `scipy.integrate.solve_ivp`, method RK45 (Dormand–Prince 5(4), the Dopri5
  pair), rtol 2e-6, atol 5e-9.
  - r(0) = 0 and the run lasts 1,000 ms.
  - Rates are sampled every 1 ms.
  - I is zero except I_stim on the stimulated neuron from 20 ms. The step is handled by
    integrating 0–20 ms and 20–1,000 ms as two segments.
- Neither the snap nor the size cap is used.

**Per-replicate drive adjustment (the preprint's rule).**
- Start at I_stim = 250.
- "Recruited" = network neurons with r > 0.01 at any sample after 250 ms.
- Fewer than 5 recruited: double I_stim. More than 500: halve it. At most 10 adjustments.
- If the rule never lands between 5 and 500, the replicate is infeasible (NaN).
- Each adjustment re-runs the same parameter draw.

**Readout and score.** Reused unchanged from V1 (`dng100_rhythm.rhythmicity`):
- each MN's 1-ms rate trace over 250–1,000 ms, with no smoothing (it is already a rate);
- an MN is active if r > 0.01 at any sample after 250 ms;
- a replicate's score is the mean over its active MNs, or NaN if none is active;
- a replicate's frequency is the median of 1000/period over active MNs with a score above 0;
- a condition's score is the mean over its feasible replicates; its frequency is the median
  over them.

**Conditions** (seeds are parameter draws):

| Condition | Stimulated | Silenced (rate held at 0) | Replicates |
|---|---|---|---|
| DNG100 | DNg100_L | none | seeds 1–64 |
| SIL_E1 / SIL_E2 / SIL_I1 | DNg100_L | E1 / E2 / I1 copy above | seeds 1–64 each |
| CONTROL_k (k = 1..20) | one control DN | none | seeds 1–16 each |
| BASELINE | none (I = 0) | none | seeds 1–16 |

- Each silenced condition uses the same seeds as DNG100 and its own drive adjustment.
- **Controls:** 20 acetylcholine descending neurons in the network other than DNg100_L/R,
  drawn without replacement by `numpy.random.default_rng(20261107)` from the sorted list of
  their dense indices. This is the preprint's screen population restricted to our network.
- **Total:** 64 × 4 + 20 × 16 + 16 = 592 replicates.
- Cost is unknown until timed. The build times one no-drive 100-ms replicate (discarded,
  outcome unread). If 592 replicates would take more than 8 hours, the replicate counts are
  reduced **before** preregistration, by the same factor for every condition, and that is
  recorded.

## Acceptance (as V1, with I1 added to necessity)

| Criterion | Rule |
|---|---|
| C1 rhythm | DNG100 score ≥ 0.5 **and** above the 80th percentile of the feasible control scores |
| C2 frequency | DNG100 frequency in [5, 20] Hz |
| C3 necessity | SIL_E1, SIL_E2 and SIL_I1 each score < 0.5. A silenced condition with no feasible replicate counts as abolished. |

| Verdict | Rule |
|---|---|
| `RATE_RHYTHM_REPRODUCED` | C1, C2 and C3 |
| `RATE_RHYTHM_PARTIAL` | C1, with C2 or C3 failing |
| `RATE_RHYTHM_NOT_REPRODUCED` | C1 fails |
| `INCONCLUSIVE` | Any of: a cache/protocol hash mismatch; the reference-fidelity test fails; no feasible DNG100 replicate. |

**Reported, not gated:**
- the fraction of DNG100 replicates scoring ≥ 0.5;
- the final I_stim distribution;
- recruited counts;
- per-MN scores and periods, with each MN's muscle name;
- flexor/extensor phase relation for the tibia pair: the lag of the cross-correlation peak;
- control scores;
- baseline activity;
- the number of neurons with s > 20.

## Integrity

- **I1 sources:** the protocol records the sha256 values of the maleCNS cache fingerprints (as
  `load_cache` checks them), `bodymap.json`, `fly-brain-main/src/ratenet.js` and the V1 module.
  The network membership (sorted body IDs) is written to the report, and its sha256 is
  declared in the protocol.
- **I2 reference fidelity:** before any run, a unit test compares the derivative of the new
  Python right-hand side with one Euler step of the actual `ratenet.js` `RateNetwork.step`.
  It runs the code through `node`, on a small synthetic fixture with snap 0, adaptation 0,
  depression 0, no cap, and identical drawn parameters passed in. They must agree within
  float32 tolerance. This checks the equation and the sign/weight/size handling, not the
  solver.
- **I3 solver:** a unit test on a two-neuron analytic case (no recurrence; exponential
  approach to a fixed tanh target) is required to match the closed form within 1e-6.
- **I4 completeness:** every declared replicate is present, and each has a status (feasible,
  infeasible or adjusted) and its parameter seed.

## Design expectations (recorded before any rate simulation)

- **P1:** C1 holds, i.e. the DNG100 score is ≥ 0.5. Basis: the preprint reports the rhythm in
  two different connectomes (MANC and FANC), which suggests the motif is robust to wiring
  differences.
- **P2:** SIL_I1 abolishes it (< 0.5). Basis: the core needs an inhibitory element to
  alternate.
- **P3:** the frequency is in 5–20 Hz.

These are guesses, not adjusted to anything seen; wrong ones are recorded as wrong.

## What each outcome means (declared now)

- **REPRODUCED or PARTIAL:**
  - Under the preprint's rate dynamics, our wiring contains a DNg100-driven front-left
    rhythm generator.
  - V1's tonic output is then attributable to differences in engine or context: spiking LIF
    with calibrated fixed parameters, a 6-synapse floor, conductance-based inhibition, the
    whole CNS.
  - The next step would be a **separately designed bridge**: the same isolated network
    stepped through our LIF engine unchanged, and then whole-CNS context. Each is a versioned
    question; none is a parameter search.
- **NOT_REPRODUCED:** the preprint's rhythm does not transfer to our maleCNS wiring, even
  under its own model as reconstructed here. Possible reasons:
  - connectome differences;
  - our 68-MN set versus their 144;
  - the b provenance;
  - the preprint itself.

  Engine changes are not expected to help, and the rhythm route to walking stays blocked.
- **In either case** it says nothing about walking, legs other than front-left, or the body.

## Limits

- **Reconstruction, not the authors' code.**
  - b and the exact nonlinearity come from ratenet.js; the preprint text does not confirm
    them.
  - "Recruited" in the adjustment rule is read as "active network neurons".
  - Their 1,024 replicates are reduced to 64.
- **Different connectome and MN set.** Our 68 bodymap MNs are those our body uses; the
  preprint used 144 MANC "fl" MNs.
- **Rate model.** No spikes, no conduction delay, no adaptation.
- **Isolated network.** No brain, other legs or sensory feedback.
- **Neural only.** No body, physics, gait or balance. No motor coordinate status change
  (20/42 admitted, +4 conditional).

## Build and run plan (on approval)

1. `docs/evidence/dng100-rate-model-v1/protocol.json`, holding:
   - these rules;
   - the network body-ID hash;
   - the control draw;
   - the source hashes.
2. `malecns_backend/embodiment/dng100_rate_model.py`:
   - network extraction, parameter draws, the RHS, solve_ivp and the adjustment rule;
   - it reuses `dng100_rhythm.rhythmicity`, `front_left_mns` and the existing size-median
     rule;
   - with `--replicate` (for timing), `--run` and `--evaluate` options.
3. Tests:
   - the I2 ratenet.js fidelity test (through `node`; it fails if `node` is absent);
   - the I3 analytic solver test;
   - adjustment-rule logic;
   - verdict logic on synthetic scores.
4. Time one no-drive replicate (discarded). Then commit and push the preregistration, run
   once in the background, evaluate once, and record the results, handoff and roadmap.

## Amendments at build time (before any protocol simulation)

Recorded in `docs/evidence/dng100-rate-model-v1/protocol.json` (sha 3785bbeb…):
- **Scored MNs are kept regardless of transmitter.** The structure-only network description
  showed that removing every `unknown` neuron would drop 21 of the 68 scored MNs. An unknown
  MN sends no input (sign 0). After this rule, 25 non-MN unknowns are removed, leaving
  2,111 neurons and 63,837 edges (zero-sign MN edges included).
- **Timing used a driven replicate**, DNg100_L with seed 0, which is not a protocol seed. A
  no-drive replicate is trivial (all rates stay 0).
  - Only the wall time (about 0.1 s) was read.
  - The output also showed that it used 3 simulations in the drive adjustment.
  - Because the cost is negligible, the replicate counts are unchanged.
- **One command runs and scores everything**, computing the verdict in-process as Stage 1 V1
  did. There are no separate run and evaluate steps.
