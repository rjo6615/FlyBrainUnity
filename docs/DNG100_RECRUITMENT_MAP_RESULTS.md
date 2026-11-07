# Rhythm, Step R2 (DNg100 recruitment map): results

Run 2026-11-06 under the preregistered protocol
`docs/evidence/dng100-recruitment-map-v1/protocol.json` (sha 4b26c10a…). The protocol, module and
tests were committed and pushed in 32a86de before any protocol simulation.
- **Run:** one command, 288 simulations, 131 s, run once and evaluated in the same process.
- **Output:** `docs/evidence/dng100-recruitment-map-v1/run/result.json` (sha 974d72f4…), with
  `console.txt` alongside.
- **Design:** `DNG100_RECRUITMENT_MAP_V1.md`, including its build-time amendments.

This was a **neural-only rate-model simulation** of R1's isolated 2,111-neuron network. No body
or physics were involved; the live engine was not touched. It is descriptive and gives **no
rhythm verdict**.

## Status: MAP_RECORDED

**Integrity.** All pass:
- I1: source hashes, R1's network hash, the 11 intermediates' body IDs, and R1b's plane
  (z* = 462) and m_VNC (507,457,760) all reproduced.
- **I2 (hard gate): R2 reproduced all 56 of R1's recorded recruited counts** at drives 250–2,000
  for seeds 1–16, exactly. So R2 runs the same model as R1.
- I3: 4 new tests passed (18 together with R1 and R1b).
- I4: 288 simulations present.

## Labels

| Arm | Label | E1 | E2 | I1 | Median recruited at the engaging drive |
|---|---|---|---|---|---|
| R1SIZE (primary) | `CORE_REACHED_BEYOND_RANGE` | ENGAGED_AT_16000 | ENGAGED_AT_16000 | ENGAGED_AT_16000 | 622.5 |
| VNCSIZE (descriptive) | `CORE_REACHED_BEYOND_RANGE` | ENGAGED_AT_2000 | ENGAGED_AT_2000 | ENGAGED_AT_2000 | 653 |

| Expectation | Outcome |
|---|---|
| X1 (R1SIZE: E1 engaged at ≥ 4,000) | **held** (16,000) |
| X2 (R1SIZE: CORE_REACHED_BEYOND_RANGE) | **held** |
| X3 (VNCSIZE engages at the same or a lower drive) | **held** (2,000 vs 16,000 for all three; none vacuous) |

No core cell went unengaged, so there is no stopping point to report.

## The map (medians over 16 seeds)

**R1SIZE**

| I_stim | DNg100_L (Hz) | Recruited | Active MNs | Core active (seeds E1/E2/I1) | E1 margin |
|---|---|---|---|---|---|
| 250 | 0.5 | 1 | 0 | 0/0/0 | −65 |
| 1,000 | 24 | 4.5 | 0 | 0/0/0 | −65 |
| 2,000 | 57 | 32 | 0.5 | 0/0/0 | −47 |
| 4,000 | 110 | 102.5 | 8 | 0/0/0 | −61 |
| 8,000 | 171 | 157 | 11.5 | 7/6/6 | −24 |
| 16,000 | 195 | **622.5** | 28 | **15/15/15** | +1,240 |
| 32,000–64,000 | 197 | 624 | 27.5 | 15/15/15 | +1,240 |

**VNCSIZE**

| I_stim | DNg100_L (Hz) | Recruited | Active MNs | Core active (seeds) |
|---|---|---|---|---|
| 500 | 14 | 5 | 0 | 0/0/0 |
| 1,000 | 38 | 38 | 0 | 3/3/3 |
| 2,000 | **2.8** | **653** | 26.5 | **16/16/16** |
| 4,000–64,000 | 69 → 197 | 640–768 | 22–24 | 16/16/16 |

## What the map shows

- **The signal does not stop at a missing link.** All three core cells are reachable, and they
  always switch on **together**.
- **Engagement is all-or-none.** The core switches on exactly when the whole network jumps from
  about 150 to about 620 active neurons:
  - R1SIZE: between 8,000 and 16,000. At 8,000 the seeds split (7 of 16 engaged).
  - VNCSIZE: between 1,000 and 2,000.
  - Below the jump, E1 stays clearly under threshold (margin −24 to −65). Above it, E1 is far
    over threshold.
- **The preprint's drive rule cannot reach the engaged state on our network.** That rule accepts
  only 5–500 recruited neurons. Over all 288 simulations:
  - R1SIZE: with the core silent, at most 167 neurons were recruited. All 51 simulations with the
    full core on had 598–635 recruited. One more (8,000, seed 5) had E1 just over the 0.01 Hz
    line (mean 0.0 Hz) with 160 recruited.
  - VNCSIZE: at most 44 recruited with the core silent; at least 621 with it on.
  - So nothing engaged lies inside the preprint's band. This explains R1: its rule stopped at
    1,000–2,000, below the jump.
- **R1b's size correction moves the jump about 8× lower** (from 16,000 to 2,000) but does not
  change its all-or-none character.
- **DNg100 itself is suppressed after the jump in VNCSIZE.** At 2,000 its median rate falls to
  2.8 Hz (from 38 Hz at 1,000) while 653 neurons are active, which suggests recurrent inhibition
  onto DNg100. This is an observation; R2 did not trace that inhibition.
- **The two size versions give different engaged states:**
  - R1SIZE: E1 about 105 Hz and E2 about 73 Hz (means), I1 mostly quiet (mean 8.8 Hz, peak 104).
  - VNCSIZE: I1 about 116–141 Hz and dominant, E2 nearly silent (mean ≈ 1 Hz), E1 16–30 Hz.

**Reported only (not a test).** The V1 rhythmicity score of the active front-left MNs stayed
between 0.01 and 0.03 in every engaged condition, against R1's 0.5 criterion. So in this model the
engaged network looks **tonic**, not rhythmic. R2 had no controls and drives outside the
preprint's rule, so this is an observation, not a rhythm verdict.

## What this means (per the design's declared outcomes)

- **Declared consequence of `CORE_REACHED_BEYOND_RANGE`:** our wiring can carry DNg100's signal
  to the core, but only at drives that recruit more than the preprint's rule allows. The next
  question is whether the engaged core oscillates. That needs a separately preregistered rhythm
  test at declared drives, with controls.
- **R2's reported scores suggest the answer will likely be no** in this model, but that is not
  the test.
- Nothing here says the preprint is wrong. Our network is a different connectome (maleCNS,
  front-left only, 68 bodymap MNs), and R2 uses a reconstructed model.

## Limits

- **Isolated network:** R1's 2,111-neuron network only.
- **Model:** reconstructed rate model (b from ratenet.js); "active" (> 0.01 Hz) is permissive.
- **Drives:** those above 2,000 are reachability probes outside the preprint's rule, not
  physiology.
- **Sizes:** VNCSIZE inherits R1b's cable-length proxy for volume.
- **Samples:** 16 seeds per drive; in R1SIZE one seed stayed unengaged at 16,000–64,000 (15 of 16).
- **Neural only:** no body, physics or engine change. Motor coordinates are unchanged (20/42
  admitted, +4 conditional).
