# FlyBrainUnity — local Codex handoff

Checkpoint: 2026-10-25. Repository: `rjo6615/FlyBrainUnity`.
Verified baseline for the LF activation-integrator update: `newBrain` at
`a5b8cdd` (merged PR #270).
Fetch and inspect current state before starting work.

## What the user wants

A scientifically controlled connectome-based fly whose movement emerges from
neural activity coupled to body physics and environmental senses. The intended
sequence is expanding the anatomically supported motor inventory toward all 42
coordinates, adding senses, then testing balance and locomotion. Stable gait
has not been established. Do not make neurons fire merely to make a joint move.
The user explicitly reaffirmed this constraint during the recent work.

Each update uses a new branch from latest `newBrain` and a PR back to `newBrain`.
The user reviews/merges. Include files changed, tests actually run, manual Git
Bash instructions and expected outcomes. Keep negative results and experimental
limitations visible. Read root `AGENTS.md` for enduring workflow requirements.
The user explicitly wants a copy-paste Git Bash run block in every final update;
provide post-merge/pull replay commands directly, not just a documentation link.
The user also requests a roadmap update after EVERY run: what ran, what its result
establishes and its limits, current motor count, active gate and next concrete gate.

## Current runtime and code map

- `malecns_backend/neural.py`: calibrated NumPy LIF runtime; graph CSR rows are
  presynaptic. Default dt=0.5 ms, rest/reset=-52 mV, threshold=-45 mV,
  tau_mem=20 ms, tau_syn=5 ms, PSP scale=0.55, minimum synapses=6,
  refractory=3.76 ms, inhibitory gain=0.606. Conductance mode is active.
- `fly-brain-main/src/lif.js`, `src/brainmodel.js`, `src/ratenet.js`, and
  `public/data/brain_params.json`: checked-in fast-neural reference and calibration.
- `malecns_backend/live/__main__.py` and `live/headless.py`: live launcher/session
  factories. Default interface v1=11 motors; v2=17; v3=20. All currently use six
  tibia proprioceptive populations (392 neurons), with tactile delivery disabled.
- `malecns_backend/embodiment/_windows_m8_live_condition.py`: shared scientific
  transition kernel, observers and optional passive probes. Reuse it rather than
  invent a second embodiment loop. Its optional old tactile path selects LM only.
- `embodiment/sensory.py`: existing modeled tibia angle encoder. Preferred angles
  depend on frozen list order, not measured individual sensory tuning.
- `live/upstream_diagnostics.py` and `live/presynaptic_trace.py`: body-ID/readout
  checks, post-step states, selected shortest positive paths and input activity.
- `live/sensory_coverage.py`: offline midpoint/up/down prescribed-angle experiment,
  optional pathway diagnostics, no physical body or motor commands.
- `live/contact_readiness.py`: bounded passive live-v3 exact Tarsus5/force survey.
- `live/contact_context.py`: fixed two-second passive live-v3 solver-force
  attribution audit with exact body/sensor ownership, complete raw evidence and
  strict observational context checks. It never enables tactile delivery.
- `embodiment/tactile_contact.py`: existing contact-only onset encoder. Engineering
  threshold 1e-12 model force units, maximum modeled rate 120 Hz, 20-ms linear
  onset pulse, no sustained-contact retrigger. These are not biological measurements.
- `embodiment/tactile_targeted_contact_calibration.py`: legacy environment-only
  targeted calibration; already accepts all six leg arguments. Source is locked
  by later milestone provenance and should remain intact.
- `embodiment/six_foot_contact_calibration.py`: new fixed batch and strict evaluator.

The authoritative maps are checked-in artifacts; inspect consumers and tests
before editing. Do not infer roles from similar names. Historical COMPLETE data
can coexist with older narrative docs saying NOT_RUN; inspect actual artifacts.

## Established recent findings

### Candidate motors and prescribed sensory stimulation

The three investigated v3 channels are `joint_RFFemur`, `joint_LFTarsus1`, and
`joint_RFTarsus1`. All were silent in the original resting live run. Identity and
observer checks passed; input reached some cells but remained subthreshold.

A seed-1, 10-second-per-condition offline experiment recruited all 392 sensors:

| Candidate channel | Midpoint spikes | Upward sweep | Downward sweep |
|---|---:|---:|---:|
| Right front femur | 3 | 1 | 3 |
| Left front tarsus | 2 | 1 | 1 |
| Right front tarsus | 0 | 0 | 0 |

The traced repeat reproduced those totals. On selected path
815569 -> 800022 -> 903285 -> 820110, counts were 363/144/0/0 at midpoint,
404/148/2/0 upward, and 392/40/0/0 downward. Motor 820110 received excitation but
remained at least 6.2316 mV below threshold in upward-condition post-step samples.
Other selected intermediates 902679 and 46348 never spiked in these conditions.
Paths are structural examples, not exhaustive causal routes. Voltage is sampled
after spike reset and synaptic decay; maxima are not pre-spike peaks. Separate
excitation/inhibition peaks cannot be subtracted as simultaneous net drive.
These sparse results establish neither useful movement nor biological function.

### Neural scaling and neuromodulation

PR #252 corrected a demonstrated regional median convention mismatch: JS uses
upper middle size for even populations; Python had averaged the middle pair.
The canonical VNC input-scale effect is about +0.001515%, too small to claim as
an explanation/remedy for the silent tarsus. Actual calibrated JS constructor
and 160-step mixed-input parity checks pass. User independently ran the 14-test
neural/parity check successfully. See `embodiment/NEURAL_SCALING_AUDIT.md`.

Python removes OA fast signs but omits the reference's separate slow modulation
system. This documented scope difference is not automatically a bug. PR #253's
static reference audit found 37 OA cells, 16 IPCs and 10004 direct OA targets.
None of the 21 watched cells (including seven right-tarsus motors and selected
intermediates) has direct OA input at minSyn=6. No direct target is in a vnc_*
superclass; descending/ascending targets leave indirect effects possible.
No physiology was enabled. See `embodiment/NEUROMODULATION_SCOPE_AUDIT.md/.json`.

### Contact readiness: positive observational result

User ran PR #254's two-second current-v3 passive survey:
`v3-contact-readiness.json`, completed=true, 20001 samples, no tactile delivery.
All feet had positive and negative exact Tarsus5-ground contact samples.
Force-above-1e-12 matched exact contact presence with zero mismatches in every
sample for every foot. This is posture-specific correspondence evidence, not a
matched threshold calibration or proof of biological sensing/balance.

### Latest calibration: controls contaminated, no feet admitted

User ran PR #255's fixed six-foot calibration and uploaded
`six-foot-contact-calibration.json`. All twelve physics conditions completed.
Each condition contains 501 samples over 0.05 seconds at dt=0.0001 seconds.
All six feet failed exactly `control_never_touches_target_surface`; accepted_legs
is empty and all_six_accepted=false. Other strict checks passed.

| Foot | Control contact samples | Contact-condition contact samples | First control contact (ms) |
|---|---:|---:|---:|
| LF | 44 | 46 | 2.9 |
| LM | 92 | 92 | 3.1 |
| LH | 80 | 82 | 3.4 |
| RF | 45 | 46 | 2.9 |
| RM | 91 | 89 | 3.1 |
| RH | 79 | 83 | 3.4 |

The nominal negative surface starts with a 0.01 model-unit gap but is contacted
during the trajectory. Exact contact/force presence agrees in **all 6012 samples**
(6 feet x 2 conditions x 501). Thus the strict failure is the negative-control
design, not a demonstrated sensor failure. The older threshold evaluator filters
out contacted control samples before computing false positives; its
THRESHOLD_ACCEPTED output must not override the newer full-condition rejection.
Do not drop those samples, shorten the window after seeing contact times, or
weaken acceptance merely to admit the feet.

A derived machine-readable summary with source-file hashes is in
`docs/evidence/contact-calibration-checkpoint.json`. It is a summary of user-run
measurements, not the complete raw record or automatic experimental approval.
The raw uploads may not be committed; look in the user's repository/root outputs
before requesting files. If unavailable, retain the checkpoint and distinguish
what cannot be independently rechecked. Do not rerun an unchanged failed protocol.

## Latest update — separately versioned isolated control implemented

`embodiment/six_foot_contact_calibration_v2.py` implements the predeclared
collision-isolation protocol in `docs/SIX_FOOT_NEGATIVE_CONTROL_V2.md`. Both arms
exclude ground, self and other-foot collisions. The negative surface is remote
and collision-disabled; the positive permits only the exact selected pair.
This changes physical support/collision context and does not validate ordinary
live-v3 contact. Original v1 sources/evidence/acceptance remain intact.

Actual local physics completed both twelve-arm runs. Initial v2 rejected all feet
for implementation integrity defects (auto-generated namespaces and float32 norm
precision). The separately documented v2.1 correction fixes those contracts,
without weakening checks or changing physical/neural parameters. It was committed
before its justified verification repeat. All six pass v2.1 in the isolated assay.
Full rejected and accepted evidence, hashes, environment and checks are preserved
under `docs/evidence/six-foot-v2*.json.gz` and
`docs/evidence/six-foot-contact-v2-checkpoint.json`. See
`docs/SIX_FOOT_NEGATIVE_CONTROL_RESULTS.md` for counts and limits.

The context-transfer prerequisite was investigated by the following separate
observational protocol. Isolated acceptance by itself did not establish transfer.

## Latest update — normal supported live-v3 context observed

The protocol in `docs/LIVE_CONTACT_CONTEXT_V1.md` was committed at 80aba8d before
its single two-second live-v3 CNS/physics experiment. The existing kernel and
normal corrected support/collision context ran unchanged, with no tactile input.
All 20000 physics transitions / 4000 neural updates completed; 20001 raw states
and 333454 complete contact records are preserved through Git LFS in
`docs/evidence/live-contact-context-v1.json.gz`. Hashes and complete evaluation
are in `docs/evidence/live-contact-context-checkpoint.json`.

All six feet passed exact sensor/body/geom ownership, force reconstruction,
telemetry conversion, immutable-context and full-window correspondence checks.
Positive/negative state counts LF/LM/LH/RF/RM/RH were 19970/31, 19946/55,
19946/55, 19902/99, 19943/58, 19938/63. No ambiguous direct sources or force,
reconstruction or telemetry disagreements occurred. All distal positive sources
were ordinary ground; the calibration surface had no positive coverage. Do not
generalize this result to unobserved collisions, other seeds/poses or continuous
geometry between physics samples. This remains observational, not causal.

127 tests plus 9 subtests passed, including full archived-evidence hash/source
verification and replay of every reported check. A separate paired ten-transition
physics-only implementation smoke test showed exact observed/unobserved parity;
its held-joint context is not scientific live-v3 evidence. See
`docs/LIVE_CONTACT_CONTEXT_RESULTS.md` for details and Git Bash commands.

The next task at that checkpoint was to design and separately version matched tactile-delivery
enabled/withheld experiment in the tested supported context, reusing the encoder
and independent/common candidate sampling, with pre-intervention equivalence and
verified delivery/readout boundaries. Define treatment of unobserved contact
sources explicitly. No tactile delivery is enabled by this update. Acceptance
does not establish balance, gait or biological transduction.

## Latest update — matched tactile delivery changed the simulated body

The fixed two-second WITHHELD/ENABLED protocol and instance-local external-input
adapter were committed at 24af69f before execution. Both fresh live-v3 arms ran
20000 physics transitions / 4000 neural updates, keeping normal supported physics,
20 motor interfaces and all physiological/encoder parameters fixed. They use a
prospectively common 2269-slot CNS external RNG schedule in both arms; this is an
explicit assay context. No locked kernel/neural/encoder source or ordinary live
default was changed. Six complete tactile populations (1877 neurons) are sampled
in both arms; only the input delivery mask differs. No retries or tuning ran.

All paired integrity and calibrated-context checks passed. First eligible tactile
event / CNS divergence was 0.5 ms; non-input state divergence 2.5 ms; non-input
spike divergence 5.5 ms; motor spike/decoder/command divergence 14.5 ms; physical,
joint and contact-force divergence 14.6 ms. Excluding all 2269 input neurons
distinguishes downstream effects from directly driven sensory spikes.

WITHHELD delivered zero tactile events; ENABLED delivered 64431 over the fixed
window. Later contact/candidate totals legitimately diverge in closed loop. The
previously investigated right-front femur motor readout had 0/56 spikes
(WITHHELD/ENABLED), left-front tarsus 0/9, right-front tarsus 0/0. Full-window A/B
joint differences reached 15.10 degrees at left-middle tibia; maximum root
separation was 0.291869 model mm. These are simulated effects, not balance/gait
or biological validation. No positive calibration-surface coverage was observed.

Full raw pair is in Git LFS at `docs/evidence/matched-tactile-v1.json.gz`; hashes,
full checks, counts and descriptive magnitudes are in
`docs/evidence/matched-tactile-checkpoint.json`. See
`docs/MATCHED_TACTILE_DELIVERY_V1.md` for prospective criteria and
`docs/MATCHED_TACTILE_DELIVERY_RESULTS.md` for actual checks and Unity commands.
The older tactile-contact artifact hash test fails unchanged in origin/newBrain
because d03f2a6 added live metadata without changing biological populations;
neither the expected hash nor the artifact was refreshed in this update.

Immediate next task: review the paired recorded Unity poses and intervention
evidence, then design any ordinary live tactile mode or next motor/balance
experiment separately. `live.tactile_replay --condition BOTH --speed 0.1` streams
the saved arms through the existing output-only protocol without rerunning CNS.
The standard live-v3 launcher remains tactile-disabled. Unity Editor was not run
by the agent; an actual two-pose TCP smoke check passed. Preserve the right-front
tarsus null result and distinguish passive mechanical motion from motor spikes.

## Latest update — matched-state disturbance/recovery completed

Protocol, runner and metrics were committed at ce2dde9 before the three fresh
two-second runs OFF_C, OFF_P, ON_P. ON_C reuses the fully verified archived
matched-pair ENABLED trace. All cells share exact neural/physical history through
500 ms. OFF withdraws tactile from 500.5 ms; P adds the unchanged historical M9B
Thorax pulse [0, 1.024, 0], outgoing transitions 5000..5199. Existing kernel,
encoder, physiology, support, collision and common 2269-slot RNG schedule remain
fixed. All integrity checks passed, including full prefix matching, exact wrench
and sensor attribution. No retries, parameter tuning or weakened acceptance.

Functional outcome is adverse: continued tactile had peak/mean orientation
deviation 12.798550/5.763657 deg versus withdrawn 3.418028/1.340016, each relative
to its own undisturbed control. The prospective label is amplified orientation
response. Both baselines qualified, both pulses resolved and exited recovery
bands, but neither met the fixed 100 ms sustained return within two seconds.
Neither rolled over or crossed the low-height limit. This does not establish
beneficial balance, gait or biological validation. Keep the adverse result.

Full fresh traces and evaluation: `docs/evidence/tactile-recovery-v1/`; prospective
criteria: `docs/TACTILE_DISTURBANCE_RECOVERY_V1.md`; results/manual Git Bash checks:
`docs/TACTILE_DISTURBANCE_RECOVERY_RESULTS.md`. Ordinary live tactile remains off.
`live.tactile_recovery_replay --manifest docs/evidence/tactile-recovery-v1/manifest.json
--condition PUSHED --speed 0.1` streams measured clips with explicit reset and
intervention labels; a clip reset is not a simulated jump. Unity Editor was not
run by the agent. Preserve the known predecessor artifact-hash test failure.

Immediate next task: review recorded pushed and undisturbed conditions, then
separately design/preregister a motor-application control with exact replayed
command provenance and matched state/sampling to distinguish active motor
application from passive mechanics and withdrawal effects. Do not tune neural
parameters, increase the pulse or broaden normal live mode to obtain a pass.

## Latest update — motor-command yoke control completed

Protocol/runner committed at 220899c before two fresh fixed two-second trials Y_C
then Y_P. All tactile/CNS/decoder computation continues, but each outgoing physical
action uses the exact same-transition archived undisturbed ENABLED command.
Y_C exactly reproduced the entire original trajectory/contact/encoder and all
4000 neural records. Y_P uses the unchanged 500..520 ms Thorax pulse. All initial,
pre-push, common RNG, input/readout, contact, applied-command and force checks pass.
Y_P altered 14720 proposed outgoing actions, first at transition 5280 (528.0 ms).

The prospective YOKING_REDUCES_RESPONSE label is supported: peak/mean orientation
deviation was 1.447819/0.453098 deg yoked versus 12.798550/5.763657 closed loop,
each against its own undisturbed control. Peak absolute tilt was nevertheless
higher yoked (9.947980 vs 7.323098 deg). Neither rolled over or crossed the low-
height limit; neither met sustained recovery within two seconds. Baseline active
actuation remains, so this is not a fully passive-body test or proof of balance.
Keep both relative-response and absolute-tilt results visible. No tuning/retries.

Protocol/results: `docs/TACTILE_MOTOR_YOKE_V1.md` and
`docs/TACTILE_MOTOR_YOKE_RESULTS.md`; complete traces/manifest in
`docs/evidence/tactile-motor-yoke-v1/`. Recorded replay:
`live.tactile_motor_yoke_replay --manifest docs/evidence/tactile-motor-yoke-v1/manifest.json
--condition BOTH --speed 0.1`, comparing Y_P and original ON_P. Explicit resets
are not physical jumps. Ordinary live mode remains tactile-disabled.
Validation: 252 tests plus 9 subtests passed, including full saved analysis and
actual recorded-pose TCP checks. Fresh Windows CRLF checkout failures were resolved
by restoring original Git blob bytes and protecting five provenance-sensitive
paths with -text; no scientific content or expected hash changed. The separate
legacy metadata-related artifact failure remains 6 passed / 1 failed. Unity
Editor was not run by the agent.

Immediate next task: separately preregister admitted motor-command dissection
using the existing M11 infrastructure in this exact 20-motor tactile context,
with matched disturbed/undisturbed controls and a channel-selection rule chosen
before outcomes. Track absolute tilt and disturbance-relative response separately.
No neural parameter tuning or channel search until a favorable result appears.
Baseline active commands/passive mechanical support remain unresolved components.

## Latest update — anatomical tibia command-group dissection completed

Protocol/runner/tests committed at 9f58379 before fresh fixed two-second T_C then
T_P trials. All six tibias selected by existing M11 anatomical mapping and exact
v3 indices 5/12/19/26/33/40, not outcome ranking. Only those six applied actions
follow the undisturbed recording; other 36 coordinates (including 14 admitted
motors) exactly retain their contemporaneous native proposals. CNS/tactile/
decoder computation remains active. All integrity checks pass; T_C reproduces
the complete original control trajectory/contact/encoder and all neural records.
Same pulse/seed/window/physiology/metrics; no tuning or retries.

Peak/mean orientation deviation is 9.881202/3.725524 deg tibia-only versus
12.798550/5.763657 full closed-loop and 1.447819/0.453098 all-command-yoked,
each relative to its own undisturbed control. The predeclared primary label is
SELECTIVE_YOKING_REDUCES_RESPONSE. Absolute tilt is nevertheless worse than full
closed loop (9.667409 vs 7.323098 deg), as are peak linear/angular velocity errors.
No rollover or low-height crossing, but no sustained recovery. Not a balance proof.

T_P replaces 14720 outgoing transitions from transition 5280 (528 ms); per-channel
LF/LM/LH/RF/RM/RH exposure counts are 14385/14560/14425/0/14695/14720. Preserve RF
tibia zero command-intervention exposure: it is not proof of silent motor neurons
or an individual causal contribution. Group effects can be non-additive and other
motors can compensate. Existing M11 classification helpers and yoke/kernel reused.

Complete evidence: `docs/evidence/tibia-command-dissection-v1/`; protocol/results
and manual Git Bash review: `docs/TIBIA_COMMAND_DISSECTION_V1.md` and
`docs/TIBIA_COMMAND_DISSECTION_RESULTS.md`. Recorded Unity command:
`live.tibia_command_replay --manifest docs/evidence/tibia-command-dissection-v1/manifest.json
--condition BOTH --speed 0.1`, T_P versus original ON_P; ALL adds T_C and Y_P.
Shared pose-stream helper preserves the earlier replay CLI; clip resets are not
physical jumps. Ordinary live tactile mode remains disabled.
Validation: 275 tests plus 9 subtests passed across the focused matrix and final
new archived-evidence/TCP check. All saved new/upstream source/hash/evaluation
checks replayed; actual recorded T_P/ON_P/Y_P endpoint poses passed local TCP.
The separate legacy tactile-contact suite remains 6 passed / 1 unchanged metadata
hash failure. No Unity Editor run, neural tuning or duplicate scientific trial.

Immediate next task: separately preregister the complementary 14 admitted motor
channels, defined as the fixed inventory minus these six tibias, with matched
disturbed/undisturbed controls and tibias retaining native closed-loop commands.
Complete the group comparison before interpreting interactions or individual
channel contributions. Preserve all tradeoffs/nulls; do not tune neural parameters
or select channels from outcome rankings to obtain a favorable result.

## Latest update — complementary 14-motor command group completed

Protocol/runner/tests committed at 939459a before fresh fixed two-second C_C then
C_P trials. The group is the exact v3 inventory minus the six tibias: six femur,
six femur-roll and LF/RF Tarsus1 channels. Only those 14 commands use archived
undisturbed actions; other 28 coordinates (including all six tibias) exactly retain
native proposals. All CNS/sensory/readout/decoder computation continues. No neural
tuning, force/window/seed/acceptance changes or retries. All integrity checks pass;
C_C exactly reproduces the entire original control trajectory and neural records.

Complementary replay peak/mean orientation deviation is 6.094436/2.337358 deg
versus full closed-loop 12.798550/5.763657, tibia-only 9.881202/3.725524 and all-
command-yoked 1.447819/0.453098, each against its own undisturbed control. Primary
label SELECTIVE_YOKING_REDUCES_RESPONSE. Peak absolute tilt is nevertheless highest
in the complementary replay (14.781105 vs 7.323098 deg closed loop), and peak
linear-velocity error increases to 19.454490 vs 11.501194 model mm/s. No rollover
or low-height crossing, but no sustained recovery. Preserve the mixed tradeoffs.

All four group contexts are now measured. Full closed loop has the lowest peak
absolute tilt and largest orientation departure from its undisturbed trajectory.
This supports a modeled posture-related motor-application effect, not general
balance, gait, intent, individual-channel necessity or fully passive support.
Group comparisons are context-dependent and non-additive; do not infer fractions
explained from differences of peak norms. C_P alters 14720 outgoing actions from
transition 5280 (528 ms). RF Tarsus1 has zero command-intervention exposure; preserve
this and the earlier RF tibia null, without claiming silent neurons.

Full evidence: `docs/evidence/complement-command-dissection-v1/`; prospective
protocol/results and manual Git Bash instructions:
`docs/COMPLEMENT_COMMAND_DISSECTION_V1.md` and
`docs/COMPLEMENT_COMMAND_DISSECTION_RESULTS.md`. Replay:
`live.complement_command_replay --manifest docs/evidence/complement-command-dissection-v1/manifest.json
--condition BOTH --speed 0.1`, C_P versus original ON_P; ALL includes C_C/T_P/Y_P.
Reuse the shared output-only measured-pose loop. Ordinary live tactile stays off.
Validation: 298 tests plus 9 subtests passed across the focused matrix and final
new/upstream archived-evidence/actual-TCP check. Actual saved C_P/T_P/ON_P/Y_P poses
passed local TCP. Separate legacy tactile-contact remains 6 passed / 1 unchanged
metadata-hash failure. Real dry CLI returned NOT_RUN/1; no Unity Editor run.

Immediate next task: separately preregister a saved-evidence time-aligned posture
analysis of the four frozen contexts, distinguishing absolute tilt/world state
from disturbance-relative trajectory error. Declare any root-vector interaction
estimand and fixed windows before computation; do not add peak norms as channel
contributions. No new CNS/physics runs are needed. Use those results to decide
the next motor/sensory roadmap step without parameter tuning or winner searches.

## Latest update — frozen posture analysis and mapping status

Analysis protocol/analyzer/tests committed at e7f808f before computing new timing
and vector interactions. All original outcomes/protocols remain unchanged. Full
frozen source/raw/evaluation chains validated, then eight root traces reduced to
20001 states each. All four unpushed controls match exactly; pre-force histories
and all old response summaries reproduce. Zero new CNS/physics transitions.

Absolute tilt and distance from a moving control explain the mixed results. Full
closed loop has absolute peak tilt 7.323098 deg at 1998.7 ms and relative orientation
peak 12.798550 at 2000 ms, while relative body-up peaks 7.788052 at 774.2 ms. At the
complementary replay's absolute peak 14.781105 deg (777.6 ms), its control is already
tilted 10.512604 deg and full relative error is only 4.288840 deg. Full orientation
includes heading; do not subtract angle metrics to calculate yaw. Last-state
relative maximum leaves behavior beyond the fixed window unknown.

Predeclared signed root-vector interaction (all replay - tibia - complement +
closed loop, each pushed minus own control) peaks 0.263570 model mm at 911.9 ms,
xyz [0.003593,-0.262681,0.021328], exceeding inherited .005 model-mm resolution.
Dimensionless body-up-vector interaction peaks .173875 at 940.8 ms. Group effects
are non-additive and context-dependent, not percentages explained or statistical
significance. No general balance/gait/intent/passive-support proof or recovery.

Evidence/report/plots: `docs/evidence/group-posture-analysis-v1/`; prospective
specification/results: `docs/GROUP_POSTURE_ANALYSIS_V1.md` and
`docs/GROUP_POSTURE_ANALYSIS_RESULTS.md`. `docs/LEG_MAPPING_STATUS.md` answers the
user's mapping question: 20/42 model coordinates admitted (6 tibia, 6 femur, 6
femur roll, 2 front Tarsus1), remaining 18 coxa + 4 middle/hind Tarsus1. Structural
coordinate names are known; motor admission is not percentage biological mapping.
Six tibia proprioceptive/experimental tactile populations remain as before;
ordinary live tactile remains off. No additional interface admitted in this work.

