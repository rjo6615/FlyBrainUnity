# Fore-aft push response with the four conditional coxa channels — design (V1)

Designed 2026-11-03, after the middle-leg C3 confirmation was merged (PR #317). This is
the design only. No code has been written and nothing has run. The protocol, code and
tests will be hash-locked and committed before any arm runs.

## Why this question

The coxa track now has four CONDITIONAL fore-aft channels, `joint_{LF,LH,LM,RM}Coxa`
(H1, labelled `COXA_CONDITIONAL_H1`). Each was confirmed as a resistance reflex
against its own leg's coxa position. Every test so far has asked whether a loop moves
*its joint*. None has asked whether the loops together change how the *body* responds
to a disturbance. That is the first question aimed at balance, rather than at coverage.

What is left in the coxa track cannot be tested locally:

- **RF** is blocked by the input from its connectome (two BANC checks were inconclusive).
- **RH** has its H1 channel on `Coxa_roll`, which the fore-aft encoder cannot see.
- **Middle and hind Tarsus1** have no source that identifies their target motor neurons.

## Question

In the assisted standing posture, does enabling the four conditional coxa channels change
how far the thorax is displaced, and how strongly the body is reoriented, by a brief
fore-aft thorax push? This is measured against the same push with no coxa channels. The
sign-flipped channels are the specificity control.

## Disturbance (reused; direction declared)

**The pulse is the existing validated engineering pulse.**
- Source: M9B and the tactile-disturbance study, `m9b_external_perturbation` /
  `tactile_recovery`.
- It is applied through the kernel's existing `external_force_by_transition` callback,
  at the exact Thorax body COM, with zero torque.
- It lasts for outgoing transitions 5,000–5,199: 200 transitions, magnitude 1.024
  native force units, impulse 0.02048 native force-seconds.

**Only the direction changes.** It is fore-aft instead of lateral, because the four
channels act fore-aft.

| Push | World force |
|---|---|
| `F` (forward) | `[+1.024, 0, 0]` |
| `B` (backward) | `[−1.024, 0, 0]` |

- The magnitude, duration and application point are unchanged and are never adjusted.
- The anterior axis is +x (Step B anterior check, 0.9997).
- The direction is a declared new stimulus. It is not a biological disturbance scale.

## Context and arms

Each arm is Step C arm A_ON:
- assisted posture;
- the same encoder and schedule;
- the 20 v3 channels unchanged;
- 2 s, 20,000 physics and 4,000 neural transitions.

There is no displacement and no release. CNS seeds are 1, 2 and 3, applied by replacing
`brain.rng` at attach. Each arm runs once, in a fresh process.

| Channel set | No push (`_0`) | Forward (`_F`) | Backward (`_B`) |
|---|---|---|---|
| `N`: no coxa channels | `N0` | `NF` | `NB` |
| `C`: four CONDITIONAL channels, H1 | `C0` | `CF` | `CB` |
| `X`: the same four, H1_FLIP | `X0` | `XF` | `XB` |

That is 9 arms per seed and **27 arms in total, about 2.3 hours**.

The channel definitions are loaded by hash from D2 through the labelled hypothesis
session path:
- `joint_LFCoxa`, `joint_LHCoxa`: as in the coxa admission test;
- `joint_LMCoxa`, `joint_RMCoxa`: as in the middle-leg C2 and C3 tests.

## Integrity (all required, else `INCONCLUSIVE_INTEGRITY` with no labels)

1. **I1 Completeness.** All 27 arms are COMPLETE, with 20,001 samples and 4,000 ticks.
2. **I2 Common random numbers.** Within each seed, every arm has identical per-tick
   uniforms and schedule.
3. **I3 Reproduction.** `N0_s` equals coxa-admission `C0_s` over the **whole run**, in
   every sample's qpos and every tick's spikes, uniforms and hair deliveries. Those raw
   files are local and their hashes are in the admission report.
4. **I4 Exact force.**
   - Every pushed arm applies exactly the planned Thorax wrench on transitions
     5,000–5,199, with nothing at any other time or on any other body, and zero torque.
   - Every `_0` arm applies no external force.
   - This reuses the tactile study's exact planned-wrench audit, with the direction
     substituted.
5. **I5 Channels and bounds.**
   - The v3 inventories are identical in every arm.
   - N arms have no hypothesis channel and never change the four coxa commands.
   - C and X arms have exactly the four channels, with the declared definition hashes.
   - Every offset satisfies |c| ≤ 0.25 rad.
   - Other non-v3 commands equal those of the matching N arm.
6. **I6 Prefixes.**
   - Within each seed and channel set, the pushed arms equal their `_0` arm through
     physics index 5,000.
   - C and X arms equal the matching N arm until their first coxa command.
7. **I7 Seeds applied.** The tick-1 uniforms differ between seeds, and every arm records
   its seed.

**Pulse precondition** (`INCONCLUSIVE_PULSE`, no labels): in every seed and direction,
`NF_s` and `NB_s` must be resolved perturbations relative to `N0_s`. This uses the tactile
study's floors: peak orientation error > 0.25° **or** peak root-position deviation > 0.005
model mm.

## Measures (all relative to the arm's own unpushed control)

Each pushed arm is compared with the `_0` arm of the **same channel set and seed**. This
removes the constant posture shift the channels add before any push.

- **Root-position deviation.** d(t) = ‖p_push(t) − p_ctrl(t)‖ of the free-joint root, in
  model mm.
- **Orientation error.** The shortest-arc angle between the root quaternions, using the
  tactile study's normalised quaternion observer.

**Windows.**
- Force on: 500.0–520.0 ms.
- Cleared: 520.1–2,000 ms, using integer indices, with no subwindow selected.

**Primary measure, D.** The integral of d(t) over the cleared window, in mm·s.

**Reported:**
- the peak of d and its time;
- the orientation-error peak, mean and integral;
- the signed fore-aft component of the root deviation;
- the inherited recovery-band status (entry and confirmation, or
  NOT_RECOVERED_IN_WINDOW / NO_BAND_EXIT);
- support counts;
- hair-plate rates and coxa commands per leg, so the reader can see which loops
  actually responded;
- coxa MN rates and tilt.

## Labels (per push direction; decided by these rules only)

R_s = D(C·_s) / D(N·_s) is the loop ratio for seed s and that direction. R′_s = D(X·_s) /
D(N·_s) is the corresponding flip ratio.

**Q_LOOP (per direction)**

| Label | Rule |
|---|---|
| `LOOP_ATTENUATES` | R_s ≤ 0.90 in all 3 seeds |
| `LOOP_AMPLIFIES` | R_s ≥ 1.10 in all 3 seeds |
| `NO_CONSISTENT_LOOP_EFFECT` | otherwise |

**Q_SIGN (per direction)** is evaluated only when Q_LOOP is not
`NO_CONSISTENT_LOOP_EFFECT`.

| Label | Rule |
|---|---|
| `SIGN_SPECIFIC` | R′ fails Q_LOOP's own bar, in Q_LOOP's direction, in at least 2 of 3 seeds |
| `SIGN_INDEPENDENT` | otherwise |

**The 10 % bar.** It is an engineering resolution fixed here. No noise estimate for this
contrast exists, and the bar is not tuned to an expected outcome. The orientation
measures are reported beside D and never folded into a composite.

## What each outcome means (declared now)

**`LOOP_ATTENUATES` + `SIGN_SPECIFIC` in a direction.**
- With the conditional channels, the body is displaced less by that push, and the
  flipped wiring does not reproduce the effect.
- This is the first evidence that the neural coxa loops contribute to postural
  resistance in this model. It is not independent balance: the posture servos are on.

**`SIGN_INDEPENDENT`.**
- The channels change the response, but not through the reflex direction. Examples are
  added servo stiffness or a posture shift.

**`NO_CONSISTENT_LOOP_EFFECT` or `LOOP_AMPLIFIES`.** Recorded as is.

In every case:
- no channel, weight, threshold, gain, magnitude or seed changes;
- no status in `COXA_COORDINATE_STATUS.md` changes, because this is not an admission test;
- coverage stays 20/42 admitted, +4 conditional.

## Predictions (expectations, not criteria)

**Forward push (F): possible attenuation, low confidence.**
1. Pushing the thorax forward over planted feet rotates the coxae backward relative to
   the body.
2. The front and hind hair plates, saturated at rest, can then desaturate.
3. The H1 posterior offsets fall, and the coxa servo targets move forward.
4. With the feet planted, that pushes the body back.

**Backward push (B): `NO_CONSISTENT_LOOP_EFFECT` more likely.**
- The middle-leg hair plates sit about 0.2 below threshold at rest, and a 20 ms push may
  not move the coxae that far.
- The front and hind plates are already saturated, so they cannot respond further.

**The main uncertainty is the effect size.** Every loop acts as an offset on an active
position servo, whose own stiffness dominates the response to a short push.

## Limits

- **Position-assisted posture.** All 42 servos stay on, so the loops can only modulate
  servo setpoints. This is not independent balance.
- **One engineering pulse.** The magnitude is reused from M9B; the fore-aft direction is
  declared. It is not a biological disturbance scale.
- **Three seeds,** which vary only stochastic sensory timing.
- **Only the four fore-aft coxa channels are added.** The 20 admitted channels are
  unchanged, and no other conditional or hypothesis channel is used.
- **Root deviation is relative to a moving control,** so it is not absolute stability.

## Build and run plan (on approval)

1. **Protocol.** Write `docs/evidence/coxa-push-response-v1/protocol.json`. It holds the
   pulse rows, the arm matrix and order, the channel hashes, the C0 references,
   integrity, the precondition, the measures and the labels.
2. **Code.** Write `malecns_backend/live/coxa_push_response.py`. It reuses:
   - the seeded D3 trial and channel loading;
   - the hypothesis session path, with the kernel's existing force callback passed
     through, as `tactile_recovery.create_session` does;
   - `m9b`'s pulse schedule shape, with a declared direction;
   - the tactile force audit;
   - `tactile_recovery_metrics` for orientation error, recovery bands and resolution.
3. **Tests.** Write `tests/test_coxa_push_response.py` using synthetic arms. It covers:
   - the force schedule and audit;
   - the D integral and ratios;
   - the label boundaries;
   - each integrity fault and the pulse precondition.
4. **Smoke.** Run 5,300 steps of `CF_2` (past the pulse) and check the force rows, the
   inventory and the seed. Discard it, then commit and hash-lock.
5. **Run.** Each of the 27 arms once (about 2.3 h), then the evaluation once. Record the
   results, the handoff and the roadmap.
