# LF selective actuation/state-ownership contract v1

Prospective static audit, 2026-10-25. Baseline origin/newBrain 5a3c8c4 (merged
PR #271). Commit this specification, audit and tests before generating the new
audit record. This update reads historical metadata and validates a design; it
does not instantiate a model, call native forward/integration, initialize CNS,
change gains or actuate the fly. No production hook or coupling permission.

## Evidence and exact identity scopes

Reuse the locked M5A full_leg_interface_audit.json for all 42 action coordinates,
compiled joint/actuator IDs, joint transmission types/IDs and qpos/DOF ranges.
Its existing content hash is 758850ea659e49fd93a36a9606bea07a1d329739fbf6be8089060ee6d706c52e.
Canonical inspection of historical JSON is not a waiver of any raw-byte lock.
Rebuild the current 20/42 admission table using the existing static reference
helper and original mapping authorities, without their live enumeration path.

Separately inspect the recorded candidate_motor_channel_experiment/attempt_004
report, canonical SHA256
0629d05f9bf4c21cd911ac5f43f8f4518db3be5706daaf4d2f23991463645199.
Use the fixed path candidates/joint_LFTarsus1/initialization/ENABLED/
physics_model_identity/components. It records dimensions, full actuator name
inventory and array hashes, not the arrays' values. Keep this scope separate
from M5A: matching local names/order does not prove native IDs/transmissions or
whole-model equivalence across snapshots. Do not reconstruct values from names
or hashes, invent current native addresses, or initialize physics to fill gaps.

Require the original accepted activation-integrator record's exact raw hash
cd545ca6863b2d2468da067b258d9aac0ecb7f3ab8a953f15c0d6574f62eb49b
and its saved evaluation through existing source validators. Copy the four source
actuator/tendon IDs and activation addresses from that record, explicitly in its
zero-DOF source fixture scope. Those addresses are not FlyGym addresses.

## Selective replacement design (no mutation in this update)

The target basis is the existing force-reference order: LF Coxa_yaw, Coxa,
Coxa_roll. Enumerate each exact action index, recorded compiled joint/actuator
name and ID, transmission, qpos/DOF range, and current neural-admission decision.
Preserve all 39 other joint controls (including all 20 currently admitted motor
coordinates and 19 baseline position controls). Account separately for the six
adhesion actuators in the 48-name historical model: disabled/constant zero must
remain so. Do not present these six as extra motor-coordinate admissions.

Proposed future neutralization: after CURRENT exact-native validation establishes
the three selected joint transmissions and fixed-gain/affine-bias semantics,
zero ONLY their full actuator_gainprm and actuator_biasprm rows in an isolated
experimental model. Never apply this to production in this update. Preserve the
other 45 actuator parameter rows, order/IDs, sensors, passive mechanics, geometry,
contact configuration and source muscle parameters. Do not remove/reindex
actuators or globally disable a shared actuator group.

Setting selected ctrl=0 is not sufficient: a position spring's bias can still
apply torque. Nor does an admission flag remove the physical position actuator.
A future native test must verify selected actuator force and selected contribution
to qfrc_actuator are zero across independently specified q/qvel/control probes,
with all retained parameter rows and controls unchanged. Baseline/reference/matched
experimental arms must use the same declared replacement context; do not silently
compare a neutralized model with the unmodified production model.

The current static audit can verify the partition and reject unsafe plans; it
CANNOT verify neutralization or force support from hashed array metadata alone.
The M5A record lacks body IDs and activation addresses; record these as unavailable,
not fabricated. The later historical 48-actuator signature has na=0, so it owns no
native activation states, but its full native address/transmission values and a
current-context capture remain prerequisite evidence.

## Proposed state ownership and timing

Four source muscle activations would live in a separate external vector with
source-fixture IDs/addresses used only for interpretation. NEVER index FlyGym
data.act with source addresses. The pure existing integrate_interval solver can
advance that vector over a held-control interval; the existing zero-DOF
advance_fixed_fixture adapter must continue to reject a moving body.

For a future explicitly specified split scheme at state n:

1. Read q_n/v_n and external a_n. Compute total source tension (active plus passive
   and control-floor preload) at a_n and the registered geometry; project with
   the established covector convention into ONLY the three resolved target DOFs.
2. Solve the external activation interval with unchanged source law/parameters.
   Hold projected left-endpoint torque for the body interval. This is a proposed
   first-order coupling scheme, not validated by the fixed-length Radau result.
3. The existing native body stepping path owns body qpos/qvel/time and advances
   one declared body interval. External code must not advance body data.time or
   integrate native data.act, add native muscle states, or perform a second step.
4. Commit external a_(n+1) once after successful body advancement; observe state
   and force with declared timestamps. Audit time delta, state ownership and call
   counts at native boundaries, not merely one high-level sim.step invocation.
5. Clear only the exact owned force contribution after use. Preserve unrelated
   applied forces. Reject unregistered competing forces on target DOFs, stale
   ownership or duplicated contributions. No blanket qfrc/xfrc zeroing. On body
   failure, retain attempted external/physical states and stop; no rollback/retry
   claim after possible native advancement.

This design has not been executed or validated on a moving model. Force units,
finite-angle physical registration, velocity/length dependence and coupled
numerical convergence remain unvalidated. All four source-class hypotheses stay
distinct from individual neuron-to-tendon assignments and neural-to-activation
conversion. Broad promotors remain excluded. No inferred biological force scale.

## Static acceptance and output

Require unchanged source hashes, exact 42-coordinate/action ordering and unique
native IDs within M5A, three exact target hinge transmissions/ranges, 39 retained
joint controls, 20 retained admissions, 19 retained baseline controls, and six
separately scoped adhesion name IDs. Require accepted source activation record
with exact four identities/addresses. Validate the proposed patch scope and single
external/body ownership tokens; reject whole-group disabling, ctrl-zero-only,
actuator removal, extra parameter rows, native+external muscle integration,
foreign-force clearing, production enablement or any claim of coupling readiness.

The audit verdict is STATIC_CONTRACT_VERIFIED_COUPLING_BLOCKED when all static
checks pass. Coupling readiness remains FALSE and blockers remain explicit:
current complete native inventory/body/activation/transmission/force-support
tables; native selective-neutralization/preservation evidence; coupled numerical
and force-unit/geometry evidence; original raw scientific prerequisites;
individual binding and neural conversion. No raw hash refresh or new admission.

Save JSON exclusively in a new directory; save source hashes before/after.
Saved review rebuilds the static result and requires exact equality. Tests forbid
FlyGym construction, live actuator enumeration, MuJoCo model/forward/step/muscle
derivative, CNS initialization and numerical solver calls during build/review.
Any malformed identity/unsafe plan is rejected, not silently downgraded to PASS.

Next bounded update: separately specify and capture a current native inventory
and run a no-integration selective-neutralization/preservation audit with native
forward probes and exact operation accounting. This would test an engineering
prerequisite, not authorize moving-fly neural coupling. No Unity run yet.

Report roadmap position after each run: current 20/42, what this result does and
does not establish, the active gate and next concrete task. Full fly balance and
walking still require later controlled evidence.

References: [MuJoCo actuator gain/bias semantics](https://mujoco.readthedocs.io/en/3.2.7/XMLreference.html#actuator-general),
[native model identity and address tables](https://mujoco.readthedocs.io/en/3.2.7/APIreference/APItypes.html).
