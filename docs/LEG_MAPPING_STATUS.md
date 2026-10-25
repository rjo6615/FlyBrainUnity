# Leg mapping and live motor-admission status

Checkpoint 2026-10-24, live-v3 inventory. The physical model has an ordered table
of all 42 leg coordinates (seven per leg). This structural inventory is distinct
from complete biological neuron-to-muscle mapping and from validated admission
for current neural motor application. Do not call the whole project 48% complete.

| Model coordinate group | Current admitted motor channels | Model coordinates |
|---|---:|---:|
| Tibia | 6 | 6 |
| Femur | 6 | 6 |
| Femur roll | 6 | 6 |
| Tarsus1 | 2, front left/right | 6 |
| Coxa, coxa roll, coxa yaw | 0 | 18 |
| Total | **20** | **42** |

The remaining 22 are all 18 coxa coordinates and four middle/hind Tarsus1. Their
names/indices are known in the model; current live-v3 does not admit them for
neural motor application. This does not assert that no anatomical annotations or
earlier candidate evidence exist. Audit that evidence before selecting the next
interface. Physical motion in an unadmitted coordinate is not proof of its own
mapped motor-neuron activity; mechanical coupling and baseline actuation matter.

Current sensory coverage includes six tibia proprioceptive populations (392
neurons) and six modeled foot-contact tactile populations (1877 neurons) in the
separate controlled experiments. Isolated calibration and normal supported-context
attribution were checked under their documented conditions, followed by matched
delivery and motor-application tests. This does not provide all-joint neural
proprioception, general biological transduction validation or established gait.
Ordinary live tactile input remains disabled; recorded Unity clips are review of
saved experimental poses, not a newly enabled ordinary live mode.

Recent work held the 20-motor count fixed while checking sensory delivery and
the causal consequences of applied motor-command changes. Four fixed contexts
are now available: full closed-loop, tibia-only replay, complementary replay,
all-command replay. They affect posture and trajectory differently. The frozen
time-aligned analysis in `GROUP_POSTURE_ANALYSIS_RESULTS.md` explains this without
new physics, parameter tuning or declaring general balance.

Remaining-coordinate admission requires the existing ordered table and
candidate/reference reports for each coordinate: anatomical
body-ID/population evidence, completeness/antagonist requirements, mechanical
sign provenance, existing validation and exact missing prerequisites. Select
the next defensible admission protocol from that evidence, not outcome rankings
or a desire to make every joint move. Any implementation/validation change is a
separate predeclared update. Preserve calibrated physiology, source/artifact locks,
null exposures, failed results and the distinction between mapping and behavior.

The 22-row read-only audit is now complete; see
`REMAINING_LEG_ADMISSION_RESULTS.md`. It found 12 shared-axis binding blockers,
six unresolved anatomical action-sign bridges and four missing exact Tarsus1
target mappings. No remaining channel was admitted. Next work is the independently
reference-backed LF proximal population activation/sign and multi-axis binding
prerequisites in `LF_PROXIMAL_ADMISSION_PREREQUISITES_V1.md`. Existing local
geometry and older neural recruitment nulls do not by themselves justify admission.

The LF reference-binding review is now complete; see
`LF_PROXIMAL_BINDING_RESULTS.md`. Exact original FlyMimic source confirms seven
muscle-actuator/tendon contracts. Conditional tensile torque is T*R for the frozen
R=-dL/dq convention. This resolves a reference force convention, not the absent
neuron-to-muscle or force-to-position decoder transfer. All three broad-promotor
hypotheses and all per-neuron unassigned bindings remain explicit. Current admission
stays 20/42. Next obtain an independent neuron-to-muscle crosswalk and specify the
intended force versus engineered position interface before numerical validation.

New independent reference research in `LF_ANATOMICAL_CROSSWALK_RESULTS.md` verifies
all 13 LF body IDs against the original official MaleCNS v1.0 annotation table,
including 12 recorded MANC body matches and one explicitly missing match. The
full FANC atlas Figure A2 explicitly leaves individual promotor targets uncertain;
names/counts cannot resolve its split into model tendons. Four other classes have
class-level anatomical support. Next scope is a separately specified LF muscle-
force reference adapter/isolated validation using those four modeled class
hypotheses, while leaving the broad promotor unassigned and production admission
at 20/42. Numerical force/activation/application gates remain to be specified.

The isolated local force-reference adapter now passes six fixed synthetic native
MuJoCo fixture cases; see `LF_FORCE_REFERENCE_RESULTS.md`. V1.1 observes exactly
18 explicit forward calls and zero integration/CNS transitions; saved review is
dynamics-free. V1's inherited model-construction side effect and failed operation
provenance are preserved. Projection/DOF isolation/clearing work at the exact
reference pose, not arbitrary moving poses. No neural force law, biological scale
or new admission is established. Current production remains 20/42. Next specify
pose-dependent mechanics, activation/passive terms, units and selective actuation
replacement before a separately bounded neural-coupling experiment.

