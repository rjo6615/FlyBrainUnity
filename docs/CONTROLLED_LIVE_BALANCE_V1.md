# Controlled live balance observation V1

2026-10-26. Status: DESIGN_ONLY_NOT_IMPLEMENTED_NOT_RUN. This separately versioned
protocol specifies one bounded new four-arm experiment after implementation,
engineering validation and committed sources. It does not launch or report one.
Machine-readable declaration: evidence/controlled-live-balance-v1/protocol.json.

## Purpose and known evidence

Can the existing assisted20motor contribution assay be observed in Unity while
it is computed, without changing scientific transitions, intervention or evidence?
The neural question remains the effect of continuing versus withdrawing decoder
input during a fixed push under unchanged position assistance. No hypothesis of
improved behavior is introduced by attaching a viewer.

The accepted V1.1 recording is known in advance:80,000physics transitions,
16,000neural updates,80,004states, INTEGRITY_ACCEPTED and MIXED_OR_UNRESOLVED.
Enabled input reduced mean pushed tilt but not peak tilt by the declared
resolution; relative recovery measures did not consistently favor it. A new live
observation is an engineering extension, not an independent replication claim or
an opportunity to tune that outcome. Preserve accepted V1.1 and failed V1 intact.

All numerical scientific rules in BALANCE_CONTRIBUTION_V1.md and process freshness
rules in BALANCE_CONTRIBUTION_PROCESS_V1_1.md are inherited. Reference hashes are
recorded separately; no historical source/specification/result/hash is refreshed.
The existing completed execution is sufficient for saved replay and need not be
rerun to fix a camera or study that recording.

## Fixed scientific conditions

|Order|Arm|Decoder input from tick1001|Thorax push|
|---|---|---|---|
|1|NC|normal|none|
|2|WC|zero BEFORE unchanged safety|none|
|3|NP|normal|fixed inherited pulse|
|4|WP|zero BEFORE unchanged safety|fixed inherited pulse|

Fresh child process/model/CNS/encoder/safety/RNG per arm; seed1;2seconds each;
dt0.0001seconds;20,000transitions/20,001states/4,000neural updates per arm.
Total80,000/80,004/16,000. No automatic retries, resume, control reuse, fall-based
early stop, favorable subset, seed/force sweep or duration extension.

All42position actuators keep existing gains, biases, ranges, damping, friction
and policy:20baseline-plus-neural targets,22fixed initial baseline targets.
392tibia proprioceptive neurons and the assay-only392-slot common CNS RNG;
unchanged per-leg candidate RNG; tactile delivery OFF. No new mappings or drive.
Withdrawal at tick1001/state5005/500.5ms; no final-target hard zero or safety reset.
Record natural slew return including the unchanged126-update/563.0ms bound.
Pulse world[0,1.024,0] at exact native Thorax COM, outgoing5000..5199;
zero torque, zero other applied forces, unchanged full contact/force audit.
All-arm prefix through5000/tick1000 and same-push applied-state prefix through5005;
first possible withdrawal physical effect5006. Retain unapplied terminal tick4000.

Reuse existing Trial/create_session, ScientificSession, transition kernel,
native inventory, encoders, observers, gating, safety, RNG and original auditors.
New code may own worker lifecycle and observation, not a competing physics/CNS
step loop or new actuator controller. Validate actual-model IDs/addresses and
action order before display; do not assume action index is qpos index. Do not
mutate module globals, physiology, FlyGym registries or frozen source files to
attach a display callback. Use an instance-local session wrapper and a dedicated
versioned controller/worker with explicit dependency injection where needed.

## Live observation boundary

Python/MuJoCo remains the scientific authority. Unity only receives poses using
the existing PoseServer and live_fly_pose v1 transport. Reuse the existing
coordinate conversion and64binding transform-only rig. No Unity physics,
balancing controller, gait script, feedback-to-neurons or interactive force input.
The camera's Frame Current Fly action changes presentation only.

Live means computed now, not guaranteed real-time speed. Do not add sleep,
simulation-time interpolation, extra steps or altered dt to meet display FPS.
The existing server emits at most30wall-Hz and may retain/drop only the newest
display packet; it never drops raw scientific samples. Client disconnects,
slow readers and client bytes must not control stepping, RNG, forces or targets.
Record wall time and simulation time separately. No client-connected prerequisite
or reconnect-triggered arm restart. Console output must show the current arm,
initialization versus stepping, simulated time and actual transition counts.

Each arm gets a fresh server/session identity and sequence starting at0. Socket
binding must succeed before native construction; failure preserves an error
receipt and starts no scientific arm. Subsequent transport failure is an
observation fault: record it, disable publication for that arm, continue the
fixed scientific schedule without automatic rebind/restart. A native/scientific
error still stops the campaign under the original failure policy. No other live
or replay server may use localhost8765 at the same time.

