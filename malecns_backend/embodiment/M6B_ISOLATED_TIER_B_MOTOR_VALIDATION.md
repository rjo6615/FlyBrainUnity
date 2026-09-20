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
* Exactly one selected canonical Tier-B contribution can be admitted. Tier A,
  Tier C/D, the six excluded Coxa-yaw interfaces, and all other eligible
  Tier-B neural contributions remain exactly zero.
* Both `ENABLED` and `MOTOR_OUTPUT_DISABLED` calculate identical neural
  activity, 40 ms observer state, bounded activation (17 Hz half-activation),
  signed raw decoder output, baseline, range clamp, and 4 rad/s slew path. The
  sole condition-dependent value is admitted contribution: raw versus zero.
* Contribution magnitude is at most 0.25 rad and is reduced to the symmetric
  range available about the baseline from live MuJoCo joint limits.

## Sign calibration

M6A's `+1/-1` describes annotation-backed anatomical opposition; it is not
silently treated as NMF coordinate sign. P4 freezes the eight independently
resolved signs from the non-neural P2 kinematic evidence (all are `-1`) and
never recalculates them from scientific output or bilateral symmetry. The six
Coxa-yaw signs remain `SIGN_UNRESOLVED` and cannot be admitted.

### Coxa-yaw anatomical sign audit (M6B-P3)

M6B-P3 is a non-scientific, non-neural audit recorded in
`interface_output/m6b_coxa_yaw_sign_diagnostic.json`.  The old
`body_forward_x` endpoint projection is inappropriate for Coxa yaw: all six
hinges produce real distal motion under the fixed `0.0001 rad` perturbation,
but rotation about the live hinge need not have a nonzero component along one
global Cartesian axis.  A defensible kinematic measurement is instead the
oriented rotational metric
`dot(axis_world, cross(v_neutral, v_perturbed))`, normalized by the vector
lengths.  MuJoCo's `jnt_axis` is in the owning body's local frame, so the audit
requires `data.xmat[model.jnt_bodyid[jid]] @ model.jnt_axis[jid]`; vectors run
from the live joint anchor to the mean of exact selected-leg distal geoms.

The locked M6A annotations for every side and segment are explicit antagonist
pairs named **Sternal anterior rotator MN T1/T2/T3 left/right** and **Sternal
posterior rotator MN T1/T2/T3 left/right**.  M6A assigned the former `+1`
(`extensor`) and latter `-1` (`flexor`) and interpreted the pair as
`coxa_twist`.  That establishes population opposition, but the evidence does
not define “anterior” or “posterior” as positive or negative handed rotation
about the actual NMF hinge axis.  Thus the annotation-positive action cannot
independently be mapped to the geometric rotation.  Moreover, the retained P2
capture contains local axes and +/- endpoints but not owning-body transforms,
joint anchors, or neutral endpoints.  M6B-P3 does not reconstruct those absent
values by assumption.

Consequently all six Coxa-yaw interfaces remain `SIGN_UNRESOLVED`; no sign was
guessed from a nonzero Y component, apparent movement, or bilateral symmetry.
The independently resolved Femur interfaces and LF/RF Tarsus1 interfaces are
unchanged.  The **canonical** M6B eligibility set is therefore exactly:

* `joint_LFFemur`, `joint_LFTarsus1`, `joint_LMFemur`, `joint_LHFemur`
* `joint_RFFemur`, `joint_RFTarsus1`, `joint_RMFemur`, `joint_RHFemur`

The unresolved interfaces retain their annotation-backed motor mappings; they
are not reclassified as unsupported. Their physical sign is insufficient for
actuation and canonical neural actuation is `WITHHELD`. P4 called no scientific
condition runner, and Scientific Run #1 remains `NOT_RUN` and unconsumed.

The frozen eligible locks are:

| interface | action index | coordinate sign |
|---|---:|---:|
| `joint_LFFemur` | 3 | -1 |
| `joint_LFTarsus1` | 6 | -1 |
| `joint_LMFemur` | 10 | -1 |
| `joint_LHFemur` | 17 | -1 |
| `joint_RFFemur` | 24 | -1 |
| `joint_RFTarsus1` | 27 | -1 |
| `joint_RMFemur` | 31 | -1 |
| `joint_RHFemur` | 38 | -1 |

The historical sequence is preserved: Attempt #1 failed on the M6A raw-byte
provenance mismatch; Attempt #2 reported no valid joint/actuator limit
intersection; Attempt #3 passed after inactive `jnt_range=[0,0]` placeholders
were correctly ignored when `jnt_limited=false`.

## Isolation, equivalence, and milestones

Before the first nonzero admitted contribution, enabled and disabled traces
must be exactly equal for qpos, qvel, action, ctrl, selected-joint state,
observer state, decoder state, sensory state, and available RNG state/counters.
A mismatch is terminal and scientifically uninterpretable. Per-joint telemetry
records B0 through B5, allowing `<=` (same-update) ordering, full-body
physical divergence, selected-joint maximum/RMS differences, directional
spikes, observer/raw/admitted maxima, limit encounters, and instability.

Scientific attempts are immutable. Results are never overwritten or repeated
to improve an outcome. Attempt #1 is retained strictly as an aborted attempt
without a scientific result. Synthetic count tests, if used, are separately
labeled `SYNTHETIC_INTERFACE_DIAGNOSTIC_ONLY` and are not scientific evidence.

## Canonical Windows invocation

From the repository root in PowerShell, after installing the project's
validated MaleCNS/FlyGym/MuJoCo environment and Windows adapter:

Run the non-scientific engineering preflight first:

```powershell
.\fly-brain-interactive\.venv\Scripts\python.exe -m malecns_backend.embodiment.isolated_tier_b_motor_validation --preflight-windows
```

It must print `M6B WINDOWS FINAL PREFLIGHT PASS`. Do **not** invoke
`--run-windows` until Scientific Attempt #2 is separately authorized. The
adapter will preserve the aborted-attempt record and populate per-joint and
aggregate results without changing this frozen protocol.

## M6B-P5 performance repair and Attempt #1 provenance

Scientific Attempt #1 was manually interrupted after static inspection found
that the final physical-admission boundary called `enumerate_live_actuators()`
on every non-final 0.1-ms physics step. That helper constructs a temporary
FlyGym/MuJoCo simulation, so the canonical plan would have created 80,000
redundant inspection environments in addition to the setup inspection and 16
fresh scientific condition environments. No completed scientific result was
available or inspected. The machine-readable record is
`interface_output/m6b_attempt_1_abort.json`; its status is
`ABORTED_IMPLEMENTATION_PERFORMANCE_DEFECT`, not a scientific classification.

P5 resolves and validates the immutable 42-actuator inventory once during
setup and passes its ordered names to every fresh condition runtime. The
physical-admission assertion remains immediately adjacent to every command.
Expected canonical construction count is now exactly 17: one closed setup
inspection plus 16 fresh condition environments, with zero constructions per
physics step. Full neural-state digests still cover the same four arrays, but
are recomputed only after each 0.5-ms `brain.step()` and reused for the four
intervening physics samples, during which those arrays cannot change.

The runner prints flushed start, ten-percent, completion, elapsed-time, and
estimated-remaining messages, writes an atomic observational checkpoint after
each completed condition, records engineering phase timings, and closes every
condition environment in `finally`. Ctrl+C writes an incomplete
`ABORTED_USER_INTERRUPT` checkpoint with the active condition, completed count,
and elapsed wall time; it never writes a completed classification.
