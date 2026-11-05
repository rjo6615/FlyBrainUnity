# Antennal gravity sense, Step C: does JO tilt information reach leg motor neurons? (design, V1)

**Status (2026-11-05):** preregistered (0ef9dbe, protocol 05655b40), run once, evaluated
once: `INTEGRITY_ACCEPTED`; G1 `JO_TILT_PATTERN_CONSISTENT` (ρ 0.70, p 1/32), FLIP
`JO_TILT_PATTERN_WEAK` (ρ 0.06, p 0.22), r_GF +0.39. See `ANTENNAL_GRAVITY_LIVE_RESULTS.md`.

Designed 2026-11-05. This is the design only. No code exists, nothing has run, and no
protocol is locked. On approval, the rules below are copied into
`docs/evidence/antennal-gravity-live-v1/protocol.json`, hash-locked in code, and committed
before any arm runs.

Related documents:
- the parent track design, `ANTENNAL_GRAVITY_SENSE_V1.md`;
- Step A (`IDENTITY_READY`), `ANTENNAL_GRAVITY_IDENTITY_RESULTS.md`;
- Step B (`ENCODER_READY`), `ANTENNAL_GRAVITY_ENCODER_RESULTS.md`.

## Question

The body is tilted by a sustained 10° pitch, either nose-down or nose-up. The Step B encoder
feeds the JO C/E sets. Does the difference in leg motor-neuron (MN) activity between
nose-down and nose-up contain a JO-attributable part with the same pattern across CNS
seeds?

This is an information-routing question. It is **not** a balance test, makes no admission,
and claims no corrective reflex.

## Context (reused unchanged)

The context is the push-response **N** context, the same as the arms in
`COXA_PUSH_REPLICATION_V1.md`:
- hair-plate Step C arm A_ON (assisted posture, hair-plate encoder delivering);
- the 20 live-v3 motor channels and tibia proprioception;
- no coxa channel and no push;
- 20,000 physics and 4,000 neural transitions (2 s);
- the seed applied as `brain.rng = default_rng(seed)` at attach.

The new module subclasses `coxa_push_response.Trial`, with kind N and push 0. It adds only
the JO input and the tilt.

## Interventions

**JO input.** Step B's `AntennalGravityEncoder` drives the four Step A sets (320 neurons)
every neural tick, through the same instance-local input boundary as the hair plates. The
Bernoulli equation is unchanged.

The external schedule is proprioception (392) + hair plates (52) + JO (320), and it is the
same in every arm. In OFF arms the JO neurons are withheld at the CNS boundary. Every arm
therefore draws identical uniforms (common random numbers). Because the schedule is longer,
the RNG stream differs from earlier N arms. That is expected, and the reproduction arm below
covers the environment.

**Tilt.** At stored state 5,005 (500.5 ms, the Step C boundary), `model.opt.gravity` is
rotated by 10° about world y and held to the end:
- **DOWN:** gravity is rotated by −10°. In the body's frame this equals pitching the body
  10° nose-down.
- **UP:** gravity is rotated by +10° (nose-up).

Rotating gravity is the same as rigidly tilting the floor and the fly together, with no
rotational transient: an idealised step tilt. It changes every gravity-dependent sense
(contact, loads, hair plates, chordotonal organs) as well as JO, which is why the OFF arms
are the matched baseline.

**Why 10° (declared, not tuned).**
- It lies inside Step B's validated ±30° grid, and Step B gives a JO drive difference of
  about 0.17 per 10°. Nose-down d ≈ +0.03; nose-up d ≈ −0.31.
- It is small enough that the friction coefficient (1.0) is far above the slip threshold
  (tan 10° ≈ 0.18).
- It is about the size of the existing assisted-posture tilt (4–10°).

The MuJoCo model record must otherwise stay unchanged. The gravity vector is recorded
separately at every stored state.

## Arms

For each seed, the six arms run in this order:

> OFF_UP, OFF_DOWN, G1_UP, G1_DOWN, FLIP_UP, FLIP_DOWN

