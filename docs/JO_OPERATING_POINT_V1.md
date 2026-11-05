# Antennal gravity sense, Step C2: where does the live JO operating point come from? (design, V1)

Designed 2026-11-05. This is the design only. No code exists, nothing has run, and no
protocol is locked. On approval, the rules below are copied into
`docs/evidence/jo-operating-point-v1/protocol.json`, hash-locked in code, and committed
before any analysis runs.

Related documents:
- the encoder, `ANTENNAL_GRAVITY_ENCODER_RESULTS.md` (Step B, `ENCODER_READY`);
- the live run, `ANTENNAL_GRAVITY_LIVE_RESULTS.md` (Step C, G1 CONSISTENT, FLIP WEAK).

## Why this step

In Step C, the recorded JO drive d did not sit where Step B's level-head geometry put it.
Already-recorded values in OFF_UP_13:
- 0.5 ms: d = −0.144 (exactly Step B's rest value);
- 250 ms, before the tilt: d ≈ −0.17;
- after the nose-up tilt: d drifted from −0.34 to about −0.38.

As a result, the nose-down tilt only brought d to about 0, so each assignment modulated only
one zone. **Before any design that tries to engage both zones, the cause of this offset has
to be known.** The possible causes have different scientific status:

| Source | Status in this model |
|---|---|
| Body (thorax) orientation relative to gravity | a genuine postural state of the assisted-posture context |
| Neck sag: the 3 Head joints, passive, stiffness 10, spring reference 0 | a model limitation; real flies stabilise the head actively, and this model has no neck motor control |
| Antenna sag: Pedicel (a1–a2) and Funiculus (a2–a3) joints, passive, stiffness 1.0 | FlyGym defaults, uncalibrated. The a2–a3 joint is the anatomical JO joint, so its deflection is the model's closest analogue of what JO actually transduces, but its stiffness is not fly data. |
| Arista joint (lever direction) | passive, stiffness 1.0, uncalibrated |
| Gravity direction (the declared tilt) | the intervention |

This is an **attribution of recorded geometry**, not a new experiment. It runs no CNS and no
physics stepping. It only replays recorded qpos through `mj_forward` in the exact Step B
runtime model.

## Inputs (locked by hash)

- The 36 seed arms of Step C, raw `.json.gz` in
  `docs/evidence/antennal-gravity-live-v1/run/`, each verified against its sha256 in
  `run/report.json` (sha 515f66dd…). REPRO_N0_7 is not used (it has no JO record).
- The model: `adapter._runtime` as used by Step B, and `AntennaFrames.drive`, unchanged.

The model's kinematic chain from root to arista was listed before this design (structure
only, no outcome computed):

> free root (qpos 0–6) → Head yaw/pitch/roll (73–75) → Pedicel (76–78 L, 85–87 R) →
> Funiculus (79–81 L, 88–90 R) → Arista (82–84 L, 91–93 R)

d depends only on the root orientation, these 12 joint coordinates per side, and gravity.
Leg joints and root position do not enter.

## Method

**Factors** (per side), six in total:
1. **ROOT:** root orientation quaternion (qpos 3–6).
2. **NECK:** the 3 Head joints.
3. **A2:** the 3 Pedicel joints (head to a2).
4. **A3:** the 3 Funiculus joints (a2 to a3, the JO joint).
5. **ARISTA:** the 3 Arista joints.
6. **GRAVITY:** the recorded gravity vector.

**Reference state:** stored state 0 of the same arm (its qpos and gravity (0, 0, −9810)).
d at state 0 must equal Step B's rest value to 1e-6.

**Attribution:** an exact Shapley decomposition of d(target) − d(reference) over the six
factors. Each factor is either at its reference or its target value. The 64 subsets are each
evaluated with `mj_forward`, and the result is weighted by the standard Shapley weights.
- The six contributions sum exactly to the total change. That is checked to 1e-9.
- No ordering is privileged.

**Targets**, per arm and side:
- **T_pre:** stored state 5005 (500.5 ms), the last state before the tilt. Gravity is still
  untilted, so GRAVITY contributes exactly 0.
- **T_win:** every 50th stored state from 5200 to 20000 (520–2000 ms; 297 states). The
  contributions are averaged over these states.

