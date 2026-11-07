# Rhythm, Step R8: which of DNg100's direct targets does the network ignition need? (design)

Designed 2026-11-07. **Status: run 2026-11-07, SINGLE_IGNITION_SOURCE in R1SIZE** (body 13964;
no rhythm unmasked, the core goes silent too); VNCSIZE DISTRIBUTED_IGNITION; X1 wrong, X2-X3 held
(protocol 528d96a2, result e4415e49). See `DNG100_IGNITION_SOURCE_RESULTS.md`. Neural-only
rate-model simulation of R1's isolated network.

## Why this step

- **R2 / R3:** DNg100_L engages the core only through an all-or-none network ignition (about
  600 or more recruited), which leaves the core in saturated steady states.
- **R5:** the rhythm-driving DNs (DNg75_R, DNa02_L) recruit about 130–190 cells and leave the
  core oscillating.
- **R7:** boosting the core's inhibitory set up to 3× never stops DNg100's ignition (610–740
  recruited at every level), and never gives it a rhythm.
- **Hypothesis (from R7):** the ignition arises in the wider network that DNg100 drives, not in
  the core's inhibitory balance.

R8 asks:

> **Is DNg100_L's network ignition carried by one (or a few) of its direct postsynaptic
> partners? If a single partner's silencing prevents the ignition, does a front-left MN rhythm
> appear?**

**Already known (disclosed).** R4 reported DNg100_L's network out-degree as 70 cells, and its
two-hop intermediates to the core. No partner has been silenced, and no partner's own activity
under DNg100 drive has been inspected.

## Conditions (declared; no drive adjustment)

