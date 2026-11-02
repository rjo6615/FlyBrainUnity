# Right-front coxa drive asymmetry — design (V1)

Designed 2026-11-01, after the D3 result was merged (PR #309). This document is the
design only. No code has been written and nothing has run. The protocol JSON, the
module and the tests are written and hash-locked at build time, and are committed
before the single run.

## Why

In D3 (and earlier in Step C), the right-front (RF) hair plates fire at the encoder's
maximum (120 Hz). The RF coxa motor neurons (MNs) still barely respond: 0.55 Hz,
against 22.7 Hz in the left front (LF) and 32.3 Hz in the left hind (LH). That one
leg decided the D3 label. Step A already showed the RF pathway is the smallest
direct hair-plate → posterior-MN pathway: 5 SNpp45 neurons and 194 synapses, against
7 and 826 in LF. But LH works with only 317 synapses, so the total count alone does
not explain the failure.

**Question:** where along the pathway does RF lose its drive, compared with its
homolog LF and with LH (a working leg that has a modest synapse count)? Which of
those losses come from engine choices rather than from the connectome itself?

**This is data only.** It uses the connectome cache, the engine's own weight rules,
and the spikes already recorded in Step C arm A_ON. There is no new CNS or physics
run, and no parameter, mapping, weight or encoder is changed.

## Fixed inputs

| Input | Source | Lock |
|---|---|---|
| Sensory sets | Step A SNpp45 sets per leg (`hair_plate_identity.sensory_sets`, same rule, including the ProLN exclusion) | Step A protocol hash; direct counts must equal Step A `result.json` exactly |
| Target sets | Step A/C posterior coxa MNs per leg: Pleural remotor/abductor + Sternal posterior rotator (bodymap dense idx). The anterior set is reported alongside | Same declared mapping |
| Engine weight rule | `neural.MaleCNSBrain` construction, reproduced exactly: edge count ≥ `min_synapses` (6), × postsynaptic size scale (`region_scales`), × graded sign, × `inhibitory_gain` for inhibitory sources, × `psp_scale`; OA- sources sign 0 | Parameters read from `ModelConfig.calibrated()`; the effective weights must equal a `MaleCNSBrain` instance's `weights` on every audited edge |
| Measured spikes | Local raw Step C `A_ON.json.gz` (per-tick `fired` for all neurons, `hair_delivered`) | sha256 8c2d90e6…, as in the D3 protocol |

## Part S — structural (cache only)

For each of the six legs, and each posterior MN m:

- **S1 Sensory inventory.** Per SNpp45 neuron: its total output synapses to all
  targets (raw), its output to its own leg's posterior set (raw and ≥ 6 floored), and
  any completeness fields the annotation table has (reported as found, not
  interpreted). This checks whether RF hair plates look smaller overall, or only
  connect less to MNs.
- **S2 Effective direct weight.** W_m = Σ_s eff(s→m), using the engine rule above.
- **S3 Hair-plate-only mean-field drive.** Each hair plate is assumed at the encoder's
  120 Hz maximum, and its conductance at tau_syn. So
  g_m = Σ_s eff(s→m) · r · tau_syn. Its steady COBA potential is compared with the
  threshold, which gives g* (computed from the config, about 8.1 at the calibrated
  values). This is a modeled prediction, labelled as such: it ignores fluctuations
  and every other input.
- **S4 Factor decomposition (pool level).** Let G be a leg's total effective direct
  weight onto its posterior pool. The identity used is

  G = N_s · (R / N_s) · (F / R) · (G / F)

  - N_s = number of sensory neurons
  - R = raw synapses onto the pool
  - F = synapses on edges ≥ 6
  - G / F = mean size scale times sign, weighted by synapses

  The four log-ratios of RF against LF, and of RF against LH, sum exactly to
  log(G_RF / G_comparison). Each one is labelled:

  | Factor | Labels it as |
  |---|---|
  | SOURCE_COUNT | connectome |
  | SYNAPSES_PER_SOURCE | connectome |
  | FLOOR_LOSS | engine choice |
  | SIZE_SCALING | engine choice |

  A fifth, MN-level number, **CONCENTRATION** = max_m W_m / G, is reported beside the
  four factors. It is not part of the identity.

## Part M — measured (Step C A_ON replay)

- **M1.** Spike rate of every posterior and anterior coxa MN in all six legs, over the
  D3/Step C window 520–2000 ms.
- **M2 Exact input replay.** For each such MN, the excitatory and inhibitory
  conductance time courses are rebuilt from the recorded spikes. This uses the
  engine's effective weights, delivery delay (ring of round(1.8 / 0.5) ticks) and
  decay, with depression_u = 0, so delivery is deterministic. Each MN's input is
  split into three sources:
  - own-leg hair plates;
  - other excitatory sources;
  - all inhibitory sources.
- **M3 Replay verification.** Each MN is integrated as a single LIF from its replayed
  conductances, with the same update order, refractory period and float32 arithmetic.
  Its predicted spike ticks are compared with the recorded ones.
  - **REPLAY_EXACT:** every MN matches exactly.
  - **REPLAY_CLOSE:** at least 95 % of recorded spikes are matched within ±1 tick, in
    every MN with 5 or more spikes.
  - Otherwise **INCONCLUSIVE_REPLAY**. M-based labels are then withheld, and Part S
    is still reported.

## Labels (decided by these rules only)

**Integrity (all required):**

- the cache, protocol and raw hashes match;
- the Step A direct counts are reproduced exactly;
- the effective weights equal the engine's on every audited edge;
- the replay is REPLAY_EXACT or REPLAY_CLOSE.

Otherwise the result is `INCONCLUSIVE_INTEGRITY` and no Q labels are given.

**Q1: does RF hair-plate drive reach threshold?** This uses S3 for the best-driven
posterior MN of each leg.

| Label | Rule |
|---|---|
| `RF_DIRECT_SUBTHRESHOLD` | RF max g_m < g*, while LF or LH has g_m ≥ g* |
| `RF_DIRECT_SUFFICIENT` | RF max g_m ≥ g* |
| `ALL_SUBTHRESHOLD` | No leg reaches g*. The direct path alone does not explain any leg's activity |

**Q2: largest loss factor.** Among the four S4 factors for RF against LF, this names
the most negative log-ratio:

- `SOURCE_COUNT`
- `SYNAPSES_PER_SOURCE`
- `FLOOR_LOSS`
- `SIZE_SCALING`

`MIXED` is used if the top two factors are within 10 % of each other. The same rule
is applied to RF against LH, and that result is reported as Q2b.

**Q3: is competing inhibition an explanation?** This uses the measured (M2) window-mean
ratio of inhibitory to excitatory conductance on each leg's best-driven posterior MN,
compared between RF and LF.

| Label | Rule |
|---|---|
| `INHIBITION_CONTRIBUTES` | RF ratio ≥ 2× LF ratio |
| `INHIBITION_NOT_DECISIVE` | Otherwise |

**Engine-attributable share.** The sum of the FLOOR_LOSS and SIZE_SCALING log-ratios is
reported as a fraction of the total RF/LF log-ratio. It is a number, not a verdict.

## What this can and cannot decide

**It can say** which steps of the modeled pathway account for the RF deficit, and
how much of that comes from two specific engine choices: the 6-synapse floor and size
scaling.

**It cannot say** whether a connectome-side deficit (SOURCE_COUNT or
SYNAPSES_PER_SOURCE) is real anatomy or a reconstruction artifact. S1 and right-side
homolog symmetry are reported only as indicators:

- T2 and T3 on the right are not weak (1,056 and 213 synapses);
- per-source total output shows whether the RF SNpp45 neurons are generally small.

**Nothing here is a fix.** Changing the floor, size scaling, weights or encoder rate
to make RF fire is an engineering intervention. It would need its own versioned
protocol and a stated scientific question. Passive replay does not prove causal
effects.

## Predictions (expectations, not criteria)

- Q2 for RF against LF: SYNAPSES_PER_SOURCE is the largest factor (about 39 against 118
  raw synapses per source), with SOURCE_COUNT second (5/7). Floor and size effects
  are unknown in advance.
- Q2b for RF against LH: CONCENTRATION may matter more. LH's 317 synapses go almost
  entirely to one population, the sternal posterior rotator. RF's split between
  remotor/abductor (153) and posterior rotator (41).
- Q1: RF_DIRECT_SUBTHRESHOLD is plausible. Q3 is uncertain.

## Build and run plan (on approval)

1. Write `docs/evidence/coxa-drive-asymmetry-v1/protocol.json`, which turns the rules
   above into exact form.
2. Write `malecns_backend/embodiment/coxa_drive_asymmetry.py`. It reuses
   `hair_plate_identity` sets, `neural.MaleCNSBrain` / `region_scales` and the Step C
   raw format.
3. Write `tests/test_coxa_drive_asymmetry.py`, with synthetic tests covering:
   - the factor identity;
   - the floor and scale rules against a `MaleCNSBrain` built on a fixture;
   - replay matching a tiny simulated network exactly;
   - the label rules.
4. Commit and hash-lock everything, then run once (seconds to a few minutes) and
   commit `result.json` and the results write-up.

Outputs are small and committed. The Step C raw stays local.
