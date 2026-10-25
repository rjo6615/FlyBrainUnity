# LF native target orientation-registration assay V1

Prospective protocol, 2026-10-25; baseline `origin/newBrain` 9553c77 (merged PR278).
Commit this protocol, implementation and reference tests before the one archived
campaign. No gain/axis/offset/pose/tolerance search, unversioned retry or omitted
failed samples. Source model, old local registration and all prior evidence stay
unchanged. This tests a modeled rotation convention, not anatomical muscle paths,
length/velocity/force calibration, neural activation or biological balance.

## Reused authorities and fixed inputs

Verify the V1 unit-lineage audit and prior transfer/software/native-source checks.
Re-evaluate the existing accepted source pose record with its original evaluator
and raw lock. Reuse its complete ordered 15 offsets: center, minus/plus0.05rad
on each source coordinate, all eight lexicographic corners. Reuse its saved
source rotations, instantaneous axes, +/-1e-6rad observations and original
`lf_pose_force.rotation_map/transfer`. No source model is compiled or rerun.

Construct one native body through the existing `_make_live(flygym,{})`, unchanged
position controls/arena/adhesion-disabled support context. Existing native input
manifest and full normalized baseline model/state identity must match the accepted
native-isolation record. Reuse inventory, exact actuator/joint/body/address and
model identity validators. LF order is yaw, pitch (`joint_LFCoxa`), roll: joint
IDs1/2/3, qpos7/8/9, DOFs6/7/8, shared `LFCoxa` body13, actions2/0/1. Resolve
the unique `Thorax` by the same namespace authority and require it is an ancestor.
No names-only inference of physiological function is made.

## Frames, reference and probes

Each observation uses fresh native data. Copy the full initialized qpos, replacing
only the three selected LF scalar qpos entries. Every other coordinate remains
at initialization. Set all qvel, act, ctrl, applied generalized/body force buffers
and time to zero. Preserve model parameters exactly; controls are merely unused
input data, not an actuator-suppression experiment.

Reference observation has all three selected qpos exactly zero. Let T be the
observed thorax world rotation and C the observed LFCoxa world rotation. The
thorax-relative coxa frame is F=T^T C. For an observation, native delta is
D_native=F(q) F(0)^T; native instantaneous basis is B_native=T^T xaxis_LF^T.
This expresses the native target in the documented thorax anatomical frame.
No best-fit alignment or sign/axis permutation is estimated from outcomes.

The old modeled map supplies q_G, delta D, B_G and J at each source pose. Set
the three native target coordinates to q_G directly (zero target reference,
not initialized tripod angles). Record orientation and basis at:

- One base sample per pose.
- Six target-coordinate samples q_G +/-1e-6rad, using the inherited epsilon.
- Six chain samples: map each already-saved source +/-1e-6rad rotation with the
  original map, then observe the native target at those mapped coordinates.

Exactly 1+15*(1+6+6)=**196 explicit `mj_kinematics` calls**. No `mj_forward`,
reset or integration calls in the probe phase. The reused initializer is expected
to record7 explicit forwards and3 resets, zero integration, as in native isolation.
Count/fail on all six integration entry points through the existing native API
accounting wrapper. Probe-phase forward/reset are forbidden; no forces need to
be computed in these probes. Compiler-internal calls are not explicit Python API
counts. Record every native input state before/after, both frames, world axes,
joint bounds, model identities, source hashes and installed-file checks.

## Fixed integrity and numerical decisions

Require the exact whole pose/sample inventory, API counts, proper finite frames,
unchanged model/initializer state/sources, exact selected addresses and preserved
full probe state. All observed times/velocities/activation/control/applied forces
stay zero. Thorax frame remains fixed. Record target joint-limit checks for ALL
196 observations, including differences; do not clamp or replace a pose.

Use the previous source assay's absolute rotation/basis precision1e-10, derivative
precision1e-7 and conditioning bound<100. These are engineering reference budgets,
not biological error limits; fixed before this native campaign.

- Native zero-pose basis versus original registered B_G=I: <=1e-10 max component.
- D_native versus old source-derived delta: <=1e-10 matrix error at every pose.
- B_native versus old modeled B_G: <=1e-10 max component.
- Target symmetric orientation finite difference (rotation vector of Fplus Fminus^T
  divided by2epsilon) versus native axes: <=1e-7 max component.
- J_native=solve(B_native,B_M) versus old modeled J: <=1e-7 max component.
- Chain finite differences of native target frames versus source B_M: <=1e-7.
- Every native basis and J condition number<100; no gimbal/singular substitute.

Integrity failure is `TARGET_ORIENTATION_INTEGRITY_FAILURE`, with evidence kept.
If intact but any prescribed sample violates a native joint range, classify
`TARGET_ORIENTATION_OUTSIDE_NATIVE_LIMITS_TRANSFER_BLOCKED`, regardless of errors.
If intact/in-range but numerical comparisons fail, classify
`TARGET_ORIENTATION_DISAGREEMENT_TRANSFER_BLOCKED`. Only intact, in-range and all
comparisons passing yields `TARGET_ORIENTATION_GEOMETRY_VERIFIED_TRANSFER_BLOCKED`.
Saved review must reproduce the recorded evaluation even for a negative result.
No scientific pass is required for a successful evidence-verification command.

## Limits and next decision

This is native forward kinematics, not a moving-fly experiment or Unity test.
Positions at prescribed coordinates are interventions, not neural motor outputs.
Even accepted orientation agreement does not validate tendon attachments, moment
arms on the moving target, length/velocity/force units or independent balance.
Unit/conversion lineage, individual anatomical binding, neural-to-activation and
original failed raw prerequisites remain gates; production stays20/42.

If geometry disagrees, localize the frame/reference/axis issue from the retained
raw measurements before proposing a separately versioned correction. If verified,
next inventory target attachment/length-velocity requirements against the source
paths without inventing force scaling. No automatic muscle coupling or admission.

MuJoCo's [3.2.7 data-field reference](https://mujoco.readthedocs.io/en/3.2.7/APIreference/APItypes.html#mjdata)
identifies `xmat` as body-frame orientation and `xaxis` as Cartesian joint axes.
Use body frames, not inertia-frame `ximat`.
