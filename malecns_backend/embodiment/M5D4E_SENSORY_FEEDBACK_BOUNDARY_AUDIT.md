# M5D-4E — Sensory feedback boundary audit

## Status

The checked-in artifact is **NOT_RUN**.  FlyGym/MuJoCo is unavailable in the
authoring environment, so this milestone makes no new empirical claim and does
not fabricate per-channel timings.  Run the command below on the validated
Windows environment to populate those fields.

The audit invokes the exact locked M5D-4D `run_live` function and replaces only
its post-run trace reducer.  Thus the condition runner, M5D-4C matched-control
pipeline, seed, clocks, physics, encoder, CNS, decoder, actuator mapping, and
contact setup are unchanged.  There are no retries, sweeps, or parameter
mutations.

## Provenance and inventory

M5D-4E fail-closes on the raw-byte SHA-256 of the authoritative M5D-4D JSON,
canonical-LF SHA-256 hashes of both M5D-4D implementation files, the locked
classification, the validated prefix, and all earlier provenance locks.

Programmatic inspection finds exactly one active modeled sensory channel in
M5D-4D: **LM Tarsus5 tactile**.  It consumes contact-force row 11, applies the
locked `norm(force) > 1e-12` contact decision and 120-Hz/20-ms onset transient,
samples candidates from the isolated LM tactile RNG stream each 0.1 ms, and
delivers accumulated candidates to `MaleCNSBrain.set_external_drive` each
0.5 ms.

Six exact tibia sensory mappings exist (LF, LM, LH, RF, RM, RH), but M5D-4D
constructs only their *motor* observers and decoders.  It never constructs or
applies `SensoryEncoder`; therefore none of the six is an active external-drive
channel.  M5D-4E nevertheless reconstructs their angle/rate sensitivity as
explicitly inactive observational telemetry and never counts that reconstruction
as candidate spikes, delivered spikes, CNS feedback, or a telemetry blind spot.

## Questions resolved by the implementation

* The global force difference at row 24 is reported separately from the active
  tactile source at row 11; the former can never automatically establish the
  latter.
* The RMTibia/RMTarsus5 semantic-contact difference is tested for relevance to
  LM Tarsus5 rather than treated as sensory feedback.
* Physical, sampled, rate, candidate, delivered, downstream-CNS, and subsequent
  mapped-motor timings remain `null` until directly observed.
* Contact status, release, rearm/re-contact, transient state, force magnitude,
  and common RNG parity are compared from the complete paired traces.
* A sensory claim fails closed if RNG states desynchronize.

## Live command (Windows, repository root)

```powershell
py -m malecns_backend.embodiment.sensory_feedback_boundary_audit --live --duration-ms 100 --seed 1 --json malecns_backend\embodiment\interface_output\sensory_feedback_boundary_100ms.json
```

Interpret the generated classification only when `run_status` is `COMPLETE`,
provenance is verified, and prefix reproduction passes.  This diagnostic is
limited to the modeled embodiment and must not be described as a natural
biological reflex.
