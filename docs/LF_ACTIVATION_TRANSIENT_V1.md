# LF source activation-transient validation v1

Prospective numerical/reference protocol, 2026-10-25. Baseline origin/newBrain
f1ba677 (merged #269). Commit protocol, generated fixed-length fixture, source
binding, runner and tests before the nine-condition campaign. Preserve every
condition and numerical failure; no timestep/parameter search after outcomes.

## Scope and source-preserving fixture

The previous source assay established instantaneous active/passive forces and
activation derivatives, not activation integration accuracy. Isolate that question
using four native muscle actuators on spatial tendons between fixed world sites.
The fixture has nq=nv=0: native time and muscle activation can advance without
body/joint motion. No CNS, production controller, force-unit transfer or admission.

Use the four existing single-class hypotheses, retaining unresolved individual
bindings and excluding broad promotors. Reuse the accepted pose/source-force
review and exact XML hash. Static extraction copies selected source muscle
defaults and explicit actuator attributes unchanged, including control floor,
dynprm/gainprm/biasprm/lengthrange and absence/presence of activation limits.
Fixed tendon lengths equal the archived central native lengths, unit gear and
zero velocity. Preserve source integrator default Euler; only the separately
declared test timestep varies. This is a source-law surrogate, not transplantation
of forces into another biological body. No physiology or model gains are tuned.

Before transients, three native forward observations at activation0/.5/1 must
reproduce the original central four force values within1e-8 native force units.
Record compiled source parameters, actlimited/actrange and actearly. Require
actearly=false so timing has the specified interpretation; never add a clamp to
make normalized activation remain bounded. The three validation observations
also record native gain/bias/dynamics for source-fidelity checks.

## Fixed nine-condition inventory

Ten-millisecond horizon. Timesteps in fixed order: 100, 50 and 25 microseconds
(1e-4,5e-5,2.5e-5 seconds), all declared before new outcomes. They are reference
grid probes, not a decision to change production timestep or choose a passing grid.
At each timestep run fresh data for these three conditions in order:

1. RELAX_ZERO: initial activation0, raw control0 throughout. Retain control floor
   and relaxation from the nonequilibrium zero-activation state.
2. FLOOR_BASELINE: initial activation equal to native effective raw-zero control
   floor, raw control0 throughout. Includes passive plus floor-active preload.
3. PULSE: identical floor initial state, raw control1 for outgoing intervals
   [2ms,5ms), raw control0 otherwise. This prescribed calibration input is not a
   CNS stimulation experiment, gait rule or production behavior.

Program control from integer interval indices, not accumulated floating time.
FLOOR_BASELINE and PULSE activation/refreshed-force histories must match exactly
through the state at2ms inclusive. Passive bias must be identical in both arms at
every state. RELAX_ZERO is deliberately not that matched baseline.

There are 100/200/400 native steps per condition, **2100 explicit mj_step calls**
in total. One initial forward refresh per condition, one after every step, plus
three source-force observations: **2112 explicit mj_forward calls**. Count Python
API calls across preflight/execution; compiler-internal checks are outside that
API count. Record all native activation/time transitions. No CNS/body transitions.

## Timing and independent numerical reference

With actearly=false, force/act_dot left by mj_step describe pre-integration
activation. Record activation before/after each step, during-step force/derivative,
raw and effective controls and time. Then call mj_forward without integrating to
record force/derivative aligned to the new activation. Do not compare stale force
to post-step activation or use a one-row shift chosen after seeing outcomes.

Use native mju_muscleDynamics as the source ODE; do not implement a competing
muscle law. Independently integrate it with SciPy solve_ivp DOP853, rtol1e-11,
atol1e-13, max_step2.5e-6 seconds, separately over exact constant-control segments
split at2ms and5ms. This compares integration schemes for the same modeled law,
not independent biological evidence. No derivative-law parameter change. Sample
the continuous reference at each native state timestamp; store all reference
activations and solver settings/results. Saved review recomputes errors from the
archived reference; it does not rerun native or reference integration.

## Acceptance declared before outcomes

Implementation integrity requires all nine complete records, finite values,
exact source/fixture hashes, nq=nv=0, nu=na=ntendon=4, correct timing/controls,
unchanged fixed lengths and source parameters, recorded API totals and no CNS/new
admission. Per-step Euler update (including ONLY native configured actrange if
enabled) must reproduce native activation within1e-10. During-step/refreshed forces
must equal native gain*respective activation+bias within1e-8. Time error<=1e-12s.
No source/fixture changes, hidden retries or external generalized/body forces.
The independent solver must succeed and preserve specified initial states.

Separately, each condition's **numerical acceptance** requires all four native
activation traces in [-1e-12,1+1e-12] and maximum full-window absolute activation
error<=0.01 against DOP853. Report peak error, overshoot, endpoint error and
force error against the same reference for every timestep/condition. No shortened
window or endpoint-only pass. A failing numerical criterion is retained as FAIL;
verification of the archive is not acceptance of that timestep. If any numerical
case fails, the campaign label is NUMERICAL_LIMITS_OBSERVED, not a global accuracy
pass. Plumbing may be verified independently; no timestep is selected for use.

Matched-prefix equality and baseline stationarity are separate integrity checks
(native equilibrium activation/force maximum drift<=1e-10/1e-8). Passive bias is
not removed for a zero-force baseline. Numerical failures do not authorize
changing clamp, gains, time constants, production dt or neural input.

## Interpretation and next gate

Source-force units remain uncalibrated to FlyGym/SI, and these are modeled source
activation constants. This fixture does not test moving geometry, neural rate-to-
activation law, individual tendon binding or production actuator replacement.
Existing raw prerequisites remain separately unresolved. Production stays20/42.
No Unity run is needed to review these saved native activation records.

References: [MuJoCo3.2.7 native activation integration and force timing](https://raw.githubusercontent.com/google-deepmind/mujoco/3.2.7/src/engine/engine_forward.c),
[actuator semantics](https://mujoco.readthedocs.io/en/3.2.7/XMLreference.html#actuator-general-actlimited).
Use existing SciPy/native functions, not copied/custom muscle dynamics.
