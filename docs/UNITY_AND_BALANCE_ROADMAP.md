# Where we are: Unity, neural balance and the LF force-interface milestone

Checkpoint2026-10-25. This is a roadmap, not a new experimental acceptance
protocol or a claim that the milestones below are already complete.

## At a glance

Motor coverage: **20/42 admitted coordinates — 47.6%**.

```text
Motor coverage   [##########-----------] 20/42
```

This is motor coverage only, not overall project completion or biological
validation. Tibia, femur and femur roll each contribute 6/6; front Tarsus1
contributes 2/6; coxa/roll/yaw contribute 0/18. Remaining: 22 coordinates.

| Roadmap gate | Current position |
|---|---|
| Existing 20-coordinate runtime and controlled sensory observations | Available within recorded conditions; ordinary live tactile disabled |
| LF source mechanics / numerical interface | Scoped reference and synthetic checks verified; historical failures retained |
| LF target attachment anatomy — active gate | Reference required; 0/8 supported endpoint correspondences in the reviewed corpus |
| Physical scaling, neural binding and activation | Unresolved; cannot infer these from a geometry check |
| Bounded moving-body muscle experiment, then Unity review | Pending prerequisites; no new Unity behavior from current document/reference checks |
| Independent neural balance, then walking | Not established |

Latest continuation: [reference acquisition V1](LF_REFERENCE_ACQUISITION_V1.md)
followed publication/data/code leads and found an upstream rig-compatibility
discussion. No qualifying target annotation artifact was acquired. Some data
shares could not be inspected with the browsing tool; that is an access limit,
not evidence of absence. Next input is an accessible, revisioned anatomical
attachment/landmark bundle tied to the exact assets in the existing request.
Another pose sweep or saved-report replay cannot supply it. This research gate
has no defensible completion percentage or fixed number of remaining PRs.

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
| Synthetic coupled validation | V2 passes the declared same-model numerical/ownership checks using explicit endpoint roles; V1 remains **INTEGRITY_FAILURE**, unchanged |
| Transfer prerequisite inventory | V1 complete; explicit source parameters identified; unsupported conversions remain null |
| Unit/conversion-lineage audit | V1 complete with unresolved result: OpenSim sources and conversion PDF found, exact conversion chain and physical scale unproven; no force multiplier chosen |
| Native LF orientation registration | V1 measured kinematics agree with the modeled map at all15declared poses;196samples in range, no integration/CNS; attachment/length/velocity transfer still unvalidated |
| Source routes / target attachments | Four source paths/eight sites inventoried; native target has no tendons or matching source muscle-site definitions; attachment correspondence remains unresolved; active LF mesh is mirrored RFCoxa |
| Paired endpoint/body-frame observer | V1.1 verifies source endpoint reconstruction, all105source lengths and derivatives;106target frames recorded, no target sites/forces; original V1namespace setup failure preserved |
| Target attachment decision | Current reviewed evidence supports0/8target endpoint correspondences; registration not authorized. Exact reference request prepared; next acquire/qualify independent anatomical or landmark data |
| Moving-fly muscle transfer | Physical units/geometry/velocity/length, raw prerequisites and anatomical/neural conversion remain unresolved gates |
| Independent neural balance/walking | Not established |

## How far until another meaningful Unity test?

The existing20-coordinate runtime is still the existing runtime. Replaying it
would inspect the same interface; these engineering updates do not introduce new
Unity behavior. For a Unity test of the NEW muscle interface, the remaining
sequence is:

1. The transfer inventory and unit-lineage audit are complete; physical scaling
   remains unresolved pending authoritative conversion records. Native target
   orientation now agrees at the declared probes. Source route/attachment audit
   identifies the target endpoint gap. Paired source endpoint and target body-frame
   observations have now validated a geometric observer in V1.1 without
   assigning target muscle sites or choosing physical scale. The registration
   decision now identifies a reference-data requirement: acquire/qualify independent
   anatomical/landmark correspondence tied to the exact source/target assets.
   Further pose sweeps cannot supply that missing authority. Preserve null target
   correspondence while it is missing.
   Resolve source-to-body prerequisites:
   physical units and registered
   geometry/length/velocity dependence, original raw-source requirements, exact
   anatomical population-to-muscle interpretation and neural-to-activation law.
   Reference fidelity does not by itself calibrate biological force or gain.
2. Run a bounded headless native experiment under a predeclared replacement/support
   context, using the existing transition kernel. Record integrity and all outcomes
   before deciding what can be replayed or tested in Unity.
3. Inspect that supported experiment in Unity with a concrete observation goal
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