75 focused tests passed; 2 previous archived simulation/TCP tests explicitly
excluded, while full upstream evaluations were recomputed during actual analysis.
New saved numeric-artifact math and all original compressed/raw hashes verified.
Separate legacy tactile-contact remains 6 passed / 1 unchanged metadata hash failure.
Charts visually inspected; no new Unity Editor run, physics, neural tuning or raw
evidence change. User can run `live.group_posture_review --report
docs/evidence/group-posture-analysis-v1/analysis.json` and open posture/interaction
PNGs in VS Code; no further Unity run is needed for this update.

Immediate next task: return to the 42-coordinate motor-admission roadmap. Audit
the existing ordered admission/candidate/reference reports for each remaining 22
coordinates: body-ID/population mapping, completeness/antagonism, mechanical sign
provenance, existing validation and exact missing prerequisites. Identify the next
defensible separate admission protocol from reference evidence, not activity or
effect ranking. Preserve calibrated physiology, all locks/nulls/tradeoffs and the
distinction between structural mapping, validated admission and emergent behavior.

## Latest update — remaining 22 admission coordinates audited

Data-only current-v3 projection confirms 20/42 admitted motors. All remaining
22 rows have exact action/annotation/neuron identity and blocker records in
`docs/evidence/remaining-leg-admission-audit-v1_1/`. Results:
12 Coxa/Coxa_roll shared-axis ambiguities; 6 Coxa_yaw anatomical sign bridges
unresolved; 4 middle/hind Tarsus1 exact target mappings absent. Tarsus2 annotations
are different targets and are not promoted/mirrored. Newly admitted channels = 0.

