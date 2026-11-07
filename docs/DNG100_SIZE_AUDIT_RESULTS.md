# Rhythm, Step R1b (neuron-size scaling audit): results

Run 2026-11-06 under the preregistered protocol `docs/evidence/dng100-size-audit-v1/protocol.json`
(sha 3813e577…). The protocol, module and tests were committed and pushed in d85e4ac before any
neck plane, cable fraction or size ratio was computed.
- **Run:** one command, a few seconds, run once.
- **Output:** `docs/evidence/dng100-size-audit-v1/run/result.json` (sha c9c2424a…), with
  `console.txt` alongside.
- **Design:** `DNG100_SIZE_AUDIT_V1.md`, including its build-time amendments.

This was a **structure-only** computation on local data (skeletons and sizes). No neural
simulation was run, and no engine, calibration, mapping or R1 evidence was changed.

## Verdict: SIZE_MISMATCH_MATERIAL, through (b), not (a)

| Check | Rule | Observed | Met |
|---|---|---|---|
| G1 neck plane | misclassified < 1 % | z* = 462 µm (minimisers 459–465); 78 of 4,619,435 vertices (0.0017 %) | yes |
| (a) DNg100_L | ρ ≥ 2 | **1.35** | no |
| (b) R1 network DNs | median ρ ≥ 2 | **2.36** (904 DNs) | yes |

| Expectation | Outcome |
|---|---|
| X1 (MATERIAL through (a), DNg100_L) | **wrong**: the label is MATERIAL, but through the other DNs, not DNg100 |

**Integrity.** All pass:
- I1: every source hash and the cache fingerprints matched; R1's network body-ID hash matched
  (cdcfcd23…).
- I2: skeleton N = meta N = 165,122; all 20 soma checks inside (5 cells, 15 drawn).
- I3: 7 synthetic tests passed before the run (14 together with R1's).
- No neuron in R1's network lacks cable; no ρ is infinite.

## What was measured

**Medians.** m_R1 = 542,747,200; m_VNC = 507,457,760 (ratio 0.935). So every cord-intrinsic neuron
(f = 1) has ρ = 0.935: R1 *under*-scaled them by about 7 %, a minor difference.

**The five cells**

| Cell | Cable (µm) | Cord fraction f | s_R1 | s_VNC | ρ |
|---|---|---|---|---|---|
| DNg100_L | 6,118 | 0.69 | 30.7 | **22.7** | 1.35 |
| DNg100_R | 6,642 | 0.61 | 30.5 | 20.0 | 1.52 |
| E1 (IN17A001_L) | 790 | 1.00 | 8.8 | 9.5 | 0.93 |
| E2 (INXXX466_L) | 578 | 1.00 | 5.1 | 5.4 | 0.93 |
| I1 (IN16B036_L) | 436 | 1.00 | 2.5 | 2.7 | 0.93 |

**R1's network by class** (median and 10th–90th percentile)

| Class | n | f | ρ |
|---|---|---|---|
| DNs | 904 | 0.40 (0.24–0.57) | **2.36** (1.64–3.84; max 7.56) |
| ANs | 105 | 0.79 (0.69–0.88) | 1.19 (1.07–1.36) |
| Cord premotor (vnc_*) | 1,032 | 1.00 | 0.93 |
| MNs | 68 | 1.00 | 0.93 |
| Other | 2 | 0.69 | 1.35 |

Network neurons with s > 20: **49 under R1, 20 under the cord-only definition.**

Whole dataset (descriptive): DNs f median 0.38 (n = 1,314); ANs 0.72 (n = 1,846); both include
some neurons with f = 0.

## Reading (within the declared limits)

- **The label is MATERIAL, as preregistered.** R1 over-scaled most of its network's descending
  neurons by a median of 2.4× relative to the preprint's cord-only definition. That is an
  implementation-fidelity difference in R1, not a biological finding.
- **But it is not the stimulated cell.** DNg100 is mostly in the nerve cord (f = 0.69), so its
  ρ is only 1.35 and its cord-only s is still 22.7. X1 was wrong. DNg100's own low sensitivity in
  R1 is therefore largely **not** explained by the brain-arbor mismatch. R1's drive rule already
  raised I_stim 4–8× (to 1,000–2,000), which more than covers a 1.35× difference.
- **Where the mismatch matters.** The over-scaled DNs are the 904 other DNs that feed R1's
  premotor neurons. In a DNg100-only stimulation they receive input only through recurrence, so
  correcting them may change little. This is a reading, not a result.

**Declared consequence.** The design said MATERIAL leads to a preregistered **R1 v2** using
size_VNC for DNs and ANs, with R1's evidence kept as recorded. Given the reading above, R1 v2
is unlikely to engage the core by itself, and the descriptive recruitment map stays the more
direct next question. Which to do first is the user's decision.

## Limits

- Cable length stands in for volume; thick axons in the neck connective could make the true f
  differ. If DN axons in the connective are thick, true f would be higher and ρ lower.
- The display skeletons are coarse, so cable lengths are approximate.
- A single flat plane approximates the neck, though it separated intrinsic brain and cord
  vertices almost perfectly (0.0017 % misclassified).
- `neuron_size.bin` has no documented source or units, so only the relative definition is
  audited, not absolute agreement with MANC volumes (MANC is not used; local-only project).
- Structure only: no simulation, no rhythm claim, no change to R1's evidence or the live engine;
  motor coordinates unchanged (20/42 admitted, +4 conditional).
