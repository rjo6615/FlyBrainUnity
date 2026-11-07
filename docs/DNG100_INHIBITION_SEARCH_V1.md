# Rhythm, Step R6: which inhibitory cells does the E1–E2 rhythm need? (design)

Designed 2026-11-06. **Status: designed only (no protocol, code or run).** A structural
candidate list followed by a silencing screen. Neural-only rate-model simulation of R1's
isolated network.

## Why this step

- **R5** (`DNG100_CONTROL_RHYTHM_RESULTS.md`), with R1's sizes at drive 16,000:
  - DNg75_R and DNa02_L drive a reproducible, specific front-left MN rhythm at 13–14 Hz.
  - Silencing E1 or E2 abolishes it, and without E2, E1 fires tonically.
  - Silencing I1 does not abolish it (DNg75_R 0.929; DNa02_L 0.542).
- **E1 and E2 are both excitatory** (acetylcholine; checked in the cache: E1 IN17A001_L, E2
  INXXX466_L; I1 IN16B036_L is glutamatergic, so inhibitory in R1's signs).
- **Why inhibition is expected.** R1's rate model has no adaptation or synaptic delay, so an
  excitatory pair alone should not oscillate. The rhythm must therefore involve inhibition
  from somewhere in the network other than I1.

R6 asks:

> **Which inhibitory cells in R1's network, other than I1, does the DNg75_R / DNa02_L rhythm
> need, and are any of them needed by both?**

## Stage A: candidate set (structural, declared rule)

On R1's signed matrix `W[post, pre]` (sign × synapse count, count ≥ 5). Let E = {E1, E2}, and
call a network cell **inhibitory** if its R1 sign is negative (GABA or glutamate).

| Tier | Rule |
|---|---|
| **T1: direct feedback loop** | inhibitory k ≠ I1 with W[k, e] > 0 for some e ∈ E (E excites k) **and** W[e', k] < 0 for some e' ∈ E (k inhibits E) |
| **T2: one-relay feedback loop** (used only if T1 has fewer than 5 cells) | inhibitory k ≠ I1, not in T1, with W[e', k] < 0 for some e' ∈ E, and some network cell x with W[x, e] > 0 and W[k, x] > 0 (E excites x, x excites k) |

- **Exclusions:** DNs, ANs and front-left MNs are excluded from candidacy, as are the core cells
  themselves.
- **Loop strength:** for T1, min(max_e W[k, e], max_e' |W[e', k]|). For T2, the inhibitory
  weight onto E alone, max_e' |W[e', k]|.
- **Cap:** at most **40 candidates**. T1 is ranked by loop strength (ties broken by dense index)
  and comes first; if T2 is used, it fills the remaining slots in the same way.
- **Not yet inspected (disclosed).** I have not counted or listed any candidate. The only
  structural facts I have looked at are E1's, E2's and I1's transmitters.

## Stage B: silencing screen (declared; no drive adjustment)

- **Arm:** R1SIZE only, at drive 16,000 (R3's and R5's), because the rhythm exists only there.
- **Targets:** DNg75_R (129181) and DNa02_L (130496). DNp09_R is left out: its rhythm is
  weaker (score 0.51).
- **Seeds:** 3001–3032, which are fresh.

| Condition | Silenced | Per target |
|---|---|---|
| STIM | none | 32 |
| SIL_SHAM | one cell per replicate, by R5's sham rule (seed + 7,000,000; the eligible set also excludes all candidates) | 32 |
| SIL_GROUP | all candidates at once | 32 |
| SIL_k | candidate k alone, for each candidate | 32 each |

**Totals:** 2 × (N + 3) × 32 simulations for N candidates; at most 2,752 (about 30 minutes).

**Model:** R1's model and R3's replicate function, unchanged.

## Readout and criteria

**Readout** (R3's, unchanged): MN rhythm score, frequency, core trace rhythmicity and activity,
and recruited count.

**Validity gate, per target:** STIM score ≥ 0.5 and SIL_SHAM score ≥ 0.5. If either fails, that
target is `INVALID`.

**Per candidate (and SIL_GROUP), per valid target**

| Class | Rule |
|---|---|
| `NEEDED_OSCILLATION` | score not ≥ 0.5 (R1's rule; NaN counts as abolished), E1 active in ≥ half the replicates, and median E1 trace rhythmicity < 0.5 |
| `NEEDED_CORE_OFF` | score not ≥ 0.5, but E1 active in fewer than half the replicates. Silencing removed the core's drive rather than its rhythm |
| `NEEDED_OTHER` | score not ≥ 0.5, E1 active and still rhythmic. The MN readout lost the rhythm downstream of E1 |
| `NOT_NEEDED` | score ≥ 0.5 |

`NEEDED_OSCILLATION` mirrors what silencing E2 did in R5, where E1 stayed on but went tonic.

**Verdict** (first matching row)

| Verdict | Rule |
|---|---|
| `INCONCLUSIVE` | an integrity failure, or both targets `INVALID` |
| `SHARED_INHIBITORY_PARTNER` | ≥ 1 candidate is `NEEDED_OSCILLATION` for both targets |
| `TARGET_SPECIFIC_PARTNER` | ≥ 1 candidate is `NEEDED_OSCILLATION` for one target only |
| `REDUNDANT_INHIBITION` | no single candidate qualifies, but SIL_GROUP is `NEEDED_OSCILLATION` for ≥ 1 target |
| `GROUP_SILENCES_CORE` | no single candidate qualifies, and SIL_GROUP is `NEEDED_CORE_OFF` for ≥ 1 target |
| `NO_PARTNER_IN_SET` | otherwise |

There is no correction across candidates. Each class is a declared, deterministic rule over 32
replicates, and every candidate's result is reported.

**Reported, not gated:** each candidate's tier, body ID, name, transmitter and loop weights; the
score and frequency for each condition; E1, E2 and I1 trace rhythmicity and mean rates; and
whether the candidate is one of either target's two-hop intermediates.

## Integrity (declared now)

- **I1 sources:**
  - file hashes (R1–R3 modules and the R5 module; R5's `result.json`);
  - R1's network body-ID hash;
  - the core cells' transmitters (E1 and E2 acetylcholine, I1 glutamate);
  - candidate set ≤ 40, containing no DN, AN, MN, core cell or I1.
- **I2 (R5 reproduction, hard gate):** re-run R5's R1SIZE STIM for DNg75_R and DNa02_L at
  seeds 2001–2004 (8 simulations). Score, recruited count and core activity must equal R5's
  stored runs exactly.
- **I3 tests:**
  - the candidate rule on a toy W (both tiers, exclusions, cap and ranking);
  - the classes;
  - the verdict order.
- **I4 completeness:** 2 × (N + 3) × 32 simulations, plus 8 reproduction simulations.

## Expectations (recorded now, before any candidate is listed)

- **X1:** T1 has at least 5 cells, so T2 is not needed.
- **X2:** the verdict is `SHARED_INHIBITORY_PARTNER`.
- **X3:** SIL_GROUP is `NEEDED_OSCILLATION` for both targets.

Wrong expectations are recorded as wrong.

## What each outcome means (declared now)

- **SHARED_INHIBITORY_PARTNER:** in this model on our wiring, the 13–14 Hz rhythm is an
  E1–E2 loop shaped by the named inhibitory cell(s). That is a model-level circuit
  identification. Comparing it with the preprint's E1–E2–I1 description, and asking how
  DNg100's drive reaches these cells, would be later, separate steps.
- **TARGET_SPECIFIC_PARTNER:** different DNs recruit different inhibitory partners. The rhythm
  is not one fixed circuit.
- **REDUNDANT_INHIBITION:** several inhibitory cells share the role. Single-cell silencing
  cannot isolate it, and pairwise or subset screens would be a separate design.
- **GROUP_SILENCES_CORE or NO_PARTNER_IN_SET:** the shaping inhibition lies outside these
  short loops, or silencing them removes the core's drive. The search would need a wider,
  separately versioned rule.
- **In no case** does R6 show walking, validate the preprint's biology, assign biological roles
  to these cells, or change the live engine, mappings or motor admission.

## Limits

- **R1's sizes only,** at one drive; the rhythm does not appear with cord-only sizes at R3's
  drive.
- **Short loops only** (T1, and T2 if needed), capped at 40 candidates.
- **Single-cell and whole-group silencing only;** no pairs or subsets.
- **32 replicates per condition** (fewer than R5's 64, because of the number of conditions).
- **Model, not biology:** reconstructed rate model; R1's transmitter signs; 68 bodymap MNs.
- **Neural only:** no body or physics. Motor coordinates are unchanged (20/42 admitted, +4
  conditional).

## Build and run plan (on approval)

1. `docs/evidence/dng100-inhibition-search-v1/protocol.json`: candidate rule, cap, conditions,
   seeds, classes, verdict, hashes, expectations.
2. `malecns_backend/embodiment/dng100_inhibition_search.py`. It reuses:
   - `dng100_engaged_rhythm`: replicate, condition_summary, setup;
   - `dng100_control_rhythm`: sham rule, targets;
   - `dng100_recruitment_map`: intermediates.
3. Unit tests (I3). Then one timing simulation at seed 0 (not a protocol seed), discarded and
   disclosed. The candidate list is computed for the first time inside the registered run.
4. Commit and push the preregistration. Run once in the background, evaluate in the same
   process, and record the results, handoff and roadmap.

## Build-time notes (before any protocol simulation)

- No amendments to the design's rule, conditions, classes or expectations. The protocol
  (`protocol.json`, sha 2d82fcd1…) spells out three details the design left implicit:
  - For T2, the relay x is any network cell excited by E1 or E2.
  - A candidate silenced with no scored replicate counts as abolished (R1's rule).
  - Per-MN detail is stored only for runs scoring ≥ 0.5.
- **Plumbing.** One R1SIZE DNg75_R simulation at seed 0 (not a protocol seed) was timed
  (0.61 s). No candidate was computed; its score and rates were not printed.
- The candidate list is computed for the first time inside the registered run.