Initial audit v1 (source commit 0128b86) failed on an incorrect global population-
name uniqueness assumption; its error output is preserved under v1. The separately
documented v1.1 correction committed at 2996dcc before generation validates every
selected alias against identical complete body-ID/dense-index identities and
exhaustive metadata, retaining multi-target ambiguity. No last-wins selection or
pool union. The exact immutable neurons.flyn index was decoded; no brain/physics
runtime or scientific transition was constructed/executed by the auditor.

All six old yaw anterior projections remain zero, classifications unresolved and
coordinate signs null. Existing LF-only local registration has seven covectors
whose transforms reproduce within 1e-12; it explicitly does not establish MaleCNS
coordinate signs/decoder weights or admission. Five LF candidate identities are
checked. Existing three-seed recruitment null decisions remain older 11-motor
context records, not inevitable silence in current tactile/v3 context.

Three old raw freeze checks fail in CRLF representation; canonical LF bytes match
both unchanged expected hashes and original Git blobs. Audit records raw failure
separately (all_original_raw_freezes_satisfied=false), not as a passed prerequisite.
No artifact/hash/verifier is altered; future scientific execution must satisfy
the original raw prerequisites independently. Admission remains blocked regardless.

Relevant matrix: 55 passed / 5 historical failures, all five reproduced on primary
checkout without new code. One assumes NOT_RUN despite frozen COMPLETE, three
call preflight against occupied frozen output, one double-converts CRLF. No old
test/code/artifact changed to hide these failures. All 15 new audit tests pass;
actual v1.1 generation and user review command pass. Zero new admissions/steps.

