# Where we are: Unity, neural balance and the LF force-interface milestone

Checkpoint2026-10-25. This is a roadmap, not a new experimental acceptance
protocol or a claim that the milestones below are already complete.

## The milestone we are working toward

A trustworthy **left-front proximal muscle-force interface**: supported neural
populations feed an explicit activation model, source mechanics map force into
the intended body coordinates, and existing position actuation is replaced only
where declared. Activation/body state advance once; force buffers and other
controls remain intact. Biological assumptions and synthetic engineering checks
must stay distinguishable.

This could support the three LF coxa coordinates that remain unadmitted, but a
working numerical interface alone does not admit them. Anatomical binding,
physical transfer and neural conversion still need evidence. Broader expansion
toward42 coordinates, richer sensory input, causal balance and eventually walking
remain the larger goals. No gait script or sensory-to-actuator shortcut substitutes
for neural emergence.

## Current position

| Item | Evidence at this checkpoint |
|---|---|
| Neural motor coverage | **20/42 motor action coordinates admitted**; this is not overall project completion |
| Existing body/sensory work | Prior matched tactile, disturbance and yoke observations are preserved within their recorded conditions |
| Source force/activation checks | Declared source/fixture checks pass; source Euler transient failures remain preserved |
| Native actuator replacement isolation | Selective suppression/preservation passed at the declared fixed inputs, without advancing the fly |
| Endpoint API | Explicit initial/terminal/interior sampling contract independently verified; no tolerance fitted to old residues |
| Synthetic coupled validation | V1 remains **INTEGRITY_FAILURE**; a separately versioned implementation must consume the explicit endpoint contract and be tested |
| Moving-fly muscle transfer | Physical units/geometry/velocity/length, raw prerequisites and anatomical/neural conversion remain unresolved gates |
| Independent neural balance/walking | Not established |

## How far until another meaningful Unity test?

The existing20-coordinate runtime is still the existing runtime. Replaying it
would inspect the same interface; these engineering updates do not introduce new
Unity behavior. For a Unity test of the NEW muscle interface, the remaining
sequence is:

1. Validate a separately specified corrected synthetic coupling implementation,
   preserving the failed V1 and keeping exact authoritative terminal-state commit,
   force ownership, physical error budgets and all planned windows/grids.
2. Resolve source-to-body transfer prerequisites: physical units and registered
   geometry/length/velocity dependence, original raw-source requirements, exact
   anatomical population-to-muscle interpretation and neural-to-activation law.
   Reference fidelity does not by itself calibrate biological force or gain.
3. Run a bounded headless native experiment under a predeclared replacement/support
   context, using the existing transition kernel. Record integrity and all outcomes
   before deciding what can be replayed or tested in Unity.
4. Inspect that supported experiment in Unity with a concrete observation goal
   and the relevant matched comparison, rather than expecting a visual change
   from code/reference tests alone.

This is several distinct engineering/research gates. A reliable date or number of
PRs cannot be inferred; unresolved anatomy or physical calibration may require
more evidence and can legitimately remain inconclusive. No promise of a passing
Unity run, a new admission or improved balance follows from an API check.

## Are we moving toward balancing on its own?

Yes, the work supports that goal by making the neural-to-body interface more
defensible. It has not yet demonstrated independent neural balance. The current
body uses engineered position actuators; unadmitted coordinates receive baseline
position-control commands. This assistance can contribute to a stable appearance.
Prior neural intervention results can establish a bounded contribution under their
conditions without establishing independent balance or gait.

A future balance milestone needs predeclared disturbance/recovery measurements,
matched neural enabled/withheld or appropriate yoke controls, verified input/output
boundaries and an explicit mechanical-assistance policy. Merely staying upright,
moving more, or looking as though it is balancing is insufficient. Any change to
support/actuation context must be separately specified and shared where matching
requires it; do not tune neural gains, thresholds or drive until a test passes.

After every run, report: what ran, what its result establishes and cannot establish,
current motor count, active milestone/gate and next concrete step.
