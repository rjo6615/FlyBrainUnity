# Rhythm, Step R7 (excitation/inhibition balance test): results

Run 2026-11-07 under the preregistered protocol
`docs/evidence/dng100-balance-test-v1/protocol.json` (sha f7d6ec97…). The protocol, module and
tests were committed and pushed in 8ac3895 before any protocol simulation.
- **Run:** one command in the background, 8 reproduction plus 768 protocol simulations, 569 s,
  run once and evaluated in the same process.
- **Output:** `docs/evidence/dng100-balance-test-v1/run/result.json` (sha 7d8575c7…), with
  `console.txt` alongside.
- **Design:** `DNG100_BALANCE_TEST_V1.md` (no amendments; build notes disclose a solver-tolerance
  equivalence correction and a fixed body-ID/dense-index bug).

This was a **neural-only rate-model simulation** of R1's isolated network (R1's sizes, drive
16,000), with a **declared weight intervention**: S's outgoing weights were scaled by g, where S
is I1 plus R6's 31 inhibitory candidates. No body or physics were involved; the live engine was
not touched.

## Verdict: REMOVAL_ONLY

- **(a) holds.** Both rhythm-driving DNs lose their rhythm by ignition as S's output is reduced:
  - DNg75_R at g = 0.25;
  - DNa02_L only at g = 0.
- **(b) does not hold.** DNg100_L never scores ≥ 0.5 at g = 1.5, 2 or 3 (0.015, 0.005 and 0.004),
  and stays ignited at every level.

| Expectation | Outcome |
|---|---|
| X1 (DNg75_R LOST_BY_IGNITION) | **held** (g = 0.25) |
| X2 (DNa02_L LOST_BY_IGNITION) | **held** (g = 0) |
| X3 (b does not hold) | **held** |

**Integrity.** All pass:
- I1: hashes; network; S is 32 distinct inhibitory cells.
- **I2: via the scaled-W path at g = 1, all 8 R6 simulations matched exactly.**
- I3: 5 new tests passed (40 together with R1–R6).
- I4: 768 simulations.

Validity passed: both drivers scored ≥ 0.5 at g = 1.

## Curves against g (32 seeds each)

Score / frequency (Hz) / median recruited; **bold** marks IGNITED (median recruited ≥ 500).

| g | DNg75_R | DNa02_L | DNg100_L |
|---|---|---|---|
| 0 | 0.002 / 5.9 / **712** | 0.012 / 7.1 / **696** | 0.004 / 6.7 / **736** |
| 0.25 | 0.047 / 4.8 / **666** | 0.843 / 8.5 / 231 | 0.004 / 1.6 / **634** |
| 0.5 | 0.909 / 10.0 / 234 | 0.907 / 10.5 / 154 | 0.001 / 6.0 / **624** |
| 0.75 | 0.989 / 11.8 / 204 | 0.942 / 12.2 / 135 | 0.004 / 7.6 / **621** |
| 1 | 0.987 / 13.2 / 186 | 0.940 / 13.5 / 128 | 0.035 / 7.2 / **626** |
| 1.5 | 0.893 / 15.6 / 170 | 0.873 / 15.0 / 125 | 0.015 / 6.9 / **612** |
| 2 | 0.639 / 17.9 / 163 | 0.781 / 16.1 / 123 | 0.005 / 3.9 / **610** |
| 3 | 0.429 / 21.3 / 157 | 0.183 / 15.3 / 112 | 0.004 / 5.2 / **612** |

Core mean rates, E1 / E2 / I1 (Hz), reported only:

| g | DNg75_R | DNg100_L |
|---|---|---|
| 0 | 185 / 164 / 6 | 197 / 181 / 7 |
| 1 | 10 / 24 / 4 | 113 / 74 / 10 |
| 3 | 6 / 13 / 0 | 2 / 2 / 128 |

## What this shows (reported, not gated)

- **The rhythm lives in a window of inhibition.**
  - Too little inhibition from S: the network ignites and E1/E2 saturate (about 150–185 Hz).
  - Too much: the rhythm weakens without ignition. DNa02_L at g = 3 scores 0.18, with E1 trace
    rhythmicity 0.35.
  - Inside the window, frequency rises with inhibition: DNg75_R goes from 10 Hz at g = 0.5 to
    21 Hz at g = 3.
- **DNg100's ignition does not depend on S.**
  - Recruitment stays at about 610–740 at every g, including g = 3.
  - Boosting S only changes which core state the ignited network settles into: saturated E1/E2
    at g ≤ 1, then I1-dominated with E1 and E2 nearly silent at g ≥ 2. The latter resembles
    the VNCSIZE state in R3.
  - The core never oscillates under DNg100 (E1 trace rhythmicity ≤ 0.003).

## What this means (per the design's declared outcomes)

- **Declared consequence of REMOVAL_ONLY.** Too little inhibition destroys the rhythm by
  ignition, but adding inhibition does not rescue DNg100. DNg100's difference lies elsewhere,
  for instance in how its drive reaches the core.
- **Sharper reading (a hypothesis, not a result).** Under DNg100 the ignition persists even when
  the core's inhibitory partners are tripled. So the jump appears to arise in the wider network
  that DNg100 drives, not in the E1–E2 loop's inhibitory balance. The core then just follows
  the ignited network. The rhythm-driving DNs recruit far fewer cells (about 130–190) and leave
  the core in the window where it oscillates. The next question is what DNg100 drives that
  ignites the network, which would be a separately designed structural or dynamical step.
- **In no case** does R7 show walking, assign biological roles to these cells, imply that
  DNg100's inhibition is biologically too weak, or change the live engine, weights, mappings or
  motor admission.

## Limits

- **R1's sizes only,** at one drive.
- **One inhibitory set,** scaled uniformly; other inhibitory cells were unchanged.
- **Eight g levels and 32 seeds;** (b) had three chances, and none passed.
- **A weight intervention:** a probe of model dynamics, not a fidelity correction or a
  biological claim.
- **g = 0 matches silencing S** only to solver tolerance, as disclosed.
- **Reconstructed rate model;** R1's transmitter signs; 68 bodymap MNs.
- **Neural only:** no body or physics. Motor coordinates are unchanged (20/42 admitted, +4
  conditional).
