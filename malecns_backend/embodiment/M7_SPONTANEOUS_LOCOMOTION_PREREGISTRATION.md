# M7 — spontaneous locomotion observation (preregistered; NOT RUN)

## Scientific question and status

What does the currently validated MaleCNS embodied system do when placed in
the FlyGym physical environment without being instructed to produce a gait or
target movement? M7 is observational. This document and the `M7.0` NOT_RUN
artifact freeze the experiment before execution. They do not authorize a seed
sweep, pilot run, duration extension, or tuning after observing the result.

## Frozen embodiment and meaning of spontaneous

M7 inherits M6C without biological expansion. Tier A comprises
`joint_LFTibia`, `joint_LMTibia`, `joint_LHTibia`, `joint_RFTibia`,
`joint_RMTibia`, and `joint_RHTibia`. Motor-only Tier B comprises
`joint_LFFemur`, `joint_LMFemur`, `joint_LHFemur`, `joint_RMFemur`, and
`joint_RHFemur`. The only admitted sensory interfaces are the six Tier-A
tibial proprioceptive streams. The other 31 physical actuators receive their
ordinary baseline action and exactly zero neural contribution.

“Spontaneous” means the frozen M6C initialization, deterministic MaleCNS
background dynamics, and admitted sensory feedback are allowed to evolve, but
no targeted stimulation, added noise, tonic drive, descending locomotor
command, gait/stance/balance controller, adhesion schedule, target, reference,
reward, optimizer, RL/AI policy, or parameter search is introduced. M6C's live
path does deliver sensory candidate drive derived from tibial encoding and its
pre-existing contact encoder; that existing initialization/path is frozen, not
claimed to be fully biological sensory transduction, and must be reported.
Contact may be recorded as physical telemetry but cannot become a new neural
input beyond the frozen M6C path. No Coxa, Coxa-yaw, femur proprioception,
tarsal motor control, visual, olfactory, or new tactile interface is admitted.

## Conditions and duration

Seed 1 is frozen for two fresh, identically initialized runtimes:

1. `SPONTANEOUS_NEURAL_EMBODIMENT`: all eleven frozen neural motor interfaces.
2. `ALL_NEURAL_MOTOR_DISABLED`: the same decoded state, with all eleven neural
   contributions gated to zero immediately before physical application.

The duration is **5,000 ms**, with physics dt 0.1 ms (50,000 transitions) and
neural dt 0.5 ms (10,000 updates). Five seconds is ten times M6C's causal
integration window and permits persistence, repetition, postural evolution,
or displacement to be measured while bounding two-condition storage/runtime.
It may not be extended because an outcome “almost” meets a category.

## Equivalence and fail-closed preflight

Before either condition steps, exact equality is required for qpos, qvel,
action, ctrl, sensory encoder state, MaleCNS state digest, spike counts,
observer state, decoder state, RNG, baseline action, and admitted-actuator
metadata. Both conditions use fresh runtimes. Provenance must bind the final
M6C evidence lock and the M6A/M6B/Tier-A raw hashes. Abort with no behavioral
classification on provenance failure, interface mismatch, equivalence failure,
pre-intervention physics instability, unauthorized contribution, a hidden
locomotion controller, telemetry corruption, or an incomplete condition.

## Outcomes and descriptive categories

Record body center-of-mass displacement; forward/lateral displacement in the
initial body frame; unwrapped yaw/orientation change; body height and velocity;
all joint positions/velocities; per-admitted-channel spikes, observer, raw
decoder and admitted contribution; six tibial encoder values and delivered
drive; CNS digest and aggregate spike count; available ground/contact state;
finite-state checks; and objectively defined fall/rollover (body height below a
frozen threshold or body-up vector crossing a frozen angular threshold).
Frozen control-relative numerical tolerances are 1e-6 rad for joints, 1e-6 m
for COM/height, and 1e-6 rad for orientation. Oscillation requires at least
three extrema with 1e-4 rad prominence. Rollover is body-up z <= 0; a fall is
height below 50% of initial height. These may not be fitted to M7 telemetry.

Categories are nonexclusive and control-relative:

* `NO_MEASURABLE_NEURAL_PHYSICAL_EFFECT`: no preregistered physical metric
  differs from control above its fixed numerical tolerance.
* `LOCALIZED_LIMB_MOVEMENT`: above-tolerance joint divergence in one leg.
* `MULTI_LEG_MOVEMENT`: above-tolerance joint divergence in at least two legs.
* `BODY_POSTURAL_CHANGE`: above-tolerance height, roll, pitch, or yaw divergence.
* `NET_BODY_DISPLACEMENT`: above-tolerance COM displacement relative to control.
* `REPEATED_OR_OSCILLATORY_LIMB_ACTIVITY`: at least three repeated extrema with
  a preregistered minimum prominence and autocorrelation-supported period.

There is no subjective `WALKING=true`. If existing contact telemetry is usable,
post-run analysis may describe stance/swing intervals, inter-leg phase,
periodicity/autocorrelation, stride-like repetition, displacement per cycle,
and directionality. It must not require or score tripod gait, compare with a
reference gait, drive the body, or optimize any outcome.

## Evidence, reduction, and replay

Write immutable compressed NPZ arrays plus a compact JSON manifest/summary.
The manifest records array names, shapes, dtypes, units, timestamps, provenance,
condition completion, and raw NPZ SHA256. Use atomic creation and refuse an
existing canonical path. A visualization is rendered only from recorded state
afterward; it must never call simulation stepping or modify state. The NPZ is
sufficient for quantitative reduction and deterministic trajectory inspection
without rerunning science.

The reducer is versioned and consumes only completed immutable recordings.
Every observed outcome—including no effect, twitching, falling, sliding,
rotation, backward displacement, cycling, or sustained displacement—is valid.
Any changed duration, seed, threshold, decoder, drive, interface, or controller
requires a new experiment ID and a new preregistration.

## Future Windows preflight (does not run M7)

```powershell
.\fly-brain-interactive\.venv\Scripts\python.exe -m malecns_backend.embodiment.m7_spontaneous_locomotion --preflight-windows
```

Expected terminal line: `M7 WINDOWS PREFLIGHT PASS — SCIENCE NOT RUN`.
