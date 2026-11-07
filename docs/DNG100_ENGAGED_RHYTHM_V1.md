# Rhythm, Step R3: does the engaged network produce the DNg100 rhythm? (design)

Designed 2026-11-06. **Status: run 2026-11-06, RATE_RHYTHM_NOT_REPRODUCED in both arms** (protocol
51bec0c2, result 099e42a7; DNG100 score 0.055 VNCSIZE / 0.023 R1SIZE; X1-X3 held; unplanned: three
control DNs drove a core oscillation in R1SIZE). See `DNG100_ENGAGED_RHYTHM_RESULTS.md`.
Neural-only rate-model simulation of R1's isolated network.

## Why this step

- **R1** (`DNG100_RATE_MODEL_RESULTS.md`) ran the preprint's DNg100 rate model on our
  front-left network. Its drive rule stopped while E1, E2 and I1 were still silent, so its
  NOT_REPRODUCED verdict did not test the core.
- **R1b** (`DNG100_SIZE_AUDIT_RESULTS.md`) found that R1 over-scaled the network's descending
  neurons (median ρ 2.36). The cord-only definition is the one closer to the preprint's.
- **R2** (`DNG100_RECRUITMENT_MAP_RESULTS.md`) mapped a fixed drive ladder. The core is
  reachable, but it switches on only with an all-or-none jump to about 600 active neurons:
  - at 2,000 with cord-only sizes (VNCSIZE);
  - at 16,000 with R1's sizes (R1SIZE).

  That jump is outside the preprint's 5–500 recruitment band.

R3 is the test R2's declared outcome called for:

> **With the core engaged, does DNg100_L stimulation produce a front-left motor rhythm that is
> specific to DNg100 (versus control DNs) and needs E1, E2 and I1?**

**Already known (disclosed).** R2 reported, as an untested observation, MN rhythm scores of
0.01–0.03 in every engaged condition. So R3's DNG100 outcome is partly anticipated. R3 still
adds the parts R2 lacked:
- the controls and silencing arms;
- 64 fresh seeds;
- the preregistered criteria;
- a direct look at whether the core cells themselves oscillate.

A null result here would close the rate-model question on our wiring, under declared
conditions, rather than leaving it to an aside.

## Conditions (declared; no drive adjustment)

**Drive rule.** Each arm uses the lowest ladder drive at which R2 recorded all three core cells
engaged in ≥ 8 of 16 seeds:
- **VNCSIZE: 2,000.**
- **R1SIZE: 16,000.**

The drive is chosen from R2's engagement data, not from any rhythm score. It is applied to
every stimulated neuron in that arm.

| Arm | Sizes | Drive |
|---|---|---|
| **VNCSIZE (primary)** | R1b cord-only: s = size·f / m_VNC; f measured for DNs and ANs, 1 otherwise | 2,000 |
| R1SIZE (secondary) | R1's: s = size / 542,747,200 | 16,000 |

**VNCSIZE is primary** because R1b showed R1's whole-CNS sizes are a fidelity defect for
descending neurons. Its size vector is computed exactly as in R2.

**Conditions within each arm**

| Condition | Stimulated | Silenced | Seeds |
|---|---|---|---|
| DNG100 | DNg100_L | none | 1001–1064 |
| SIL_E1, SIL_E2, SIL_I1 | DNg100_L | one core cell (its activation held at 0, as R1) | 1001–1064 each |
| CONTROL × 20 | each of R1's 20 control DNs (the same dense indices, ACh DNs, drawn with rng 20261107) | none | 1001–1016 each |

- Totals: 576 simulations per arm, 1,152 in all.
- The seeds are fresh. R1 and R2 used 1–64.
- Note: control 129181 is also one of E1's two-hop intermediates. This is reported, not
  changed.

**Model.** Everything else is R1's model unchanged:
- the same network and signs, b = 0.03, the same draws and solver;
- 1 s, onset 20 ms, window 250–999 ms.

## Readout and criteria (R1's, unchanged)

**Readout**
- **Replicate score:** the V1 `rhythmicity` score of each active front-left MN (max > 0.01 Hz),
  averaged over the active MNs. NaN if no MN is active.
- **Frequency:** the median of 1000/period over the active MNs with score > 0.
- **Condition score:** the mean over replicates with a score. Condition frequency is the median.

**Criteria**

| Criterion | Rule |
|---|---|
| C1 rhythm | DNG100 score ≥ 0.5 and > the 80th percentile of the 20 control scores |
| C2 frequency | DNG100 frequency in 5–20 Hz |
| C3 necessity | SIL_E1, SIL_E2 and SIL_I1 each score < 0.5 |

**Verdict per arm**

