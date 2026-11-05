# Antennal gravity sense, Step B: kinematic JO C/E encoder (design, V1)

Designed 2026-11-05. This is the design only. No code exists, nothing has run, and no
protocol is locked yet. On approval, the rules below are copied into
`docs/evidence/antennal-gravity-encoder-v1/protocol.json` and hash-locked before any run.
Step B is geometry only. It uses no CNS and does no physics stepping. It mirrors the
hair-plate Step B (`HAIR_PLATE_ENCODER_V1.md`).

**Status 2026-11-05:** Step B was preregistered (2e2def7, protocol 0e97fe33…), run once and
evaluated once: `ENCODER_READY`. Rest d is −0.144 on both sides, so E fires at 17.2 Hz under G1.
The pitch slope is 0.965 per rad and the roll slope ±0.215 per rad; all three predictions held.
See `ANTENNAL_GRAVITY_ENCODER_RESULTS.md`. The text below is unchanged.

The parent track design is `ANTENNAL_GRAVITY_SENSE_V1.md`. Step A (`IDENTITY_READY`) is
reported in `ANTENNAL_GRAVITY_IDENTITY_RESULTS.md`.

## Facts inspected for this design

These are body-model facts only. No encoder output, rate or tilt response was computed.

- **The antenna's geometry, from the MJCF** (`neuromechfly_seqik_kinorder_ypr.xml`, FlyGym
  1.2.1). Positions are in the pedicel or funiculus frame, at zero pose; L/R mirror in y.

  | Point | Value |
  |---|---|
  | Funiculus (a3) centre of mass, from its joint anchor | (0.013, ∓0.002, −0.091) |
  | Arista origin, in the funiculus frame | (0.020, ±0.054, −0.068) |
  | Arista centre of mass, in the arista frame | (0.019, ±0.085, 0.017) |

  So a3 hangs ventrally from the pedicel and the arista projects laterally. This matches
  the textbook arrangement, in which a3 rotates about its own long axis and the arista acts
  as a lever. That arrangement is a recalled reference claim (Göpfert & Robert; Kamikouchi
  et al. 2009) and is treated as a modelling assumption.
- **The MJCF hinge axes are generic, not anatomical.** `joint_<side>Funiculus`, `_yaw` and
  `_roll` are an Euler decomposition about the parent frame's y, x and z axes. Their names
  say nothing about the JO rotation axis. The track design's outline proposed using the
  `joint_<side>Funiculus` (y) axis. **This design replaces that** with the geometric a3
  long axis (below), because the y axis is not the a3 axis.
- **Runtime stiffness (correction to the track design).** The track design said the antenna
  joints have zero stiffness. That is true in the raw MJCF only. The runtime builds
  `flygym.Fly` with defaults (`m7c_b2_pose_geometry_audit._make_sim`), which give every
  non-actuated joint stiffness 1.0 and damping 1.0. The antenna joints are therefore weak
  engineering springs, with no anatomical basis. The encoder does **not** read antenna
  joint angles. It reads the gravity direction relative to the antenna's current frame.
- **Head.** The head is **not fixed**. The neck joints are passive springs (FlyGym default
  `neck_stiffness` 10, damping 1.0) with no head stabilisation. The encoder reads the live
  head and antenna pose. Any passive neck motion is therefore part of the signal, as it
  would be in a fly.
- **Masses are not used.** The compiled arista mass (1.0e-6) differs from the XML value
  (1.1e-7), presumably because MuJoCo applies a lower mass bound. The signal below uses
  only positions (inertial centres), so it does not depend on mass.

## Signal (per antenna, per state)

All quantities come from the current MuJoCo state after `mj_forward`.

1. **Anchor:** a = the funiculus body origin. All three funiculus hinges sit at its origin.
2. **a3 long axis:** n̂ = unit(funiculus centre of mass − a). This points distally.
3. **Lever:** p = the arista centre of mass, and r⊥ is the component of (p − a)
   perpendicular to n̂.
4. **Tangent:** t̂ = unit(n̂ × r⊥). This is the direction the arista moves when a3 rotates
   about its long axis. Its sign is set so that t̂ · x̂_head ≥ 0, where x̂_head is the head
   body's anterior axis. Because the anterior direction is unchanged by a left/right
   mirror, the sign convention matches on both sides by construction.
5. **Drive:** d = ĝ · t̂, where ĝ is the normalised `model.opt.gravity`. d lies in
   [−1, 1]. **+d means gravity pulls the arista anteriorly.**

This is a static gravity-torque direction, not a deflection magnitude. Real antennal
stiffness and mass are not modelled, so the magnitude of a true gravity-driven deflection is
unknown. The rate scale below is an engineering choice.

## Tuning and zone sign

- **Rate:** tonic and one-sided per zone, using the existing encoders' 120 Hz engineering
  maximum. The "+" zone fires at 120 Hz × max(d, 0). The "−" zone fires at
  120 Hz × max(−d, 0). Every neuron of a set gets its set's rate. There is no threshold.
- **G1:** C is the "+" zone (arista pulled anteriorly) and E is the "−" zone.
- **G1_FLIP:** the zones are swapped.
- The G1 label is **arbitrary**. It is not a recalled zone sign. Step C's G1 vs G1_FLIP
  contrast is what tests the sign.

## Left/right handling rule (declared before any output is seen)

Step A found far fewer right-side output synapses than left (C 5.31×, E 2.54×, against
1.4× in neuron count). The rule, fixed now:

