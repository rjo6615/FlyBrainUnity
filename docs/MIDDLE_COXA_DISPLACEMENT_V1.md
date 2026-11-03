# Middle-leg coxa resistance reflex under an imposed forward displacement — design (V1)

Designed 2026-11-03, after the RF hair-plate thread was closed (PR #315).

**Status:** preregistered in f91fd74 (protocol sha 9854e0af…), run once and evaluated once:
INTEGRITY_ACCEPTED, context met. `joint_LMCoxa` and `joint_RMCoxa` are both **C2_PASSED**
(3/3), with no flags. See `MIDDLE_COXA_DISPLACEMENT_RESULTS.md`. Apart from the sign
correction noted below, the design is unchanged.

## Why this question

The middle legs are the largest untested group in the coxa track: 9 of the 18 coxa
coordinates.

| Line of evidence | What it shows |
|---|---|
| Anatomy (Step A, `HAIR_PLATE_IDENTITY_RESULTS.md`) | LM has 12 and RM 11 SNpp45 hair plates, the largest pools of any leg. They make 662 (LM) and 1,056 (RM) direct synapses onto posterior-moving coxa MNs, almost all onto the sternal posterior rotator. |
| Modeled transduction (Step B) | Middle legs are silent at rest only because the standing pose (forward component −0.037 LM, −0.012 RM) is behind the walking-derived threshold (+0.160, saturating at +0.184). |
| Measured (released-posture test, KF arms) | When the middle-left coxa was displaced forward, its hair plates fired at 69–116 Hz and middle-left coxa MNs rose to 5.7–9.5 Hz. |
| Binding (D2, H1) | Both the hair-plate target (posterior rotator) and the remotor bind to `joint_<LM/RM>Coxa` with sign +1 (posterior), the same as LF/LH. |

D3 excluded the middle legs because their encoder was silent. They have never been tested.

Unlike LF/LH, the pair is **bilateral**, and RM has the strongest anatomical drive of all
six legs.

The standard way to probe a resistance reflex is an **imposed displacement**: move the
joint towards its limit and ask whether the loop pushes it back. The design does that here.

## Question

When the middle-leg coxae are held at the forward edge of their recorded walking range,
does the closed hair-plate → CNS → coxa loop on `joint_LMCoxa` and `joint_RMCoxa` push
each coxa back? And does the sign-flipped binding push it further forward?

## Policy position (Part A, approved 2026-11-02)

The CONDITIONAL tier requires four things:

- **C1:** a rule-fixed binding;
- **C2:** a falsification test with a sign-reversal control;
- **C3:** a separately preregistered, isolated confirmation on seeds not used before;
- **C4:** integrity.

**This test is the C2 step for the two middle-leg coordinates.** It cannot make them
CONDITIONAL by itself.

- A C2 pass makes a coordinate eligible for a later C3 confirmation on seeds 4–6.
- The coordinate is counted nowhere until that confirmation is done.

## The imposed displacement (declared engineering perturbation)

**Operation `SHIFT_SERVO_EQUILIBRIUM`** happens at state 5005 (500.5 ms), the same boundary
as the Step C release.

- For the baseline position servos of `joint_LMCoxa` and `joint_RMCoxa` only,
  `actuator_biasprm[0]` gains +kp·Δ, where kp is the actuator's own `gainprm[0]`. (Corrected before
  registration: the design first said −kp·Δ, which would shift the equilibrium backward. For
  a position servo the equilibrium is ctrl + biasprm[0]/kp.)
- This moves the servo equilibrium by Δ. Gain, damping, every other row and the neural
  command path are unchanged.
- The neural channel's offset, sent through `ctrl`, adds on top as before.
- The expected after-record is the original record with exactly those two `biasprm[0]`
  entries changed. It is checked exactly, as Step C checks its release.

**Magnitude**, fixed here by rule from committed Step B values (result sha 04ccced2…):

- The target forward component is f* = f_max + (f_max − θ) = 0.2074. That is one
  encoder band past the recorded walking forward limit, so modest servo tracking error
  under load still leaves the hair plates firing.
