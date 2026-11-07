# Rhythm, Step R5: is the control-DN core oscillation real, and does it need E1, E2 and I1? (design)

Designed 2026-11-06. **Status: run 2026-11-06, OBSERVATION_NOT_CONFIRMED by the declared rule**
(protocol 0fabdb48, result c4318d93): in R1SIZE all three targets are RHYTHM_CORE_INDEPENDENT
(rhythm reproduced and specific; E1 and E2 needed, I1 not); VNCSIZE NOT_CONFIRMED; X1 wrong,
X2-X3 held. See `DNG100_CONTROL_RHYTHM_RESULTS.md`. Neural-only rate-model simulation of R1's
isolated network.

## Why this step

- **R3** (`DNG100_ENGAGED_RHYTHM_RESULTS.md`) found no DNg100 rhythm with the core engaged. As
  an **unplanned observation** (R1SIZE, drive 16,000, no silencing), two of R1's control DNs
  drove a front-left MN rhythm with the E1, E2 and I1 traces oscillating at a 74 ms period:
  - DNg75_R (dense 129181): score 0.97, 13.6 Hz, 16/16 seeds;
  - DNa02_L (130496): 0.95, 14.1 Hz, 16/16 seeds;
  - DNp09_R (1087) was weaker: 0.52, 10/16 seeds ≥ 0.5.

  With cord-only sizes (VNCSIZE, drive 2,000) all three scored 0.05–0.12.
- **R4** (`DNG100_ROUTE_COMPARISON_RESULTS.md`) found that these three share strong two-hop
  drive into E1, and that DNg100_L has more of it. Route features did not explain the difference.

R5 turns the observation into a test:

> **In R1's rate model on our wiring, do DNg75_R, DNa02_L and DNp09_R each drive a front-left
> MN rhythm that is reproducible on fresh seeds, specific against an independent set of DNs,
> and abolished by silencing E1, E2 or I1 (but not by silencing an unrelated cell)? Does it
> hold with cord-only sizes?**

**Selection (disclosed).** These DNs were chosen *because* they scored high in R3. Fresh seeds
address seed-level luck, and a newly drawn control set gives a reference that played no part
in choosing them. Neither removes the choice of DNs itself.

## Conditions (declared; no drive adjustment)

**Drives** are R3's, unchanged: the drive at which the observation was made.

| Arm | Sizes | Drive | Role |
|---|---|---|---|
| R1SIZE | R1's (size / 542,747,200) | 16,000 | **primary for this question** (where the observation was made) |
| VNCSIZE | R1b cord-only, as R2 and R3 | 2,000 | secondary (the more faithful size definition) |

The VNCSIZE arm asks only whether the observation holds at R3's VNCSIZE drive. It does not
search other drives; that would be a separate, versioned question.

**Targets:** DNg75_R (129181) and DNa02_L (130496), the primary targets, and DNp09_R (1087),
secondary.

**Conditions per target, per arm**

| Condition | Stimulated | Silenced | Seeds |
|---|---|---|---|
| STIM | the target | none | 2001–2064 |
| SIL_E1, SIL_E2, SIL_I1 | the target | one core cell (activation held at 0, as R1) | 2001–2064 each |
| SIL_SHAM | the target | one network cell drawn per replicate (below) | 2001–2064 |

**Sham cell.** For each replicate, the sham cell is drawn uniformly with
`numpy.random.default_rng(seed + 7_000_000)` from the network's cells that are not DNs, ANs,
front-left MNs, E1, E2, I1 or one of the target's own two-hop intermediates to the core. This
checks that removing an arbitrary single cell does not by itself abolish the rhythm.

**New control set (specificity reference).** 20 DNs drawn with `default_rng(20261108)` from
R1's control pool (network acetylcholine DNs, excluding DNg100_L and DNg100_R), with R1's 20
controls removed. If fewer than 20 remain, all are used. Each is stimulated at the arm's drive
with seeds 2001–2016, without silencing. The draw happens at run time and does not depend on any
simulation.

