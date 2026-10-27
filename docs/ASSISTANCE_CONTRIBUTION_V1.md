# Assistance contribution V1 — neutralizing the22baseline-only servos

2026-10-26. Prospective design, NOT_IMPLEMENTED_NOT_RUN. The user's review of the
accepted controlled-live V1.1 replay reported normal movement, no unexpected
visual issue and similarity to previous runs. This is a human replay observation,
not confirmation of live client delivery or independent neural balance. The
earlier native study remains COMPLETE/INTEGRITY_ACCEPTED/MIXED_OR_UNRESOLVED.

## Question and causal scope

How does removing position-servo support at the22currently unadmitted motor
coordinates change posture and the contribution of the existing20decoded neural
inputs, with and without the same fixed thorax push?

Those22coordinates currently receive fixed initial baseline commands. Their
position servos can supply restoring/damping forces despite receiving no neural
commands. The20admitted coordinates retain their existing position actuators,
baseline, decoder and safety policy in ALL arms. Neutralizing all42would also
remove the neural force path and would not separate these effects. This protocol
targets the22baseline-only servos, not all mechanical assistance. The20remaining
servos, passive joint damping/friction, limits and ground mechanics still assist
or constrain posture. No independent balance/gait or motor-admission claim follows.

Use the frozen original20/22authority, not anatomical guesses or ranked output
groups. The22comprise18coxa/roll/yaw and4middle/hind Tarsus1 coordinates; they stay
neurally UNADMITTED. No muscle replacement, new population/sign/gain assignment,
sensory-to-actuator rule, scripted gait or source-to-target force transfer.

## Eight fixed fresh arms

|Order/ID|22servo policy after boundary|20decoder input after boundary|Push|
|---|---|---|---|
|1 A_NC|held,original parameters|enabled|none|
|2 A_WC|held|withdrawn before safety|none|
|3 A_NP|held|enabled|fixed|
|4 A_WP|held|withdrawn|fixed|
|5 R_NC|neutralized|enabled|none|
|6 R_WC|neutralized|withdrawn|none|
|7 R_NP|neutralized|enabled|fixed|
|8 R_WP|neutralized|withdrawn|fixed|

A=original assistance at22coordinates; R=their position servos neutralized.
Each arm uses a fresh OS process/model/CNS/encoders/safety/RNG; seed1,2s,
dt0.0001s,neural dt0.5ms. Per arm20,000physics transitions/20,001states/4,000neural
updates; TOTAL160,000/160,008/32,000. No archived A controls reused:all8are fresh.
The prior outcome is known, so fresh A measurements are an engineering reference,
not an independent confirmatory biological replication. Fixed order,no retries,
resume, parameter/force/seed sweep, outcome ranking or fall-based early stop.

Only six tibia/392proprioceptive inputs; tactile OFF. Preserve existing392-slot
assay common CNS RNG and per-leg PCG64samplers. All equal-tick uniform/RNG-state
checks remain mandatory throughout. After body divergence, rates, candidates,
delivered inputs, spikes and neural state may differ; do not force them equal.
Keep weights, thresholds, signs, neural gains, drive and all20actuator parameters.

## Declared mechanical boundary and native identity

All eight arms begin with original model M0 and full42position-actuator policy.
After recording state5005/time500.5ms, before outgoing transition5005, R arms
write exactly zero to EVERY column of actuator_gainprm and actuator_biasprm in
the selected22native actuator rows. This binary engineering intervention is
predeclared, not a gain search to achieve activity or stability. A performs an
observation-only boundary journal; no parameter write. No ramp, re-enable,
recompile, live forward/reset, constraint/support change, direct position or
velocity write, compensating force, damping edit or native actuation-disable bit.

Do NOT zero controls alone:position/velocity bias can still generate force.
The42targets continue under their existing policy, including22baseline values;
all48ctrl slots, six zero adhesion controls and20safety/decoder histories are
recorded. Only the declared22gain/bias rows differ. Keep every other model field
and all20retained servo rows EXACTLY unchanged. No runtime native ID is inferred
from action index:reuse lf_native_isolation.inventory/validate_inventory and
actual transmission/body/joint/qpos/dof/activation/force-support tables. Saved
M5A or accepted-run IDs are leads in their recorded model, not future bindings.