Read `docs/REMAINING_LEG_ADMISSION_RESULTS.md` and
`docs/LF_PROXIMAL_ADMISSION_PREREQUISITES_V1.md`. Review:
`embodiment.remaining_leg_admission_review --report
docs/evidence/remaining-leg-admission-audit-v1_1/audit.json`; open matrix.md and plan
in VS Code. No Unity run. Include exact Git Bash commands in every final update.

Immediate next task: LF proximal reference-backed population-to-muscle activation/
sign binding and multi-axis mapping prerequisites, using the five exact populations
and seven LF-only local tendon records. Resolve broad promotor multi-tendon hypotheses
without averaging/ranking by outcome. Do not infer a coordinate sign from names,
neurotransmitter alone or geometric dominance. Only after independent reference and
numeric/application gates are specified, create a separate bounded validation
protocol in the current context. Never tune neural parameters to obtain activity,
reinterpret frozen yaw nulls, mirror front tarsi or flip current admission flags.

## Latest update — LF proximal muscle-reference semantics reviewed

Protocol/code/tests committed at aeb4824 before generating
`docs/evidence/lf-proximal-binding-review-v1/review.json`. Static XML inspection
verifies the original local FlyMimic source-model raw hash against the frozen
registration (a72d4a31...). All seven LF tendon actuators have the recorded muscle
activation/gain/bias semantics and unit gear. No XML compilation, mesh loading,
physics/CNS transitions, force application, dependencies or current decoder change.