| Arm | Sizes | Drive | Role |
|---|---|---|---|
| R1SIZE | R1's | 16,000 | **primary** (consistent with R5–R7, where the rhythm exists) |
| VNCSIZE | R1b cord-only | 2,000 | secondary (the more faithful sizes; R3's engaged drive) |

**Candidates P:** every network cell j ≠ DNg100_L with W[j, DNg100_L] ≠ 0, taken from R1's
signed matrix in dense-index order. That is DNg100_L's direct partners; R4 found 70.

**Conditions per arm, all stimulating DNg100_L**

| Condition | Silenced | Seeds |
|---|---|---|
| STIM | none | 5001–5016 |
| SIL_SHAM | one cell per replicate, by R5's sham rule (seed + 7,000,000; the eligible set also excludes P) | 5001–5016 |
| SIL_GROUP | all of P (a sanity anchor: DNg100_L then has no network output) | 5001–5016 |
| SIL_j | partner j alone, for each j in P | 5001–5016 |

- **16 seeds.** R2 found the ignition all-or-none and highly consistent across seeds, so 16
  seeds suffice to read a median recruited count. This is fewer than the rhythm steps.
- **Totals:** 2 arms × (|P| + 3) × 16. With |P| = 70, that is 2,336 simulations (about 25
  minutes).
- **Model:** R1's model and R3's replicate function, unchanged. No weight changes.

## Readout and criteria

**Readout** (R3's): median recruited, MN rhythm score and frequency, E1, E2 and I1 trace
rhythmicity and mean rates. A condition is **IGNITED** if its median recruited count is at
least 500 (R2's `RANGE_MAX`, as in R7).

**Validity, per arm:** STIM is IGNITED and SIL_SHAM is IGNITED. Otherwise the arm is `INVALID`.

**Class per partner, per valid arm**
- `PREVENTS_IGNITION`: SIL_j is not IGNITED.
- `NOT_NEEDED`: SIL_j is IGNITED.

**Verdict per arm** (first matching row)

| Verdict | Rule |
|---|---|
| `INVALID` | validity failure |
| `SINGLE_IGNITION_SOURCE` | ≥ 1 partner is `PREVENTS_IGNITION` (all such partners are listed) |
| `DISTRIBUTED_IGNITION` | no single partner, and SIL_GROUP is not IGNITED |
| `IGNITION_NOT_VIA_PARTNERS` | SIL_GROUP is still IGNITED (not expected: with all of P silenced, DNg100_L has no network output) |

The **primary verdict** is R1SIZE's; VNCSIZE is reported alongside.

**Secondary: is a rhythm unmasked?** For each `PREVENTS_IGNITION` partner in R1SIZE, check
whether SIL_j scores ≥ 0.5 **and** has a median E1 trace rhythmicity ≥ 0.5.
- `RHYTHM_UNMASKED` if any partner does; the partners are listed.
- `NO_RHYTHM_UNMASKED` otherwise. It is not applicable if there is no `PREVENTS_IGNITION`
  partner.

**Reported, not gated**
- Every partner's body ID, name, transmitter, weight from DNg100_L, and out-degree.
- Its recruited count, core rates and score.
- Whether it is one of DNg100_L's two-hop intermediates to the core.
- The same for VNCSIZE.

## Integrity (declared now)

- **I1 sources:**
  - file hashes (R1–R3, R5–R7 modules; R3 and R7 `result.json`);
  - R1's network body-ID hash;
  - DNg100_L's dense index resolved from body ID 10045;
  - P computed from W and non-empty.
- **I2 (reproduction, hard gate):** 8 simulations must equal the stored runs exactly (score,
  recruited, core activity):
  - R1SIZE: R7's DNg100_L runs at g = 1, seeds 4001–4004;
  - VNCSIZE: R3's DNG100 runs, seeds 1001–1004.
- **I3 tests:** the partner rule on a toy W; the classes, validity and verdict order; the
  rhythm-unmasked rule.
- **I4 completeness:** 2 × (|P| + 3) × 16 simulations, plus 8 reproduction simulations.

## Expectations (recorded now)

- **X1:** R1SIZE is `DISTRIBUTED_IGNITION`. I expect no single partner to be needed, because
  the ignition is a network-wide jump.
- **X2:** VNCSIZE is `DISTRIBUTED_IGNITION`.
- **X3:** no rhythm is unmasked (`NO_RHYTHM_UNMASKED` or not applicable).

Wrong expectations are recorded as wrong.

## What each outcome means (declared now)

- **SINGLE_IGNITION_SOURCE:** in this model, DNg100's ignition runs through the named
  partner(s). If a rhythm is also unmasked, DNg100 can drive the oscillating core once that
  route is removed. That would locate the difference between DNg100 and the rhythm-driving
  DNs at a specific connection. It is a model statement only: it says nothing about that cell's
  biological role, and it changes nothing in the live engine.
- **DISTRIBUTED_IGNITION:** no single direct partner carries the ignition. It is a property of
  DNg100's broad output (R4: 70 partners, 1,641 synapses), which subset or graded designs could
  probe later.
- **INVALID / IGNITION_NOT_VIA_PARTNERS:** recorded as found. The assumptions behind R8 would
  need revisiting.
- **In no case** does R8 show walking, assign biological roles, or change the live engine,
  weights, mappings or motor admission.

## Limits

- **Direct partners only,** singly and as a whole group; no subsets or two-hop cells.
- **16 seeds** per condition.
- **One drive per size version;** R1's isolated network.
- **Reconstructed rate model;** R1's transmitter signs; 68 bodymap MNs.
- **Neural only:** no body or physics. Motor coordinates are unchanged (20/42 admitted, +4
  conditional).

## Build and run plan (on approval)

1. `docs/evidence/dng100-ignition-source-v1/protocol.json`: partner rule, arms, seeds, criteria,
   hashes, expectations.
2. `malecns_backend/embodiment/dng100_ignition_source.py`. It reuses:
   - `dng100_engaged_rhythm`: setup, replicate, condition_summary;
   - `dng100_control_rhythm`: the sham rule;
   - `dng100_recruitment_map`: intermediates.
3. Unit tests (I3). Then one timing simulation at seed 0 (not a protocol seed), discarded and
   disclosed.
4. Commit and push the preregistration. Run once in the background, evaluate in the same
   process, and record the results, handoff and roadmap.

## Build-time notes (before any protocol simulation)

- No amendments to the design's partner rule, conditions, criteria or expectations. The
  protocol is `protocol.json` (sha 528d96a2…).
- **Sham.** The sham eligibility set also excludes DNg100_L's two-hop intermediates to the core,
  following R5's rule as declared.
- **Plumbing.** One R1SIZE DNg100_L simulation at seed 0 (not a protocol seed) was timed
  (0.80 s). No partner was listed; its score and rates were not printed.
- The partner list is computed for the first time inside the registered run.
