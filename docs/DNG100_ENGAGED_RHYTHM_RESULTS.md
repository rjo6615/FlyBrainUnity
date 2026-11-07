# Rhythm, Step R3 (rhythm test in the engaged regime): results

Run 2026-11-06 under the preregistered protocol
`docs/evidence/dng100-engaged-rhythm-v1/protocol.json` (sha 51bec0c2…). The protocol, module and
tests were committed and pushed in 1e3e38a before any protocol simulation.
- **Run:** one command in the background, 8 reproduction plus 1,152 protocol simulations,
  892 s, run once and evaluated in the same process.
- **Output:** `docs/evidence/dng100-engaged-rhythm-v1/run/result.json` (sha 099e42a7…), with
  `console.txt` alongside.
- **Design:** `DNG100_ENGAGED_RHYTHM_V1.md` (no amendments).

This was a **neural-only rate-model simulation** of R1's isolated 2,111-neuron network. No body
or physics were involved; the live engine was not touched.

## Verdict: RATE_RHYTHM_NOT_REPRODUCED (primary VNCSIZE; R1SIZE the same)

| Criterion | VNCSIZE (primary, drive 2,000) | R1SIZE (drive 16,000) |
|---|---|---|
| C1 rhythm: DNG100 ≥ 0.5 and > control p80 | **0.055** (p80 0.101) — no | **0.023** (p80 0.227) — no |
| C2 frequency 5–20 Hz | 8.9 Hz — yes, but not meaningful (see below) | 8.0 Hz — same |
| C3 necessity: SIL_E1/E2/I1 each < 0.5 | 0.008 / 0.003 / 0.004 — yes, vacuously | 0.003 / 0.004 / 0.010 — yes, vacuously |
| Qualifier | none: core engaged in 64/64 DNG100 replicates | none: 60/64 (0.94) |

- **C2:** "frequency" is the median over MNs with any score > 0. With scores this low it is not
  evidence of a rhythm.
- **C3:** it holds vacuously, because DNG100 itself is not rhythmic.

**DNG100 replicates.** No replicate scored ≥ 0.5 in either arm. The best single replicate scored
0.40 in VNCSIZE and 0.17 in R1SIZE.

| Expectation | Outcome |
|---|---|
| X1 (VNCSIZE NOT_REPRODUCED, score < 0.1) | **held** (0.055) |
| X2 (R1SIZE NOT_REPRODUCED) | **held** |
| X3 (VNCSIZE E1 trace median rhythmicity < 0.5) | **held** (0.18) |

**Integrity.** All pass:
- I1: hashes, R1 network, control list, and R1b's plane and median.
- **I2: all 8 R2 reproduction simulations matched exactly.**
- I3: 4 new tests passed (22 together with R1, R1b and R2).
- I4: 1,152 simulations.

## What the engaged core does under DNg100

| Arm | DNg100_L (Hz) | E1 / E2 / I1 mean (Hz) | Core-trace rhythmicity E1 / E2 / I1 |
|---|---|---|---|
| VNCSIZE | **4.1** (suppressed, as in R2) | 15.8 / 1.0 / **113.9** | 0.18 / 0.00 / 0.13 |
| R1SIZE | 199.5 | **115.8 / 69.2** / 6.5 | 0.00 / 0.03 / 0.00 |

In both arms DNg100 drives the core into a **steady state**, with no oscillation in the core cells
themselves:
- **VNCSIZE:** I1 dominates and E2 is shut down.
- **R1SIZE:** E1 and E2 are high and I1 is nearly off.

Silencing behaves as the wiring predicts. SIL_E1 also silences E2 (E1 → E2 465), and silencing
any one cell removes engagement.

## Unplanned observation: some control DNs make the core oscillate (R1SIZE only)

This is **not a preregistered test**: control conditions had no silencing, and the observation
was not anticipated. It is recorded as found.

In R1SIZE, three of the 20 control DNs, stimulated at 16,000, gave strong front-left MN rhythms.
In each case the E1, E2 and I1 traces oscillated too:

| Control DN | MN score (frac ≥ 0.5) | Frequency | E1 / E2 / I1 trace rhythmicity | Recruited (median) |
|---|---|---|---|---|
| DNg75_R (129181) | **0.97** (16/16) | 13.6 Hz | 1.00 / 1.00 / 1.00 | 184 |
| DNa02_L (130496) | **0.95** (16/16) | 14.1 Hz | 1.00 / 1.00 / 1.00 | 127 |
| DNp09_R (1087) | 0.52 (0.62) | 13.1 Hz | 0.98 / 0.98 / 0.95 | 157 |

- **DNg75_R best replicate:**
  - E1, E2 and I1 all cycle at a 74 ms period, at low rates (E1 mean 8 Hz, peak 17).
  - The front-left promotor, rotator and trochanter-flexor MNs cycle at the same period.
- **Recruitment:** these runs recruited 127–184 neurons, inside the preprint's 5–500 band.
  DNG100's engaged runs recruited about 620.
- **Not in VNCSIZE.** With cord-only sizes, the same three DNs gave scores of 0.05–0.12.
- **Same neuron as an intermediate.** DNg75_R (129181) is also one of E1's two-hop
  intermediates from DNg100 (R2).

**Reading (a hypothesis, not a result).** In this model on our wiring, the E1–E2–I1 core *can*
oscillate at about 13–14 Hz. That happens when it is driven moderately, so the core cells fire
at low rates. DNg100 does not put it there: its drive engages the core only through the
all-or-none jump, which pushes the cells into saturated steady states. Whether these
oscillations need E1, E2 and I1 was **not tested**, because control conditions had no
silencing. They also appear only with R1's sizes, which R1b found to be the less faithful
definition.

## What this means (per the design's declared outcomes)

- **Declared consequence of NOT_REPRODUCED.** With the core engaged, this reconstruction of the
  preprint's model on our maleCNS front-left wiring does not produce a DNg100-specific MN rhythm.
  Together with V1 (LIF, tonic), both engines give tonic DNg100 output on our wiring. The design
  said any further step should be a structural comparison, not tuning.
- **The unplanned observation sharpens that.** The core can oscillate in our wiring, under other
  DNs' drive, at low core rates. So the question becomes *how* DNg100's input to the core differs
  from DNg75_R's and DNa02_L's, not whether the oscillator exists. That is a structural
  comparison of their routes into E1/E2/I1. Any test of the control-DN oscillation (with core
  silencing, and in both size versions) would need its own preregistration.

## Limits

- **Isolated network:** R1's 2,111-neuron network; no other brain or cord input.
- **Drives:** chosen by a declared engagement rule, outside the preprint's recruitment rule.
- **Model, not biology:** reconstructed rate model (b from ratenet.js); 64 replicates, not
  1,024; 68 bodymap MNs, not 144.
- **Our measure:** the V1 score, not the preprint's analysis.
- **Anticipated outcome:** DNG100's result was partly anticipated by R2.
- **The control-DN rhythms are unplanned observations:** 16 seeds each, no silencing, R1SIZE
  only.
- **Neural only:** no body or physics. Motor coordinates are unchanged (20/42 admitted, +4
  conditional).