Pose/source-force reference v1.1 now passes 15 fixed source poses under an explicitly
modeled rotational correspondence, with native tendon derivatives and active/
passive/activation-dynamics checks. See `LF_POSE_FORCE_RESULTS.md`. The source
anterior rotator has passive preload at zero activation, and positive control floors
make raw zero control distinct from a zero-activation equilibrium. These are source
model properties, not biological calibration. Failed v1 sparse-format interpretation
is preserved. No finite-angle anatomical FlyGym registration or cross-body force
scale is established; no production change or new admission. Next validate activation
transients/baseline semantics and establish physical/units transfer before coupling.

Source activation-transient v1 completed nine fixed-length cases; see
LF_ACTIVATION_TRANSIENT_RESULTS.md. Implementation integrity passes, but pulse
activation fails full-window numerical acceptance at all three predeclared Euler
grids (100/50/25us). The100us pulse overshoots activation to1.9993; finer grids
remain inaccurate despite bounded states. Baseline and passive preload are retained,
not zeroed to obtain a pass. No timestep is selected and production remains20/42.
Next separately validate reference-faithful activation integration with unchanged
law/parameters, then resolve force-unit/geometry and application prerequisites.

Separately versioned activation integrator v1 now passes all nine same-window,
same-external-grid cases using Radau and the unchanged native source law. Maximum
pulse error is 1.7643e-10 against the original archived DOP853 reference; all Euler
failures remain unchanged. See LF_ACTIVATION_INTEGRATOR_RESULTS.md. This clears
the fixed-length numerical integration gate only, not a mapping/admission or
biological-force gate. Current production remains 20/42, new admissions 0. Next
design/static-audit the selective LF actuator replacement and activation/body
state-ownership contract before any moving-fly coupling. Physical units/geometry,
original raw prerequisites, individual binding and neural conversion remain open.
After each run, report this roadmap position and the next concrete gate.

Selective LF actuation contract v1 now verifies the STATIC design, with coupling
explicitly blocked; see LF_ACTUATION_CONTRACT_RESULTS.md. M5A recorded yaw/pitch/
roll target action IDs2/0/1 map to DOFs6/7/8, distinct from synthetic fixture DOFs.
The design preserves39 joint controls (all20 admissions plus19 baseline position
controls) and separately accounts for six adhesion actuators in a later historical
48-actuator signature. Missing native body/activation/transmission values remain
missing; no identity equivalence between snapshots is assumed. Source activation
states remain separate from body state. No model mutation or physics/CNS execution
in the audit; production stays20/42. Next separately specify/capture the current
native inventory and audit selective-neutralization/preservation with declared
forward probes and no integration. Physical/neural/raw scientific gates remain.

Native selective isolation v1.1 now passes27 declared forward-only observations
on the current live/contact initializer, with34explicit forwards/3resets/0integration
or CNS. Three target position actuators and their target generalized contributions
are zero after selective gain/bias suppression; all45 retained actuator forces,
other model parameters and final restored model identity are preserved. Current
body13/LFCoxa, target yaw/pitch/roll DOFs6/7/8, no native activation states. V1's
incomplete export due infinite compiled limits remains failed; V1.1 only corrects
lossless metadata encoding with unchanged probes/criteria. Read
LF_NATIVE_ISOLATION_RESULTS.md. Production still20/42; no muscle/neuronal changes.
Next separately validate synthetic coupled-state/force-buffer ownership and
numerical convergence. Biological force units/registration, original raw gates,
individual binding and neural conversion remain before moving-fly coupling.

Synthetic split-coupling v1 completed all9cases/2100native rotor steps, with
preserved foreign force buffers and numerical budgets/pulse refinement passing.
The original verdict remains INTEGRITY_FAILURE: three pulse cases fail exact
equality of dense-output endpoint and solver terminal state (14total differences,
maximum1.110223e-16). Committed external states match authoritative terminal states
exactly, but no guard was relaxed or acceptance changed. Full raw evidence and
read-only failure review are preserved; see LF_SYNTHETIC_COUPLING_RESULTS.md.
Production remains20/42. Next independently specify/test endpoint ownership/API
semantics before a separately versioned correction/protocol, not fit an epsilon
to this data or advance to physical transfer. No Unity or FlyGym coupling yet.

Endpoint contract v1 now independently verifies explicit initial/terminal/interior
sampling roles using a constructed counterexample and two analytic linear-mock
Radau solves. Exact authoritative terminal state is preserved, every original
dense value retained, near-end interior timestamps are not snapped. No epsilon,
old guard change or coupled/native/CNS repeat. Historical synthetic V1 remains
INTEGRITY_FAILURE; current production20/42. Next separately specify corrected
synthetic coupling consuming this contract before new outcomes. Physical units/
geometry/velocity/length, original raw prerequisites and anatomical/neural transfer
remain before a new Unity muscle-interface experiment. Independent balance is not
established by the current assisted observations.
See UNITY_AND_BALANCE_ROADMAP.md and LF_ENDPOINT_CONTRACT_RESULTS.md.