**Totals:** 2 arms × 3 targets × 5 conditions × 64 = 1,920 simulations, plus 2 × 20 × 16 = 640
control simulations, so 2,560 in all (about 35 minutes at R3's 0.77 s each).

**Model.** Everything else is R1's model and R3's replicate function, unchanged:
- the same network and signs, b = 0.03, the same draws and solver;
- 1 s, onset 20 ms, window 250–999 ms.

## Readout (R3's, unchanged)

- **Replicate score:** the V1 `rhythmicity` of each active front-left MN, averaged over the
  active MNs. NaN if no MN is active.
- **Frequency:** the median of 1000/period over the active MNs with score > 0.
- **Condition score:** the mean over replicates with a score.
- **Core trace rhythmicity** of E1, E2 and I1 (median over replicates where the cell is
  active), engagement, and recruited counts, as in R3.

## Criteria (per target, per arm)

| Criterion | Rule |
|---|---|
| C1 rhythm | STIM score ≥ 0.5 and > the 80th percentile of the new controls' scores in that arm |
| C2 frequency | STIM frequency in 5–20 Hz |
| C3 core necessity | SIL_E1, SIL_E2 and SIL_I1 each score < 0.5 |
| C4 sham | SIL_SHAM score ≥ 0.5 |

**Verdict per target, per arm** (first matching row)

| Verdict | Rule |
|---|---|
| `RHYTHM_NOT_CONFIRMED` | not C1 |
| `RHYTHM_OUT_OF_BAND` | C1, not C2 |
| `SILENCING_NONSPECIFIC` | C1, C2, and not C4 |
| `RHYTHM_CORE_INDEPENDENT` | C1, C2, C4, and not C3 (at least one core cell is not needed) |
| `CORE_RHYTHM_CONFIRMED` | C1, C2, C3 and C4 |
| `INCONCLUSIVE` | an integrity failure, or no STIM replicate with a score |

For `RHYTHM_CORE_INDEPENDENT`, the cells whose silencing left a score ≥ 0.5 are listed.

**Headline.** The observation is **confirmed** if DNg75_R and DNa02_L are both
`CORE_RHYTHM_CONFIRMED` in R1SIZE. DNp09_R and the VNCSIZE arm are reported alongside.

**Reported, not gated**
- The E1, E2 and I1 trace rhythmicity and period in STIM, compared with the MN period.
- Engagement fraction, recruited counts, the target's own rate, and per-MN scores with muscle
  names.
- The Ti flexor/extensor cross-correlation lag (R1's `tibia_phase`).
- The new control set's scores, names and body IDs.

## Integrity (declared now)

- **I1 sources:**
  - file hashes (R1, R2 and R3 modules; R3 and R4 `result.json`);
  - R1's network body-ID hash;
  - R1's control list;
  - R1b's z* = 462 and m_VNC reproduced;
  - the targets equal R4's RHYTHMIC group.
- **I2 (R3 reproduction, hard gate):** before any protocol condition, re-run R3's
  CONTROL_129181 and CONTROL_130496 in both arms at seeds 1001–1004 (16 simulations). Score,
  recruited count and core activity must equal R3's stored runs exactly.
- **I3 tests:**
  - the condition builder;
  - the sham draw (excluded classes, determinism);
  - the new control draw;
  - the verdict order and headline.
- **I4 completeness:** 2,560 simulations, plus the 16 reproduction simulations.

## Expectations (recorded now)

- **X1:** DNg75_R and DNa02_L are `CORE_RHYTHM_CONFIRMED` in R1SIZE (headline confirmed).
- **X2:** all three targets are `RHYTHM_NOT_CONFIRMED` in VNCSIZE.
- **X3:** the new controls' p80 in R1SIZE is below 0.5. I expect rhythm-driving DNs to be
  uncommon.

These are informed by R3's observation (16/16 seeds for the two primary targets; 0.05–0.12 in
VNCSIZE). Wrong expectations are recorded as wrong.

## What each outcome means (declared now)

- **Headline confirmed:** in this reconstruction of the preprint's model on our wiring, the
  E1–E2–I1 core can generate a front-left MN rhythm when driven by DNg75_R or DNa02_L, but
  not by DNg100, in R1's sizes. That makes the DNg100 difference a question about how drive
  enters the network, which a later step could study as dynamics (no tuning). It is a model
  result, not a biological claim about these DNs.
- **Holds in VNCSIZE too:** the core rhythm does not depend on the size definition R1b found
  less faithful. **Does not hold in VNCSIZE:** it depends on R1's sizes at R3's drive. R5 does
  not test other VNCSIZE drives.
- **RHYTHM_CORE_INDEPENDENT:** the rhythm does not need every core cell; the cells it does need
  are the next structural lead.
- **SILENCING_NONSPECIFIC:** single-cell silencing is too disruptive to test necessity this way.
- **RHYTHM_NOT_CONFIRMED:** R3's observation did not reproduce on fresh seeds against an
  independent reference, and is recorded as a chance or selection effect.
- **In no case** does R5 show walking, validate the preprint's biology, or change the live
  engine, mappings or motor admission.

## Limits

- **Selected DNs:** chosen from R3 because they scored high.
- **R3's drives only:** no drive search; VNCSIZE is tested at a single drive.
- **Isolated network:** R1's 2,111 neurons; no other brain or cord input.
- **Model, not biology:** reconstructed rate model; 64 replicates; 68 bodymap MNs.
- **The V1 score is our measure**, not the preprint's analysis.
- **Neural only:** no body or physics. Motor coordinates are unchanged (20/42 admitted, +4
  conditional).

## Build and run plan (on approval)

1. `docs/evidence/dng100-control-rhythm-v1/protocol.json`: arms, drives, targets, seeds, sham
   and control draws, criteria, hashes, expectations.
2. `malecns_backend/embodiment/dng100_control_rhythm.py`. It reuses:
   - `dng100_engaged_rhythm`: replicate, condition_summary, setup, DRIVES;
   - `dng100_rate_model`: control pool rules, summarize;
   - `dng100_recruitment_map`: intermediates.
3. Unit tests (I3). Then one timing simulation at seed 0 (not a protocol seed), discarded and
   disclosed.
4. Commit and push the preregistration. Run once in the background (about 35 minutes),
   evaluate in the same process, and record the results, handoff and roadmap.

## Build-time notes (before any protocol simulation)

- No amendments to the design's conditions, criteria or expectations. The protocol
  (`protocol.json`, sha 0fabdb48…) spells out three details the design left implicit:
  - C1 uses R1's rule (if the control p80 were NaN, only score ≥ 0.5 is required);
  - C3 uses R1's rule (a silenced condition with no scored replicate counts as abolished);
  - per-MN detail is stored only for runs scoring ≥ 0.5, to keep the result file small.
- **Plumbing.** One R1SIZE DNg75_R simulation at seed 0 (not a protocol seed) was timed
  (0.58 s). It also printed the control pool size (640) and the source hashes; its score and
  rates were not printed.
