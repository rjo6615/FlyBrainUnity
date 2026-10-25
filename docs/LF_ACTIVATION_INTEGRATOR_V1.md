# LF activation integrator v1: prospective protocol

2026-10-25; baseline origin/newBrain a5b8cdd, merged PR #270. Commit this
protocol, integrator, assay and implementation tests before the campaign. Run
one campaign; keep every case and failure. No retry or solver/tolerance/grid
search after outcomes. This is a separately versioned engineering intervention
in response to the archived Euler failures, not a revision of their acceptance.

## Question and fixed intervention

Can an independent implicit solver integrate the unchanged native source muscle
law accurately at the SAME external control intervals that failed under Euler?
Use SciPy Radau, rtol=1e-9, atol=1e-12, max_step equal to each control interval,
with dense output. Radau is an implicit order-five method appropriate for this
fast activation system. Adaptive internal steps implement the fixed error policy;
they are not a post-outcome search for a passing external timestep. This is one
declared solver, no fallback. Reuse installed dependencies.

Call MuJoCo 3.2.7 mju_muscleDynamics with unchanged compiled dynprm and effective
control. No new muscle ODE, activation clamp, time-constant increase, fitted gain,
neural drive or seed change. Preserve raw-control clipping to the source range
[0.0001,1] and the source passive force bias. The integrator accepts/returns
copied state vectors and owns activation only within a constant-control interval.

## State ownership and force timing

Reuse the original hash-locked zero-DOF, four-tendon fixture and source binding.
Resolve the exact tendon/actuator names and native actuator_actadr/actnum, rather
than assuming names alone or confusing actuator IDs and activation addresses.
Require nq=nv=ngeom=0, nu=na=ntendon=4, actearly=false, source activation limits
disabled. Reject moving models, unsupported dynamics or non-bijective state maps.

Only the fixture adapter commits activation and advances data.time once. It calls
mj_forward before/after the commit to expose force/derivative at the two states.
It NEVER calls mj_step or any native integrator; doing so would advance activation
twice. Initial native force and three activation=0/.5/1 calibration forwards use
the existing frozen forces. Store source parameters, exact identities/addresses,
full before/after activation, controls, time, force, derivatives, geometry and
external-force arrays. Record all accepted Radau internal nodes, solver status,
message, nfev/njev/nlu and dense samples. Solver success alone is not accuracy.
This adapter is explicitly restricted to the zero-DOF fixture. It is not an
implementation of split activation/body integration or a production hook.

## Nine cases and independent, preserved comparison

Keep the entire previous inventory: external intervals 100/50/25 us, horizon
10 ms, RELAX_ZERO, FLOOR_BASELINE and PULSE. Use integer outgoing indices;
PULSE raw control=1 only on [2,5) ms, otherwise 0. Start relaxation at a=0;
baseline/pulse at effective-zero floor=.0001. Baseline and pulse match exactly
through the state at 2 ms, including passive plus floor-active preload.

Reuse the archived DOP853 reference rather than duplicating that experiment.
Require its exact 3799210-byte source report SHA256
539c26fb35d15824d970b482d36af579186e2ed4fe1bf707c03c4e592a90e5fc,
successful original integrity evaluation, original source locks and fixture hash.
Use each condition's existing finest reference grid (401 timestamps at 25 us,
including 0 and 10 ms). Evaluate Radau dense output at ALL those times even for
the 100/50-us external intervals. Also compare the original coarser reference
slices and retain all nine Euler numerical decisions in the new report. No
Euler rerun, edited historical reference, dropped interval or selected window.
The reference independently integrates the SAME native law (DOP853, rtol1e-11,
atol1e-13, max_step2.5us, exact control boundaries); not biological evidence.

2100 Radau interval solves/activation commits; 4212 explicit native mj_forward
calls (2*2100+9 initial+3 calibrations); ZERO mj_step, CNS/body-joint transitions
or new motor admissions. Count Python API calls across preflight/execution,
excluding compiler-internal validation. Preserve partial outputs on exceptions
and reject an existing output directory. No automatic retry.

## Acceptance fixed before outcomes

Integrity: all nine complete finite records, original and new source hashes,
compiled parameters and exact identity/address checks, correct API counts,
control/time/state continuity, source force=activation*gain+bias at both states
(absolute tolerance 1e-8), native/ODE derivative agreement (1e-8), fixed lengths
(1e-12), no external force or body state. Solver internal nodes must start/end at
the interval endpoints/activations, increase in time, have finite values and
successful status. Dense endpoint state must match the committed state (1e-12).
Time tolerance 1e-12 s. Baseline drift<=1e-10, force drift<=1e-8. Exactly matched
prefix through 2 ms. Preserve the recorded false historical raw-prerequisite
flag; do not turn a canonical-content match into raw-freeze acceptance.

Numerical: unchanged activation bounds [-1e-12,1+1e-12] and maximum absolute
activation error<=.01 against the reference over the ENTIRE window. Apply to
all 401 dense samples and macro states, and check bounds at internal accepted
nodes too. Report full-window and endpoint errors, activation extrema, force
errors and solver costs for EVERY case. These are sampled numerical checks,
not a rigorous continuous-time error bound. All nine must pass for
ALL_NUMERICALLY_ACCEPTED; otherwise retain NUMERICAL_LIMITS_OBSERVED when
integrity is valid, or INTEGRITY_FAILURE when invalid. Archive review verifies
saved records/decisions/locks without constructing a model or integrating.

## Scope and next gates

Production remains 20/42. Success would establish integration fidelity only for
these source-law fixed-length controls/windows; it cannot validate biological
constants, neural rate-to-activation, moving geometry, physical units/registration,
individual tendon binding, actuator replacement, balance or walking. No Unity
run required. Before a moving-fly experiment, specify body/activation state
ownership and selective replacement without double actuation; retain original
raw scientific prerequisites and anatomical uncertainties as separate gates.

Roadmap updates after each run must state: what ran, the result and its limits,
current motor admission count, the active gate and the next concrete gate.

References: [SciPy solve_ivp / Radau](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html),
[MuJoCo 3.2.7 stateful actuators](https://mujoco.readthedocs.io/en/3.2.7/computation/index.html#stateful-actuators),
[native source muscle law](https://raw.githubusercontent.com/google-deepmind/mujoco/3.2.7/src/engine/engine_util_misc.c).
