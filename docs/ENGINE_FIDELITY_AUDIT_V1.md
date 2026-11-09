# Engine fidelity audit, Step F1: why does descending drive not reach the locomotor core? (design)

Designed 2026-11-08. **Status: designed only** (no protocol, code or run). This is a neural-only
audit (no body, no physics) of the live, calibrated whole-CNS LIF engine. It does not change the
live engine, its calibration, weights, signs, mappings or motor admission.

## Why this step

Both the rhythm track and the balance track keep running into the same symptom:
- **Rhythm (V1, R1–R9, L1).** In the rate model of R1's isolated front-left network, some DNs
  (DNg75_R, DNa02_L) engage the E1/E2/I1 core and give a rhythm (R5). In the live engine the
  same DNs barely engage it (L1: E1/E2 silent for DNg75_R; 4–8 Hz for DNa02_L only at 200 Hz).
  DNg100_L drives MNs tonically (V1).
- **Balance (coxa push, Step D, D5).** Sensory input reaches leg motor neurons, but every
  closed-loop response measured so far is destabilising.

Before more behavioral experiments, we need to know whether the engine turns the connectome
into motor-network activity faithfully. F1 asks:

> **A (defect check).** Does the live engine implement its own declared rules correctly on the
> real data for the front-left motor network: its configuration, weights, signs, sizes,
> masks and identities?
>
> **B (difference decomposition).** Of the declared rule differences between the live engine
> and the rate model, does any one, alone, let descending drive engage the core in the live
> engine?
>
> **C (description).** How do the two models weight the inputs to E1, E2 and I1?

Only Part A can justify a change to the live engine, and only through a separately versioned
correction step with reference evidence. Part B is a diagnostic. Its swaps are copied from the
rate model's specification, not searched, and they never change the live engine. A B result
that "engages the core" is **not** a reason to adopt that rule.

## Evidence gathered for this design (structure only; no simulation)

- **The live engine** (`malecns_backend/neural.py`) is a literal port of
  `fly-brain-main/src/lif.js`. `tests/test_calibrated_neural_parity.py` checks the constructor and
  integration against the JS code, on a synthetic fixture.
- **The calibration** (`fly-brain-main/public/data/brain_params.json`) comes from a CEM search
  (`scripts/calib_search.mjs`, 20 generations × 24). Its benchmark terms are mostly brain-level:
  sugar/bitter feeding, Kenyon-cell sparseness, PN, loom and baseline activity. It also has two
  leg terms ("legs" 1.0, "rhythm" 0.418, with legRhythm 0.251). The parameters are global: one
  set for the whole CNS, including the nerve cord. This is context, not a defect.
- **Declared rule differences** between the live engine and R1's rate model:

| Rule | Live engine | Rate model (R1, from ratenet.js and the preprint) |
|---|---|---|
| Context | whole CNS (~165k neurons) | isolated front-left network (2,136 neurons) |
| Synapse floor | ≥ 6 synapses | ≥ 5 |
| Inhibitory weights | × 0.606 (`inhGain`) | × 1 |
| Signs | graded (`ntsign.bin`) | binary by transmitter (ACh +, GABA/Glu −) |
| Size | weights × (s_post)^−0.609, capped | gain a*/s and threshold θ*·s |
| Unit | conductance-based LIF, spikes | rectified tanh rate unit |
| Drive | Poisson forced spikes (L1) | constant current, adjusted per replicate |

The first four can be swapped in the LIF engine using its own options
(`effective_weights`, `min_synapses`, `inhibitory_gain`, `graded_sign`). The last three cannot
be translated without inventing a mapping, so Part C only describes them.

## Part A: defect checks (gated)

Each check compares the engine with a declared reference. A failure is a **demonstrated
defect** only when the reference is unambiguous.

| Check | Reference | Rule |
|---|---|---|
| A1 configuration | `brain_params.json` | `ModelConfig.calibrated()` equals the file on every mapped key; the L1 harness builds the brain with it and no override |
| A2 port parity | `lif.js` | the existing parity test passes, unchanged |
| A3 weights on real data | the documented rule, re-implemented independently in the audit | for every edge into E1, E2, I1 and the 68 front-left MNs, the engine's weight equals count × size factor × inhibitory gain (when sign < 0), where count ≥ `min_synapses` and the target is not sensory; exact in float32 |
| A4 signs | the cache's transmitter predictions | for every neuron in R1's network, sign < 0 iff GABA, glutamate or histamine; sign > 0 for ACh, dopamine and serotonin; 0 for OA-types (neuromodulation on). The graded magnitudes are reported. |
| A5 sizes and region | `neuron_size.bin` and the superclass regex | each network neuron's size factor equals the rule using its region's upper-middle median; region medians equal `region_scales`; every DN, AN and VNC neuron is in region 2 |
| A6 identities | body IDs | the three DNs, E1/E2/I1 and the 68 MNs resolve from body ID to dense index exactly (L1's I1 values) |
| A7 sensory mask | the declared rule | the mask removes only edges whose target is in a sensory superclass; the count removed inside the network is reported |

| Label | Rule |
|---|---|
| `DEFECT_FOUND` | any of A1–A7 fails |
| `NO_DEFECT_FOUND` | all pass |

## Part B: single-rule swaps (gated as a diagnostic, never adopted)

**Simulation.** L1's harness (`lif_driver_rhythm.one`) unchanged: neural-only, 3 s, Poisson forced
drive on one DN, front-left MNs and the core read out.
- **Drive:** DNg100_L, DNg75_R and DNa02_L, each at 100 and 200 Hz.
- **Seeds:** 1–8.

| Config | Change from the live engine |
|---|---|
| S0 LIVE | none (reproduction gate) |
| S1 ISOLATED | weights zeroed for every edge with its pre- or postsynaptic neuron outside R1's network (membership sha cdcfcd23…) |
| S2 MINSYN5 | `min_synapses` = 5 |
| S3 INHGAIN1 | `inhibitory_gain` = 1 |
| S4 BINARYSIGN | `graded_sign` = False |
| S5 ALL | S1 + S2 + S3 + S4 |

6 configs × 3 DNs × 2 rates × 8 seeds = **288 simulations**. At L1's cost (about 6 s for each
whole-CNS simulation), that is roughly 30 min or less.