Require stateless fixed-gain/affine position semantics, exact scalar hinge/unit
transmission and a complete disjoint42joint+6adhesion inventory. Record/control
native actuator and joint force limits, joint actuator-gravity-compensation flags,
body gravity compensation and force-support/moment matrices. Selected force
limits must admit zero and selected joints must have no extra actuator gravity
compensation or other ENABLED actuator force contribution. Full moment support
may include the six adhesion transmissions; their controls AND actual forces must
remain zero. Do not assume structural support disappears when a force is zero.
Unsupported semantics FAIL qualification;
do not alter those settings to make the intervention work. Passive forces and
constraint/contact loads remain:neutralized servo is not a torque-free joint.

The mechanical event occurs after the W decoder gate at neural1001 in state5005.
W gating remains BEFORE original range/slew safety; no final-target zero/reset.
Baseline return bound126off updates/563.0ms stays unchanged for retained20targets.
Pulse[0,1.024,0],zero torque,exact Thorax COM,outgoing5000..5199 is unchanged.
No new phase increment or extra scientific step at the patch. First possible
mechanical/neural-withdrawal physical effect is state5006. Terminal neural4000
proposal at2000ms remains retained/unapplied.

Full science equality across all8holds through state5000/tick1000. For the four
arms sharing a push class, physical/applied-control and pre-gate neural histories
remain equal through state5005; proposed W targets can differ there. Gain/bias
patch journal is OUTSIDE the recorded state5005scientific sample. State5005force
arrays describe the previous interval and may contain pre-patch cached force;
do not claim they already show neutralization. Audit selected scalar/generalized
actuator forces from state5006onward, including terminal state20000.

## One bounded native force-law qualification before science

Earlier LF native isolation verified only3selected LF coordinates at instantaneous
probes; it is not validation of these22or moving-body transfer. Reuse its native
inventory, force-projection inspectors and exact row-zero/restoration mechanism,
not its hardcoded LF target selector. Before stepping the FIRST actual A_NC model,
use that already initialized model and ONE separate shadow MjData for a declared
instantaneous qualification. No second FlyGym model or CNS initialization.
Require no plugin state/mocap/dynamic activation unsupported by the stateless
shadow-input contract. Never write the live MjData or sample/advance encoders/CNS.

Use initial measured qpos center. Four Cartesian input probes:control sign +/-1
and velocity sign +/-1. For all42joint actuators set ctrl to measured center plus
control_sign*0.01rad*(-1)^action_index; six adhesion controls0. Shadow qvel starts
zero, with selected22dofs set velocity_sign*0.1rad/s*(-1)^action_index. All controls
must be in original ranges; if not, retain failure, do not clip, shrink or search.
Applied generalized/body forces are0. These are engineering shadow probes, not
neuronal stimulation, live transduction or evidence of biological force scale.

For each probe run original B, neutralized R, restored B:12EXPLICIT shadow
mj_resetData and12EXPLICIT mj_forward calls total,1shadow allocation; ZERO live
reset/forward, integration or CNS updates. Other constructor/internal operations
are accounted separately, not inferred absent from time0. Reuse inherited LF
force tolerances:selected force/generalized force zero, retained actuator force
and outside-target delta<=1e-10; moment-force projection error<=1e-8. Passive forces
and moment matrix must be identical at equal probe inputs; all non-patched model
fields and final restored model identity exact. Each selected original actuator
must expose force>1e-8in at least one predetermined probe (old nonvacuity bound).
No favorable probe selection; preserve all12cases. Failure stops before scientific
transitions, retains initialized/qualification evidence and all other arms unstarted.

Record exact live state,model,brain,encoder,safety,RNG before/after qualification;
they must match. Keep qualification artifacts/accounting outside shared science
context so there is no fabricated prefix equality. All subsequent actual initialized
models must exactly match qualified M0 before any step. Dynamic force suppression
still requires every actual post-boundary sample:instantaneous checks alone do
not prove the moving case. No additional probe campaign or automatic retry.