- Δ = (f* − f_rest) / (∂f/∂Coxa), using the Step B rest values and axis slopes:

| Leg | f_rest | ∂f/∂Coxa (per rad) | Δ (rad) |
|---|---:|---:|---:|
| LM | −0.03653 | −0.99584 | **−0.2450** |
| RM | −0.01202 | −0.99766 | **−0.2199** |

**Context.**
- The displacement is a forward (protraction) shift of about 0.22–0.24 rad.
- The recorded walking range of LM/RM Coxa is 0.59 rad peak-to-peak.
- It is a stimulus imposed by the experiment. It is not a biological input and not a
  tuned parameter. It is never adjusted after any run.

## Context (fixed)

Each arm is Step C arm A_ON with these settings:

- the same encoder, schedule, window and step counts;
- the 20 v3 channels unchanged;
- the posture servos on (assisted, no release).

The displacement is applied at state 5005. CNS seeds are 1, 2 and 3, set by replacing
`brain.rng` at attach, as in the confirmation test. Each arm runs once, in a fresh
process.

## Arms (per seed s; 9 arms, about 45 minutes)

| Arm | Displacement at 5005 | Coxa channels |
|---|---|---|
| `P0_s` | yes | none |
| `PC_s` | yes | H1 `joint_LMCoxa`, `joint_RMCoxa` only (D2 definitions by hash; hypothesis-labelled session path) |
| `PF_s` | yes | H1_FLIP of the same two channels |

**Comparisons.**
- Neural comparisons are PC vs P0 and PF vs P0.
- For the before-displacement prefix, `P0_s` is compared with the existing coxa-admission
  arm `C0_s` (raw files local; hashes are in that report).

## Integrity (all required, else `INCONCLUSIVE_INTEGRITY` with no labels)

1. **I1 Completeness.** All 9 arms are COMPLETE, with 20,001 samples and 4,000 ticks.
2. **I2 Common random numbers.** Within each seed, the arms have identical per-tick
   uniforms and schedule.
3. **I3 Reproduction.** `P0_s` equals coxa-admission `C0_s` (with matching hashes) in fired
   spikes, uniforms, hair deliveries and qpos through state 5005.
4. **I4 Displacement verified.**
   - The event happens at state 5005 with operation `SHIFT_SERVO_EQUILIBRIUM`.
   - The after-record sha equals the expected record. The model is unchanged before the
     event.
   - The applied Δ values equal the protocol values.
5. **I5 Channels and bounds.**
   - The v3 inventories are identical in every arm.
   - P0 has no hypothesis channel and never changes the LM/RM Coxa commands.
   - PC and PF have exactly the two channels, with the declared definition hashes.
   - Every offset satisfies |c| ≤ 0.25 rad.
   - Other commands equal P0.
6. **I6 Prefix.** PC and PF equal P0 until their first coxa command.
7. **I7 Seeds applied.** Tick-1 uniforms differ between seeds, and every arm records its
   seed.

**Context precondition** (separate status, `INCONCLUSIVE_CONTEXT`, no labels): in every
`P0_s`, the mean hair-plate rate in the window is ≥ 30 Hz in both LM and RM. If the
displacement does not make the middle hair plates fire, the loop has not been tested.
The design then records that, and the displacement is not changed.

## Measures (window 520–2000 ms)

- **Per middle leg:** the mean coxa forward component f (Step B geometry), and
  df = f(arm) − f(P0_s).
- **Reported:**
  - hair-plate rate per leg;
  - coxa MN rates per leg;
  - commanded offsets and their near-bound fraction;
  - first coxa command;
  - first physical divergence;
  - body tilt;
  - all other legs' f, as cross-leg effects.

## Labels (per coordinate, decided by these rules only)

A **seed passes** for leg L if df(PC_s) ≤ −0.02 **and** df(PF_s) ≥ +0.02. This is the same
bar and the same two-sided rule as the coxa confirmation.