Reference R=-dL/dq gives tau=T*R for positive tensile magnitude T; the scalar
pulling-force sign must not flip R a second time. Virtual-work/reference algebra
tests pass. This is conditional local generalized torque, not neuron-to-angle
sign, acceleration, decoder gain or biological validation. Current shared kernel
uses position commands; force-to-target transfer remains absent.

Complete existing admission reviewer rechecks five populations/13 neurons and
every alias, seven local covectors and original raw failures/nulls. All three
broad-promotor alternatives remain separate (even roll signs differ). All
per-neuron tendon assignments, spike-to-activation, activation-to-force,
force-to-position transfers, decoder vectors and gains remain unassigned. Four
single-class hypotheses are not independently established specimen crosswalks.
Current admission remains 20/42; no new channel or ordinary tactile mode enabled.

31 focused tests pass (16 new plus 15 existing audit tests). Initial sandbox run
had 26 pass/5 temp-directory setup errors; writable fresh --basetemp resolves the
execution issue without changing code/scientific criteria. Actual generation and
saved-report verification pass; original raw-freeze flags remain false. No new
Unity run. See `LF_PROXIMAL_BINDING_REVIEW_V1.md` for primary sources/access limits
and `LF_PROXIMAL_BINDING_RESULTS.md` for all changed files, tests and Git Bash code.
Review CLI: `embodiment.lf_proximal_binding_review --model
"$HOME/Documents/FlyMimic/flymimic/assets/models/best_combined_cvt3.xml" --report
docs/evidence/lf-proximal-binding-review-v1/review.json`.

Immediate next evidence requirement: independently traceable neuron-to-muscle/
tendon crosswalk, especially the four broad-promotor neurons versus three model
tendons, and an explicit force-interface versus engineered position-target design.
Do not repeat the same audit or infer bindings from labels/order/activity. Without
new independent evidence, report the unresolved blocker rather than enabling
channels. Specify activation/passive dynamics, units, supported pose/range and
transfer validation before a separate numerical/application experiment. Original
raw scientific prerequisites must pass independently; canonical agreement does
not waive them. No numerical bounded admission experiment is ready yet.

## Latest update — independent LF anatomical source crosswalk

New primary reference acquisition, not another replay of the same saved audit.
Official MaleCNS v1.0 raw annotations are separately archived in Git LFS at
`docs/evidence/lf-anatomical-crosswalk-v1/annotations.feather`, raw SHA
2177e246113e4cfbf1e7772ec37c6da1955ff22e8063d0b1f833101f99a9a3b2,
14483314 bytes / 211577 source rows. Dataset CC-BY attribution recorded. The
existing runtime remains unchanged; this broader source table does not add cells.

