# Antennal gravity sense, Step D: does a zone-crossing tilt give direction-specific leg-MN responses? (design, V1)

Designed 2026-11-05. This is the design only. No code exists, nothing has run, and no
protocol is locked. On approval, the rules below are copied into
`docs/evidence/jo-zone-crossing-v1/protocol.json`, hash-locked in code, and committed
before any arm runs.

Related documents:
- Step B, `ANTENNAL_GRAVITY_ENCODER_RESULTS.md` (`ENCODER_READY`);
- Step C, `ANTENNAL_GRAVITY_LIVE_RESULTS.md` (G1 CONSISTENT, FLIP WEAK, d ≤ 0 in both
  tilts);
- Step C2, `JO_OPERATING_POINT_RESULTS.md` (drift = body posture; neck sag opposes;
  antenna joints about 0).

## Why this step

**In Step C, d never became positive.**
- The live body sits about 4° nose-up relative to gravity.
- Its posture response lowers d further after either tilt.

So each assignment modulated only one zone: E under G1 and C under FLIP. Step C's
comparison was therefore E route against C route. It did not test what a gravity sense must
supply for balance, which is **opposite JO zones signalling opposite tilt directions.**

Step C2 measured where the operating point comes from. This step places the tilt so that d
**crosses zero**.
- At LEVEL, d is clearly negative (one zone active).
- After a 20° nose-down tilt, d is clearly positive (the other zone active).
- In both assignments the tilt therefore switches the active zone.

## Expected operating point (stated from measurements, verified as a condition)

| Arm tilt | Basis | Expected window d |
|---|---|---|
| LEVEL (no gravity change) | Step C2 pre-tilt d in OFF arms, −0.161 to −0.225 at 500 ms | about −0.18. Not measured after 500 ms without a tilt. |
| DOWN20 (gravity rotated −20° about world y at state 5005) | Step B geometry at 20° nose-down = +0.195. Step C2 posture terms at 10° DOWN: ROOT −0.057, NECK +0.032, about −0.025 net. | about +0.17. The posture response at 20° is unmeasured. |

**These are estimates. They become an integrity condition on the OFF arms** (rule O1 below).
If the measured operating point misses, the run is `INCONCLUSIVE_OPERATING_POINT`. The
operating point is a property of the input, not an outcome, so this is not tuning against
the result.

Implied JO rates (Step B rule, 120 Hz × max(±d, 0)):

| | LEVEL | DOWN20 |
|---|---|---|
| G1 (C = +d, E = −d) | E ≈ 21 Hz, C 0 | C ≈ 20 Hz, E 0 |
| FLIP (E = +d, C = −d) | C ≈ 21 Hz, E 0 | E ≈ 20 Hz, C 0 |

## Question and predictions (recorded before the run)

**Q1.** Under each assignment, does the zone-crossing tilt contrast (DOWN20 − LEVEL), beyond
the matched JO-withheld contrast, give a leg-MN pattern that is consistent across seeds?

Under both assignments the E drive changes by about 20 Hz:
- under G1 it goes off (about −21 Hz);
- under FLIP it comes on (about +20 Hz).

Step C found the E route strong and the C route weak. That gives these predictions:
- **P1:** G1 is `JO_TILT_PATTERN_CONSISTENT`.
- **P2:** FLIP is `JO_TILT_PATTERN_CONSISTENT`.
- **P3:** r_GF < 0. The two assignments change the E drive in opposite directions, so their
  seed-mean contrasts should anti-correlate.
- **P4:** the direct JO-target DNs (DNp73, DNbe001) have opposite-signed DOWN20 − LEVEL rate
  changes in G1 versus FLIP, in all 6 seeds.

If a prediction is wrong, it is recorded as wrong. A wrong P3 or P4 would mean the C route,
or the tonic history, matters more than Step C suggested.

**Not tested and not claimed:**
- the true zone sign. No motor statistic can identify it.
- balance or a corrective response. Whether any pattern opposes the tilt is a later,
  functional question.

## Context and arms (reuse Step C unchanged except the tilt set and seeds)

The context is the same as Step C:
- the push-response N context (assisted posture, hair plates, 20 live-v3 channels, no coxa
  channel, no force);
- the JO encoder from Step B, with the 764-neuron common schedule;
- JO withheld in OFF;
- the gravity rotation applied after stored state 5005;
- the 520–2,000 ms window, leg-MN pools, measures, pool-inclusion rule and statistics,
  all as in Step C.

| Item | Value |
|---|---|
| Arm types | OFF, G1, FLIP |
| Tilts | LEVEL (gravity unchanged, still recorded at every state); DOWN20 (φ = −20°) |
| Seeds | 19–24 (unused so far) |
| Per-seed order | OFF_LEVEL, OFF_DOWN20, G1_LEVEL, G1_DOWN20, FLIP_LEVEL, FLIP_DOWN20 |
| Reproduction arm | REPRO_N0_7 first, which must equal the local N0_7 raw arm exactly (as in Step C) |
| Total | 37 fresh-process arms, about 3 h; each runs once and is evaluated once |

Why 20°:
- it lies inside Step B's validated ±30° grid;
- the friction coefficient (1.0) is far above tan 20° ≈ 0.36;
- with Step C2's measured posture terms, it is the smallest step that is expected to make d
  clearly positive (+0.17 against a 0.05 margin).

It was chosen before any arm ran and will not be changed after.

## Integrity (all required, else `INCONCLUSIVE_INTEGRITY` with no labels)

