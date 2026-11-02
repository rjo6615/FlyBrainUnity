# Hair-plate relay interneurons — causal intervention design (V1)

Designed 2026-11-02, after the RF excitation result was merged (PR #311). **Built and run
once 2026-11-02; results in `RF_RELAY_INTERVENTION_RESULTS.md`.** This document
is the design only. No code has been written and nothing has run. The protocol JSON,
the adapter, the evaluator and the tests are written and hash-locked at build time, and
committed before any arm runs.

## Why

The RF excitation replay (`RF_COXA_EXCITATION_RESULTS.md`) was passive. It found that
LF's extra excitation (8.6) comes mainly from left-side interneurons of three types:
IN03A066, IN03A075 and IN03A080. These sit directly downstream of the LF hair plates.
Their right-side copies are wired onto RF coxa MNs but stay silent (0 Hz).

That is a correlation in one run. It suggests a causal story that has not been tested:

- **Necessity:** the left relay contributes to LF coxa MN firing.
- **Sufficiency:** activity in the right relay would raise RF coxa MN firing.

**The three types were chosen after seeing the observational result.** This design
tests that post-hoc hypothesis prospectively, with controls.

**These are engineering interventions.** They test causal roles inside the model. They
are not biological claims, and they are not a fix. Nothing here changes weights,
thresholds, mappings, the encoder or the motor interface. No arm admits a coxa channel.

## Context (fixed)

Every arm is the Step C A_ON condition, unchanged:

- assisted posture, hair plates delivered;
- the same seed, external schedule and encoder;
- the live-v3 session with 20 channels and no coxa channels;
- 20,000 physics steps and 4,000 neural ticks.

Each arm runs once, in a fresh process. The analysis window is 520–2000 ms (the Step C
convention).

The Step C Trial already draws its uniforms for all 444 schedule slots every tick, so
CNS random-number use does not depend on activity. Both interventions are layered on
that Trial without touching the random-number stream.

- **Silencing** uses the engine's existing `transmission_withheld_indices`. The withheld
  neurons still integrate and spike, but their events are not delivered.
- **Injection** adds forced events, with the engine's own forced-event semantics (reset,
  refractory period, counted as fired). They come from a precomputed Poisson train and
  are OR-ed into the Trial's `event_trials` mask. An event is delivered only if the
  neuron is not refractory, matching sensory forcing. The train comes from an
  independent generator seeded by the protocol (`numpy.random.default_rng(20261102)`),
  and is precomputed and hashed before the run. The CNS generator is never used.

## Neuron sets (deterministic rules, frozen at preregistration)

Every count below uses floored edges (≥ 6 synapses), excitatory sign, and the V1 sets
(Step A SNpp45 sets and the posterior coxa MN pools).

| Set | Rule |
|---|---|
| **LEFT_RELAY** | Type IN03A066, IN03A075 or IN03A080; left side; at least one edge from an LF SNpp45; and at least one excitatory edge onto an LF posterior coxa MN |
| **RIGHT_RELAY** | Same three types; right side; at least one excitatory edge onto an RF posterior coxa MN (hair-plate input not required) |
| **LEFT_SHAM** | Same size as LEFT_RELAY. Left-side neurons whose type starts with `IN03A` (same hemilineage), not in LEFT_RELAY, with no edge onto any replayed coxa MN in any leg. For each relay neuron in dense order, the unused candidate whose saved A_ON window rate is closest (ties: lowest dense index) |
| **RIGHT_SHAM** | The same rule on the right side, matched to RIGHT_RELAY |

**Injection rate.** Each injected neuron gets the window-mean rate of the LEFT_RELAY
neurons of its own type, from the saved Step C A_ON. RIGHT_SHAM neuron i receives
exactly the train of RIGHT_RELAY neuron i.

The resolved body IDs, dense indices, rates and train hash are written into the
protocol before it is committed. If any set comes out empty, or a sham set cannot be
filled, the build stops with `PROTOCOL_NOT_BUILDABLE` and nothing runs.

## Arms

| Arm | Intervention | Tests |
|---|---|---|
| C0 | none | Must reproduce saved Step C A_ON exactly |
| L_SIL | withhold transmission of LEFT_RELAY | necessity (LF) |
| L_SHAM | withhold transmission of LEFT_SHAM | non-specific effect of removing similar activity |
| R_INJ | inject into RIGHT_RELAY | sufficiency (RF) |
| R_SHAM | inject the same trains into RIGHT_SHAM | non-specific effect of adding similar activity |

## Integrity (all required, else `INCONCLUSIVE_INTEGRITY`, with no labels)

