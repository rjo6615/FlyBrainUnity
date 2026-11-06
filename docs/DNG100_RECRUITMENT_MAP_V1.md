# Rhythm, Step R2: where does DNg100's signal stop? A recruitment map (design)

Designed 2026-11-06. Design only: no protocol, code or run yet. Neural-only rate-model
simulation of R1's isolated network; descriptive, no rhythm verdict.

## Why this step

- **R1** (`DNG100_RATE_MODEL_RESULTS.md`) ran the preprint's rate model on our front-left
  network. The preprint's drive rule stopped as soon as 5 neurons were recruited, at I_stim
  1,000–2,000. At those drives E1, E2 and I1 were never active, so R1 never tested the core.
- **R1b** (`DNG100_SIZE_AUDIT_RESULTS.md`) found that R1 over-scaled the network's other
  descending neurons (median ρ 2.36) but barely over-scaled DNg100 itself (ρ 1.35). So the size
  definition does not explain DNg100's non-engagement.

R2 asks:

> **In R1's rate model, at a fixed ladder of DNg100_L drives, which neurons become active, along
> which routes does the signal reach (or fail to reach) E1, E2, I1 and the front-left MNs, and
> where does it stop?**

R2 is descriptive. It does not test for a rhythm, change R1's verdict or tune anything. Drive
values are a declared ladder, not chosen to make anything fire.

## Evidence gathered for this design (structure only, no simulation)

From R1's network (2,111 neurons; edges ≥ 5 synapses; W signed by transmitter):

- **Hop distance from DNg100_L** (any sign): 70 neurons at 1 hop, 970 at 2, 847 at 3, 121 at 4,
  23 further, 79 unreachable. Front-left MNs: 48 at 2 hops, 19 at 3, 1 unreachable.
- **No direct DNg100_L → core synapses.** E1, E2 and I1 are all 2 hops away.
- **The two-hop routes** (synapse counts; s = R1 size ratio; θ ≈ 7.5·s):

  | Core cell (θ) | Intermediate | DNg100_L → mid | mid → core | mid s (θ) |
  |---|---|---|---|---|
  | E1 (≈ 66) | DNg100_R | 119 | 155 | 30.5 (≈ 229) |
  | | IN01A018_R | 29 | 113 | 4.75 (≈ 36) |
  | | DNge050_R | 5 | 106 | 22.0 (≈ 165) |
  | | IN01A002_R | 94 | 24 | 9.6 (≈ 72) |
  | | AN19B009_R | 8 | 24 | 7.5 (≈ 56) |
  | | 6 more, each ≤ 13 synapses onto E1 | | | |
  | E2 (≈ 38) | AN19B009_R (only route) | 8 | 139 | 7.5 (≈ 56) |
  | I1 (≈ 19) | AN08B031_L (only route) | 5 | 6 | 2.3 (≈ 17) |

- **The core's own wiring is present:** E1 → E2 465, E2 → I1 38, I1 → E1 −526, I1 → E2 −121.
- **A structural ceiling.** In this model DNg100_L's rate cannot exceed rmax (≈ 200 Hz), so its
  direct input to any target is at most b·W·rmax. At that ceiling, 46 of its 70 direct targets
  would cross threshold. AN19B009_R would not (0.03·8·200 = 48 < ≈ 56), so E2's only two-hop route
  depends on other input to AN19B009_R.

**Rough expectation from these numbers** (ignores inhibition, recurrence and sampled
parameters). At R1's drives DNg100_L fires about 25–55 Hz. That is too little to bring DNg100_R
over its threshold. At about 4,000 or more, DNg100_R and IN01A018_R should start to fire and
push E1 toward threshold. If E1 fires, E1 → E2 (465) should recruit E2.

## Method

**Model.** R1's model, unchanged: `dng100_rate_model.Model`, `draw`, `scale` and `simulate`.
The same network, signs, b = 0.03, solver, 1 s, onset 20 ms and window 250–999 ms. The only
difference is that drive is not adjusted: each simulation uses one fixed I_stim on DNg100_L.

**Conditions**

| Arm | Sizes | Drives (I_stim) | Seeds |
|---|---|---|---|
| R1SIZE (primary) | R1's: s = size / 542,747,200 | 250·2^k, k = 0…8 (250 to 64,000) | 1–16 |
| VNCSIZE (secondary) | R1b cord-only: s = size·f / m_VNC; f from R1b's locked plane (z* = 462 µm), f = 1 for cord-intrinsic neurons | same | 1–16 |

- That is 2 × 9 × 16 = 288 simulations.
- The ladder contains R1's visited drives (250–2,000). It extends to where DNg100_L should be
  saturated: at 64,000 the term inside its tanh is about 10, so it fires at about rmax.
- VNCSIZE is descriptive. It shows whether R1b's mismatch changes the map. It is not R1 v2 and
  gives no rhythm verdict.

**Readouts per simulation** (all in the 250–999 ms window)
- DNg100_L mean rate, and that rate as a fraction of its rmax.
- Recruited neurons (R1's definition: max rate > 0.01 Hz), by hop layer and by class (DN, AN,
  cord-intrinsic, MN). Also active front-left MNs.
