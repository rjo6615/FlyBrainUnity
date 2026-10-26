# Balance-contribution protocol V1 — existing20motor interface

Status: **SPECIFIED_NOT_IMPLEMENTED_NOT_RUN**. Selected by the user after distal
anatomical qualification. This update specifies an experiment; it contains no
new runner, execution result, Unity mode or new motor admission. The
machine-readable design is in `evidence/balance-contribution-v1/protocol.json`.
Implement/test the adapter in the next update before any scientific execution.

## Question and scope

From matched pre-push states, how does continuing versus withdrawing the current
20-channel neural decoder input change posture and recovery after the inherited
lateral thorax pulse, while position-control assistance is held to the same policy?

This extends the old11-motor M9B force experiment to the current20motor interface
and a post-onset withdrawal with a common prefix. It differs from old tactile
withdrawal and command-replay studies: only tibia proprioception is delivered,
and the intervention zeros newly decoded motor inputs rather than replaying an
undisturbed command trajectory. Existing null/unrecovered outcomes are retained.
Known prior outcomes do not predict success in this new context.

All42position actuators remain active with their existing gains/biases/ranges,
friction, damping and control policy. The22unadmitted coordinates keep fixed
initial baseline commands; the20admitted coordinates retain baseline plus the
existing safety-limited neural command. These servos can themselves support
posture. The experiment estimates a bounded neural command contribution under
this assistance; it cannot establish independent balance, muscle physiology,
walking or the fraction of balance supplied by the servos. A later mechanical-
assistance intervention would require a separate protocol, not a post-hoc rerun.

## Four fresh arms and fixed budget

| Order / ID | Decoder inputs through neural update1000 | From update1001 | Force |
|---|---|---|---|
|1 NC|normal20channels|normal|zero|
|2 WC|normal20channels|zero before safety|zero|
|3 NP|normal20channels|normal|fixed pulse|
|4 WP|normal20channels|zero before safety|fixed pulse|

N means continued neural decoder input, W withdrawal; P push, C own no-push
control. Every arm is a fresh model/brain/encoder/observer/safety/RNG instance.
Seed1, duration2s, physics dt0.0001s, neural dt0.5ms:20,000physical transitions,
20,001states and4,000neural updates per arm. Totals80,000transitions/80,004states/
16,000neural updates. Fixed order, no retries, parameter/force/seed sweep, trial
selection or early termination on a fall. Nonfinite/error/interruption preserves
partial raw data and a failed/inconclusive status; never relabel as complete.

All four arms are fresh because the proprioception-only392-slot RNG context
differs from archived tactile-enabled/2269-slot experiments. Do not reuse their
controls based on apparent similarity. No new channels, drive, thresholds,
weights, gains, signs or per-neuron parameters are introduced.

Use the existing validated environment (Python3.12, FlyGym1.2.1, MuJoCo3.2.7,
dm_control1.0.27, NumPy2.0.2). This design authorizes no dependency changes. All
original neural/mapping/raw-evidence prerequisites remain mandatory at execution;
the design's source fingerprint is not a waiver or a completed native preflight.

Before execution verify the existing neural calibration/raw-data authorities,
then record original loaded graph/neuron artifact identities, decoded body-ID
order/dense indices, CSR structure, weights/delays and complete ModelConfig.
Require the same verified data/configuration in all arms. A newly recorded hash
does not satisfy a failed older prerequisite or authorize a changed graph.

## Runtime and random-number conditioning

Reuse `ScientificSession` and `_windows_m8_live_condition` with existing v3 motor
authority, `proprioception_only=True`, `fixed_initial_baseline=True`, and existing
force/contribution/observer hooks. Six tibia encoders supply the existing392
neurons. Tactile delivery is off in all arms; contact sensing remains recorded.
Do not use the tactile-delivery Trial adapter, which changes the input context.

