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

### M6A byte-provenance diagnostic (M6B-P1)

Preflight Attempt #1 ended with `M6B WINDOWS PREFLIGHT FAIL: M6A raw-byte
provenance mismatch`. This was an engineering/preflight failure: no scientific
simulation ran, and Scientific Run #1 remains unconsumed (`NOT_RUN`).

The investigation classified the event as
`REPRESENTATION_ONLY_PROVENANCE_MISMATCH`. The source commit and current LF
checkout are 431,453 bytes with 14,486 LF bytes, no CRLF sequences, no UTF-8
BOM, a terminal newline, and SHA-256
`722ee9b3b1d6a0fad2bf8ef0f02fc63f49277c5f44e3bccf27898e6c4ea673d9`.
Expanding only those line endings produces the 445,939-byte Windows CRLF
representation (14,486 CRLF sequences), SHA-256
`07e5395689bd2c9c055aa384d0c8536dede7311b7400bf1767dae0772d442c98`.
Both parse to identical JSON, including every required M6A constraint. There
was no BOM or terminal-newline difference.

The repository previously had no path-specific `.gitattributes` policy, so
`core.autocrlf` could change this raw-byte-locked artifact during Windows
checkout. The path is now declared `-text`, matching the project’s established
raw-byte artifact policy. Git therefore disables line-ending conversion and
materializes the indexed LF bytes unchanged on every platform. M6B deliberately retains the stronger raw-byte hash (rather than accepting arbitrary platform hashes or relying on
semantic checks), so any content-byte change still fails provenance. The
machine-readable non-scientific investigation is recorded in
`interface_output/m6b_m6a_provenance_diagnostic.json`.


### Limit-domain diagnostic (M6B-P2)

Preflight Attempt #2 ended with `joint and actuator limits have no valid
intersection`. It too was an engineering/preflight failure: no 500-ms
condition ran, Scientific Run #1 remains unconsumed, and the canonical M6B
artifact remains `NOT_RUN`.

The failing implementation unconditionally intersected `model.jnt_range` and
`model.actuator_ctrlrange`. MuJoCo makes each raw pair applicable only when its
corresponding `jnt_limited` or `actuator_ctrllimited` flag is true. An inactive
`[0, 0]` slot is metadata storage, not a zero-width allowable range. M6B-P2 now
records both flags and both raw ranges for all fourteen interfaces before sign
calibration and uses only active, same-domain bounds. A genuine empty
intersection of two active same-domain ranges still fails closed.

The live stack uses `Fly(control="position")`, but the diagnostic also verifies
the compiled position-servo gain/bias signature, scalar joint transmission,
and unit gear. Only then does `ctrlrange` represent the same absolute
joint-position target (rad) as a hinge `jnt_range`. A torque, velocity, muscle,
general, non-joint, or non-unit-gear control range is classified
`VALID_BUT_DIFFERENT_DOMAINS` and is not intersected with joint angle.

M5D-4C computes an absolute target (`current measured position + admitted
neural offset`), applies its target clamp, then the unchanged 4 rad/s slew and
final target clamp. M5 did not perform M6B's unconditional raw-range
intersection. P2 intersects only active bounds verified as absolute position
targets, derives symmetric offset headroom about the current target, and caps
the contribution at 0.25 rad.

The next Windows preflight writes
`interface_output/m6b_live_limit_diagnostic.json` (`M6B-P2.0`), including all
live IDs/names, addresses, axes, flags and raw ranges, transmission/gear/servo
parameters, current qpos/ctrl/action, domain labels, safe bound, first legacy
failure, and all legacy failures. Earlier locked live evidence contains:

| Tier-B interface | position range (rad) | prior live ctrlrange |
|---|---:|---:|
| joint_LFCoxa_yaw / joint_RFCoxa_yaw | [-0.8, 0.8] | [-1000000, 1000000] |
| joint_LFFemur / joint_RFFemur | [-0.15, 2.0] | [-1000000, 1000000] |
| joint_LFTarsus1 / joint_RFTarsus1 | [-0.7, 1.2] | [-1000000, 1000000] |
| joint_LMCoxa_yaw / joint_RMCoxa_yaw | [-0.75, 0.8] | [-1000000, 1000000] |
| joint_LMFemur / joint_RMFemur | [-0.15, 2.0] | [-1000000, 1000000] |
| joint_LHCoxa_yaw / joint_RHCoxa_yaw | [-0.15, 0.8] | [-1000000, 1000000] |
| joint_LHFemur / joint_RHFemur | [-0.7, 1.5] | [-1000000, 1000000] |

Those previously recorded pairs overlap and cannot themselves reproduce
Attempt #2. The exact first/affected actuator and current raw Windows values
must come from the P2 live artifact, not inference from symmetry. If it finds
two active same-domain non-overlapping ranges, classification remains
`SAME_DOMAIN_LIMIT_CONFLICT`; if no applicable target bound exists, preflight
also remains failed closed.

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