1. **Use the sets as reconstructed.** The populations are exactly Step A's four bodyId
   sets. The same d gives the same per-neuron rate on both sides. There is no
   per-side gain, normalisation, or synapse-count correction, because any of these would be
   a weight or gain change chosen to offset the data. The asymmetry is **labelled** as a
   reconstruction limit in every output.
2. **Primary quantities do not compare left with right.** Step B checks, and Step C's
   preregistered primary contrasts, will use either:
   - pitch-driven, bilaterally symmetric stimuli; or
   - within-side comparisons (OFF vs G1 vs G1_FLIP on the same side), or bilateral sums.

   No left-minus-right difference in CNS or motor output will be interpreted as roll
   sensing, because the asymmetric wiring alone could produce one.
3. **Roll is descriptive only.** Step B reports how d changes with roll on each side. With
   the a3 axis nearly vertical, d is expected to be mainly a pitch signal (see Predictions).

## Static stimuli (Step B)

The runtime is the exact B4 initialisation (`_windows_m7d_corrected_spontaneous_adapter.
_runtime`), as in hair-plate Step B. It sets imposed whole-body orientations only:
- the root free-joint quaternion is pre-multiplied by a world rotation;
- pitch runs from −30° to +30° in 5° steps (about world y) at zero roll;
- roll runs from −30° to +30° in 5° steps (about world x) at zero pitch;
- after each pose, `mj_forward` only, with no stepping;
- qpos is restored afterwards.

Neck and antenna joints stay at their initial values.

## Checks (all required for `ENCODER_READY`)

| Check | Rule |
|---|---|
| B0 frame | Run at the initial (rest) pose, per side. The head anterior axis points from Thorax to Head (fraction > 0.99, as in hair-plate). \|r⊥\| > 0. \|t̂ · x̂_head\| ≥ 0.7, so the anterior sign convention is well defined. Gravity is non-zero. |
| B1 identity | The four populations equal Step A's `result.json` bodyId sets exactly: C 31 L / 22 R, E 157 L / 110 R. |
| B2 bounded | d is finite and \|d\| ≤ 1 in every grid pose. |
| B3 mirror | In every zero-roll pitch pose, \|d_L − d_R\| ≤ 0.05. This checks geometry and sign convention, not neural symmetry. |
| B4 pitch response | On each side, d is strictly monotonic over the pitch grid. |

**Verdict:**
- `INCONCLUSIVE` if B0 fails, because the frame or sign is ill-posed;
- `ENCODER_READY` if B0–B4 all pass;
- `NOT_READY` otherwise.

## Reported, not gated

- The rest-pose d and the per-set rates under G1 and G1_FLIP, with the label "left/right
  synapse asymmetry, as reconstructed".
- d against pitch and against roll, per side. Slopes are measured at 0 by central
  difference.
- d_L − d_R over the roll grid. If it stays small, the sense cannot report roll, and the
  report says so.
- n̂ and t̂ in the head frame at rest.

## Predictions (recorded now; they are not checks)

They come from hand arithmetic on the zero-pose MJCF positions above. No runtime state, no
B4 pose and no rate was computed. In the zero pose, t̂ ≈ (0.97, ∓0.22, 0.14) in the
head frame, left/right.
- **Level stance:** d is small, about −0.1 to −0.2, because the a3 axis tilts about 8° from
  vertical. Under G1, the E sets fire at a low tonic rate and C is silent. The runtime head
  pose may shift this.
- **Pitch:** nose-down pitch gives gravity a +x component in the head frame, so d rises
  steeply (slope near 1 per radian) and the G1 C sets fire.
- **Roll:** the response is weaker, with a slope magnitude of about 0.2 per radian, and of
  opposite sign on the two sides. That gives a small roll channel, which the L/R rule keeps
  descriptive only.

If any of these is wrong, it is recorded as wrong.

## What Step B can and cannot show

- **Can:** that a defined, mirror-consistent, pitch-sensitive gravity drive exists for the
  exact JO C/E sets, before any CNS exposure.
- **Cannot:** show function, the true zone sign, or the deflection magnitude. Nor does it
  show that the CNS uses the signal, which is Step C. It changes no motor coordinate status
  (20/42 admitted, +4 conditional).
- **Modelling assumptions:**
  - the a3 long axis is taken from the mesh inertial centre;
  - the arista centre of mass is taken as the lever point;
  - the two zones are treated as a single tonic, one-sided split.

## Build and run plan (on approval)

1. Write `docs/evidence/antennal-gravity-encoder-v1/protocol.json` with the signal,
   tuning, the L/R rule, the grids, B0–B4 and the predictions. Hash-lock it in code.
2. Write `malecns_backend/embodiment/antennal_gravity_encoder.py`:
   - reuse Step A's `antennal_gravity_identity.populations` and the hair-plate runtime
     path (`_runtime`, the exclusive `--output` write);
   - provide an `encode(data)` and `apply(brain, encoded)` pair, shaped like the
     hair-plate encoder's, for Step C.
3. Write `tests/test_antennal_gravity_encoder.py`. It uses a toy MuJoCo body with a known
   a3 axis and lever, and covers the sign convention, mirror, bounds, monotonicity and every
   check boundary.
4. Run smokes, which are discarded. Commit and push the preregistration. Run once
   (seconds), evaluate once, and record the results, handoff and roadmap.
