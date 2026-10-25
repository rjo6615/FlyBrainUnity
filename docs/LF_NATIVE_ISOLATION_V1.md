# LF native position-actuator isolation v1

Prospective engineering protocol, 2026-10-25; baseline origin/newBrain a50ef0b,
merged PR #272. Commit protocol, input manifest, runner and implementation tests
before the single native campaign. No retries, changed probes/tolerances or gain
fitting after outcomes. Preserve failures/partial data. Production remains20/42.

## Context and immutable inputs

Re-verify the existing static contract and accepted source records, without live
enumeration. Pin installed package versions and local FlyGym scientific files,
native MuJoCo binaries and relevant dm_control construction/reset sources in
docs/evidence/lf-native-isolation-v1/input-manifest.json before outcomes. Do not
install or alter dependencies. Use MuJoCo3.2.7/FlyGym1.2.1/dm_control1.0.27.

Reuse tactile_motor_loop_audit._make_live(flygym,{}) exactly: one position-control
Fly with adhesion disabled, existing calibrated arena/contact placements, one
SingleFlySimulation and its existing reset/surface placement. No new initializer,
surface fitting, CNS or ordinary live run. Source inspection predicts **7 explicit
mj_forward and3 mj_resetData** calls during this initializer: one construction
after_reset, two construction pose-reset forwards, one explicit reset forward,
two reset pose-context forwards and one surface-placement forward. Count these
separately from probes, starting before construction; compiler-internal native
work is outside Python API accounting. No mj_step/mj_step1/mj_step2 or mj_Euler/
mj_RungeKutta/mj_implicit calls are permitted at any phase. Record and fail on an
unexpected count rather than silently changing accounting. No simulation step.

## Current native identities and preservation

Reuse physics_model_identity for complete numeric model/option/sensor/name hashes
and the existing compiled-name/namespace and resolve_dof observers for identities.
Supplement with explicit native actuator, joint, body, activation and sensor tables;
do not copy historical IDs. Public ordered42 action names must match the existing
authority. Resolve exact qualified native joints and position actuators, require
unique one-DOF hinge joint transmissions, same attachment namespace, unit gear,
fixed gain and affine bias, no activation dynamics (actadr=-1,actnum=0), na=0.
Resolve six adhesion actuators separately by exact identities and body transmissions.

Keep all48 actuator slots and all39 retained joint controls (20 admitted+19
baseline), plus six disabled/zero adhesion controls. Capture full gain/bias/control,
transmission and activation tables; joint/body/address/axis tables; sensor identity
tables; initial state and full model/option identities. Source muscle constants
are not changed. No source-force application or neural conversion in this assay.

After baseline comparisons, zero ONLY full gainprm and biasprm rows of the three
resolved LF proximal position actuators in this isolated model. Verify every other
numeric model field/option/name unchanged and every other45 gain/bias rows exactly
unchanged. Restore exact original rows after probes; verify full model identity
restored before closing. No actuator deletion/reindex or global-group disable.
This is suppression of engineered position forces, not muscle/neuronal tuning.

## Fixed probe inventory

Nine probes, each applied identically to three arms:
BASELINE, CTRL_ZERO_ONLY (selected control=0, native position parameters intact),
NEUTRALIZED (selected gain/bias zero, all controls same as BASELINE).

Start from captured reset qpos, zero qvel, empty act, time0 and zero external forces.
All42 position controls equal each corresponding probe qpos plus alternating
signed .01rad offsets (+ for even action index, - for odd); adhesion controls0.
These are diagnostic inputs, not neural commands or behavior control.

1. CENTER: reset qpos, zero velocity.
2. YAW_PLUS/YAW_MINUS: target yaw position +/- .05rad, others at reset.
3. PITCH_PLUS/PITCH_MINUS: target Coxa position +/- .05rad.
4. ROLL_PLUS/ROLL_MINUS: target Coxa_roll position +/- .05rad.
5. VELOCITY_PLUS/VELOCITY_MINUS: reset qpos; target yaw/pitch/roll velocities
   respectively +/-[.1,-.1,.1]rad/s; other velocities0.

Each arm/probe gets fresh native MjData, declared inputs and exactly ONE
mj_forward. Store before/after qpos/qvel/act/ctrl/time/applied forces plus native
actuator force/length/velocity, qfrc_actuator/passive/constraint, qacc and sensors.
Reuse the validated dense_moments native CSR conversion and independently saved
CSR evaluator. Preserve sparse descriptors and dense force-support rows; do not
reshape sparse actuator_moment as dense. Native generalized actuator force must
equal moment.T @ actuator_force. Different qacc/constraint/sensor output after
suppression is an allowed forward-computation outcome, not body advancement.

27 probe forwards +7 initialization = **34 explicit mj_forward**,3 reset calls,
zero integration/CNS transitions. Fresh data allocation is not a native reset.
Record partial cases on exceptions, restore model rows in finally, close stack.

## Acceptance fixed before outcomes

All nine probes in all three arms, finite values and complete identity/array
records. Exact current identities above; no hidden initialization steps. Inputs
and body state remain exactly as prescribed with time0. Raw controls are in their
source ranges; no clipping/auto-adjustment to obtain acceptance. Model/parameter
preservation is exact; native/CSR force projection absolute tolerance1e-8.

For EVERY probe, NEUTRALIZED selected actuator forces AND total qfrc_actuator on
the three target DOFs must be <=1e-10 absolute. The other45 actuator forces must
equal BASELINE within1e-10; projected force difference must be zero outside target
DOFs within1e-10. Complete moment matrices and passive generalized forces must
match baseline exactly. Each selected baseline actuator must have >1e-8 absolute
force in at least one probe, to rule out vacuous suppression. Capture current
force support; reject other active actuator contributions on selected DOFs.

CTRL_ZERO_ONLY is a mechanism comparison: at least one declared probe must have
nonzero selected position force >1e-8 despite raw ctrl0, or label that comparison
inconclusive. It is never a substitute suppression arm. Keep all individual forces
and decisions. Never change the probe after inspecting that comparison.

Verdict NATIVE_ISOLATION_VERIFIED_COUPLING_BLOCKED only if all integrity,
non-vacuity, comparison and suppression/preservation checks pass. Otherwise retain
NATIVE_ISOLATION_FAILED with complete failure evidence. Saved review rechecks
source locks, current tables, identity hashes and stored force/state/CSR algebra;
it must perform no model construction, reset/forward/integration or CNS work.

## Limits and next gate

This tests engineering isolation at fixed instantaneous inputs. No body motion,
muscle coupling, current biological force scale, anatomical registration, individual
binding, neural activation law, balance or walking result. Original raw prerequisites
remain separate/false where recorded. The old zero-DOF Radau adapter stays restricted.

After an accepted result, next separately specify a synthetic coupled-state/force-
buffer ownership and numerical convergence experiment, retaining the source law
and this explicit replacement context. Do not connect to production or bypass
physical/neural/raw gates. Report roadmap after each run; current20/42. No Unity
run is needed for saved review.

References: [MuJoCo3.2.7 actuation](https://mujoco.readthedocs.io/en/3.2.7/computation/index.html#actuation-model),
[native model tables](https://mujoco.readthedocs.io/en/3.2.7/APIreference/APItypes.html).