Unity's existing client reconnects between arms. Initial t=0 per arm is a new
initialization, not a physical jump or continuous four-arm trajectory. Console
labels/session IDs distinguish arms; do not alter the frozen wire schema merely
to add scientific controls. Do not promise that Unity displays every tick or
that the terminal pose reaches a client. Journal exact offered packet fields,
simulation state indices, sequence/session identity, local publication results,
sent/replaced counts and transport faults outside the scientific raw traces.
Publication is not proof of client receipt or visual correctness. Preserve any
received/visually observed counts as separate evidence.

All live output is labelled LIVE_PROVISIONAL_NOT_YET_AUDITED before the first
pose. A partial or later rejected arm may have been seen during acquisition;
it never becomes an accepted balance demonstration. At the end, prominently
print scientific integrity, separate display integrity and behavioral status.
Accepted saved replay still requires complete offline gates; do not weaken the
existing balance_contribution_replay gate to expose live partial data.

## Integrity and behavior

Run unchanged per-arm scientific auditors and full original cross-arm prefix,
source/model/data, initialization/process, RNG, command/slew/exposure, force,
contact, finite, clock and complete-coverage checks. The new versioned report
must bind its own committed controller/worker/observer/specification as well as
the untouched scientific sources and data. Test adapter equivalence with the
original evaluator; do not fabricate a V1.1 report/source identity for new code.

Display audit requires every offered packet to match its actual recorded state
and exact native-address mapping, monotonic within-arm identity/sequence/clock,
no unrecorded step and no input path. It also reports delivery faults/coverage;
zero clients or missing packets means VISUAL_REVIEW_UNCONFIRMED, not scientific
failure or a completed Unity test. Physical/native or pose-identity corruption
fails the applicable gate. Keep scientific INTEGRITY_ACCEPTED/INCONCLUSIVE_INTEGRITY
separate from display VERIFIED/FAILED/UNCONFIRMED. A broken display does not
erase a scientifically valid arm; scientific acceptance cannot certify display.

As a read-only engineering diagnostic, compare corresponding original V1.1
model/data/initial context and full physics/neural records, excluding documented
OS/PID/wall-time/publication metadata. First report environment/source differences;
never silently strip numeric fields, normalize scientific names or add tolerances
to create parity. Record exact matches or first mismatch. Cross-record mismatch
does not retroactively invalidate old data or justify rerunning either campaign.
It leaves cross-execution transparency unresolved; within-new-campaign original
integrity rules remain mandatory. This is one new four-arm attempt, not two
display-on/display-off campaigns.

Behavior uses the SAME full0..2000ms traces, baseline4000..5000, cleared window
5201..20000, inherited recovery bands/dwell and0.25degree/0.005mm resolution.
Preserve null, mixed, amplification, baseline loss, unqualified and unrecovered
outcomes. Keep world tilt and own-control-relative response separate, with all
height/velocity/support tradeoffs and nonlinear factorial limitations.
No behavior label is a live-display eligibility requirement. No inference of
independent balance, gait, biological calibration or42motor admission follows.

## Stop, budget and execution gates

User stop requests are checked before initialization and before each next
scientific transition. Preserve all partial raw records and reasons; no resume
or automatic retry. Native initialization may need to return before a graceful
stop can be saved; hard termination can leave only incomplete logs. A fall alone
does not stop or shorten the predeclared window. No outcome-directed intervention.

Before ONE native attempt: implement the dedicated lifecycle/observation/report
adapter; test with synthetic sessions and real OS workers/sockets, including
disconnection/slow readers/input bytes, socket faults, stop, source corruption,
exact counters, native-address permutations, endpoint semantics, no-client runs
and original-auditor equivalence. None of those tests is a new scientific run.
Verify pinned environment/original static and neural-data prerequisites using
construction-free readers; measure each arm's sole actual initialization without
a duplicate native/CNS preflight campaign. Commit implementation/tests/spec first.

Human full-body review of the existing accepted recording remains unconfirmed
here. Do that before the live attempt and retain the observation honestly; this
protocol design does not imply it happened. Use an exclusive new evidence folder
under evidence/controlled-live-balance-v1/; never overwrite older records. Failure
requires a documented separately versioned correction/question, not a retry
chosen for favorable behavior. This design has no execution command yet.

## Distance to the milestone

Recorded assay and replay connection:done. Full-body human review:pending.
Controlled-live design:this document. Live adapter/tests, original prerequisites,
committed implementation, one bounded observed execution and offline audit:next.
Motor coverage20/42;0new admissions. Independent neural balance remains a later
question requiring explicit, prospectively justified assistance comparisons.
