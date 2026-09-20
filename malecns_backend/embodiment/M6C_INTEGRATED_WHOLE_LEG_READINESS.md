# M6C — integrated whole-leg embodiment / locomotion readiness

## Scope and scientific claim

M6C is a preregistered integration test, **not a walking experiment**. It asks
whether the already validated motor interfaces can coexist in one MaleCNS →
decoder → FlyGym/NMF → sensory-feedback simulation without routing errors,
unauthorized actuation, instability, or hidden coordination logic. M7, after
human review, will ask the separate spontaneous-locomotion question.

No tripod pattern, gait generator, phase relationship, reference trajectory,
stance/swing state, target velocity/heading, reward, optimizer, RL/AI policy,
balance/posture controller, scripted stimulation, or seed search is introduced.

## Locked scientific inputs

Canonical execution fails closed unless raw-byte SHA256 and semantic checks
pass for:

1. the completed M6A 42-actuator whole-leg mapping audit;
2. a completed canonical M6B artifact classified
   `ISOLATED_TIER_B_VALIDATION_COMPLETE_WITH_PARTIAL_CAUSALITY`; and
3. the existing six-tibia causal artifact (`S7`, seed 1, 500 ms).

The repository currently contains the M6B **NOT_RUN preregistration**, not the
completed canonical artifact described in the handoff. Consequently M6C
correctly refuses preflight/science until the completed artifact is installed
and its reviewed SHA256 is passed explicitly. This is not repaired by inventing
or reconstructing scientific observations.

## Motor and sensory admission

The six validated Tier-A channels are:

| actuator | action index | coordinate semantics |
|---|---:|---|
| `joint_LFTibia` | 5 | +1, validated existing decoder |
| `joint_LMTibia` | 12 | +1, validated existing decoder |
| `joint_LHTibia` | 19 | +1, validated existing decoder |
| `joint_RFTibia` | 26 | +1, validated existing decoder |
| `joint_RMTibia` | 33 | +1, validated existing decoder |
| `joint_RHTibia` | 40 | +1, validated existing decoder |

M6C derives (rather than independently asserts) M6B eligibility from completed
per-joint results, then requires the derived set to equal:

| actuator | action index | coordinate sign |
|---|---:|---:|
| `joint_LFFemur` | 3 | -1 |
| `joint_LMFemur` | 10 | -1 |
| `joint_LHFemur` | 17 | -1 |
| `joint_RMFemur` | 31 | -1 |
| `joint_RHFemur` | 38 | -1 |

Thus exactly 11 motor channels are admitted. Every other one of the 42
physical actions remains at its ordinary baseline command with exactly zero
neural contribution. In particular, `joint_LFTarsus1`, `joint_RFFemur`, and
`joint_RFTarsus1` are withheld because the canonical M6B handoff classifies
them `NO_MAPPED_MOTOR_ACTIVITY`; this is silence, not an anatomical or
mechanical failure. All six `Coxa_yaw` candidates are withheld because their
physical coordinate sign is unresolved. Remaining Tier-C/D channels are
unsupported and withheld under M6A policy.

Only the six annotation-backed, previously validated tibia proprioceptive
interfaces enter the sensory loop. Motor knowledge does not imply sensory
knowledge: no femur angle sensor is synthesized, ambiguous Coxa candidates are
not used, and tactile/contact candidates are not relabeled as proprioceptors.

## Three matched conditions

Seed 1 and 500 ms are frozen, with no sweep or outcome-dependent rerun:

1. `INTEGRATED_NEURAL_MOTOR_ENABLED`: all 11 contributions admitted.
2. `ALL_NEURAL_MOTOR_DISABLED`: all 11 contributions zeroed immediately before
   physical application.
3. `TIER_B_FEMUR_DISABLED`: six tibiae admitted and five femora zeroed at the
   same boundary.

Each condition receives a fresh brain, sensory system, decoder/observer state,
RNG state, baseline action, and physics runtime. Condition C is an interface
control, not a gait ablation.

## Admission, equivalence, telemetry, and performance

The physical inventory is read once from the compiled live model and cached.
Before every application a cheap assertion checks the fixed 42-vector against
immutable admission metadata. Runtime creation is O(conditions): one inventory
environment during preflight plus three fresh canonical condition runtimes,
never O(physics steps).

Pre-intervention equivalence includes qpos, qvel, action, ctrl, sensory encoder,
MaleCNS, spike counts, observers, decoders, RNG, baseline action, and actuator
metadata. Same-update command divergence is valid; no strict-before timing
requirement is imposed.

The live contract records per-channel spike/observer/decoder/admission/action,
clipping, slew, and first-event telemetry; all 42 joint positions and relevant
velocities; body pose and velocities; available contact state; validated
sensory encoding/delivery; CNS digest/count; and finite-state/stability data.
Timing is separated into initialization, neural, MuJoCo, sensory,
observer/decoder, telemetry/hash, admission assertion, and reduction phases.
Progress printing has no access to simulation RNG.

## Milestones and classifications

`C0` through `C9` implement equivalence, activity, decoder output, admission,
command/physical divergence, multi-channel, multi-leg, authorization, and
stability checks. `C10` through `C12` record (but do not force) validated sensory
divergence, subsequent CNS divergence, and subsequent motor return.

The reducer supports conservative causality, multi-channel, multi-leg,
sensorimotor-feedback, and motor-return classifications plus provenance,
interface, equivalence, authorization, inactivity, no-causality, and physics
failure outcomes. It defines no walking/gait classification.

M7 readiness requires provenance, exactly 11 admissions, C0–C5/C8/C9, valid
sensory provenance, no runtime failure, and
`hidden_locomotion_assistance_executed: false`. Readiness means only that the
spontaneous-locomotion experiment may be attempted; it predicts no movement.

## Commands (PowerShell, repository root)

Non-scientific Windows preflight, after installing the reviewed completed M6B
artifact and replacing `<REVIEWED_M6B_SHA256>`:

```powershell
.\fly-brain-interactive\.venv\Scripts\python.exe -m malecns_backend.embodiment.integrated_whole_leg_readiness --m6b-sha256 <REVIEWED_M6B_SHA256> --preflight-windows
```

The terminal success line is `M6C WINDOWS PREFLIGHT PASS`. Preflight may inspect
and construct runtimes but never invokes a scientific condition.

**DO NOT RUN UNTIL HUMAN REVIEW — future canonical scientific command:**

```powershell
.\fly-brain-interactive\.venv\Scripts\python.exe -m malecns_backend.embodiment.integrated_whole_leg_readiness --m6b-sha256 <REVIEWED_M6B_SHA256> --run-windows
```

Ctrl+C closes within the live condition boundary and atomically records an
incomplete, non-resumable attempt without producing a canonical classification.
