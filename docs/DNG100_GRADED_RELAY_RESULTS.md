# Rhythm, Step R9 (graded relay test): results

Run 2026-11-08 under the preregistered protocol
`docs/evidence/dng100-graded-relay-v1/protocol.json` (sha de66566b…). The protocol, module and
tests were committed and pushed in fb6a66a before any protocol simulation.
- **Run:** one command in the background, 8 reproduction plus 704 protocol simulations,
  250 s, run once and evaluated in the same process.
- **Output:** `docs/evidence/dng100-graded-relay-v1/run/result.json` (sha 28e1673c…), with
  `console.txt` alongside.
- **Design:** `DNG100_GRADED_RELAY_V1.md` (no amendments).

This was a **neural-only rate-model simulation** of R1's isolated network. The weight change
existed only in the model copy; the live engine was not touched.

## Verdict: NOT_SEPARABLE (both modes)

- **Validity passed:** g = 1 ignited in both modes (median 612.5), and WHOLE at g = 0 did not
  (161.5).
- **No level** was both not ignited and core-engaged, in either mode. So there is no rhythm
  window either.
- **Transition:** in both modes, every level from 0 to 0.8 is not ignited and 0.9–1.0 are
  ignited, one contiguous block from 0.
- **SPARE_E1 behaves like WHOLE.** Keeping the 8-weight synapse onto E1 changed recruitment at no
  level, and changed E1's mean rate by at most about 0.1 Hz.

**Median curve (identical in both modes, except E1 activity at the lowest levels)**

| g | median recruited | E1 active | E1 mean Hz | 13964 mean Hz | MN score |
|---|---|---|---|---|---|
| 0–0.5 | 161–163 | 4/32 (SPARE_E1: 4–5/32) | ≤ 0.11 | 31.2–31.3 | 0.000 |
| 0.6 | 164 | 4/32 | 2.9 | 30.1 | ≤ 0.003 |
| 0.7 | 166 | 6/32 | 9.7 | 28.0 | ≤ 0.002 |
| 0.8 | 169.5 | 14/32 | 38.2 | 19.3 | 0.005 |
| 0.9 | 615 | 24/32 | 77.9 | 8.6 | 0.014 |
| 1.0 | 612.5 | 28/32 | 96.8 | 3.8 | 0.018 |

E1's median trace rhythmicity is 0 at every level: whenever E1 is active, it is tonic. DNg100_L's
own rate is 194.1 Hz at every level.

| Expectation | Outcome |
|---|---|
| X1 (WHOLE NOT_SEPARABLE) | **held** |
| X2 (SPARE_E1 NOT_SEPARABLE) | **held** |
| X3 (no RHYTHM_WINDOW) | **held** |

**Integrity.** All pass:
- I1: hashes; network; both body IDs resolved (13964 → dense 3694). The wiring re-checked from W:
  52 from DNg100_L; 68 targets, all excitatory; 8 onto E1, its only core target; 1,086 total.
- **I2: all 8 reproduction simulations matched exactly** (R7 at g = 1 through the WHOLE g = 1
  model; R8's SIL_3694 by silencing).
- I3: 4 new tests passed (54 across all `test_dng100_*` files).
- I4: 704 simulations.

## Descriptive, not gated (read after the verdict)

These are per-run tallies I made after the verdict. They are not preregistered criteria.
- **The ignition is per-seed all-or-none.** At every level each replicate either recruited
  144–175 cells or 597–651. None fell in between. The number ignited out of 32
  is:

  | g | 0–0.5 | 0.6 | 0.7 | 0.8 | 0.9 | 1.0 |
  |---|---|---|---|---|---|---|
  | ignited | 0 | 1 | 3 | 12 | 23 | 27 |

  So grading 13964 shifts the probability of a jump rather than giving a partial one.
- **E1 activity tracks the ignition run by run.** Every ignited run had E1 active. The
  non-ignited runs counted as "E1 active" (34 in WHOLE, 37 in SPARE_E1, across all levels) had
  E1 mean rates of 1.2 Hz or less.
- **13964 itself is quieter when the network ignites:** 31 Hz at low g, 3.8 Hz at g = 1.

## What this means (per the design's declared outcomes)

- **Declared consequence of NOT_SEPARABLE.** E1's engagement and the network ignition fall
  together at every level of 13964's output, with or without its direct synapse onto E1. In this
  model with R1's sizes, DNg100 engages the core only through the ignition. That closes this
  relay line.
- **Reading (a hypothesis, not a result).**
  - DNg100's network has two states: quiet (about 160) or ignited (about 615). 13964's output
    sets the chance of the jump.
  - The core is engaged only in the ignited state, and then it is tonic.
  - So in this rate model, DNg100 cannot reach the oscillating regime that the rhythm-driving DNs
    reach (R5–R7) by turning down this relay.
- **In no case** does R9 show walking, assign a biological role to cell 13964, or change the
  live engine, weights, mappings or motor admission.

## Limits

- **One relay, one output column,** scaled uniformly; only E1's entry spared.
- **R1's sizes only,** at one drive. R8 found no single ignition source with cord-only sizes.
- **Steps of 0.1:** a window narrower than one step could be missed, though the per-seed
  tallies show no intermediate state anywhere.
- **32 seeds per condition;** no sham relay.
- **Reconstructed rate model;** R1's transmitter signs; 68 bodymap MNs.
- **Neural only:** no body or physics. Motor coordinates are unchanged (20/42 admitted, +4
  conditional).