**Readout per simulation** (over 250–3,000 ms):
- E1, E2 and I1 mean rates;
- the number of front-left MNs active (≥ 5 spikes);
- L1's rhythmicity score (reported only).

**Core engaged** for a config, DN and rate: E1 and E2 **both** ≥ 10 Hz mean in at least 5 of the 8
seeds. A config engages for a DN if it is engaged at either rate. The 10 Hz bar is a declared,
not derived, level. L1's best case (DNa02_L at 200 Hz: E1 3.9 Hz, E2 7.6 Hz) is below it.

| Label (first matching row) | Rule |
|---|---|
| `INCONCLUSIVE` | S0 does not reproduce L1 exactly for DNg75_R and DNa02_L at 100 and 200 Hz, seeds 1–8 (scores and per-MN spike counts) |
| `SINGLE_RULE_ENGAGES` | at least one of S1–S4 engages the core for at least one DN |
| `COMBINATION_ONLY` | only S5 engages it |
| `NOT_THESE_RULES` | no config engages it |

Reported, not gated:
- every config × DN × rate cell;
- which rules engage which DNs;
- the rhythm scores;
- the network-wide active fraction (for S1, the network only).

## Part C: input weighting of the core (description only)

For E1, E2 and I1, and for each of the three DNs:
- the direct DN → cell weight under both rules (LIF effective PSP in mV, and rate-model
  b · w · a/θ);
- each cell's size factor (LIF) and its gain and threshold (rate model);
- the edges into the cell that the 6-synapse floor drops and the 5-synapse floor keeps;
- the excitatory and inhibitory weighted input from inside R1's network vs from the rest of the
  CNS (live weights);
- the strongest 2-hop DN → premotor → core paths under each rule.

Nothing in Part C is gated.

## Integrity (declared now)

- **Z1 sources:** the hashes of `neural.py`, `lif.js`, `ratenet.js`, `brain_params.json`, the
  cache fingerprints, `bodymap.json`, the L1 module and its result, and the R1 network membership.
- **Z2 reproduction:** the S0 gate above (hard; it makes Part B `INCONCLUSIVE` on failure).
- **Z3 swap audit:** each config's brain differs from LIVE only in the declared rule. Weights,
  signs and options are compared, and the number of changed weights is recorded.
- **Z4 completeness:** 288 simulations, each 3 s.

## Expectations (recorded now)

- **XA:** `NO_DEFECT_FOUND`. The engine is a parity-tested port, and earlier steps resolved
  identities exactly.
- **XB:** `NOT_THESE_RULES`. The gap lies in the unit type, size handling or drive form, which
  F1 can only describe. If any single swap engages the core, the most likely is S1 ISOLATED,
  because whole-CNS inhibition is absent from the rate model.

Wrong expectations are recorded as wrong.

## What each outcome means (declared now)

- **`DEFECT_FOUND`:** a separately versioned correction step, with reference evidence and tests.
  Affected earlier results are re-examined in new evidence, never overwritten. That would be the
  first change to the live engine justified by fidelity, not by behavior.
- **`NO_DEFECT_FOUND` + `SINGLE_RULE_ENGAGES`:** the engine is faithful to itself, and one
  modelling choice of the calibration blocks descending drive from reaching the core. That rule
  is a candidate for a scientific question (is it right for the nerve cord?), not a fix. Adopting
  it would be a model change needing evidence beyond "it engages the core". That decision is the
  user's.
- **`NO_DEFECT_FOUND` + `COMBINATION_ONLY`:** the same, for the combination.
- **`NO_DEFECT_FOUND` + `NOT_THESE_RULES`:** the swappable rules do not explain the gap. The
  remaining candidates are the neuron model (spiking vs graded; many VNC interneurons are
  non-spiking), size handling and drive form. The next step would be a desk review of
  neuron-model evidence for the core cells before any simulation.
- **In no case** does F1 show rhythm, balance, walking or a biological role. Part B swaps are
  probes, not proposed parameters.

## Limits

- One leg's network (front-left) and three DNs.
- Part B tests four rules, one at a time and all together, not every combination.
- The 10 Hz engagement bar is declared, not derived from data.
- Part C cannot translate unit type, size rule or drive form between the models.
- Neural only. Motor coordinates are unchanged (20/42 admitted, +4 conditional).

## Build and run plan (on approval)

1. `docs/evidence/engine-fidelity-audit-v1/protocol.json`: checks, configs, seeds, criteria,
   source hashes and expectations.
2. `malecns_backend/embodiment/engine_fidelity_audit.py`. It reuses `MaleCNSBrain` options,
   `region_scales`, L1's harness, target resolution and R1's network builder.
3. Unit tests on toy data: the independent weight rule, sign consistency, swap construction (only
   the declared rule changes) and the labels.
4. A plumbing smoke: one S1 simulation on a non-protocol seed, discarded and disclosed; only its
   exit status and swap audit are read.
5. Commit and push the preregistration. Run once, evaluate once, then record the results,
   handoff and roadmap.
