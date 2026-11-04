# Open-loop coxa offset yoke: is the push amplification reflex or posture? — design (V1)

Designed 2026-11-03, after the push-response results were merged (PR #318). This is the
design only. No code has been written and nothing has run. The protocol, code and tests
will be hash-locked and committed before any arm runs.

## Why this question

The push-response test (`COXA_PUSH_RESPONSE_RESULTS.md`) found LOOP_AMPLIFIES in both
directions: with the four CONDITIONAL coxa channels (H1), a fore-aft thorax push displaced
the body 24–104 % more than without them.

The reported measures suggested the cause, without testing it:
- in the pushed arms, the window-mean hair-plate rates and coxa offsets equalled their
  unpushed controls;
- LF and LH sat at tonic offsets of about +0.17–0.22 rad, and LM and RM stayed silent;
- C arms tilted 9–10°, against about 4° without coxa channels.

The post hoc reading was that the static posture set by the offsets amplifies the push,
and that the loops' moment-to-moment response is not the cause. That is a claim about a
mechanism, so it should be tested directly before anything is built on it.

## Question

In the push-response context, does replaying the C arms' **unpushed** coxa command time
series open loop reproduce the C arms' amplified push response? The replay is driven by
no neural coxa loop at all.

- **If it does,** the amplification is a property of the setpoints the loops settle on.
  Their response to the push is not needed for it.
- **If it does not,** the loops' push-time modulation matters, even though it is small in
  window means.

## Method (reused, not new)

**Selected-index motor yoke.** This is the tibia command-group dissection's method
(`tibia_command_dissection.selected_action`, `TIBIA_COMMAND_DISSECTION_V1.md`), applied
to a different index set.
- At every outgoing physics transition n, the action the session proposes is applied
  with only the selected indices replaced.
- Their values come from the archived source arm's `samples[n+1]['commanded_joints']`, by
  the same sample convention as `tactile_motor_yoke.commands`.
- Every other coordinate is applied exactly as proposed.
- The wrapper sits at the same boundary as the yoke's: `sim.step` is wrapped at bind.
- Both proposed and applied actions are recorded.
- The tibia module's helper uses its own locked index set, so the new module carries an
  equivalent four-index helper. The tibia module and its locks are not modified.

**Selected indices.** These are the four H1 coxa actions, resolved exactly from the
push-response protocol's `action_index`: `joint_LFCoxa` 0, `joint_LMCoxa` 7,
`joint_LHCoxa` 14, `joint_RMCoxa` 28.

**Source arm.** For seed s, the source is push-response `C0_s`, the unpushed C arm of the
same seed. It is local and uncommitted. Its SHA-256 is in the push-response report
(sha 4c03a59e…):

| Source arm | SHA-256 |
|---|---|
| `C0_1` | `f11daca5…` |
| `C0_2` | `36117006…` |
| `C0_3` | `39818c86…` |

**Context.** Everything else is inherited unchanged from `coxa_push_response`:
- the Step C A_ON assisted posture, the 20 v3 channels and the encoder;
- the seed mechanism (`brain.rng = default_rng(seed)` at attach);
- the Thorax pulse through `external_force_by_transition`: ±1.024 for transitions
  5,000–5,199, zero torque;
- 20,000 physics and 4,000 neural transitions.

The yoked arms run the **N** configuration, with no hypothesis channel. The coxa
commands come only from the archive.

## Arms

| Arm | Push | Coxa indices 0/7/14/28 |
|---|---|---|
| `Y0_s` | none | yoked to `C0_s` |
| `YF_s` | F `[+1.024, 0, 0]` | yoked to `C0_s` (unpushed) |
| `YB_s` | B `[−1.024, 0, 0]` | yoked to `C0_s` (unpushed) |

The arms run for seeds s = 1, 2, 3, which gives **9 fresh-process arms, about 45 min**.
Each runs once, in seed-major order. The references are the existing, already-run
push-response arms `N{0,F,B}_s` and `C{0,F,B}_s`. They are not rerun.

`Y0_s` is expected to equal `C0_s` exactly. The physical inputs are identical at every
transition, and the push-response I6 check already showed that the hypothesis and N
session paths are identical until the first coxa command. `YF_s` and `YB_s` differ from
`CF_s` and `CB_s` only in that their coxa commands cannot respond to the push.

## Integrity (all required, else `INCONCLUSIVE_INTEGRITY` with no labels)

1. **I1 Completeness.** All 9 arms are COMPLETE, with 20,001 samples and 4,000 ticks.
2. **I2 Source and reference arms verified.**
   - The 18 push-response arms `N·_s` and `C·_s` hash to the values in the push-response
     report.
   - That report hashes to 4c03a59e….
3. **I3 Reproduction.** `Y0_s` equals `C0_s` over the **whole run**: every sample's qpos
   and applied commands (all 42), and every tick's spikes, uniforms and hair deliveries.
4. **I4 Common random numbers.** Every Y arm's per-tick uniforms equal those of `N0_s`.
5. **I5 Yoke audit.** At every transition:
   - the applied action equals the proposed action, with indices 0, 7, 14 and 28
     replaced by the source arm's sample n+1 values;
   - the other 38 coordinates equal the proposal.
   - The v3 inventory equals the N arms'. There is no hypothesis channel and no label.
6. **I6 Exact force.** This is the push-response audit, unchanged. Every pushed arm
   records exactly the planned Thorax wrench of transition i−1, and `Y0_s` records none.
7. **I7 Prefixes.** `YF_s` and `YB_s` equal `Y0_s` through physics index 5,000 (qpos and
   applied commands), and the ticks at or before 500 ms are equal. Every arm records its
   seed.

The pulse precondition is already established: `NF_s` and `NB_s` were resolved in every
seed and direction in the push-response run. It is not re-tested.

## Measures

D is the primary measure of the push-response test, unchanged. It is the trapezoidal
integral of ‖root(pushed) − root(own control)‖ over stored states 5,201–20,000, in model
mm·s, using `tactile_recovery_metrics.trace`. The own controls are:
- `Y0_s` for the Y arms;
- `N0_s` and `C0_s` for the references, recomputed from the raw arms by the same function.

For each direction p ∈ {F, B} and seed s:
- **R_Y = D(Yp_s) / D(Np_s).** Does open-loop replay amplify?
- **E = D(Yp_s) / D(Cp_s).** Does it match the closed-loop C arm?

**Reported (not labelled):**
- `metrics.response` for each Y arm;
- the signed fore-aft deviation and tilt;
- the per-direction loop modulation actually present in the C arms:
  - the mean |c(Cp_s) − c(C0_s)| per coxa index over the cleared window;
  - the number of transitions where they differ;
- the applied-minus-proposed coxa difference in the Y arms, which is what the yoke
  removed.

## Labels (per push direction; decided by these rules only)

| Label | Rule |
|---|---|
| `OFFSETS_REPRODUCE` | R_Y ≥ 1.10 in all 3 seeds **and** 0.90 ≤ E ≤ 1.10 in all 3 seeds |
| `OFFSETS_PARTLY_REPRODUCE` | R_Y ≥ 1.10 in all 3 seeds, but E is outside [0.90, 1.10] in at least one seed |
| `OFFSETS_DO_NOT_REPRODUCE` | R_Y < 1.10 in at least one seed |

**The bars are inherited.** The 10 % resolution is the push-response test's engineering
bar. No noise estimate exists for E; it measures the effect of removing only the loops'
push-time modulation.

## What each outcome means (declared now)

**`OFFSETS_REPRODUCE`.**
- The amplification is explained by the open-loop setpoint schedule the conditional
  channels settle on.
- Their moment-to-moment response to this push is not needed for it.
- The push-response reading moves from post hoc to tested, for this pulse and posture.

**`OFFSETS_PARTLY_REPRODUCE`.**
- The posture accounts for amplification, but removing the loops' push-time modulation
  changes D by more than 10 % in at least one seed. The direction of that change is
  reported.

**`OFFSETS_DO_NOT_REPRODUCE`.**
- The fixed setpoints alone do not amplify, so the push-response mechanism reading was
  wrong or incomplete. That result is recorded.

In every case:
- no channel, weight, threshold, gain, magnitude or seed changes;
- no coordinate status changes, because this is not an admission test;
- coverage stays 20/42 admitted, +4 conditional.

## Prediction (expectation, not a criterion)

**`OFFSETS_REPRODUCE`, moderate confidence.**
- The C arms' window-mean coxa offsets barely moved with the push. The front and hind
  plates are saturated, and the middle plates are silent.
- The main risk is that small per-sample modulations matter through chaotic divergence.
  That would show up as E outside the band.

## Limits

- **Position-assisted posture.** All servos stay on. This is not independent balance.
- **The archive's commands are themselves neural output.** The yoke removes only the
  loops' response to the push. It does not remove the loops' history before the push,
  which the archive embeds.
- **One engineering pulse and three seeds.** These are inherited from the push-response
  test.
- **E has no noise estimate.** Chaotic divergence after the push can move D without any
  causal role for loop modulation.
- **The reference arms are local and not committed.** I2 makes the evaluation depend on
  their verified hashes.

## Build and run plan (on approval)

1. **Protocol.** Write `docs/evidence/coxa-offset-yoke-v1/protocol.json`. It holds:
   - the index set, the source and reference hashes and the arm order;
   - integrity, the measures and the labels.
2. **Code.** Write `malecns_backend/live/coxa_offset_yoke.py`. It holds:
   - a `coxa_push_response.Trial` subclass that wraps `sim.step` at bind, following the
     tibia dissection, and records proposed and applied actions;
   - the four-index `selected_action`;
   - the evaluator, reusing `coxa_push_response.deviation_integral`, `force_ok` and
     `tactile_recovery_metrics`.
3. **Tests.** Write `tests/test_coxa_offset_yoke.py` using synthetic arms. It covers:
   - index replacement and the sample n+1 convention;
   - the yoke audit and each integrity fault;
   - R_Y, E and the label boundaries.
4. **Smoke.**
   - Run 1,500 steps of `Y0_2` and check that it equals the start of `C0_2` exactly.
   - Run 5,300 steps of `YF_2` and check the force rows and the yoke audit.
   - Discard both, then commit and hash-lock.
5. **Run.** Each of the 9 arms once (about 45 min), then the evaluation once. Record the
   results, the handoff and the roadmap.
