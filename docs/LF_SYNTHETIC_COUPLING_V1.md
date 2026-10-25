# LF synthetic split-coupling / force ownership v1

Prospective protocol, 2026-10-25. Baseline origin/newBrain c665480, merged PR #273.
Commit protocol, fixture, runner and tests before one campaign. Preserve every
grid/condition and numerical/integrity failure. No parameter/grid/acceptance search
or automatic retry after outcomes. No production, CNS or moving FlyGym coupling.

## Scientific question and explicit synthetic model

Does the proposed left-endpoint force-hold split scheme converge to the SAME
continuous model while advancing external activation and native body state once,
clearing only owned forces and preserving unrelated generalized/body forces?

Use four independent fixed-base hinge rotors, no geoms/contacts/actuators/native
activation, nq=nv=4. Sentinel inertia1, target yaw/pitch/roll inertias2/3/4. All COMs
at their hinge, isotropic body inertias, gravity/damping/friction/stiffness/armature0.
Thus exact mechanical equations are q'=v, I*v'=tau with constant diagonal I.
These are dimensionless engineering units, not fly mass/inertia/force calibration.
Names identify test coordinates, not anatomical attachment to this synthetic body.

Reuse source muscle derivative mju_muscleDynamics and existing pure Radau
integrate_interval (rtol1e-9,atol1e-12), source dynprm/control floor/gain/bias from
the locked source binding. Reuse force.load_reference and its existing R_G matrix
and four-tendon order. Define synthetic total tensions T=-(gain*a+bias) and target
torque=R_G*T. This deliberately REINTERPRETS the frozen source numbers in synthetic
units and holds the reference coefficients/length/velocity force law constant.
It is the same declared algebra in both split and independent continuous models;
it is not finite-angle source/FlyGym registration or a moving-muscle length law.
No fitted force scale, per-joint gain or new physiology. Keep passive bias/floor.

## State ownership and force buffer contract

Native body has nu=na=0. External activation is a separate copied vector, never
data.act. Resolve exact hinge/body/DOF/qpos metadata via the existing observer;
verify fixed synthetic inertias/mass matrix and no passive/contact actuation.
The older fixed-pose/zero-DOF adapters remain restricted and unmodified. A new
adapter is required only for this explicitly different moving synthetic context.

At each outgoing interval:
1. Snapshot a_n,q_n,v_n,t_n. Calculate T(a_n) and project with the existing covector
   convention into only the three target DOFs. Separately solve held-control
   activation for a_(n+1) with the unchanged pure Radau interval solver.
2. Apply one owned generalized-force contribution. Preserve a fixed foreign
   sentinel generalized force .125 and sentinel body z-torque .25 (total .375).
   Reject foreign target force/body wrench, stale/duplicate ownership or tampering.
3. Call native mj_step exactly once. Native Euler owns all body qpos/qvel/time;
   external code never writes body time or integrates q/v. Check semi-implicit
   updates v_next=v+h*tau/I, q_next=q+h*v_next and time increment h.
4. Clear only the owned contribution, leaving both foreign force buffers exactly
   intact. Refresh native forward outputs. Commit external a_next once after the
   successful native advance. Retain before/applied/cleared buffers and state,
   force timing, torque, solver nodes/costs and external/native commit indices.

On failure retain attempted state/phase, latch adapter failed and prohibit retry.
No body rollback or external commit may be claimed after an uncertain native step.
Clearing a verified owned buffer is allowed without altering physical state. Unit
tests inject failures both before and after native advancement to verify this.

## Fixed inventory, reference and API accounting

Same external intervals100/50/25us and entire10ms horizon as the activation assay.
At each grid run fresh RELAX_ZERO (a0=0,rawctrl0), FLOOR_BASELINE (a0=.0001,rawctrl0)
and PULSE (same floor,rawctrl1 on outgoing[2ms,5ms),0otherwise). q/v start0. No new
seed/drive. Baseline and pulse histories must match exactly through2ms inclusive;
later synthetic physical divergence is expected, not an integrity mismatch.

