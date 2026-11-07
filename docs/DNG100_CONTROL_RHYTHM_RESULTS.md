# Rhythm, Step R5 (control-DN rhythm test): results

Run 2026-11-06 under the preregistered protocol
`docs/evidence/dng100-control-rhythm-v1/protocol.json` (sha 0fabdb48…). The protocol, module and
tests were committed and pushed in a500af8 before any protocol simulation.
- **Run:** one command in the background, 16 reproduction plus 2,560 protocol simulations,
  1,637 s, run once and evaluated in the same process.
- **Output:** `docs/evidence/dng100-control-rhythm-v1/run/result.json` (sha c4318d93…), with
  `console.txt` alongside.
- **Design:** `DNG100_CONTROL_RHYTHM_V1.md` (no amendments).

This was a **neural-only rate-model simulation** of R1's isolated 2,111-neuron network. No body
or physics were involved; the live engine was not touched.

## Headline: OBSERVATION_NOT_CONFIRMED (by the declared rule)

The headline required both primary targets to be `CORE_RHYTHM_CONFIRMED` in R1SIZE. Both are
instead **`RHYTHM_CORE_INDEPENDENT`**: the rhythm reproduced and was specific, and silencing
E1 or E2 abolished it, but silencing I1 did not.

| Arm | DNg75_R | DNa02_L | DNp09_R |
|---|---|---|---|
| R1SIZE (16,000) | RHYTHM_CORE_INDEPENDENT (I1 not needed) | RHYTHM_CORE_INDEPENDENT (I1 not needed) | RHYTHM_CORE_INDEPENDENT (I1 not needed) |
| VNCSIZE (2,000) | RHYTHM_NOT_CONFIRMED | RHYTHM_NOT_CONFIRMED | RHYTHM_NOT_CONFIRMED |

**R1SIZE condition scores** (64 fresh seeds each; new-control p80 0.192)

| Target | STIM | SIL_E1 | SIL_E2 | SIL_I1 | SIL_SHAM | STIM frequency |
|---|---|---|---|---|---|---|
| DNg75_R | **0.983** (64/64 ≥ 0.5) | 0.006 | 0.000 | **0.929** (64/64) | 0.984 | 13.4 Hz |
| DNa02_L | **0.926** (63/64) | 0.000 | 0.000 | **0.542** (33/64) | 0.924 | 13.7 Hz |
| DNp09_R | 0.509 (34/64) | 0.001 | 0.000 | 0.508 (34/64) | 0.512 | 13.1 Hz |

**VNCSIZE.** STIM scores were 0.051, 0.087 and 0.095 (new-control p80 0.085), all below 0.5.

| Expectation | Outcome |
|---|---|
| X1 (headline confirmed) | **wrong**: rhythm confirmed and specific, but I1 is not needed |
| X2 (all three NOT_CONFIRMED in VNCSIZE) | **held** |
| X3 (new-control p80 in R1SIZE < 0.5) | **held** (0.192) |

**Integrity.** All pass:
- I1: hashes, network, R1b's plane and median; targets equal R4's RHYTHMIC group; 20 new
  controls disjoint from R1's.
- **I2: all 16 R3 reproduction simulations matched exactly.**
- I3: 5 new tests passed (31 together with R1–R4).
- I4: 2,560 simulations.

## What the core does (reported, not gated)

**R1SIZE, STIM.** E1, E2 and I1 traces all oscillate (median rhythmicity 1.00 for DNg75_R and
DNa02_L), at low mean rates:

| Target | E1 / E2 / I1 mean (Hz) | Recruited (median) |
|---|---|---|
| DNg75_R | 9.9 / 24.1 / 3.1 | 184 |
| DNa02_L | 6.9 / 17.2 / 5.9 | 126 |
| DNp09_R | 4.7 / 6.6 / ~0 (I1 active in 13/64) | 150 |

**Silencing in R1SIZE**
- **SIL_E1:** E1 off, and E2 nearly off too (E1 → E2). No rhythm.
- **SIL_E2:** E1 stays on but **tonic** (DNg75_R 23 Hz, trace rhythmicity 0.00); I1 off. No
  rhythm.
- **SIL_I1:** E1 and E2 keep oscillating at the same period:
  - DNg75_R: trace rhythmicity 1.00, MN score 0.93 at 13.3 Hz;
  - DNa02_L: weaker, traces 0.69 and 0.68, MN score 0.54 at 12.5 Hz.
- **SIL_SHAM:** unchanged (scores within 0.003 of STIM), so single-cell silencing per se is
  not disruptive.

**VNCSIZE, STIM.** All three DNs push the network into the same kind of state DNg100 reached in
R3: 650–1,000 recruited neurons, with I1 at 110–130 Hz and E2 suppressed, and no oscillation.

**New controls.** In R1SIZE, three of the 20 new DNs reached 0.37–0.43 but none reached 0.5:
DNae007(VES009)_L, DNde002(VES029)_R and DNde003(LAL106)_L. Five had no scored replicate.

## What this means (per the design's declared outcomes)

- **Declared consequence of RHYTHM_CORE_INDEPENDENT.** The rhythm does not need every core
  cell; the cells it does need are the next structural lead.
  - **Needed:** E1 and E2. Silencing either abolishes the rhythm, and without E2, E1 fires
    tonically.
  - **Not needed:** I1. The rhythm survives without it in all three targets (fully for
    DNg75_R).
- **The observation is real in this model, with R1's sizes.** It reproduced on 64 fresh seeds
  and was specific against an independent control set. It does not hold with cord-only sizes
  at R3's drive (X2), where these DNs, like DNg100, ignite the network into an I1-dominated
  steady state. R5 does not test other VNCSIZE drives.
- **Reading (a hypothesis, not a result).** E1 and E2 are both excitatory in R1's signs. An
  excitatory pair alone cannot oscillate in this rate model, which has no adaptation or delay.
  So the inhibition that shapes this rhythm presumably comes from other network cells rather
  than from I1. That differs from the preprint's E1–E2–I1 description and would be a
  structural question for a later, separately designed step.
- **For DNg100.** In both size versions, DNg100 never reached this regime. With R1's sizes, the
  rhythm-driving DNs recruited 126–184 neurons, while DNg100 needed a drive that ignited ~600.
  The difference remains how drive enters the network, now with E1–E2 as the needed cells.
- **In no case** does R5 show walking, validate the preprint's biology, or change the live
  engine, mappings or motor admission.

## Limits

- **Selected targets:** chosen from R3 because they scored high.
- **R3's drives only:** no drive search; VNCSIZE tested at a single drive.
- **Isolated network:** R1's 2,111 neurons; no other brain or cord input.
- **Model, not biology:** reconstructed rate model; 64 replicates; 68 bodymap MNs.
- **Our measure:** the V1 score, not the preprint's analysis.
- **I1's role is graded:** for DNa02_L, I1 silencing roughly halved the score (0.93 to 0.54),
  just above the 0.5 line; the verdict follows the declared rule.
- **Neural only:** no body or physics. Motor coordinates are unchanged (20/42 admitted, +4
  conditional).
