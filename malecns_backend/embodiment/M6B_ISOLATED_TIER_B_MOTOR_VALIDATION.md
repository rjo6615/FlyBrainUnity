# M6B — Isolated Tier-B Whole-Leg Motor Validation

## Status and scientific scope

The committed `M6B.0` artifact is a **NOT_RUN preregistration**. No scientific
simulation was executed while implementing M6B. This milestone can validate
only modeled isolated motor-interface causality between an annotation-backed
mapped motor population and one physical actuator. It cannot validate
biological motor function.

The first Windows invocation terminated during interface setup because
`_windows_isolated_tier_b_motor_validation_adapter` did not exist.  It ran no
simulation, is recorded as `INTERFACE_SETUP_FAILURE`, and **does not consume
Scientific Run #1**.  The committed canonical artifact remains the original
`NOT_RUN` preregistration; engineering preflight output is kept separately.

## Canonical adapter and reused live path

The Windows adapter is intentionally an integration layer.  It reuses:

* `load_malecns` and `MaleCNSBrain` for connectome loading and neural runtime;
* `full_leg_interface.enumerate_live_actuators` for compiled action,
  actuator, joint, qpos, and qvel associations;
* `tactile_motor_loop_audit._make_live`, `_joint_positions`, `_forces`, and
  `_state_tuple` for the validated M5D-4 environment/state path;
* `validated_interfaces`, `SensoryEncoder`, `proprio_rngs`,
  `sample_candidates`, and `TactileContactEncoder` for the M5D-5B sensory and
  RNG path;
* `MotorActivityObserver` for the locked 40-ms motor observation; and
* `tactile_motor_matched_control.MatchedControlPipeline` for the corrected
  M5D-4C baseline, gate, clamp, slew, and command path.

The adapter's public contract is `run_preflight(protocol, output_path)` and
`run_canonical(protocol, output_path)`, plus independently testable joint
metadata, physical-sign calibration, decoding, and admission guards.

## Immutable M6A input

`interface_output/whole_leg_motor_mapping_audit.json` is locked as raw bytes
(SHA-256 `722ee9b3b1d6a0fad2bf8ef0f02fc63f49277c5f44e3bccf27898e6c4ea673d9`).
The loader also requires schema `M6A.0`, `COMPLETE`,
`WHOLE_LEG_MOTOR_AUDIT_COMPLETE`, exact tier counts A/B/C/D = 6/14/18/4, the
exact ordered eligible list, and a passing six-tibia regression. Any mismatch
fails closed before simulation and does not consume Scientific Run #1.

## Frozen protocol

* Canonical seed: **1**; no seed sweep.
* Duration: **500 ms per condition per joint**, frozen before the first run.
* Every actuator and condition receives a fresh simulation.
* Exactly one selected Tier-B contribution can be admitted. Tier A and all
  other Tier-B neural contributions remain zero.
* Both `ENABLED` and `MOTOR_OUTPUT_DISABLED` calculate identical neural
  activity, 40 ms observer state, bounded activation (17 Hz half-activation),
  signed raw decoder output, baseline, range clamp, and 4 rad/s slew path. The
  sole condition-dependent value is admitted contribution: raw versus zero.
* Contribution magnitude is at most 0.25 rad and is reduced to the symmetric
  range available about the baseline from live MuJoCo joint limits.

## Sign calibration

M6A's `+1/-1` describes annotation-backed anatomical opposition; it is not
silently treated as NMF coordinate sign. All 14 interfaces therefore begin as
`PHYSICAL_SIGN_CALIBRATION_REQUIRED`. Before neural admission, the Windows
adapter must inspect MuJoCo joint-axis metadata and apply deterministic
positive/negative kinematic epsilon perturbations, using endpoint geometry—not
neural behavior—to associate anatomical and NMF directions. An indefensible
association is `SIGN_UNRESOLVED`, and that interface is not admitted.

## Isolation, equivalence, and milestones

Before the first nonzero admitted contribution, enabled and disabled traces
must be exactly equal for qpos, qvel, action, ctrl, selected-joint state,
observer state, decoder state, sensory state, and available RNG state/counters.
A mismatch is terminal and scientifically uninterpretable. Per-joint telemetry
records B0 through B5, allowing `<=` (same-update) ordering, full-body
physical divergence, selected-joint maximum/RMS differences, directional
spikes, observer/raw/admitted maxima, limit encounters, and instability.

Scientific Run #1 for each joint is immutable. Results are never overwritten
or repeated to improve an outcome. A setup/provenance failure before physics
starts does not consume Run #1. Synthetic count tests, if used, are separately
labeled `SYNTHETIC_INTERFACE_DIAGNOSTIC_ONLY` and are not scientific evidence.

## Canonical Windows invocation

From the repository root in PowerShell, after installing the project's
validated MaleCNS/FlyGym/MuJoCo environment and Windows adapter:

Run the non-scientific engineering preflight first:

```powershell
.\fly-brain-interactive\.venv\Scripts\python.exe -m malecns_backend.embodiment.isolated_tier_b_motor_validation --preflight-windows
```

Only after it prints `M6B WINDOWS PREFLIGHT PASS`, invoke Scientific Run #1:

```powershell
.\fly-brain-interactive\.venv\Scripts\python.exe -m malecns_backend.embodiment.isolated_tier_b_motor_validation --run-windows
```

The adapter must preserve each first-run artifact and populate per-joint and
aggregate results without changing this frozen protocol.