Exact source pools reproduce five LF classes / all 13 existing body IDs, types,
side fallback, motor superclass, front-leg subclass, T1 and exit nerves. Full
selected source rows are in crosswalk.json. Twelve recorded mancBodyid matches
are retained as published annotations, not independently revalidated morphology.
Body 1050335829 has null mancBodyid; its mancGroup 21241 is not a substitute ID.
No individual FANC MN number, tendon, sign or gain is assigned to any body ID.

Full author-hosted 46-page Azevedo anatomical appendix was downloaded and relevant
figures/captions visually inspected (PDF pages 15-19), resolving the previous
web-reader size limit. Figure A2 explicitly says each of its four promotor MN
targets is uncertain even within the original two-muscle grouping. FANC is a
different specimen; atlas numbering, names/counts/nerve agreement do not establish
a MaleCNS-to-FANC individual match or a split into FlyMimic's three tendons.
Four other classes have single-class anatomical support, still modeled hypotheses
when transferred to the simulation. No complete individual tendon crosswalk found.

Source research was inspected before the written report; no claim of prospective
physiological experimentation. 45 focused tests pass (14 new / 16 LF reference /
15 audit), including actual full official-byte and upstream identity verification.
Actual generation and saved-review CLI pass. No new CNS/physics/Unity trial,
dependencies, neural tuning or admission; current 20/42 and old raw failures remain.
See `LF_ANATOMICAL_CROSSWALK_V1.md` and `LF_ANATOMICAL_CROSSWALK_RESULTS.md`.
Git Bash: LFS pull new annotations.feather, then run
`embodiment.lf_anatomical_crosswalk --report
docs/evidence/lf-anatomical-crosswalk-v1/crosswalk.json`. Include full copy-paste
commands in every delivery. Local PDF/rendered pages remain untracked in this
update's tmp/pdfs; source URL, hash and locators recorded in tracked reports.

Immediate next engineering scope: separately specify an LF muscle-force reference
adapter and isolated force-projection/isolation validation using four explicit
class-to-muscle hypotheses, keeping broad promotors unassigned and production
20-motor behavior intact. Do not repeat the same audit to force a promotor split.
Reuse existing observer/registration, distinguish torque from position targets,
and prevent double actuation. Specify force units, activation/passive dynamics,
supported reference pose/range and numerical/application gates before scientific
coupling. Synthetic known-tension fixtures establish software/reference mechanics,
not biological gain or neural recruitment. No production admission or bounded CNS
experiment until original raw and remaining scientific prerequisites independently
pass. Preserve all historical nulls and never tune to get activity.

## Latest update — isolated LF force-reference adapter validated

Initial protocol/fixture/adapter/tests committed at 8228e84 before archived v1.
Four explicit single-class tendon hypotheses project known nonnegative tensions
through frozen R_G; no broad promotor, per-neuron tendon assignment, neural gain or
activation law. Synthetic fixture has free root + sentinel hinge + three LF-named
reference hinges; DOFs 7/8/9, qpos 8/9/10, not logical action indices 2/0/1.
Require exact reference pose/time, zero actuators/passive/contact forces, and exact
force ownership. Apply/clear reject pose/velocity/foreign force/double application.
No production runner or position actuator behavior changed; current 20/42.

V1 array checks passed but strict review-boundary test exposed inherited side
effect: audit.build -> corrected _protocol -> old._inventory ->
enumerate_live_actuators constructs FlyGym and calls mj_forward during model init.
Its calls were outside the fixture counter. V1 operation/construction-free-review
provenance is rejected and raw evidence preserved, with context-audit-v1_1.json.
No CNS/integration transitions identified. Older audit/crosswalk implementations
remain untouched; their inventory calls can construct a native model despite
earlier data-only phrasing. Do not infer zero construction from zero transitions.

V1.1 correction committed at 276c4f1 before justified fixed repeat. New local
static loader reuses original snapshot/frozen_record/codec/inspect_lf/row_record/
crosswalk validators plus locked build_live_protocol and pure v2/v3 metadata
derivations; no live enumeration or fabricated physical records. All exact LF
records/aliases/nulls/covectors and 22 remaining rows reproduce. This is static
admission verification, not newly compiled current-fly physical validation.

Six native fixture conditions all pass. Across preflight/execution, Python API
instrumentation observes exactly 18 mj_forward and 0 mj_step calls; compiler-
internal calculations are not counted as API calls. No integration or CNS.
Complete matrices/accelerations/poses/forces preserved in
`docs/evidence/lf-force-reference-v1_1/validation.json`. Max projection error
8.674e-18, dynamics residual 7.807e-17, virtual-work error 4.337e-19 under declared
1e-12/1e-10 implementation tolerances. Old raw prerequisites remain false.

74 focused tests pass (29 new, 45 previous). Discovery matrix was 71 pass/1 strict
boundary failure; corrected path keeps that test and also forbids enumeration and
integration. Exact saved-review command passed in Windows Git Bash. No dependency
changes, Unity Editor or neural/fly behavioral experiment. Saved review is now
verified without dynamics. See LF_FORCE_REFERENCE_V1.md, V1_1.md and RESULTS.md.
Git Bash after pull/LFS: `embodiment.lf_force_reference_validation --report
docs/evidence/lf-force-reference-v1_1/validation.json`. Include full copy-paste
commands every delivery. V1 remains preserved and is rejected by v1.1 review.

Immediate next scope: separately specify pose-dependent mechanical transfer and
activation/passive tension/units, plus selective actuator replacement preventing
double actuation in a moving fly. Current adapter deliberately supports only the
exact synthetic reference pose and nu=0, not production attachment. No arbitrary
finite-angle reuse, peak-force/gain transfer or new admission from fixture success.
Original raw and remaining biological/application prerequisites must independently
pass before bounded neural coupling. Preserve broad-promotor uncertainty and
historical nulls. Do not tune neural parameters or gains to produce activity.

## Latest update — pose-dependent rotation/source-force reference

Protocol/code/XML+71-asset locks committed at 51a22f3 before v1. Original source
XML hash unchanged, assets 13961614 bytes. Validated MuJoCo3.2.7 reused without
environment/source changes. Four class hypotheses only; broad promotors unassigned.
New declared map Q_G=Q_M(q)*Q_M(qref)^T, target intrinsic XYZ. J=inverse(B_G)*B_M,
R_G=inverse(J)^T*R_M. This is a modeled rotational correspondence, NOT anatomical
finite-angle registration to actual FlyGym, attachment/mass or translation matching.