- **OFF:** JO withheld.
- **G1:** C = +d, E = −d.
- **G1_FLIP:** the zones are swapped.

**Seeds are 13, 14, 15, 16, 17 and 18.** None has been used before (seeds 1–12 have).

**One reproduction arm runs first.** `REPRO_N0_7` reruns replication arm `N0_7`, and must
equal that local raw arm (hash 1a94e5ad…) over the whole run.

That is 6 × 6 + 1 = **37 fresh-process arms, about 3 h**. Each runs once, and is evaluated
once.

## Integrity (all required, else `INCONCLUSIVE_INTEGRITY` with no labels)

1. **I1 Completeness.** All 37 arms are COMPLETE, with 20,001 samples and 4,000 ticks.
2. **I2 Reproduction.** `REPRO_N0_7` equals `N0_7` exactly, using the replication I2
   comparison.
3. **I3 Common random numbers.** Within each seed, all six arms have identical per-tick
   uniforms and an identical external schedule.
4. **I4 Prefixes.**
   - Within each seed and assignment, UP and DOWN are identical through state 5,005
     (qpos, commands and spikes).
   - The OFF, G1 and FLIP arms of a seed share their state-0 physical state.
5. **I5 Tilt record.**
   - Gravity is (0, 0, −9810) through state 5,005, and exactly the declared rotated vector
     from 5,006 on.
   - No other model-record change occurs.
   - No external force is applied.
6. **I6 JO delivery.**
   - JO events are delivered only in G1/FLIP arms, and only to the four Step A sets.
   - Each tick's JO rates equal the Step B rule applied to that tick's state, under the
     arm's assignment.
   - **Sign sanity check.** At the first tick after 5,005, d(DOWN) > d(UP) on both sides,
     in every ON pair.
7. **I7 Seeds.** Every arm records its seed. The tick-1 uniforms of seeds 13–18 differ
   from each other.

**Physical precondition** (`INCONCLUSIVE_PHYSICS`, no labels). In every OFF arm, the body's
tilt relative to the current gravity direction must stay below 45° throughout the window,
so there is no rollover. Tilt for ON arms is reported, not gated, because divergence after
the neural intervention is an outcome.

## Measures

**Window.** 520–2,000 ms, which leaves 19.5 ms after the tilt onset. This is the
hair-plate Step C window.

**Pools.** Leg MN pools by leg × actuator class, parsed from the bodymap muscles as in
`hair_plate_posture.mn_sets`. That gives 6 legs × the classes present. A pool is **included**
if it has at least one spike in the window in any of the 36 seed arms. This rule ignores
sign and is fixed now.

**Tilt contrast.** For each arm type a ∈ {OFF, G1, FLIP} and seed s, the vector over
included pools is

> Δ_a,s = rate(a_DOWN_s) − rate(a_UP_s), in Hz.

**JO-attributable contrast.** S_G1,s = Δ_G1,s − Δ_OFF,s, and likewise for FLIP. Subtracting
Δ_OFF removes the part of the tilt response carried by the other senses and the mechanics.

**Consistency statistic.**
- **ρ_a** is the mean Pearson correlation of S_a,s over the 15 seed pairs.
- **Exact sign-flip test.**
  - Under the null hypothesis of no seed-consistent pattern, each S_a,s is
    sign-symmetric.
  - Recompute ρ for all 2⁶ sign assignments. Flipping every sign leaves ρ unchanged, so
    there are 32 distinct values.
  - p_a is the fraction of the 64 assignments whose ρ is at least the observed value.
  - The minimum p is 2/64 = 1/32.

## Labels (per assignment a ∈ {G1, FLIP}; decided by these rules only)

**Q1: is there a seed-consistent JO tilt response in leg MNs?**

| Label | Rule |
|---|---|
| `JO_TILT_PATTERN_CONSISTENT` | ρ_a > 0 and p_a ≤ 1/32 (the observed signs are the most aligned possible) |
| `JO_TILT_PATTERN_WEAK` | ρ_a > 0 and 1/32 < p_a ≤ 0.25 |
| `NO_CONSISTENT_JO_TILT_PATTERN` | otherwise |