These are Step C's I1–I7, with the tilt set replaced:
1. **I1 Complete.** All 37 arms are COMPLETE, with 20,001 samples and 4,000 ticks.
2. **I2 Reproduction.** REPRO_N0_7 equals N0_7.
3. **I3 Common random numbers.** Within each seed, all six arms have identical schedules and
   uniforms.
4. **I4 Prefixes.**
   - Within each seed and assignment, LEVEL and DOWN20 are identical through state 5005.
   - All six arms of a seed have equal state-0 qpos.
5. **I5 Tilt record.**
   - LEVEL records (0, 0, −9810) at every state.
   - DOWN20 records (0, 0, −9810) through 5005 and exactly R_y(−20°)·(0, 0, −9810) from
     5006 on.
   - No applied wrench or force occurs.
6. **I6 JO delivery.**
   - JO is delivered only in G1 and FLIP, and only to the four sets.
   - The rates equal `zone_rates(d, assignment)` at every tick.
   - Sign check: at the first tick after 500.5 ms, d(DOWN20) > d(LEVEL) on both sides for
     each seed and assignment.
7. **I7 Seeds.** Every arm records its seed, and the tick-1 uniforms of seeds 19–24 differ.

**Operating point (O1; failure gives `INCONCLUSIVE_OPERATING_POINT`, no labels).** In every
OFF arm, the window-mean d per side must be:
- **> +0.05** in OFF_DOWN20;
- **< −0.05** in OFF_LEVEL.

The ON arms' d values are reported, not gated, because their posture can respond to the
neural input.

**Physical precondition (`INCONCLUSIVE_PHYSICS`, no labels).** In every OFF arm, the body
tilt relative to gravity stays below 45° at every stored state in the window.

## Measures and labels (Step C rules, with LEVEL in place of UP)

- **Δ_a,s** = rate(a_DOWN20_s) − rate(a_LEVEL_s) per included pool.
- **S_a,s** = Δ_a,s − Δ_OFF,s for a ∈ {G1, FLIP}.
- **ρ_a** is the mean pairwise seed correlation of S_a.
- **p_a** is the exact sign-flip p over 64 sign vectors (minimum 1/32).

| Label | Rule |
|---|---|
| `JO_TILT_PATTERN_CONSISTENT` | ρ > 0 and p ≤ 1/32 |
| `JO_TILT_PATTERN_WEAK` | ρ > 0 and p ≤ 0.25 |
| `NO_CONSISTENT_JO_TILT_PATTERN` | otherwise |

**Prediction checks.** P1–P4 are each recorded as `HELD` or `NOT_HELD` by these rules:
- P1: the G1 label is CONSISTENT;
- P2: the FLIP label is CONSISTENT;
- P3: r_GF < 0;
- P4: sign(G1 DOWN20 − LEVEL) ≠ sign(FLIP DOWN20 − LEVEL) for both DNp73 and DNbe001, in
  all 6 seeds, with neither difference equal to 0.

**Reported, not labelled:**
- window d per arm and side;
- the posture terms (body pitch and roll relative to gravity) and the first ON/OFF physical
  difference;
- mean |Δ| and ‖S‖;
- per-pool medians with seed sign counts;
- DOWN20 − LEVEL contrasts for the five direct DNs (DNp73, DNp18, DNg29, pIP1, DNbe001);
- the tonic 0–500 ms MN rates;
- per-side contrasts, with the reconstruction-asymmetry label (no roll claims).

## What each outcome means (declared now)

- **Both CONSISTENT with r_GF < 0:** switching the active JO zone with tilt direction gives
  reproducible, assignment-dependent leg-MN patterns. The E/C routes act as a signed
  channel for tilt direction in this reconstruction. That is the information structure a
  balance response would need. It is not shown to be corrective.
- **Only one assignment CONSISTENT, or r_GF ≥ 0:** the effect of zone switching is not a
  simple sign flip. The tonic history (the zone active before the tilt) or the C route
  shapes it. This is reported as it stands.
- **Neither CONSISTENT:** a 20° zone-crossing tilt through this encoder gives no
  reproducible leg-MN pattern beyond the other senses over 1.5 s. The causes are not
  distinguished.
- **`INCONCLUSIVE_OPERATING_POINT`:** the estimate from Step C2 did not hold at 20°. This
  is recorded together with the measured window d. A new versioned protocol would be needed
  for any other tilt; no rerun will be made under this one.

## Limits

- Step C's limits all apply:
  - the transduction is modelled, with an arbitrary G1 label;
  - the tilt is an idealised gravity step;
  - ON arms carry tonic JO from t = 0, so the OFF subtraction works only to first order;
  - coxa MNs are read out only;
  - the right-side JO reconstruction is sparser.
- **The tilt directions are not symmetric.** LEVEL against DOWN20 compares no tilt with a
  tilt. Some of the contrast is a generic response to tilting, which the OFF subtraction
  removes only to first order.
- **The passive neck droop (+0.033 in d) is present in every arm,** as measured in C2.
- No motor coordinate status changes: 20/42 admitted, +4 conditional.

## Build and run plan (on approval)

1. Write `docs/evidence/jo-zone-crossing-v1/protocol.json`.
2. Write `malecns_backend/live/jo_zone_crossing.py`. It reuses `antennal_gravity_live`'s
   Trial, measures, statistics and integrity code. Only the tilt set, seeds, O1 and the
   prediction checks are new; the Step C module itself is unchanged.
3. Write synthetic tests: the tilt set and gravity record, O1 pass and fail, the P1–P4
   rules, label boundaries, and that LEVEL records unchanged gravity.
4. Run a plumbing smoke (scratch, discarded unread except for exit status).
5. Commit and push the preregistration, run the 37 arms once in the background, evaluate
   once, and record the results, the handoff and the roadmap.
