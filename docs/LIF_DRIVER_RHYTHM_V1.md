# LIF return, Step L1: do the rate model's rhythm drivers give a front-left rhythm in the live engine? (design)

Designed 2026-11-08. **Status: run 2026-11-08, NOT_REPRODUCED_IN_LIF** (DNg75_R and DNa02_L
NOT_RHYTHMIC, best 0.328 and 0.427 at ~2-3 Hz; DNp09_R NO_MN_OUTPUT); X1-X3 held (protocol
47278c7c, result 4d00b72f). See `LIF_DRIVER_RHYTHM_RESULTS.md`. Neural-only
simulation in the live, calibrated whole-CNS LIF engine (`MaleCNSBrain`), untuned. No body,
physics, mapping, sign, gain or admission change.

## Why this step

The rate-model steps R1–R9 ran on R1's isolated 2,111-neuron front-left network. They found
the following.
- **DNg100 never gives a rhythm** in the rate model. It engages the core only through an
  all-or-none network ignition, after which the core is tonic (R2, R3, R7–R9).
- **Three other cholinergic DNs do,** with R1's sizes: DNg75_R, DNa02_L and DNp09_R (R3, R4,
  R5).
  - Their front-left MN rhythm is strong and specific: DNg75_R scores 0.983, DNa02_L 0.926,
    DNp09_R 0.509, all at about 13 Hz.
  - It needs E1 and E2 but not I1 (R5), and it lives in a window of inhibition (R7).
- **With cord-only sizes,** the more faithful size definition (R1b), none of the three reached
  0.5 (R5).

The live LIF engine is what drives the body. Stage 1 (V1, 2026-11-01) found it carries a
specific DNg100 → front-left MN pathway, but the output is **tonic**. **No DN other than
DNg100 has been tested for a rhythm in the live engine.** V1's 20 random control DNs did not
include these three.

L1 asks:

> **In the live whole-CNS LIF engine, untuned, does stimulating DNg75_R or DNa02_L (and, as a
> secondary, DNp09_R) give rhythmic front-left MN activity at 5–20 Hz, and if so, does it need
> E1 and E2?**

This is the first step back to the live engine. It asks whether the rate model's one positive
finding transfers, without changing anything in the engine.

**Already known (disclosed).** Before writing this design I checked the following, with no
stimulation run.
- **Identities, from the cache:**

  | Cell | Dense | Body | Synapses onto the 68 front-left MNs |
  |---|---|---|---|
  | DNg75(hb1874217622)_R | 129181 | 520300 | 167 |
  | DNa02_L | 130496 | 523769 | 217 |
  | DNp09_R | 1087 | 11177 | 0 |
  | E1, IN17A001_L | 142920 | 800173 | — |
  | E2, INXXX466_L | 143429 | 800863 | — |

  All three DNs are cholinergic descending neurons.
- **Engine unchanged:** `neural.py` and `brain_params.json` still hash to V1's registered
  values.
- **V1's 20 control DNs** do not include any of the three targets. Those controls' best scores
  were 0.211 and 0.217 (only 2 of 20 reached any front-left MN), giving a control p80 of 0.216.

## Conditions (declared)

- **Engine:** `MaleCNSBrain(data)` with the calibrated config, the whole CNS as loaded, untuned.
- **Stimulus:** V1's method (`set_external_drive` Poisson forced spikes) on one target, 3 s per
  simulation.
- **Readout:** V1's (68 front-left MNs, window 250–3,000 ms, the preprint rhythmicity score,
  the best-rate rule).
- **Harness:** V1's `simulate`, `score_simulation` and `best`, reused unchanged.

| Condition | Targets | Rates (Hz) | Seeds (`brain.reset`) | Simulations |
|---|---|---|---|---|
| STIM | DNg75_R, DNa02_L (primary); DNp09_R (secondary) | 25, 50, 100, 200 | 1–16 | 3 × 4 × 16 = 192 |
| SIL_E1, SIL_E2, SIL_SHAM | each target, at its best rate | that rate | 1–16 | 3 × 3 × 16 = 144 |
| I2 reproduction | DNg100_L (V1) | 100 | 1–4 | 4 |

- **Silencing:** V1's method (`transmission_withheld_indices`).
- **SIL_SHAM** withholds one cell per seed by R5's sham rule (`default_rng(seed + 7,000,000)`
  over R5's eligible set in R1's network, mapped to dense indices).
- **No feasible rate:** if a target has no feasible rate (no active front-left MN at any rate),
  its silencing conditions are skipped. That is declared now, not chosen later.
- **Totals:** 340 simulations, about 36 minutes at V1's measured cost.
- **Also watched:** E1, E2 and I1 (dense 144200) spike trains are recorded alongside, for
  reporting only. Watching changes no dynamics, and these cells never enter the MN score.

## Criteria (per target)

