# M5D-4A — pre-motor physical equivalence diagnostic

## Status and scope

The checked-in M5D-4A artifact is **`NOT_RUN`** because this repository
environment is not the validated Windows FlyGym/MuJoCo environment. No
diagnostic classification or new scientific result is claimed. The first
canonical M5D-4 result remains `PRE_MOTOR_EQUIVALENCE_FAILED`; its authoritative
2.8–14.5 ms timing and `interface_output/tactile_motor_loop.json` are not
changed, rerun, tuned, replaced, or reinterpreted. In particular, M5D-4A makes
no C5/C6/C7/C8 motor-causality claim.

## Hard actuation boundary

Four fresh runs are constructed: enabled-like/motor-off,
disabled-like/motor-off, `CONTROL_A`, and `CONTROL_B`. Every run uses the same
locked M5D-2C contact setup, tactile encoder, seed, MaleCNS, and six established
tibia decoders. Candidate tactile events are delivered and motor output is
observed and decoded. Nevertheless, the value sent to each tibia actuator is
unconditionally the current measured BASE/HOLD position. The application flag
and applied neural contribution are respectively `false` and zero on every
sample. This is a diagnostic, not an M5D-4 rerun.

## Initialization and per-step audit

Before stepping, snapshots compare dimensions (`nq`, `nv`, `nu`, `na`, bodies,
joints, geoms, actuators), reset contacts, dynamic model arrays, geom/contact
arrays, gravity and solver options, state arrays, and the calibration surface's
identity, transform, size, friction, and solver parameters. Equality is exact;
the report records the first differing path, values, absolute difference, and
maximum absolute difference.

At the native 0.1 ms physical timestep through 15.0 ms, telemetry records
simulation time, qpos/qvel/qacc/ctrl, complete contact pair set, full resolved
contact records (distance, position, frame, and friction), selected LM
Tarsus5/surface metadata, the raw sensor observation and magnitude, and—when
available without stepping—the MuJoCo contact wrench. Joint state indices are
resolved to joint, body, component/DOF; controls are resolved to actuator, leg,
and six-tibia membership.

First divergence is searched independently for ctrl, contact set, selected
contact metadata, qacc, qvel, qpos, and contact-force observations. Control
rows also identify whether the base came from the current measured position,
record decoded values, and prove the neural application flag stayed false.

## Repeatability, order, and classification

`CONTROL_A` and `CONTROL_B` are literally identical fresh configurations. A
difference takes precedence as `PHYSICS_REPEATABILITY_FAILURE`. If the repeat
matches but the wrappers differ, the runner performs a fresh reversed-order
pair. It reports whether the outcome follows label or order and can classify a
run-order effect as `SHARED_STATE_LEAK`. More specific established evidence can
produce `MODEL_CONFIGURATION_MISMATCH`, `INITIAL_STATE_MISMATCH`,
`CONTROL_COMMAND_MISMATCH`, or `CONTACT_SOLVER_DIVERGENCE`; otherwise wrapper
differences are `CONDITION_WRAPPER_MISMATCH`. Exact matching throughout is
`EXACT_REPEATABILITY_CONFIRMED`.

## Windows command

From the repository root in the same validated Windows environment used for
the canonical artifacts:

```powershell
.\fly-brain-interactive\.venv\Scripts\python.exe -m malecns_backend.embodiment.tactile_motor_equivalence_diagnostic_audit --live --json malecns_backend\embodiment\interface_output\tactile_motor_equivalence_diagnostic.json
```

The command writes only the M5D-4A JSON path and does not overwrite the
canonical `tactile_motor_loop.json`.
