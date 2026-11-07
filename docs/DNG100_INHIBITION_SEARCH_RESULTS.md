# Rhythm, Step R6 (inhibition search): results

Run 2026-11-06 under the preregistered protocol
`docs/evidence/dng100-inhibition-search-v1/protocol.json` (sha 2d82fcd1…). The protocol, module and
tests were committed and pushed in 2172e7f before any protocol simulation, and before any
candidate was listed.
- **Run:** one command in the background, 8 reproduction plus 2,176 protocol simulations,
  1,354 s, run once and evaluated in the same process.
- **Output:** `docs/evidence/dng100-inhibition-search-v1/run/result.json` (sha 3d0d800c…), with
  `console.txt` alongside.
- **Design:** `DNG100_INHIBITION_SEARCH_V1.md` (no amendments).

This was a **neural-only rate-model simulation** of R1's isolated network (R1's sizes, drive
16,000). No body or physics were involved; the live engine was not touched.

## Verdict: REDUNDANT_INHIBITION

- **Candidates:** 31 T1 cells (21 GABA, 10 glutamate), each in a direct loop with E1 or E2.
  T2 was not needed.
- **No single candidate is needed.** Silencing any one of the 31 left the rhythm in place for
  both targets. The lowest single-cell scores were 0.82 (DNg75_R, IN08A002_L) and 0.76 (DNa02_L,
  IN19A007_L).
- **Silencing all 31 together** (SIL_GROUP) abolished the rhythm for DNg75_R, classed
  `NEEDED_OSCILLATION`, but **not** for DNa02_L, classed `NOT_NEEDED`. That makes the verdict
  `REDUNDANT_INHIBITION`, reached through DNg75_R only.

| Target | STIM | SIL_SHAM | SIL_GROUP | Frequency STIM → GROUP | Group class |
|---|---|---|---|---|---|
| DNg75_R | 0.988 | 0.988 | **0.052** | 13.3 → 1.6 Hz | NEEDED_OSCILLATION |
| DNa02_L | 0.928 | 0.926 | **0.993** | 13.4 → **7.5 Hz** | NOT_NEEDED |

Both targets passed the validity gate (STIM and SHAM ≥ 0.5).

| Expectation | Outcome |
|---|---|
| X1 (T1 ≥ 5) | **held** (31) |
| X2 (SHARED_INHIBITORY_PARTNER) | **wrong**: no single partner |
| X3 (SIL_GROUP NEEDED_OSCILLATION for both) | **wrong**: DNa02_L's rhythm survives |

**Integrity.** All pass:
- I1: hashes; network; E1 and E2 acetylcholine, I1 glutamate; 31 candidates, none excluded.
- **I2: all 8 R5 reproduction simulations matched exactly.**
- I3: 4 new tests passed (35 together with R1–R5).
- I4: 2,176 simulations, matching 2 × (31 + 3) × 32.

## What happened when the group was silenced (reported, not gated)

| Target, condition | E1 / E2 / I1 mean (Hz) | E1 / E2 / I1 trace rhythmicity | Recruited |
|---|---|---|---|
| DNg75_R STIM | 9.9 / 24.1 / 3.4 | 1.00 / 1.00 / 1.00 | 187 |
| DNg75_R SIL_GROUP | **154.8 / 138.4** / 11.0 | 0.00 / 0.00 / 0.00 | **689** |
| DNa02_L STIM | 7.0 / 17.4 / 6.4 | 1.00 / 1.00 / 1.00 | 128 |
| DNa02_L SIL_GROUP | 14.8 / 47.7 / **53.9** | 1.00 / 1.00 / 1.00 | 274 |

- **DNg75_R.** Removing all 31 inhibitory partners lets the network **ignite**: about 690
  recruited, with E1 and E2 saturated near 140–155 Hz. This is the same kind of saturated
  steady state DNg100 reached in R3. So the rule's `NEEDED_OSCILLATION` class is met, but the
  oscillation is lost through runaway excitation, not by removing one specific rhythm-shaping
  cell.
- **DNa02_L.** The rhythm survives at about half the frequency (7.5 Hz). I1, which R5 found
  was not needed when the candidates were intact, becomes strongly active (54 Hz) and
  oscillates. That is consistent with I1 and the 31 candidates sharing the inhibitory role, but
  silencing I1 together with the group was not tested.

## What this means (per the design's declared outcomes)

- **Declared consequence of REDUNDANT_INHIBITION.** Several inhibitory cells share the role, so
  single-cell silencing cannot isolate it. Pairwise or subset screens would be a separate design.
- **Further reading (a hypothesis, not a result).** In this model, the E1–E2 rhythm sits on a
  balance. Distributed inhibition from many short-loop partners (and from I1) holds E1 and E2
  at low rates, where they oscillate. Remove enough of it and the network ignites into the
  saturated state seen with DNg100. That suggests DNg100's failure to produce a rhythm and these
  DNs' success are two sides of the same excitation/inhibition balance, rather than one missing
  cell. Testing it would need its own preregistration (for example, I1 plus the group, or a
  graded removal of inhibition), with no tuning.
- **In no case** does R6 show walking, assign biological roles to these cells, validate the
  preprint's biology, or change the live engine, mappings or motor admission.

## Limits

- **R1's sizes only,** at one drive.
- **Short loops only:** 31 T1 cells; T2 and longer loops were not screened.
- **Single-cell and whole-group silencing only;** I1 was not silenced together with the group.
- **The verdict rests on one target:** REDUNDANT_INHIBITION comes from DNg75_R; for DNa02_L the
  group was not needed.
- **The rule's class does not capture the mechanism:** DNg75_R's "oscillation loss" is network
  ignition.
- **32 replicates per condition;** reconstructed rate model; R1's transmitter signs.
- **Neural only:** no body or physics. Motor coordinates are unchanged (20/42 admitted, +4
  conditional).