The **best rate** is the rate with the highest condition score (V1's rule).

| Class | Rule (first matching row) |
|---|---|
| `NO_MN_OUTPUT` | no feasible rate |
| `NOT_RHYTHMIC` | best score < 0.5, or ≤ V1's control p80 (0.216) |
| `LIF_RHYTHM_CORE` | rhythmic, frequency at best rate in 5–20 Hz, SIL_E1 and SIL_E2 both < 0.5, and SIL_SHAM ≥ 0.5 |
| `LIF_RHYTHM_OTHER` | rhythmic, but any of the frequency, core or sham conditions fails (which ones are reported) |

**Step verdict (primaries)**

| Verdict | Rule |
|---|---|
| `REPRODUCED_IN_LIF` | both primaries are `LIF_RHYTHM_CORE` |
| `PARTIAL` | at least one primary is `LIF_RHYTHM_CORE` or `LIF_RHYTHM_OTHER` |
| `NOT_REPRODUCED_IN_LIF` | neither primary is rhythmic |

DNp09_R's class is reported alongside.

**Reported, not gated:**
- per rate: score, frequency, feasible seeds, active MNs and their per-MN rates;
- E1, E2 and I1 spike rates and trace rhythmicity;
- which MNs are recruited, compared with DNg100's 12 in V1.

## Integrity (declared now)

- **I1 sources:**
  - hashes of `neural.py` and `brain_params.json` equal V1's protocol;
  - hashes of V1's module and `result.json`, and of the R5 module;
  - the three targets resolved from **body IDs** (520300, 523769, 11177) to the dense indices
    above, with their instance names checked;
  - E1 and E2 equal V1's core copies; 68 front-left MNs.
- **I2 (reproduction, hard gate):** DNg100_L at 100 Hz, seeds 1–4, must equal V1's stored runs
  exactly (score and per-MN spike counts). If not, the step is `INCONCLUSIVE` and nothing else
  runs.
- **I3 tests:** class order and verdict on toy summaries; the watch split (core cells never
  enter the MN score); the sham mapping.
- **I4 completeness:** 340 simulations, fewer by exactly 48 for each target with no feasible
  rate.

## Expectations (recorded now)

- **X1:** DNg75_R is not rhythmic (`NOT_RHYTHMIC` or `NO_MN_OUTPUT`).
- **X2:** DNa02_L is not rhythmic.
- **X3:** the step verdict is `NOT_REPRODUCED_IN_LIF`.

My reasons:
- V1 found the LIF engine tonic for DNg100.
- The rate-model rhythm held only with R1's sizes, not with cord-only sizes.
- It needed a narrow window of inhibition (R7).

Wrong expectations are recorded as wrong.

## What each outcome means (declared now)

- **REPRODUCED_IN_LIF / PARTIAL:** the live engine, untuned, carries a front-left rhythm from
  at least one DN that the connectome-based rate model also picked out. That would be the first
  neurally emergent leg rhythm in the live engine. The next step would be a separately designed
  embodied test through the existing mapping, with its own baselines. It would not show walking
  by itself, and it adopts no stimulus into any behaviour.
- **NOT_REPRODUCED_IN_LIF:** the rate model's rhythm does not transfer to the live engine for
  these DNs either. Any reason (spiking versus rate dynamics, whole-CNS context, calibrated
  parameters, the drive form) would be a separate question. The engine must not be tuned until
  it oscillates.
- **In no case** does L1 show walking, assign biological roles, or change the live engine,
  weights, mappings or motor admission.

## Limits

- **Three DNs,** chosen by the rate model, which is my reconstruction. Other DNs are untested.
- **Forced-spike Poisson drive** at four rates. The rate model used a constant input, so the
  drive forms differ.
- **16 seeds per condition.** The specificity reference is V1's stored control distribution
  (20 DNs, of which only 2 were feasible). No new controls are run.
- **Rhythm is read from the front-left MNs only;** other legs are not read.
- **Neural only:** no body or physics. Motor coordinates are unchanged (20/42 admitted, +4
  conditional).

## Build and run plan (on approval)

1. `docs/evidence/lif-driver-rhythm-v1/protocol.json`: targets by body ID, rates, seeds,
   criteria, hashes, expectations.
2. `malecns_backend/embodiment/lif_driver_rhythm.py`. It reuses:
   - `dng100_rhythm`: `simulate`, `score_simulation`, `best`, `front_left_mns`, `rhythmicity`,
     `rates`, V1's protocol readout;
   - `dng100_control_rhythm`: the sham rule;
   - `dng100_engaged_rhythm.setup`: R1's network, for the sham's eligible set.
3. Unit tests (I3). Then one timing simulation (DNg100_L, 100 Hz, seed 0, not a protocol seed),
   discarded and disclosed.
4. Commit and push the preregistration. Run once in the background, evaluate in the same
   process, and record the results, handoff and roadmap.

## Build-time notes (before any protocol simulation)

- No amendments to the design's targets, rates, seeds, criteria or expectations. The protocol is
  `protocol.json` (sha 47278c7c…).
- **Aggregation.** V1's `condition` scores every watched cell, so the module reproduces its
  aggregation as `aggregate` and watches E1, E2 and I1 separately (`split`). I2 checks this
  against V1's stored runs exactly.
- **Sham.** R5's eligible set for each target in R1's network has 1,022–1,028 cells; the drawn
  local index is mapped to its dense index through R1's network.
- **Plumbing.**
  - One DNg100_L simulation at 100 Hz, seed 0 (not a protocol seed), was timed at 6.62 s. Its
    spikes were not inspected.
  - The I1 identity path (targets, core, MN list, sham sets and two sham draws) was exercised
    with no simulation.