**Descriptive (not labelled):**
- the A3 (a2–a3) joint angles at each target;
- the head pitch relative to the thorax;
- the thorax pitch relative to the current gravity;
- for UP and DOWN separately, d at T_win in DOWN minus UP, decomposed the same way. That
  shows how much of the tilt contrast came from the gravity rotation itself and how much
  from posture that changed after it.

## Integrity (all required, else `INCONCLUSIVE_INTEGRITY` with no labels)

1. **J1 Inputs.** All 36 arm hashes equal the Step C report.
2. **J2 Replay fidelity.** At every neural tick in every arm, d recomputed from the recorded
   qpos and gravity of that tick's state (the stored state the live encoder read, taken from
   the Step C code before the run) equals the recorded `jo_d` on both sides to 1e-9.
   This also confirms that the replay uses the same model as the live run.
3. **J3 Reference.** d at state 0 equals −0.14359 (Step B rest, to 1e-4) in every arm.
4. **J4 Additivity.** For every decomposition, the Shapley contributions sum to the total
   change to 1e-9.

## Labels (decided by these rules only)

For each question below and each side, compute every factor's share =
contribution / total change, per arm. Use the 36 arms for Q1 and the 18 nose-up and 18
nose-down arms separately for Q2.

| Label | Rule |
|---|---|
| `DOMINANT_<factor>` | That factor's median share is ≥ 0.5, and its contribution has the sign of the total change in ≥ 90% of the arms. |
| `MIXED` | No factor qualifies. |

If the total change has |median| < 0.01, the label is `NO_MATERIAL_DRIFT` instead, and no
share is computed.

- **Q1 (pre-tilt drift):** where does the change from state 0 to state 5005 come from?
  This involves no tilt, so it is about the resting operating point.
- **Q2 (window offset):** where does the change from state 0 to the window mean come from,
  for UP and DOWN separately? The GRAVITY factor here is the tilt itself. Anything else is
  posture that moved with or after the tilt.

## What each outcome means (declared now)

- **ROOT dominant:** the offset is a genuine postural state of the assisted-posture context.
  The next design should set its tilt range around the measured live operating point, for
  example tilts that make d cross 0. The encoder needs no change.
- **NECK dominant:** the offset comes from an uncontrolled passive neck. That is a model
  limitation and not fly physiology: real flies stabilise the head. Any step that relies on
  JO operating points should record this as a confound. Fixing it (neck motor control from
  the connectome, or a declared head constraint) would need its own design.
- **A2, A3 or ARISTA dominant:** the offset comes from passive sag of antenna joints with
  uncalibrated default stiffness. This matters most:
  - the a2–a3 joint is where JO transduces, so its deflection is a candidate *input
    variable* for a more anatomical encoder;
  - but its stiffness is not fly data, so its magnitudes are not physiological.

  A follow-up should compare the a3-orientation encoder with an a2–a3 joint-angle reading,
  and state that no stiffness is calibrated.
- **MIXED:** the factors are reported as they stand. Any follow-up must handle all of them.

In no case does this step change the encoder, the Step C labels, or any threshold. The
Step C result stands as recorded.

## Limits

- **It attributes geometry and nothing more.** It does not say whether the brain would act
  differently with another operating point.
- **Shapley attributions of a nonlinear function depend on the reference state.** Here the
  reference is state 0 of each arm, which is declared.
- **Step C's arms all run in one context.** Other contexts (free standing, walking) may
  differ.
- The joint stiffnesses are FlyGym defaults; nothing here calibrates them.
- No motor coordinate status changes: 20/42 admitted, +4 conditional.

## Build and run plan (on approval)

1. Write `docs/evidence/jo-operating-point-v1/protocol.json`.
2. Write `malecns_backend/embodiment/jo_operating_point.py`. It reuses `AntennaFrames` and
   the Step B runtime, and holds the replay, the Shapley decomposition, the checks and the
   labels.
3. Write `tests/test_jo_operating_point.py`. The synthetic tests cover Shapley exactness on
   a known function, additivity, label boundaries, `NO_MATERIAL_DRIFT`, and the integrity
   failures. One test checks that a model with only the root rotated is attributed fully to
   ROOT.
4. Smoke on one arm and a few states into scratch, discarded unread except for exit status.
5. Commit and push the preregistration, run once (minutes, geometry only), evaluate once,
   and record the results, the handoff and the roadmap.