**Reported, not labelled:**
- **Linearity check, r_GF.** This is the Pearson correlation of the seed means of S_G1 and
  S_FLIP. If responses were additive, swapping zones would invert the contrast, giving
  r_GF ≈ −1. A departure from −1 measures nonlinearity, including the effect of the
  different tonic rest zone. **It does not identify the true zone sign.** Without a
  functional criterion, no motor-pattern statistic can.
- **Magnitudes:** mean |Δ_a,s| per arm type, and ‖S_a,s‖.
- The per-pool seed medians of S, with the seed sign counts.
- **Descending neurons:** the DOWN − UP rate contrast in the window for the top direct JO
  targets from Step A (DNp73, DNp18, DNg29, pIP1, DNbe001), by exact bodyId.
- **Tonic effect:** mean leg-MN rate in G1_UP versus OFF_UP over 0–500 ms, before the tilt.
- **Body:** pitch and roll relative to gravity over time, tilt, supports, and the first
  physical difference between ON and OFF arms.
- **Left/right:** per-side MN contrasts, labelled with the reconstruction asymmetry. Under
  the Step B rule, **no** left-minus-right difference is interpreted as roll sensing.

## What each outcome means (declared now)

- **`JO_TILT_PATTERN_CONSISTENT`:** the sustained pitch is encoded by JO and passes through
  the connectome to a reproducible pattern of leg-MN change, beyond what the other senses
  carry. This establishes the information path that balance would need. It does not show
  the pattern is corrective, and it is not balance.
- **`WEAK` or `NO_CONSISTENT`:** a 10° tilt delivered through this encoder does not produce
  a reproducible leg-MN pattern over 1.5 s, beyond the other senses. Possible reasons, which
  would not be distinguished:
  - chaotic divergence swamps the signal;
  - the drive is too small;
  - the route is too indirect.

  The result is recorded as it stands. It would not be repeated with a larger tilt or more
  seeds without a new, versioned protocol.
- **The two assignments may disagree,** for example one CONSISTENT and one not. That is
  reported as it is, and neither assignment is promoted.

## Limits

- **Modelled kinematic transduction.** The 120 Hz scale is an engineering choice, and the
  G1 zone label is arbitrary.
- **The tilt is an idealised gravity rotation.** It is not an applied rotation of the body.
- **Δ_OFF is an imperfect control.** ON arms carry tonic JO input from t = 0, so their body
  and network state at 500 ms already differ from the OFF arms. S removes the
  other-senses tilt response only to first order.
- **Coxa MNs drive nothing** (the coxa coordinates are unmapped or CONDITIONAL). Any MN
  pattern is read out, not acted on, except through the 20 admitted channels.
- **The right-side JO reconstruction is far less connected.** The sets are used as
  reconstructed.
- No motor coordinate status changes: 20/42 admitted, +4 conditional.

## Build and run plan (on approval)

1. Write `docs/evidence/antennal-gravity-live-v1/protocol.json` with the arms, seeds,
   tilt, integrity rules, measures and labels.
2. Write `malecns_backend/live/antennal_gravity_live.py`. It subclasses
   `coxa_push_response.Trial` (kind N, push 0) and reuses:
   - Step B's encoder;
   - the hair-plate input-boundary pattern;
   - `hair_plate_posture.mn_sets` and `rate`;
   - the replication I2 comparison.
3. Write `tests/test_antennal_gravity_live.py`, with synthetic tests covering the
   gravity rotation sign, schedule and withholding, the sign-flip test (exact p on
   constructed vectors), every label boundary and the integrity checks.
4. Run a short smoke on scratch output (about 50 steps, with the tilt boundary moved
   earlier). It is discarded unread except for exit status.
5. Commit and push the preregistration. Run all 37 arms once in the background, then
   evaluate once. Raw `.json.gz` arms stay local, and their hashes go in the report.
   Record the results, the handoff and the roadmap.
