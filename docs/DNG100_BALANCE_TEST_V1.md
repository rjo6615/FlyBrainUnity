# Rhythm, Step R7: does the E1–E2 rhythm sit on an excitation/inhibition balance? (design)

Designed 2026-11-06. **Status: designed only (no protocol, code or run).** Neural-only
rate-model simulation of R1's isolated network, with R1's sizes.

## Why this step

- **R5:** with R1's sizes at drive 16,000, DNg75_R and DNa02_L drive a reproducible 13–14 Hz
  rhythm that needs E1 and E2 but not I1.
- **R6:** none of the 31 short-loop inhibitory partners of E1/E2 is needed on its own.
  - Silencing all 31 made the network **ignite** under DNg75_R (689 recruited, E1/E2 about
    150 Hz, tonic). That is the same kind of saturated state DNg100 reached in R3.
  - Under DNa02_L, the rhythm survived at half the frequency, with I1 taking over.
- **Hypothesis (from R6):** distributed inhibition holds E1 and E2 at low rates, where they
  oscillate. With too little inhibition relative to drive, the network ignites. If so,
  DNg100's steady output and these DNs' rhythm are two sides of one balance.

R7 tests that hypothesis in both directions:

> **(a) As the inhibitory set's output is reduced, do the rhythm-driving DNs lose their rhythm
> by ignition? (b) As it is increased, does DNg100_L gain a rhythm without igniting?**

**Nature of the intervention (disclosed).** R7 scales synaptic weights. This is a declared,
model-level causal probe of a hypothesis, with every level fixed in advance and every outcome
reported. It is not a parameter change for the live engine, and not a search for settings
that make DNg100 move. A rhythm under boosted inhibition would say something about this
model's dynamics, not that DNg100's inhibition is biologically too weak.

## Conditions (declared; no drive adjustment)

- **Arm:** R1SIZE (R1's sizes), drive 16,000 (R3, R5 and R6's).
- **Inhibitory set S (32 cells):** I1 plus R6's 31 T1 candidates, read from R6's committed
  `result.json`.
- **Intervention:** every outgoing weight of every cell in S (its column in `W[post, pre]`) is
  multiplied by g. All other weights are unchanged.
  - g = 0 removes S's output entirely, which is equivalent to silencing all 32 cells.
  - g = 1 is the unmodified network.
- **Levels:** g ∈ {0, 0.25, 0.5, 0.75, 1, 1.5, 2, 3}.
- **Stimulated:** DNg75_R (129181), DNa02_L (130496) and DNg100_L (10045), each alone.
- **Seeds:** 4001–4032, which are fresh, for every DN × g.
- **Total:** 3 DNs × 8 levels × 32 = 768 simulations (about 8 minutes).
- **Model:** R1's model and R3's replicate function, unchanged except for the scaled W.

## Readout

Per condition, with R3's readout unchanged:
- the MN rhythm score and frequency;
- recruited count (median);
- E1, E2 and I1 trace rhythmicity and mean rates.

A condition is **IGNITED** if its median recruited count is at least 500. That is R2's
`RANGE_MAX`, the upper end of the preprint's recruitment band; R2 found the ignited state at
about 600 or more.

## Criteria (declared now)

**Validity.** At g = 1, DNg75_R and DNa02_L must each score ≥ 0.5, as in R5 and R6. Otherwise
the test is `INVALID`.

**(a) Removal, per rhythm-driving DN.** Scan g = 0.75, 0.5, 0.25, 0 in that order. The
**loss level** is the first g at which the score is not ≥ 0.5.
- `LOST_BY_IGNITION`: at the loss level, the condition is IGNITED and the median E1 trace
  rhythmicity is < 0.5.
- `LOST_OTHER`: the rhythm is lost, but not by ignition.
- `NOT_LOST`: the score stays ≥ 0.5 down to g = 0.

**(a) holds** if both DNg75_R and DNa02_L are `LOST_BY_IGNITION`.

