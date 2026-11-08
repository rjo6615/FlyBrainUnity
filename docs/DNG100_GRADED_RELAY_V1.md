# Rhythm, Step R9: can relay 13964's two roles be separated by grading its output? (design)

Designed 2026-11-08. **Status: designed only (no protocol, code or run).** Neural-only
rate-model simulation of R1's isolated network, using a declared weight intervention that is
confined to the model copy.

## Why this step

- **R8 (R1's sizes, drive 16,000):** exactly one of DNg100_L's 70 direct partners prevents
  the network ignition: body **13964** (dense 3694, cholinergic, unnamed). With it silenced,
  the median recruited count is 160, against 616.
- **But the core goes silent too:** E1 is active in 1/16 replicates, so no rhythm is unmasked.
- **R7:** the rhythm-driving DNs' E1–E2 rhythm lives in a window. It is lost when the network
  ignites, and DNg100 ignites at every inhibition level.
- **Open point:** silencing is all-or-none. A partial reduction of 13964's output might land
  between "ignited" and "silent", or the two might fall together.

R9 asks:

> **When relay 13964's output strength is graded from 0 to 1 while DNg100_L is stimulated, is
> there a level where the network does not ignite but the core is still engaged, and is the
> core then rhythmic? Does keeping 13964's direct synapse onto E1 at full strength change the
> answer?**

**Already known (disclosed).** Before writing this design I read 13964's wiring from R1's
signed matrix. No simulation was run.
- 13964 has 68 network targets. All of its output is excitatory: 1,086 synapse-weight in total.
- One target is **E1**, with weight 8. It has no synapses onto E2 or I1.
- DNg100_L has no direct synapse onto E1, E2 or I1.
- 13964 is one of 11 two-hop intermediates from DNg100_L to E1 (R2).

## Intervention (declared)

The weight matrix W[post, pre] is copied, and entries in 13964's **column** (its outgoing
synapses) are multiplied by g. This reuses R7's `scaled` helper for WHOLE; SPARE_E1 needs a
helper that leaves one entry unscaled.

| Mode | Scaled entries | Kept at full strength |
|---|---|---|
| WHOLE | all 68 of 13964's outputs | none |
| SPARE_E1 | the 67 outputs other than E1 | 13964 → E1 (weight 8) |

- **Levels g:** 0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0.
- **At g = 1** both modes equal the unmodified W bitwise, so they are R8's STIM condition.
- **At g = 0,** WHOLE equals silencing 13964 only to solver tolerance (as in R7, about 1e-5).
  It is not used as a stand-in for R8's SIL_3694; I2 reproduces that condition directly.
- **Fixed:** R1's sizes, drive 16,000, stimulating DNg100_L. R3's replicate function is used
  unchanged on a model copy carrying the scaled W.
- **Seeds:** 6001–6032 (32 per condition, as in R7, since a rhythm claim is possible).
- **Total:** 2 modes × 11 levels × 32 seeds = 704 simulations, plus 8 reproductions (about 10
  minutes).
- **Scope: R1's sizes only.** R8 found no single ignition source with cord-only sizes, where
  silencing 13964 raised recruitment, so the question does not arise there. This is stated as
  a limit.

This is a model dissection, not a parameter change. Every level is reported, no level is
adopted, and the live engine, weights, mappings and motor admission are untouched.

## Readout and criteria