## Piecewise model audit, not an old-hash waiver

Frozen contact_context.configuration and old auditors expect a constant model;
they correctly reject a changed R model. Do not edit them, refresh old hashes or
fabricate an A report. Build a separately versioned adapter/evaluator that reuses
old force/command/RNG/behavior math while explicitly auditing this new context.

Independently derive MR from complete recorded M0 arrays by zeroing ONLY the22
declared native gain/bias rows. Record full typed arrays and hashes, exact before/
after patch, scientific index/time, actual selected IDs and zero operation.
Expected sampled model phase:A=M0always; R=M0states0..5005,MRstates5006..20000.
Verify every other field exact, all actual selected actuator/generalized forces
<=1e-10in R after5005, and no hidden force overwrite or extra stepping. Retained
actuator forces can change after physical feedback diverges; require their
PARAMETERS/law preserved, not equal force values across different trajectories.
Sample qfrc_actuator,qfrc_passive,qfrc_bias,actuator_force,moments and complete
applied-force arrays in addition to original raw data. Contact reconstruction
tolerances remain original rtol1e-10/atol1e-14, separate from force-law bounds.

Require complete original graph/neuron/calibration/raw/data/environment locks,
including balance_source_prerequisites, in parent and each worker before/after
acquisition. Own code/schema/protocol sources committed before qualification/run.
Fresh-process namespace, strict numeric/native identities, complete coverage,
finite clocks, full per-leg/CNS RNG, pre-gate and applicable prefixes mandatory.
Any undeclared model write/counter/force difference or missing data yields
INCONCLUSIVE_INTEGRITY, preserving partial raw. Physical falls/divergence alone
are outcomes, not integrity failures. All source/collision contamination retained.

## Measures and interpretation

Keep complete0..2000ms traces;baseline4000..5000,force500..520ms,cleared-force
window5201..20000. Original recovery bands,dwell1001states/100ms,resolution
0.25deg or0.005mm and statuses unchanged. Report all no-push trajectories:release
can destabilize its own control. Retain original own-control-relative descriptors;
if the control itself loses upright/height/support in the cleared window, add
CONTROL_POSTURE_LOSS_CONFOUNDS_RECOVERY and do not interpret relative return as
independent functional recovery. Absolute target/control posture remain visible.

Predeclare FOUR mechanical comparisons A vsR at each neural/push combination,
and FOUR neural comparisons N vsW at each mechanical/push combination. For each
report full-world tilt mean/peak,root height/position/world velocities,exact-ground
support,rollover/low-height and own-control recovery. Label lower/higher tilt
only if BOTH mean and peak differences exceed0.25deg in the same direction;
otherwise MIXED_OR_UNRESOLVED. Never select a successful arm or composite score.
These are descriptors, not acceptance or pass/fail of balance.

Also record signed root/up-vector contrasts:at fixed neural policy compare
[(R_P-R_C)-(A_P-A_C)];at each assistance level compare
[(N_P-N_C)-(W_P-W_C)],and their difference across R/A. Reuse existing vector
conventions. Angle/norm/recovery contrasts are nonlinear, not additive fractions
of balance. One seed supplies no statistical/generalization claim. No inferred
percentage of support from torque ratios or reference geometry.

Complete valid null/adverse/unrecovered results can pass integrity and allow
saved Unity review. Live output is provisional,actual sent/received/review counts
separate. A fall should not be hidden by a following camera. Use existing fixed
world camera/recorded-pose transport and honest clip-reset labels. No new Unity
controller,smoothed scientific data or physical feedback from client commands.

## Next implementation gate

This update creates the plan/static verifier ONLY. No model mutation,qualification,
native body/CNS construction or scientific run. Native bindings/qualification and
all execution prerequisites are explicitly unverified. Next implement the instance-
local Trial/session adapter using existing injectable factories and original
kernel;qualify bound event order,22/20isolation,phase hashes and force fields with
synthetic/reference tests,then commit before the ONE bounded qualification and
eight-arm campaign. No extra native preflight initialization or tuning for a pass.