| Verdict | Rule |
|---|---|
| `RATE_RHYTHM_REPRODUCED` | C1, C2 and C3 |
| `RATE_RHYTHM_PARTIAL` | C1, but not C2 or not C3 |
| `RATE_RHYTHM_NOT_REPRODUCED` | not C1 |
| `INCONCLUSIVE` | an integrity failure, or no DNG100 replicate with a score |

The **primary verdict** is VNCSIZE's. R1SIZE is reported alongside.

**Engagement qualifier.** Each condition reports the fraction of replicates in which all three
core cells were active (R2's definition). If fewer than half of the DNG100 replicates are
engaged, the verdict carries the qualifier `CORE_NOT_RELIABLY_ENGAGED`, because the test would
not then be about the engaged core.

**Reported, not gated**
- **Core oscillation:** the `rhythmicity` score of the E1, E2 and I1 rate traces themselves
  (window 250–999 ms). This shows whether the core oscillates even if the MNs do not.
- The Ti flexor/extensor cross-correlation lag (R1's `tibia_phase`).
- Recruited counts, DNg100_L's rate, and per-MN scores with muscle names.

## Integrity (declared now)

- **I1 sources:**
  - file hashes;
  - R1's network body-ID hash;
  - R1's control list;
  - R1b's z* = 462 and m_VNC reproduced.
- **I2 (R2 reproduction, hard gate):** before the protocol conditions, re-run R2 seeds 1–4 at
  each arm's drive. Their recruited count, core activity and MN score must equal R2's
  `result.json` exactly.
- **I3 tests:**
  - the verdict, qualifier and core-oscillation code;
  - the condition builder (drives, seeds, silencing).
- **I4 completeness:** 1,152 simulations, plus the 8 reproduction simulations.

## Expectations (recorded now; informed by R2's reported scores, disclosed above)

- **X1:** VNCSIZE is `RATE_RHYTHM_NOT_REPRODUCED`, with DNG100 score < 0.1.
- **X2:** R1SIZE is `RATE_RHYTHM_NOT_REPRODUCED`.
- **X3:** E1's own trace has a median rhythmicity below 0.5 in VNCSIZE DNG100. The core
  settles rather than oscillates.

Wrong expectations are recorded as wrong.

## What each outcome means (declared now)

- **NOT_REPRODUCED in the primary arm:**
  - With the core engaged, this reconstruction of the preprint's model on our maleCNS
    front-left wiring does not produce a DNg100-specific MN rhythm.
  - Together with V1 (LIF, tonic), both engines give tonic output on our wiring.
  - The remaining candidate explanations are differences in wiring and MN set between our
    connectome and MANC, and model details we could not reconstruct. R3 cannot separate them.
  - Any further step should be a structural comparison, not tuning.
- **REPRODUCED or PARTIAL:**
  - The rhythm exists in our wiring, but only in a regime the preprint's drive rule would
    reject.
  - The next question is whether the live LIF engine can be placed in a comparable regime.
    That would be a separate, versioned design.
- **In no case** does R3 show walking, validate the preprint's biology, or change the live
  engine or motor admission.

## Limits

- **Isolated network:** R1's 2,111 neurons; no other brain or cord input.
- **Drive outside the preprint's rule:** the drives are chosen by a declared engagement rule,
  not the preprint's 5–500 recruitment rule. The engaged state has about 600+ active neurons.
- **Model, not biology:** a reconstructed rate model (b from ratenet.js); 64 replicates rather
  than the preprint's 1,024; 68 bodymap MNs rather than MANC's 144.
- **The V1 score is our measure.** It is not the preprint's analysis.
- **Neural only:** no body or physics. Motor coordinates are unchanged (20/42 admitted, +4
  conditional).

## Build and run plan (on approval)

1. `docs/evidence/dng100-engaged-rhythm-v1/protocol.json`: arms, drives, seeds, controls,
   criteria, hashes, expectations.
2. `malecns_backend/embodiment/dng100_engaged_rhythm.py`. It reuses:
   - `dng100_rate_model`: Model, draw, scale, simulate, score_rates, tibia_phase, summarize,
     verdict;
   - `dng100_recruitment_map`: cord_only_sizes and context;
   - `dng100_rhythm.rhythmicity`.
3. Unit tests (I3). Then one timing simulation at seed 0 (not a protocol seed), discarded and
   disclosed.
4. Commit and push the preregistration. Run once in the background (about 15–20 min), evaluate
   in the same process, and record the results, handoff and roadmap.

## Build-time notes (before any protocol simulation)

- No amendments to the design's conditions, criteria or expectations.
- **Plumbing.** One VNCSIZE DNG100 simulation at seed 0 (not a protocol seed) was timed
  (0.74 s). It also printed z* = 462 and m_VNC = 507,457,760; its score and rates were not
  printed.