Fixed 15 source poses: center, +/- .05 on each axis, 8 corners. Activation0/.5/1,
six +/-1e-6 derivative probes per pose, two central activation derivatives. Exactly
137 explicit mj_forward calls; observed mj_step0, no integrated observation/CNS.
Compiler-internal model validation is not counted as explicit API calls. Preserve
all nonselected/passive source forces. No production actuator replacement or gain.

V1 completed but failed moment/total-force checks: raw actuator_moment is sparse,
despite a misleading dense-sized allocation. Rotation and muscle-function checks
passed; archived length differences independently matched frozen R_M2.765e-11.
Preserve failed v1 raw in LFS. Sparse-decoding correction committed at 7b9bbad
before justified v1.1 repeat. Native mju_sparse2dense plus archived raw CSR metadata;
saved review independently reconstructs with SciPy CSR. Same poses/epsilon/criteria.

V1.1 all checks pass: maximum tendon FD error1.889e-10, axes8.922e-11,
JacobianFD2.221e-10, native force reconstruction1.777e-15, work5.552e-17.
Central frozen J/R reproduce1e-10. J changes up to .02433096925 over sampled poses;
four R_G column component changes max .006291/.002568/.003326/.003562, descriptive
only, not a continuous-pose envelope or new gains. Total99 tests pass (25 new+74
prior); saved Git Bash review5.10s, strict no model construction/dynamics. Old
raw prerequisites false; current20/42, new admissions0. No Unity/neural experiment.

Central zero-activation source anterior-rotator tension11.60235359 native units
is passive; full activation total18.45632371. Others central passive0. Native
selected control floor.0001 means rawctrl0 at activation0 has derivative+2/s.
At activation.5 ctrl0/1 gives -1562.1875/+4000/s. Source tau_act/deact .0001/.0004s
before state factors are model choices, not measured MaleCNS physiology. No
activation transient/integration stability or biological force units established.

Evidence: `docs/evidence/lf-pose-force-v1/input-manifest.json`, failed
`lf-pose-force-v1/run/validation.json`, accepted `lf-pose-force-v1_1/run/validation.json`.
Both native records in LFS. Specs LF_POSE_FORCE_V1.md/V1_1.md; full outcomes and
manual commands LF_POSE_FORCE_RESULTS.md. Review `embodiment.lf_pose_force --report
docs/evidence/lf-pose-force-v1_1/run/validation.json`, without dynamics or external
meshes. LFS pull both pose records + existing annotations.feather. Always include
copy-paste Git Bash block in delivery; no Unity run for saved review.

Immediate next scope: separately specify bounded source activation-transient/
integration validation and zero-input/passive-preload baseline semantics. Establish
force/mass/length units and physical registration before current-body application.
Do not blindly copy source peak forces/time constants or existing 17Hz rate scale
as physiology. Future matched arms must retain identical passive/preload context.
Selective removal of exact3coxa position actuators must precede torques while
other39controls stay intact; do not globally disable20motors or double actuate.
No moving-fly neural coupling/admission until independent raw and numeric/application
gates pass; preserve broad-promotor ambiguity/nulls and never tune for movement.

## Latest update — source activation transients reveal numerical limits

Protocol/source binding/generated zero-DOF native fixture committed at9b95220
before one nine-condition campaign. Native muscle defaults/params/control limits
copied unchanged from exact source XML; fixed lengths equal prior central source
records, all activation0/.5/1 force values reproduce. Fixture nq=nv0,nu=na4;
no joint/body movement or CNS. Source-law surrogate only, not force-unit transfer.

Predeclared100/50/25us Euler grids,10ms duration, three conditions per grid:
RELAX_ZERO a0=0/rawctrl0; FLOOR_BASELINE a0=.0001/rawctrl0; PULSE same floor state
with rawctrl1 outgoing[2ms,5ms), zero otherwise. Control floor/passive bias retained.
Independent DOP853 reference uses native mju_muscleDynamics, tight declared
tolerances/maxstep2.5us, split at exact control boundaries; one fine reference per
condition reused for native grids. No new physiology or neural conversion law.

All implementation integrity checks pass:2100 explicit mj_step calls advance
activation/time only;2112 explicit mj_forward refreshes, zero CNS/body-joint
transitions. Compiler-internal validation excluded from API counts. During-step
force belongs to preintegration activation; refreshed force to updated activation.
Native Euler update, source forces, fixed contexts, source hashes and exact matched
baseline/pulse prefix through2ms all pass. Stationary baseline activation=.0001.

NUMERICAL_LIMITS_OBSERVED: all three PULSE cases FAIL predeclared full-window
activation error<=.01/bounds criterion. Maximum errors100/50/25us are
1.380663692/.559500792/.209847371.100us maxactivation1.999300240 (no configured
activation clamps);50/25us bounded but still inaccurate. Endpoint errors only
.000232091/.000125484/.0000653802 do not rescue full-window failures. Six zero-
input/baseline cases pass numerically. No grid chosen, no retry, no clamp/time-
constant/gain/threshold/window change. Both numerical failures and integrity
success are explicit; evidence review success is NOT timestep numerical acceptance.

Complete LFS record: docs/evidence/lf-activation-transient-v1/run/validation.json,
3799210bytes,SHA539c26fb35d15824d970b482d36af579186e2ed4fe1bf707c03c4e592a90e5fc.
115tests pass (16new+99prior), including actual native timing and strict no-native/
reference-integration review. Exact Windows Git Bash saved review5.60s. Full-window
plots generated by tools/plot_lf_activation_transient.py and visually inspected;
no overshoot clipped. No dependencies, Unity/neural experiment or production change.
Current20/42, newlyadmitted0, old raw prerequisites remain false.

Read LF_ACTIVATION_TRANSIENT_V1.md and RESULTS.md. Git Bash review module
embodiment.lf_activation_transient --report docs/evidence/lf-activation-transient-v1/run/validation.json
prints TRANSIENT EVIDENCE VERIFIED, NUMERICAL_LIMITS_OBSERVED and3PULSE FAIL lines
as expected findings. Pull new record and previous pose records/annotations via
LFS. Review performs no native or reference integration. Include full copy-paste
commands after each update and explain expected FAIL findings; no Unity run yet.

Immediate next scope: separately specify/validate a reference-faithful activation
state integrator with explicit ownership and force timing, keeping the same native
law/time constants/control floor/passive preload and all failed Euler baselines.
Do not add clamps or tune source/neural parameters/timesteps for a pass. Integration
fidelity is not biological calibration or movement evidence. Force units/physical
registration, exact selective actuator replacement, original raw prerequisites,
individual binding and neural conversion remain gates before moving-fly coupling.

## Latest update — source-law activation integrator validated at fixed lengths