Configure the existing `MaleCNSBrain.configure_external_rng_schedule` once before
the first tick with the exact sorted union of392proprioceptive dense indices.
Every arm samples all392CNS external uniforms each tick, independent of candidate
availability/refractoriness. Reuse unchanged per-leg `proprio_rngs` and
`sample_candidates`; draw every offered per-neuron candidate uniform each tick.
This explicit assay-only common-random-number schedule is an engineering
conditioning change, not the ordinary live conditional-draw mode. Event equations,
rates, eligibility and delivery rules remain unchanged. No2269-slot adapter.

Require identical CNS uniform hashes/RNG states and matching per-leg candidate
draw-stream states at equal ticks throughout. Encoded rates, eligibility, offered
events and delivered input may diverge after physical feedback diverges; record
them rather than forcing them equal. Full neural state equality is required only
in the applicable matched prefix, not after intervention. No RNG resets mid-run.

## Withdrawal boundary and safety history

At post-neural tick1001 (time500.5ms, physical state5005), the W gate replaces all
20decoded contributions with exactly zero **before** `MatchedControlPipeline`.
Observers, decoder calculation, CNS and existing range/clamp/slew histories keep
advancing. Use the existing contribution gate; leave `final_contribution_gate`
unset. Do not reset safety history, hard-zero final targets, add a custom ramp or
change the4rad/s slew limit. No step or clock is added to perform the gate.

Slew-limited commands may retain an offset while returning to the fixed baseline.
The pipeline's `admitted_neural_contribution` is a pre-slew quantity; zero there
does not prove zero actual target offset. Record pre-gate decoder, post-gate input,
baseline, previous target, candidate/clamped/slew/final targets, actual42commands
and native ctrl. Replay the same existing pipeline offline to audit every update.
Record actual target minus baseline and the withdrawal transient without cutting
it out of the analysis. With inherited max offset<=0.25rad and4rad/s, baseline
return is bounded by126off updates (through time563.0ms, allowing float rounding).
That is a predeclared application check, not a new recovery window.

For exposure, record raw-gate differences, safe-command differences and the first
actual outgoing target difference. A one-step enabled counterfactual can be
reconstructed from the same recorded prior safety state without mutating it;
this is an exposure diagnostic, not an alternate full trajectory. Absence of
physical command exposure limits causal interpretation; never increase drive.

## Push, matching and endpoint semantics

Reuse `m9b_external_perturbation.force_at_transition`: world force[0,1.024,0],
zero torque, uniquely resolved Thorax COM, outgoing transitions5000..5199,200
transitions, impulse0.02048native-force seconds. Its origin is prior engineering
calibration, not biological scale or guaranteed effectiveness here. Start/reset
and other transitions have zero force. Audit every body's entire applied wrench
and generalized-force array; permit only the declared Thorax pulse.

Physics state i observes outgoing transition i-1. First forced state5001(500.1ms),
last5200, first cleared5201(520.1ms). Across all arms, complete neural/physical/
encoder/safety/source equality holds through state5000/tick1000. Within NC/WC and
NP/WP, physical/ctrl and pre-gate neural/safety states remain equal through state
5005; newly proposed gated commands may first differ there. Their first possible
physical effect is state5006(500.6ms). Do not require post-intervention trajectories,
torques or sensory inputs to stay equal; divergence can be the causal outcome.

Keep the terminal neural update4000/time2000ms, but mark its newly proposed
command as terminal/unapplied: there is no outgoing transition20000. Physical
exposure audits cover only transitions0..19999. Do not count a terminal proposal
as an applied intervention or drop it from raw evidence.

Verify identical compiled model/configuration/identities, free-root addresses,
contact/geometric ownership and effective actuator settings. Capture initialization
construction/reset/forward/settling operations separately from scientific steps;
zero clock is not proof of zero constructor work. Do not call the legacy live
inventory reviewer as a supposedly static prerequisite. Use existing static
authority readers and resolve native identities from each actual experimental
model, avoiding extra unrecorded model construction or duplicate CNS setup.
Current initialized model/brain states must be measured, never fabricated.