**Readout** (R3's, per mode and level): median recruited, MN rhythm score and frequency, E1, E2
and I1 active fractions, median trace rhythmicity and mean rates.

**Per level**
- **IGNITED:** median recruited ≥ 500 (R2's `RANGE_MAX`, as in R7 and R8).
- **CORE_ENGAGED:** E1 active fraction ≥ 0.5.
- **RHYTHMIC:** MN score ≥ 0.5 **and** median E1 trace rhythmicity ≥ 0.5 (R8's unmasked rule).

**Validity (both must hold, or the step is `INVALID`)**
- g = 1 is IGNITED, as in R8's STIM.
- WHOLE at g = 0 is not IGNITED, as in R8's SIL_3694.

**Class per mode** (first matching row)

| Class | Rule |
|---|---|
| `RHYTHM_WINDOW` | some g is not IGNITED and RHYTHMIC (all such levels are listed) |
| `SEPARABLE_NO_RHYTHM` | some g is not IGNITED and CORE_ENGAGED, but none is RHYTHMIC |
| `NOT_SEPARABLE` | no g is both not IGNITED and CORE_ENGAGED |

**Step verdict:** `RHYTHM_WINDOW` if either mode has it; otherwise `SEPARABLE_NO_RHYTHM` if
either mode has it; otherwise `NOT_SEPARABLE`. Both modes' classes are reported.

**Reported, not gated**
- The ignition transition per mode: the highest g that is not IGNITED, and whether the levels
  that are not IGNITED form one contiguous block starting at 0.
- 13964's own mean rate at each level.
- DNg100_L's rate, and the full curves.

## Integrity (declared now)

- **I1 sources:**
  - file hashes (R1–R8 modules; R7 and R8 `result.json`);
  - R1's network body-ID hash;
  - 13964's dense index resolved from its **body ID**, and DNg100_L's from body ID 10045;
  - the wiring above re-checked from W: weight 52 from DNg100_L, 68 targets, weight 8 onto E1,
    1,086 total.
- **I2 (reproduction, hard gate):** 8 simulations must equal the stored runs exactly (score,
  recruited, core activity).
  - Seeds 4001–4004: R7's DNg100_L runs at g = 1, through the WHOLE g = 1 model. This also
    confirms that g = 1 is the unmodified W.
  - Seeds 5001–5004: R8's R1SIZE SIL_3694 runs, by silencing 13964 on the unmodified model.
- **I3 tests:**
  - the SPARE_E1 helper scales exactly the declared entries;
  - both modes give W unchanged at g = 1;
  - WHOLE at g = 0 matches silencing to 1e-4;
  - the per-level labels, validity and class order.
- **I4 completeness:** 704 simulations, plus the 8 reproductions.

## Expectations (recorded now)

- **X1:** WHOLE is `NOT_SEPARABLE`. E1 went silent when 13964 was silenced, even though 10
  other two-hop routes to E1 remain. So I expect E1's engagement to need the ignition itself,
  and to fall with it.
- **X2:** SPARE_E1 is `NOT_SEPARABLE` too. A single 8-weight synapse is small next to the
  input an ignited network gives E1.
- **X3:** no level in either mode is `RHYTHM_WINDOW`.

Wrong expectations are recorded as wrong.

## What each outcome means (declared now)

- **RHYTHM_WINDOW:** in this model, a partial reduction of one relay's output lets DNg100 drive
  a rhythmic core without the network ignition. That would locate the difference between
  DNg100 and the rhythm-driving DNs at the strength of one connection. It is a model
  statement only: it gives cell 13964 no biological role and sets no weight anywhere.
- **SEPARABLE_NO_RHYTHM:** the two roles can be separated, but the core DNg100 then drives is
  not rhythmic. Something beyond the ignition would then distinguish DNg100 from the
  rhythm-driving DNs.
- **NOT_SEPARABLE:** E1's engagement and the network ignition fall together at every level.
  In this model with R1's sizes, DNg100 engages the core only through the ignition. That
  closes this relay line.
- **INVALID:** recorded as found. R9's assumptions would need revisiting.
- **In no case** does R9 show walking, assign biological roles, or change the live engine,
  weights, mappings or motor admission.

## Limits

- **One relay, one output column,** scaled uniformly; only E1's entry can be spared. No other
  partner or combination is graded.
- **R1's sizes only,** at one drive. R8 found the single source does not exist with cord-only
  sizes.
- **11 levels** at steps of 0.1. A window narrower than one step could be missed.
- **32 seeds** per condition. There is no sham relay: g = 1 is the baseline.
- **Reconstructed rate model;** R1's transmitter signs; 68 bodymap MNs.
- **Neural only:** no body or physics. Motor coordinates are unchanged (20/42 admitted, +4
  conditional).

## Build and run plan (on approval)

1. `docs/evidence/dng100-graded-relay-v1/protocol.json`: modes, levels, seeds, criteria,
   wiring checks, hashes, expectations.
2. `malecns_backend/embodiment/dng100_graded_relay.py`. It reuses:
   - `dng100_balance_test`: `scaled`, `with_W`;
   - `dng100_engaged_rhythm`: setup, replicate, condition_summary;
   - `dng100_control_rhythm`: `slim`.
3. Unit tests (I3). Then one timing simulation at seed 0 (not a protocol seed), discarded and
   disclosed.
4. Commit and push the preregistration. Run once in the background, evaluate in the same
   process, and record the results, handoff and roadmap.

## Build-time notes (before any protocol simulation)

- No amendments to the design's modes, levels, seeds, criteria or expectations. The protocol is
  `protocol.json` (sha de66566b…).
- **Relay trace.** Each protocol run also records 13964's own trace by adding it as an extra
  key (`RELAY`) to the cells R3's replicate function reports. It gates nothing, and the
  simulation is unchanged; I2 uses the plain core set.
- **Plumbing.** One unscaled R1SIZE DNg100_L simulation at seed 0 (not a protocol seed) was
  timed (0.72 s). Its score and rates were not printed.
- **Test fix before registration.** The first test draft built dicts with float keyword keys,
  which Python rejects. It was a test-code error, fixed before any protocol simulation.