Prospective protocol/solver/assay/tests committed at e1dadc7 before one nine-case
campaign, fresh baseline a5b8cdd. Same 100/50/25us external intervals and 10ms full
window, controls/initial states/passive preload/fixture/source parameters as the
old transient campaign. Radau rtol1e-9/atol1e-12, max_step=external interval; native
mju_muscleDynamics unchanged. No clamp, tuned time constants, grid search or retry.

All nine cases pass integrity and numerical acceptance: ALL_NUMERICALLY_ACCEPTED.
Full-window pulse errors 1.76429649e-10/1.24318000e-10/1.82032167e-12; all floor
baselines stationary, matched pulse prefix through2ms exact. Every case compared
at all401 archived25us reference timestamps plus macro states, with bounds also
checked on internal accepted Radau nodes. Criteria unchanged error<=.01 and bounds
[-1e-12,1+1e-12]. Not a continuous-time error theorem or biological calibration.

Reused exact prior DOP853 archive/hash, verified all coarse reference slices and
old numerical decisions. Old Euler PULSE failures stay FAIL; no historical record
modified. Pure interval solver returns copied state; zero-DOF adapter commits state
and time once, with native forward before/after for correctly aligned force and
derivative. 2100 interval solves/commits,4212 explicit mj_forward,0mj_step,CNS or
body/joint transitions. Strict zero-DOF/exact identity/address checks prevent use
as an unspecified moving-body split integrator; no production hook.

New LFS evidence docs/evidence/lf-activation-integrator-v1/run/validation.json,
7841130bytes,SHA256 cd545ca6863b2d2468da067b258d9aac0ecb7f3ab8a953f15c0d6574f62eb49b.
All accepted internal nodes, dense samples and solver costs retained. Existing
plotting tool optionally overlays new Radau results and all prior Euler failures;
comparison.png visually inspected. Read LF_ACTIVATION_INTEGRATOR_V1.md and
LF_ACTIVATION_INTEGRATOR_RESULTS.md for exact conditions and limitations.

139 implementation/reference tests passed in55.65s (24new+115prior). Includes
actual native single-interval ownership/timing checks, analytic mocked linear
solver plumbing separately, corruption/output protection and strictly model/native/
solver-free static review. Development scratch-parent setup error fixed before
campaign; full result passed. Exact Git Bash saved review5.61s, no new integration.
No dependencies, neuron/gain/production changes, Unity run or new motor admission.
Current20/42; original raw scientific prerequisites remain false.

Immediate next update: DESIGN AND STATIC AUDIT of selective LF actuator replacement
and activation/body state ownership, using exact coordinate/actuator/activation IDs,
identifying existing position controls to replace and controls to preserve. Prevent
double actuation and double integration. Keep disconnected from production. Specify
required physical-unit/geometry registration, old raw prerequisites, individual
tendon-binding and neural-conversion gates before moving-fly coupling; do not claim
those gates passed from this source-law numerical result. No Unity run yet.

Every run/final update must include a roadmap checkpoint. Admission20/42 is a
coordinate inventory, not overall project completion. Previous causal tactile/
disturbance/yoke observations remain bounded evidence, not established gait or
independent balance. Continue toward richer supported motor/sensory interfaces,
then causal balance/locomotion tests without scripted behavior substitution.

Git Bash review module: malecns_backend.embodiment.lf_activation_integrator_validation
--report docs/evidence/lf-activation-integrator-v1/run/validation.json. Pull the new
record and prior transient/pose records plus original annotations through LFS.
Expected INTEGRATOR EVIDENCE VERIFIED: ALL_NUMERICALLY_ACCEPTED and9PASS lines;
production20/42,0newadmissions, oldrawFalse. No repeat or Unity run needed.

## Completed predecessor task — negative-control design requirements

1. Inspect the actual legacy calibration runner, six-foot wrapper/evaluator,
   latest raw report if available, and existing tests/provenance locks.
2. Identify a defensible environment-only negative-control design that maintains
   independently verifiable separation throughout the planned window. An initial
   gap alone is insufficient. State what collision sources the control excludes
   and how total force versus exact-pair contact will be interpreted.
3. Document/version the revised protocol before inspecting its outcomes. Keep the
   engineering threshold, transduction choices and neural parameters fixed. Any
   change of support, constraint or calibration context must be explicit and
   applied consistently where matching requires it; do not disguise it as a test
   of the ordinary live body. Do not tune surface offsets until it passes.
4. Implement a focused, separately versioned runner or reusable adapter and tests;
   preserve the locked legacy source and old evidence. Require exact identities,
   intact matched poses/schedules, clean negative evidence and verified positive
   contact. Record failed and inconclusive outcomes without automatic retries.
5. Open a PR from latest `newBrain` with concrete Git Bash commands. Run relevant
   local tests and, if the validated local physics environment is available, the
   approved bounded experiment. Report exactly which checks/experiments ran.

Do **not** enable tactile input yet. After an accepted calibration, the next
separate step is a matched tactile-delivery-enabled versus withheld experiment,
reusing the existing encoder with independent/common candidate sampling and
verified input/readout boundaries. Subsequent physical divergence in closed loop
can be an outcome; require matching before the intervention. Neither calibration
nor new motor activity by itself establishes balancing or gait.

## Local environment, tests and handoff usage

User's Git Bash checkout: `~/Documents/FlyBrainUnity`. Bare `python` has worked
for their recent runs. An older validated environment may be at
`fly-brain-interactive/.venv/Scripts/python.exe`; inspect rather than assume.
Node is needed for JS reference checks. Live physics needs FlyGym/MuJoCo; do not
silently install/upgrade physics dependencies or treat mocks as physics results.
The prior remote environment lacked FlyGym; local Codex should verify what is
actually available. Full CNS loading can take minutes; use physics-only tests
for the current calibration question. Unity is not required for these CLI runs.

Useful quick checks from repository root:

```bash
python -m pytest -q tests/test_six_foot_contact_calibration.py tests/test_tactile_targeted_contact_calibration.py
python -m pytest -q tests/test_live_contact_readiness.py tests/test_live_cli.py tests/test_live_headless.py tests/test_live_motor_diagnostics.py tests/test_live_pose_transport.py
python -m pytest -q tests/test_calibrated_neural_parity.py tests/test_neural_runtime.py
node --test tests/js/neuromod_scope_audit.test.mjs
```

Latest calibration implementation validation: 57 tests + 9 subtests passed across
the batch, old targeted calibration (including artifact locks), contact survey,
CLI/headless/motor/transport. Earlier broader neural-audit testing encountered
three missing-FlyGym failures and one differing historical-artifact comparison;
these reproduced with original code. Reassess locally rather than assuming
these remain the only failures or updating artifacts to pass tests.

Before edits, fetch, protect unrelated local changes and start a new branch from
`origin/newBrain`. Follow root agent instructions. Keep this checkpoint current
when a substantive new result changes the next decision.