- **E1, E2, I1:** max and mean rate. At t = 999 ms, the input decomposition: excitatory
  b·ΣW⁺r, inhibitory b·ΣW⁻r, threshold θ_i, and margin = (input − θ_i).
- **Rates of the named route intermediates:** the 11 E1 intermediates, AN19B009_R and
  AN08B031_L.
- **For a core cell that is not active:** its active presynaptic partners and their summed
  contribution.
- **The V1 rhythmicity score of the active MNs** (`score_rates`), reported only. R2 has no
  controls and drives outside the preprint's rule, so it cannot give a rhythm verdict.

## Descriptive labels (declared now)

**Per core cell and arm**

| Label | Rule |
|---|---|
| `ENGAGED_AT_<I>` | the lowest ladder drive at which the cell is active in ≥ 8 of 16 seeds |
| `NOT_ENGAGED_DNG100_SATURATED` | never engaged, and at 64,000 DNg100_L's mean rate is ≥ 0.9·rmax in ≥ 8 seeds. More drive cannot help; the stop is in the network. |
| `NOT_ENGAGED_UNSATURATED` | never engaged, and DNg100_L is not saturated at 64,000 |

**Per arm (map)**

| Label | Rule |
|---|---|
| `CORE_REACHED_IN_PREPRINT_RANGE` | E1, E2 and I1 are all engaged, and at the highest of their three engaging drives the median recruited count is ≤ 500 |
| `CORE_REACHED_BEYOND_RANGE` | all three are engaged, but that median recruited count is > 500 |
| `CORE_PARTIAL` | one or two are engaged |
| `CORE_NOT_REACHED` | none is engaged |

**Stopping point.** For each core cell that is not engaged, the result reports the following
at the top drive: its median margin, its active versus silent intermediates, and the farthest
hop layer with any active neuron.

## Integrity (declared now)

- **I1:** source hashes; R1's network body-ID hash (cdcfcd23…); R1b's plane and m_VNC
  reproduced (z* = 462, m_VNC = 507,457,760).
- **I2 (R1 reproduction):** for seeds 1–16, R1SIZE's recruited counts at 250, 500, 1,000 and
  2,000 equal every entry in R1's recorded drive history at those drives (from R1's
  `result.json`). This is a hard gate: a mismatch makes the run INCONCLUSIVE.
- **I3:** unit tests for the input decomposition (it must equal the model's RHS input), the
  label rules and the VNCSIZE size vector.
- **I4:** completeness (288 simulations, each with arm, drive and seed).

## Expectations (recorded before any R2 simulation; based only on the structure above)

- **X1:** in R1SIZE, E1 is engaged at a drive ≥ 4,000.
- **X2:** in R1SIZE, all three core cells are engaged, but beyond the preprint's range
  (`CORE_REACHED_BEYOND_RANGE`).
- **X3:** VNCSIZE engages each core cell at the same or a lower drive than R1SIZE.

Wrong expectations are recorded as wrong.

## What each outcome means (declared now)

- **Core reached only beyond the preprint's range:** our wiring can carry DNg100's signal to the
  core, but only at drives that recruit more than the preprint's rule allows. The next question is
  whether the engaged core oscillates. That needs a separately preregistered rhythm test at a
  declared drive, with controls.
- **Core reached within range:** R1's drive rule stopped too early on our network, because its
  recruitment band was met by off-route neurons. Same next question.
- **Partial, or not reached with DNg100 saturated:** the stop is in our wiring or this model's
  thresholds. The map names the missing link, for example AN19B009_R → E2. That leads to a
  structural comparison, not a tuning step.
- **In no case** does R2 show a rhythm, validate the preprint, or say anything about the LIF
  engine.

## Limits

- **Isolated network:** R1's 2,111-neuron network only, with no other brain or cord input.
- **Model, not biology:** rates and thresholds follow a reconstructed rate model (b from
  ratenet.js). "Active" means > 0.01 Hz, which is permissive.
- **Drives above 2,000 are outside anything the preprint's rule would select.** They are probes
  of reachability, not physiological claims.
- **VNCSIZE uses R1b's cable-length proxy for volume**, with R1b's limits.
- **Neural only:** no body, physics or engine change. Motor coordinates are unchanged (20/42
  admitted, +4 conditional).

## Build and run plan (on approval)

1. `docs/evidence/dng100-recruitment-map-v1/protocol.json`: ladder, seeds, labels, source hashes
   and R1's recorded histories for I2.
2. `malecns_backend/embodiment/dng100_recruitment_map.py`. It reuses `dng100_rate_model` (model
   and simulation) and `dng100_size_audit` (decode, cable_split, scaling).
3. Unit tests (I3). Then a plumbing/timing smoke (one simulation at seed 0, not a protocol
   seed), discarded and disclosed.
4. Commit and push the preregistration. Run once, evaluate in the same process, and record the
   results, handoff and roadmap.