**(b) Boost, DNg100_L.** **(b) holds** if, at any g ∈ {1.5, 2, 3}, DNg100_L's score is ≥ 0.5
**and** the condition is not IGNITED. That is three chances, disclosed. Each level's result is
reported.

**Verdict**

| Verdict | Rule |
|---|---|
| `BALANCE_SUPPORTED` | (a) and (b) |
| `REMOVAL_ONLY` | (a), not (b) |
| `BOOST_ONLY` | (b), not (a) |
| `NOT_SUPPORTED` | neither |
| `INVALID` / `INCONCLUSIVE` | validity failure / integrity failure |

**Reported, not gated**
- The full score, frequency and recruitment curve against g for all three DNs.
- DNg100's E1, E2 and I1 rates against g.
- Whether the rhythm-driving DNs' rhythm changes frequency as g rises above 1.

## Integrity (declared now)

- **I1 sources:**
  - file hashes (R1–R3, R5 and R6 modules; R6's `result.json`);
  - R1's network body-ID hash;
  - S equals I1 plus R6's 31 candidates, all inhibitory in R1's signs.
- **I2 (R6 reproduction, hard gate):** through the scaled-W code path at g = 1, re-run R6's STIM
  for DNg75_R and DNa02_L at seeds 3001–3004 (8 simulations). The results must equal R6's
  stored runs exactly.
- **I3 tests:**
  - the weight scaling on a toy W (only S's columns change; g = 0 matches silencing S in the
    simulator on a toy network);
  - the loss-level scan and its classes;
  - the boost rule and the verdict.
- **I4 completeness:** 768 simulations, plus 8 reproduction simulations.

## Expectations (recorded now)

- **X1:** DNg75_R is `LOST_BY_IGNITION`, as R6's group silencing suggests.
- **X2:** DNa02_L is `LOST_BY_IGNITION` too, reaching ignition at g = 0 once I1 is also removed.
- **X3:** (b) does **not** hold. I expect boosting inhibition to quiet DNg100's network rather
  than make it oscillate, because DNg100's drive is so large.

Wrong expectations are recorded as wrong.

## What each outcome means (declared now)

- **BALANCE_SUPPORTED:** in this model, the same E1–E2 circuit yields a rhythm or a saturated
  steady state depending on the inhibition-to-drive balance. DNg100's lack of a rhythm on our
  wiring would then be a balance effect in the model. That is a model statement; it does not
  justify changing weights in the live engine. Any such idea would need its own separately
  versioned evidence.
- **REMOVAL_ONLY:** too little inhibition destroys the rhythm by ignition, but adding inhibition
  does not rescue DNg100. DNg100's difference would then lie elsewhere, for instance in how its
  drive reaches the core.
- **BOOST_ONLY or NOT_SUPPORTED:** the balance reading from R6 is not supported in this form.
- **In no case** does R7 show walking, validate the preprint's biology, or change the live
  engine, mappings or motor admission.

## Limits

- **R1's sizes only,** at one drive. The rhythm does not appear with cord-only sizes at R3's
  drive.
- **One inhibitory set** (I1 plus 31 short-loop partners), scaled uniformly. Other inhibitory
  cells are unchanged.
- **Eight g levels and 32 seeds;** (b) has three chances.
- **A weight intervention:** a probe of model dynamics, not a fidelity correction or a
  biological claim.
- **Reconstructed rate model;** R1's transmitter signs; 68 bodymap MNs.
- **Neural only:** no body or physics. Motor coordinates are unchanged (20/42 admitted, +4
  conditional).

## Build and run plan (on approval)

1. `docs/evidence/dng100-balance-test-v1/protocol.json`: S, levels, DNs, seeds, criteria,
   hashes, expectations.
2. `malecns_backend/embodiment/dng100_balance_test.py`. It reuses `dng100_engaged_rhythm`
   (replicate, condition_summary, setup), with W replaced by the scaled copy.
3. Unit tests (I3). Then one timing simulation at seed 0 (not a protocol seed), discarded and
   disclosed.
4. Commit and push the preregistration. Run once, evaluate in the same process, and record the
   results, handoff and roadmap.