Independently integrate continuous [a,q,v] with DOP853,rtol1e-11,atol1e-13,
max_step2.5us, exact control segments[0,2],[2,5],[5,10]ms. RHS uses the SAME native
activation derivative and explicit analytic rotor acceleration, not native mj_step
or a second physiology. Sample all401 fine timestamps and retain solver status/
nodes/costs/reference states. Each native grid compares ALL its state timestamps
against reference slices; no endpoint-only or selected window. Fine sampling and
accepted internal Radau nodes are numerical checks, not rigorous error bounds.

One fresh native model per grid; nine fresh condition data. Three zero-state
mass-matrix checks (one forward each), nine initial forwards,2100body mj_step,
2100after-clear forwards: **2112 explicit mj_forward,2100 mj_step**, zero resets,
zero native step1/step2/Euler/RK/implicit API calls outside internal mj_step work.
Reference uses no native model/forward/step. Record all Python API counts; native
compiler/internal integrator work is explicitly outside those counters. Count2100
Radau intervals/external commits from retained complete transitions. No FlyGym/CNS.

## Acceptance declared before outcomes

Integrity: complete nine cases, finite physical/reference values, source/fixture/
upstream/input locks unchanged, exact fixture identity/metadata and diagonal mass,
API counts, activation/body state continuity, correct controls/floor, matching
prefix, once-only commit indices, native time error<=1e-12s. Exact owned/foreign
force preservation; no hidden position/native muscle actuation. Force projection,
native mass*acceleration and semi-implicit q/v relations within1e-9. External state
matches stored solver endpoint, dense endpoint and finite accepted nodes. Failure
handling tests are synthetic implementation tests, not successful campaign cases.

Numerical per case, complete native sample window:
- Activation bounds[-1e-12,1+1e-12] at saved endpoints/internal nodes and maximum
  activation error<=.01, unchanged from the source assay.
- Maximum absolute position error<=1e-5 and velocity error<=1e-3 in SYNTHETIC units.
  These engineering error budgets are not biological tolerances.
- Report all peak/endpoint errors, not only acceptance. Define E=max(q_error/1e-5,
  v_error/1e-3). For PULSE require E_50<=.75*E_100+1e-12 and
  E_25<=.75*E_50+1e-12 to support first-order grid refinement; no monotonic-velocity
  claim for exact-zero/constant-torque cases near roundoff.

All integrity, nine numerical cases and pulse refinement must pass for
SYNTHETIC_COUPLING_VERIFIED_TRANSFER_BLOCKED. Valid integrity with failed numerical/
refinement checks remains NUMERICAL_LIMITS_OBSERVED. Invalid integrity stays
INTEGRITY_FAILURE. Neither classification selects a production timestep. Save all
outcomes exclusively; reuse the validated lossless metadata encoding if needed.
Saved review re-evaluates locks, stored trajectories/solver records/force algebra
without constructing a model, integrating reference/Radau or executing CNS.

## Interpretation and roadmap

Current production20/42. A synthetic pass establishes mechanics/ownership/numerical
fidelity only for this chosen constant-coefficient model. It cannot resolve source
to FlyGym physical force units, finite-angle registration, velocity/length transfer,
individual tendon binding, neural rate-to-activation or original raw prerequisites.
The native selective-neutralization pass is preserved, not extended to moving-fly
muscle application. No Unity run yet, independent balance or walking claim.

Next after a valid synthetic result: source-to-body transfer prerequisite review
with explicit physical units/registration/velocity/length and evidence gaps. Do not
use a synthetic numerical pass as biological calibration or enable production.

References: [MuJoCo3.2.7 numerical integration](https://mujoco.readthedocs.io/en/3.2.7/computation/index.html#numerical-integration),
[SciPy integrators](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html).
