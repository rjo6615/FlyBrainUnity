# Assistance native adapter V1 — engineering component

2026-10-26. Implements the mechanical part of the frozen
[assistance design](ASSISTANCE_CONTRIBUTION_V1.md). That prospective document and
its protocol stay unchanged. No native qualification/campaign has run in this
update. No biological or balance result follows from synthetic fixture tests.

## Implemented boundary

`assistance_native.py` reuses lf_native_isolation inventory/validation,
physics_model_identity, typed array identities and lf_pose_force moment
reconstruction. Logical20/22selection comes from the original raw-locked motor
authority. Native actuator/joint/body IDs and scalar addresses are validated;
action index never substitutes for a native ID. Force-limit/gravity-compensation,
plugin/mocap and position semantics are checked without changing them. Adhesion
can structurally support selected DOFs, but its control AND force must be zero.
Global control/passive/actuation callbacks are rejected before shadow work.

The component records complete typed numeric model arrays (including zero-sized
shapes and lossless native nonfinite metadata), dimensions, normalized compiled
inventories and option identities. Wrapper/native-pointer paths share one model
identity. MR is independently derived by zeroing exactly22full gain/bias rows.
Every sampled model identity is checked against M0/MR; retained20parameters and
all other recorded model fields remain exact. Model identity excludes changing
body state; the separate MjData digest includes exposed numeric arrays/scalars,
including warm starts. Native opaque/internal memory is outside that digest.

One shadow MjData on the first actual A_NC initialized model performs the fixed
2x2control/velocity probes, each B/R/restoredB. Explicit API budget:1shadow
allocation,12shadow resets,12shadow forwards. No integration/CNS API, live reset/
forward or second model is called by this code. Constructor observed Python/C API
entries are reported separately; invisible native internals are not counted.
Probe inputs outside original control ranges fail without clipping/search.
Gain/bias rows restore in finally even on failure; unrelated contamination is
reported and left visible, not silently repaired. All partial cases/counters and
errors are retained in the caller-owned qualification record. A nonempty record
cannot be retried. No selected force exposure means qualification fails.

Offline qualification reconstruction enforces all12cases, phase identities,
fixed inputs, exact restoration/passive/moment equality, retained-force and
outside-target delta<=1e-10, selected force/generalized-force<=1e-10, projection
error<=1e-8 and each selected original force exposure>1e-8. Those bounds are
inherited from the declared protocol; no outcome-dependent changes.

`assistance_trial.Trial` subclasses the frozen original balance Trial. Original
encoders, neural gate before safety,392-slot RNG, decoder/observer, pulse and
scientific integration kernel remain in place. It captures mechanical evidence
alongside the original raw sample, then calls the original state_boundary first.
Qualification happens only at initialized state0 of the first A_NC. Later arms
must supply its fully re-evaluated qualification and exactly match qualified M0.
No direct force/control/body-state write is introduced by the mechanical event.

After recording state5005, R changes only selected gain/bias rows; A journals
without writes. State5005remains M0; sample5006onward must reflect MR for R. Full
data and brain/session/RNG/encoder/decoder/safety digests must match around the
event and qualification. Selected force suppression begins at sample5006,
including terminal20000. The mechanical trace auditor checks all20001states,
clocks, sparse moments/force projection and adhesion/selected force conditions.
It does NOT classify behavioral success or implement full scientific acceptance.

The internal run_arm wrapper uses the existing driver's explicit Trial factory
injection and preserves partial mechanical/qualification data on driver failure.
It never replaces module-global factories. Its result has a new schema and
full_scientific_audit_completed=false. Frozen constant-model auditors still reject
R changes; no sources/hashes/old reports are rewritten to make them accept R.

## Remaining gates before native use

This component deliberately has no --live/--execute option or campaign launcher.
Its --check entry point verifies source/design identity only. The internal Python
API is not an authorized/complete scientific execution entry point. Next integrate:

1. A separately versioned full eight-arm evaluator: reuse original command/RNG/
   contact/behavior math under explicitly piecewise model context; exact prefixes,
   all eight comparisons, no-push posture-loss qualifier, factorial contrasts.
2. Fresh OS controller/workers with complete original balance_source_prerequisites
   before/after controller and each worker, committed source checks, exact arm
   order, exclusive durable artifacts, qualification transfer, no retry/resume.
3. Preserve failed/incomplete qualification and untouched/unstarted later arms;
   retain live provisional display accounting and allow saved review only after
   full integrity. Exercise stop/cleanup/partial-write paths before execution.
4. Commit the complete implementation before ONE bounded qualification/campaign.
   No extra native initialization or probe campaign. Measure actual runtime and
   storage costs; full model hashing is intentionally stricter than old config
   hashing and has not been performance-qualified on the native moving model.

All20retained position actuators still assist posture. Motor coverage20/42,
zero admissions; independent balance/gait remain unproven. No parameter, source
lock, dependency, original acceptance or historical result change.
