# Released-posture test with the conditional coxa channels — design (V1)

Designed 2026-11-02, after the coxa admission confirmation was merged (PR #313). This
document is the design only: no code has been written and nothing has run. The protocol,
code and tests will be hash-locked and committed before any arm runs.

## Question

In Step C, releasing the posture servos makes the fly roll over every time: mean tilt
about 150° in R_OFF and R_ON, and also in all four V1.2 R arms. The neural channels never
prevented or measurably slowed it. `joint_LFCoxa` and `joint_LHCoxa` are now CONDITIONAL
(`COXA_COORDINATE_STATUS.md`).

The question is: **after the posture servos are released, does the closed hair-plate →
CNS → coxa loop on these two channels change how, or how fast, the body rolls over,
compared with a matched control that keeps the same two servos with no neural input?**

This is the step named in the coxa track design. It is a test of the conditional
channels. It is not a balance test, and no rescue is expected.

## A design constraint found before writing this

The Step C release (`ZERO_FULL_SELECTED_ROWS`, state 5005) zeroes the gain and bias of the
22 baseline-only actuators. These are fixed by the locked assistance authority, and they
**include `joint_LFCoxa` and `joint_LHCoxa`**. The coxa channels act as an offset on their
position servo, so after the standard release they would act on a zero-gain actuator and
do nothing.

The test therefore needs a declared variant of the release that leaves those two rows
intact. That variant itself adds position assistance at two joints. So the matched
control (`K`) keeps the same two servos with **no** neural channel, and every neural
comparison is made against K, not against Step C R_ON.

## Context (fixed)

Each arm is Step C arm R_ON with these settings:

- the same encoder, schedule, window and step counts;
- the same release time (state 5005, 500.5 ms);
- the 20 v3 channels unchanged.

CNS seeds are 1, 2 and 3, with the same mechanism as the confirmation test: `brain.rng`
is replaced at attach, before the first transition.

Each arm runs once, in a fresh process.

## Arms (per seed s; 12 arms, about 60 minutes)

| Arm | Release at state 5005 | Coxa channels |
|---|---|---|
| `R22_s` | all 22 rows (Step C operation) | none |
| `K_s` | 20 rows: the 22 minus `joint_LFCoxa`, `joint_LHCoxa` | none |
| `KC_s` | the same 20 rows | H1 `joint_LFCoxa`, `joint_LHCoxa` (conditional, labelled `COXA_CONDITIONAL_H1`) |
| `KF_s` | the same 20 rows | H1_FLIP of the same two channels |

**Definitions and paths.**

- The channel definitions are loaded by hash, exactly as in the confirmation test (H1
  6bf08be7…, H1_FLIP ee4da58b…), through `coxa_hypothesis_loop.create_hypothesis_session`.
- The 20-row release is a declared engineering operation, `ZERO_SELECTED_ROWS_EXCEPT_2`.
  It is implemented in the new adapter using the existing `assistance_native` partition
  and record functions, and `assistance_native` itself is unchanged.
- Its expected after-record has those 20 rows zeroed and every other model array equal to
  the original. It is checked exactly, as Step C checks its 22-row operation.

## Integrity (all required, else `INCONCLUSIVE_INTEGRITY` with no labels)

1. **I1 Completeness.** All 12 arms are COMPLETE, with 20,001 samples and 4,000 ticks.
2. **I2 Common random numbers.** Within each seed, every arm has identical per-tick
   `uniforms_sha256` and the same schedule.
3. **I3 Reproduction.** `R22_1` equals the saved Step C R_ON in fired, uniforms, hair
   deliveries and qpos. The R_ON sha comes from the Step C report.
4. **I4 Release verified.**
   - Each arm's release event happens at state 5005 with the declared operation.
   - Its after-record sha equals the expected neutral record: 22 rows for R22, 20 rows for
     the K arms.
   - The model is unchanged before the event.
5. **I5 Channels and bounds.**
   - The 20 v3 channel inventories are identical in every arm.
   - R22 and K arms have no hypothesis channel and never change commands 0 or 14.
   - KC and KF arms have exactly the two candidates, with matching definition hashes.
   - Every offset satisfies |c| ≤ 0.25 rad.
   - Other non-v3 commands equal `K_s`.
6. **I6 Prefix identity.**
   - Within each seed, R22 and K are identical through state 5005, since they differ only
     in the release.
   - KC and KF equal K until their first coxa command.
7. **I7 Seeds applied.** The tick-1 uniforms differ between seeds, and every arm records
   its seed.

## Measures (after release; window 520–2000 ms unless stated)

- **T_roll (primary).** The time of the first sample after state 5005 with world tilt
  > 90°. It is `None` if none occurs. A non-rollover counts as 2000 ms for differences
  (right-censored) and is reported as censored.
- **Tilt.** Mean and peak tilt in the window, and the number of rollover samples.
- **Descriptive:**
  - the direction of the rollover (the roll/pitch sign of body z at T_roll);
  - commanded coxa offsets after release;
  - LF and LH coxa forward component;
  - hair-plate rates;
  - coxa MN rates per leg;
  - the first physical divergence from K.

## Labels (decided by these rules only)

**Q_ASSIST — does keeping the two coxa servos matter?** (K vs R22)

| Label | Rule |
|---|---|
| `ASSIST_DELAYS` | T_roll(K_s) − T_roll(R22_s) ≥ +20 ms in all 3 seeds |
| `ASSIST_HASTENS` | ≤ −20 ms in all 3 seeds |
| `NO_CONSISTENT_ASSIST_EFFECT` | otherwise |

**Q_NEURAL — does the conditional loop change the rollover?** (KC vs K)

| Label | Rule |
|---|---|
| `LOOP_DELAYS` | T_roll(KC_s) − T_roll(K_s) ≥ +20 ms in all 3 seeds |
| `LOOP_HASTENS` | ≤ −20 ms in all 3 seeds |
| `NO_CONSISTENT_LOOP_EFFECT` | otherwise |

**Q_SIGN — is any loop effect sign-specific?** It is only evaluated if Q_NEURAL is not
`NO_CONSISTENT_LOOP_EFFECT`.

| Label | Rule |
|---|---|
| `SIGN_SPECIFIC` | FLIP's effect (T_roll(KF_s) − T_roll(K_s)) fails the same ≥ 20 ms, same-direction test in at least 2 of 3 seeds |
| `SIGN_INDEPENDENT` | otherwise; the effect also appears with the sign flipped, so it is not specific to the reflex direction |

**Q_RESCUE.**

| Label | Rule |
|---|---|
| `RESCUE` | KC has no rollover sample in any seed, while K rolls over in every seed |
| `NO_RESCUE` | otherwise |

**The 20 ms bar** is 200 physics samples and 40 neural ticks. It is chosen as clearly
above sample resolution. It is not tied to any expected outcome.

## Predictions (expectations, not criteria)

- **Q_RESCUE: NO_RESCUE.** Twenty other coordinates are released, including every other
  coxa and the tarsi. Two fore-aft coxa joints cannot hold the body.
- **Q_ASSIST: NO_CONSISTENT_ASSIST_EFFECT is most likely.** Two servos out of 22 are a small
  share of the lost assistance.
- **Q_NEURAL: NO_CONSISTENT_LOOP_EFFECT, with low confidence.**
  - After the rollover starts, the hair plates leave their saturated range, so the loop may
    briefly act.
  - The biological reflex has no predicted direction for whole-body rollover, so this
    is exploratory.
- **The informative outcomes:**
  - any consistent loop effect, and whether it depends on sign;
  - whether the coxa channels saturate (BOUND) during the fall;
  - how hair-plate and MN activity evolve once the posture is lost.

## Limits

- **Assisted context.** The 20 v3 position servos are still on. The release is partial,
  as in Step C.
- **Offset-on-servo actuation.** K adds position assistance by design, and it is
  controlled for.
- **One body model, three seeds.** The seeds vary only stochastic sensory timing.
- **Conditional channels.** These results carry `COXA_CONDITIONAL_H1`. A loop effect is
  not balance, and a null is expected and still informative.
- **No change to admission.** Motor coverage stays 20/42 admitted, +2 conditional.

## Build and run plan (on approval)

1. **Protocol.** Write `docs/evidence/coxa-release-posture-v1/protocol.json`. It includes
   the release row sets, as action indices and actuator IDs resolved at bind, the expected
   neutral-record rule, the channel hashes, the seeds, integrity and labels.
2. **Code.** Write `malecns_backend/live/coxa_release_posture.py`. It reuses the confirmation
   test's seeded Trial and channel loading, the D3 session path and the Step C release.
   It adds the 20-row release variant, the arm runner and the evaluator.
3. **Tests.** Write `tests/test_coxa_release_posture.py`, covering:
   - the 20-row set equals the 22 minus the two;
   - the neutral record for 20 rows (synthetic model arrays);
   - T_roll with censoring;
   - the label rules;
   - integrity faults.
4. **Smoke.** A short plumbing smoke test that crosses state 5005 (5,100 steps, just past the
   release) for `K_2` and `KC_2`. It checks only the release event and inventory, and is
   discarded. Then commit and hash-lock.
5. **Run.** Each of the 12 arms once (about 60 min), then the evaluation once.
6. **Record.** Write the results document and update the status table only if a
   preregistered failure revokes something (none of these labels revokes CONDITIONAL).
   Raw arms stay local.