1. **I1 Completeness.** Every arm is COMPLETE, with 20,001 samples and 4,000 ticks.
2. **I2 Common random numbers.** In every arm, the per-tick `uniforms_sha256` and the
   external schedule are identical to C0's.
3. **I3 C0 reproduction.** C0 equals saved A_ON in fired, uniforms, hair-plate
   deliveries and qpos at every tick and sample.
4. **I4 Intervention verified.** These checks are run per tick.
   - **Silencing arms:** every spike of a withheld neuron is recorded as withheld and
     delivered nowhere, and no other neuron is withheld.
   - **Injection arms:** every injected event in the record is a scheduled event on an
     available neuron, and every scheduled, available event was injected. Events
     blocked by refractoriness are counted and reported.
5. **I5 Prefix identity.** Each arm equals C0 in fired and qpos at every tick before its
   first intervention event (the first withheld spike, or the first injected event).

## Measures (window 520–2000 ms)

- **Pool rate.** The posterior coxa MN pool rate per leg (V1 pools) and the best-driven MN
  rate (V1 `best_mn`). The primary legs are LF for L arms and RF for R arms.
- **Spillover.** The pool rates of all other legs, and the rates of the 20 admitted v3
  motor channels' MNs.
- **Sensory confound.** The window-mean hair-plate rate of the primary leg against C0.
  If it changes by more than 10 %, the label is flagged `SENSORY_CONFOUNDED`. The flag
  is reported with the label, not instead of it.
- **Descriptive measures:**
  - the excitation decomposition of each primary best MN, using the V1/V2 replay and
    attribution functions unchanged (the replay must again match the recorded spikes);
  - the first physical divergence from C0;
  - body tilt.

## Labels (decided by these rules only)

Ratios are pool rate in the arm divided by C0.

**Q_NEC: is the left relay necessary?** (LF pool)

| Label | Rule |
|---|---|
| `NONSPECIFIC` | L_SHAM ratio < 0.8 (the control itself changes LF). This takes precedence |
| `NECESSARY` | L_SIL ratio ≤ 0.5 |
| `CONTRIBUTES` | 0.5 < L_SIL ratio ≤ 0.8 |
| `NOT_NECESSARY` | L_SIL ratio > 0.8 |

**Q_SUF: is the right relay sufficient?** Increases are in Hz over C0, on the RF pool.

| Label | Rule |
|---|---|
| `NONSPECIFIC` | R_SHAM increase ≥ 2 Hz. This takes precedence |
| `RESCUED` | R_INJ rate ≥ 0.5 × C0's LF pool rate |
| `PARTIAL` | R_INJ increase ≥ 5 Hz, but not RESCUED |
| `NO_EFFECT` | Otherwise |

## Predictions (expectations, not criteria)

- **Q_NEC: CONTRIBUTES.** LF's direct hair-plate drive (19.6) is well above g*, so LF
  should keep firing without the relay. A drop of 20–50 % is plausible.
- **Q_SUF: PARTIAL.** The right relay's weight onto RF's best MN (about 102 summed over the three
  types) is comparable to the left relay's onto LF's (about 107). Injecting left-like rates should add excitation, roughly
  doubling it on top of RF's hair-plate drive of about 6. Full rescue is uncertain,
  because the injected rates are type means and RF's hair-plate drive is subthreshold.

## Limits

- One seed, assisted posture, open-loop coxa (coxa MNs move nothing).
- An intervention that changes motor output can change physics and hair-plate input.
  That is an outcome, flagged by the sensory confound check.
- Silencing by withheld transmission and injection by forced events are engineering
  manipulations, not models of biological manipulations.
- A RESCUED or NECESSARY label shows a causal role in this model only. It does not
  settle anatomy versus reconstruction, and it admits no coordinate. Motor coverage
  stays 20/42.

## Build and run plan (on approval)

1. **Resolve and freeze.** Resolve the neuron sets and the injection trains, and write
   `docs/evidence/rf-relay-intervention-v1/protocol.json`. It includes the resolved IDs,
   rates and train hash.
2. **Write the code.** `malecns_backend/live/rf_relay_intervention.py` holds the adapter
   (Trial subclass with silencing and injection hooks), the arm runner and the
   evaluator, reusing Step C, V1 and V2 functions. `tests/test_rf_relay_intervention.py`
   holds synthetic tests: set rules, train determinism, the injection OR-mask leaving
   the RNG untouched, a withheld-transmission audit on a tiny engine network, and the
   label rules.
3. **Smoke test.** A short engineering smoke test (100 steps, C0 and one arm, plumbing
   only, discarded). Then commit and hash-lock.
4. **Run.** Each of the five arms once, in a fresh process (about 5 minutes each), then
   the evaluation once.
5. **Record.** Commit the report, the console logs and the results write-up. The raw
   arms stay local.
