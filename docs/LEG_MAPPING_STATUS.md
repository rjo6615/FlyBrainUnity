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
