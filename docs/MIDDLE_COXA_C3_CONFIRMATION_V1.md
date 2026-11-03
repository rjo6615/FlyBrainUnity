# Middle-leg coxa C3 confirmation on new seeds — design (V1)

Designed 2026-11-03, after the C2 step was merged (PR #316).

**Status:** preregistered in 3c677c2 (protocol sha dd268b80…), run once and evaluated once:
INTEGRITY_ACCEPTED, and REPRO_1 matched C2 exactly. `joint_LMCoxa` and `joint_RMCoxa` are
both **CONFIRMED** and now **CONDITIONAL**. See `MIDDLE_COXA_C3_CONFIRMATION_RESULTS.md`.
The design below is unchanged.

## Question

Does the C2 result (`MIDDLE_COXA_DISPLACEMENT_RESULTS.md`) reproduce on CNS seeds that
have never been run: 4, 5 and 6? The C2 result was that `joint_LMCoxa` and
`joint_RMCoxa` resist an imposed forward displacement under H1, and that H1_FLIP reverses
the effect.

## Policy position (Part A, approved 2026-11-02)

C3 requires a pass to be reproduced in a separately preregistered test. The channels must
be isolated from the other hypothesis channels, and the seeds must not have been used
before.

| Requirement | How this test meets it |
|---|---|
| Separately preregistered | Its own protocol, hash-locked before any arm runs |
| Isolated | Only `joint_LMCoxa` and `joint_RMCoxa` are enabled. This is the same isolation standard as the LF/LH confirmation, which enabled its two candidates together. |
| New seeds | CNS seeds 4, 5 and 6 have never been run in any experiment |
| Same test otherwise | Identical to C2: same displacement, Δ values, window, bar and rule |

Outcome mapping, as in the LF/LH confirmation:

| Label | Status |
|---|---|
| `CONFIRMED` | CONDITIONAL |
| `PARTIAL` | stays "C2 passed"; no tier change |
| `NOT_CONFIRMED` | NOT_SUPPORTED |

## Context (fixed; identical to C2)

- Step C arm A_ON: the assisted posture, the same encoder, schedule and step counts, and
  the 20 v3 channels unchanged.
- At state 5005, `SHIFT_SERVO_EQUILIBRIUM` on the LM and RM Coxa servos:
  - `biasprm[0] += kp·Δ`;
  - Δ = −0.24496486703405715 rad for LM and −0.21994650976688868 rad for RM.
- The candidate definitions are loaded by hash:
  - H1: bffaae7f…
  - H1_FLIP: f80ffaf7…
- Seeds are applied by replacing `brain.rng` at attach.
- Each arm runs once, in a fresh process.

## Arms (10 arms, about 50 minutes)

| Arm | Seeds | Content |
|---|---|---|
| `P0_s`, `PC_s`, `PF_s` | 4, 5, 6 | the same three arm types as C2 |
| `REPRO_1` | 1 | a rerun of C2 arm `P0_1` with the new module |

`REPRO_1` checks that the new module runs the same experiment. It is required to equal C2
`P0_1` exactly. That raw file is kept local, not committed; its sha, 59d29c6f…, is recorded
in the C2 report.

## Integrity (all required, else `INCONCLUSIVE_INTEGRITY` with no labels)

1. **I1 Completeness.** All 10 arms are COMPLETE, with 20,001 samples and 4,000 ticks.
2. **I2 Common random numbers.** Within each seed, the arms have identical per-tick
   uniforms and schedule.
3. **I3 Reproduction.** `REPRO_1` equals C2 `P0_1` in every sample's qpos and commanded
   joints, and in every tick's fired spikes, uniforms and hair deliveries. Its displacement
   event record (after-record sha) is also identical.
4. **I4 Displacement verified.**
   - The event happens at state 5005 with operation `SHIFT_SERVO_EQUILIBRIUM` and the
     declared Δ values.
   - The after-record equals the expected record, and it is the same expected record in
     every arm.
5. **I5 Channels and bounds.**
   - The v3 inventories are identical in every arm.
   - P0 has no hypothesis channel and constant LM/RM Coxa commands.
   - PC and PF have exactly the two channels, with the declared hashes.
   - Every offset satisfies |c| ≤ 0.25 rad.
   - Other commands equal P0.
6. **I6 Prefix.** PC and PF equal P0 until their first coxa command.
7. **I7 Seeds applied.** Seeds 4, 5 and 6 have tick-1 uniforms that differ from each
   other and from seeds 1–3 (taken from the C2 report's arms). Every arm records its seed.

**Context precondition** (`INCONCLUSIVE_CONTEXT`, no labels): every `P0_s` has a mean
window hair-plate rate of at least 30 Hz in both LM and RM.

## Measures and labels (rule unchanged from C2)

- **Window:** 520–2,000 ms.
- **df:** the mean coxa forward component in the arm minus that in `P0_s`, per middle leg.

A **seed passes** if df(PC_s) ≤ −0.02 **and** df(PF_s) ≥ +0.02.

| Label | Rule | Status consequence |
|---|---|---|
| `CONFIRMED` | 3 of 3 new seeds pass | **CONDITIONAL** (counted separately, labelled `COXA_CONDITIONAL_H1`) |
| `PARTIAL` | 1 or 2 pass | stays "C2 passed"; no tier change |
| `NOT_CONFIRMED` | 0 pass | NOT_SUPPORTED |

The flags BOUND_LIMITED, ROLLOVER and NO_DRIVE are defined as in C2. A `NO_DRIVE`
coordinate is reported as input-limited.

**Reported, not labelled:**
- **Pre-displacement share.** C2 found that the channels already issue commands before
  the displacement (46–158 ms). This test reports, per arm, the mean channel offset over
  samples 1–5005 (before the displacement) and over the window. It also reports df over
  the last 100 ms before the displacement (400–500 ms) for PC and PF against P0. This
  shows how much of any window difference already existed before the stimulus.
- Graded feedback (hair-plate rate in PC vs P0 vs PF), coxa MN rates, cross-leg df, tilt,
  first command and first physical divergence.

## What each outcome means (declared now)

**CONFIRMED.**
- The coordinate becomes CONDITIONAL. Its evidence line cites C1 (D2 H1), C2 (PR #316),
  C3 (this test) and C4 (integrity).
- If both coordinates are confirmed, the tally becomes **20/42 admitted, +4
  conditional**, with the conditional set counted separately. LM/RM would be the first
  bilateral conditional pair.

**PARTIAL or NOT_CONFIRMED.** Recorded as above. Nothing is retried.

In every case:
- no weights, thresholds, gains, mappings or Δ values change;
- `COXA_COORDINATE_STATUS.md` is updated;
- independent balance and gait remain not established.

## Predictions (expectations, not criteria)

**RM: CONFIRMED is likely.**
- Its C2 margins were stable across seeds: PC −0.032 to −0.038, PF about +0.19.
- Its PC margin is only 0.012–0.018 above the bar, so one seed failing is possible.

**LM: CONFIRMED is somewhat less likely.**
- C2 PC ranged from −0.030 to −0.058, and seed 2 was the narrowest pass.
- PARTIAL is a realistic outcome.

**Pre-displacement share.** I expect a small difference before the displacement (much
smaller than in the window), because the middle hair plates are silent before it.

## Limits

- **Engineering perturbation.** The displacement is imposed through the servo
  equilibrium. It is a probe stimulus, not a biological input.
- **Assisted context and offset-on-servo actuation.**
- **The modeled encoder threshold is walking-derived** and unchanged.
- **The seeds vary only stochastic sensory timing.** The body model, connectome and engine
  are the same.
- **CONDITIONAL is not admission.** The v3 standard is unchanged, and a later
  preregistered failure revokes the status.

## Build and run plan (on approval)

1. **Protocol.** Write `docs/evidence/middle-coxa-c3-v1/protocol.json` with the seeds, the
   REPRO reference, integrity, the precondition, labels and descriptives.
2. **Code.** Write `malecns_backend/live/middle_coxa_c3.py`. It reuses the C2 module's
   equilibrium shift, Trial, candidate loading, run loop and evaluator logic, with its own
   arm set and the REPRO check. The C2 module and its protocol stay unchanged.
3. **Tests.** Write `tests/test_middle_coxa_c3.py` using synthetic arms. It covers:
   - the seed set and arm order;
   - the REPRO equality check;
   - the label mapping;
   - the pre-displacement measure;
   - each integrity fault and the precondition.
4. **Smoke.** Run 5,100 steps for `P0_4` and confirm the event, the seed and the
   inventories, then discard it. Commit and hash-lock.
5. **Run.** Each of the 10 arms once (about 50 minutes), then the evaluation once. Record
   the results, the status update, the handoff and the roadmap.