Reuse existing exact contact/force observers and approved surface context. Record
ground and calibration/support-surface contacts separately, zero adhesion and all
unexpected contacts. A contaminated ground context limits the ground-support
interpretation; no sample is deleted to make an arm pass. No support/collision
geometry, attachment, force multiplier or ordinary live default is changed.

## Measures, integrity and interpretation

Report full0..2000ms traces, force-on500..520ms, and complete cleared-force
520.1..2000ms window, including safety return. Use existing quaternion/up-vector,
world-velocity and recovery observers. Baseline qualification uses states4000..5000.
For NP versus NC and WP versus WC, reuse `tactile_recovery_metrics` without
changing its engineering bands: relative orientation<=5deg, height error<=0.05mm,
linear-speed error<=1mm/s, angular-speed error<=1rad/s, absolute up_z>0.5,
height>half initial and>=3exact-ground contacts;100ms dwell needs1001states.
Keep NO_BAND_EXIT, NOT_RECOVERED_IN_WINDOW and SUSTAINED_BAND_RETURN distinct.
Pulse-resolution floors remain0.25deg or0.005model-mm; no force increase on a null.

Primary posture descriptor: absolute pushed world-up tilt peak and mean in the
whole cleared-force window. Label LOWER/HIGHER_PUSHED_WORLD_TILT_WITH_NEURAL_INPUT
only if NP is lower/higher than WP by>0.25deg on both peak and mean; otherwise
MIXED_OR_UNRESOLVED. This is a descriptive label, not a global success criterion.
Report no-push posture separately and whether withdrawal destabilizes WC itself.

Also report disturbance-relative shortest-arc orientation, up-vector, root-height,
position, linear/angular velocity, exact-ground support losses, rollover/low-height
samples and recovery. Compare each pushed arm to its own control. Report the
full signed factorial root/up-vector contrast (NP-NC)-(WP-WC), reusing existing
vector conventions. Norm/angle/recovery contrasts are nonlinear descriptions,
not independent additive contributions or a statistical estimate from one seed.
Lower world tilt and larger departure from a leaning control can coexist.
No composite score may conceal worsening height, speed or support.

Integrity and behavior are separate. Failed provenance/identity/prefix/RNG/force/
application/clock/finite/full-coverage checks yield INCONCLUSIVE_INTEGRITY, retaining
the cause and raw data. A complete null, amplification, baseline loss or unrecovered
outcome can pass integrity. No motor exposure, below-resolution push, unqualified
baseline or no band exit limits functional interpretation. Never label independent
balance, gait, biological calibration or success of all42motor mappings.

Integer indices determine scheduling. Reuse the existing clock tolerances:
absolute physical time error<=1e-10s (`contact_context`), neural time error<=1e-8ms
(`matched_tactile_delivery`); do not use floating time to decide the gate. Native
force reconstruction retains contact-context rtol1e-10/atol1e-14. Exact identity,
prefix equality, RNG hashes, declared force arrays and command replay checks
are not replaced by these numeric tolerances.

## Implementation and Unity gates

Next update: implement an isolated adapter/recorder/evaluator, test synthetic timing,
raw gating versus slew, RMS/world-frame math,392-slot common RNG, exact20/22 isolation,
terminal exposure and failure preservation; audit real source/prerequisite identities.
Commit the implementation before a single bounded four-arm execution. This design
does not claim that native/runtime prerequisites have already passed.

During that eventual execution, each fresh arm records its own measured native/CNS
initialization and matched prefix; no duplicate expensive initialization campaign
is required solely to call something preflight. Preserve every arm and all partial
data in exclusive versioned namespaces. Output includes raw numeric pose/neural/
command/force traces, provenance, full integrity checks and separate behavior labels.

Unity replay is eligible after complete valid pose data and all declared integrity
gates, with the existing validated pose transport. A null/negative/recovery-failure
outcome is still replayable if integrity holds and is labeled honestly. Do not
require a favorable behavior before allowing visual review. Incomplete/invalid
evidence is not an accepted balance demonstration. Unity replay is observation of
saved physics, not a new neural simulation or new ordinary live controller.