| Label | Rule |
|---|---|
| `C2_PASSED` | 3 of 3 seeds pass |
| `C2_PARTIAL` | 1 or 2 seeds pass |
| `C2_NOT_SUPPORTED` | 0 seeds pass |

**Flags (reported with the label):**

- `BOUND_LIMITED`: the offset is within 0.01 rad of 0.25 in more than half of the
  window samples, in any PC or PF arm.
- `ROLLOVER`: any rollover sample, as in the admission test.
- `NO_DRIVE`: the PC command for the coordinate never changes in any seed. The loop then
  never acted, and the result is input-limited, like RF.

**Reported, not labelled: graded feedback.** Does the hair-plate rate fall in PC and rise
in PF, relative to P0? Unlike LF, the middle-leg encoder may not be pinned at saturation,
so this is the first chance to see the sensor respond to the loop's own correction in both
directions.

## What each outcome means (declared now)

| Label | Consequence |
|---|---|
| `C2_PASSED` | The coordinate is marked "C2 passed, awaiting C3". The next step is a separately preregistered C3 confirmation on CNS seeds 4–6 (on approval). |
| `C2_PARTIAL` | Recorded. No status change, and no follow-up is implied. |
| `C2_NOT_SUPPORTED` | The coordinate is recorded as NOT_SUPPORTED for H1 in this context. |
| `NO_DRIVE` | Recorded as an input limit. |
| `INCONCLUSIVE_CONTEXT` or `INTEGRITY` | No status change. |

In every case:
- no weights, thresholds, gains, mappings or seeds change;
- motor coverage stays 20/42 admitted, +2 conditional;
- `COXA_COORDINATE_STATUS.md` gets the evidence line.

## Predictions (expectations, not criteria)

- **The context precondition is likely to pass.** The target is one band past saturation.
- **RM: C2_PASSED is more likely than not.** It has the largest direct hair-plate pool
  (1,056 synapses), and the released-posture KF arms showed that middle hair plates
  recruit middle coxa MNs.
- **LM: lower confidence.** Its posterior MNs carry net inhibition at rest (−5 to −7). That
  could make it `NO_DRIVE` or `C2_PARTIAL`.
- **Graded feedback is likely to be visible,** at least in PF: the hair-plate rate stays
  high or rises while the coxa is pushed further forward.

## Limits

- **Engineering perturbation.** The displacement is imposed through the servo
  equilibrium. It is a probe stimulus, not a biological input or a behaviour.
- **Assisted context and offset-on-servo actuation.** A "push back" is a shift in the
  servo setpoint, as in every coxa test so far.
- **Walking-derived encoder threshold.** The modeled transduction is unchanged.
- **One body model, three seeds.** The seeds vary only stochastic sensory timing.
- **C2 only.** Nothing becomes CONDITIONAL from this test. Balance and gait are not
  addressed.

## Build and run plan (on approval)

1. **Protocol.** Write `docs/evidence/middle-coxa-displacement-v1/protocol.json` with:
   - the Δ values and their derivation;
   - the expected after-record rule;
   - the channel hashes, seeds and C0 references;
   - integrity, the precondition and the labels.
2. **Code.** Write `malecns_backend/live/middle_coxa_displacement.py`. It reuses the coxa
   confirmation test's seeded Trial and channel loading (with the candidate set
   `joint_LMCoxa`, `joint_RMCoxa`), the D3 session path and the Step C event boundary,
   and adds the equilibrium shift. `assistance_native` stays unchanged.
3. **Tests.** Write `tests/test_middle_coxa_displacement.py` using synthetic model arrays
   and arms. It covers:
   - the bias shift and the exact after-record;
   - df and the seed rule;
   - the labels and flags;
   - each integrity fault and the precondition.
4. **Smoke.** Run 5,100 steps for `P0_2` and `PC_2` to check the event and the
   inventories, then discard them. Commit and hash-lock.
5. **Run.** Each of the 9 arms once (about 45 min), then the evaluation once. Write the
   results, the status evidence, the handoff and the roadmap.
