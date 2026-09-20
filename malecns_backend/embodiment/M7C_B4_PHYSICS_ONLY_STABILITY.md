# M7C-B4 physics-only initial support stability

This protocol consumes the completed canonical B3 JSON and refuses any schema,
status, analytic-height, reconstructed-geometry, or zero-transition protocol
mismatch. The B3 bytes are hashed and the absolute source path and digest are
carried into the B4 result. B3 is read, never regenerated.

The initialization is frozen to FlyGym's `tripod` resource, position control,
spawn position `(0, 0, 0.6045752232266313)`, zero Euler spawn orientation, and
disabled adhesion. FlyGym 1.2.1, MuJoCo 3.2.7, a 0.0001 s timestep, 1,000
transitions, and 1,001 sampled states are mandatory. No settling transition is
allowed.

Preflight reconstructs the inherited M7/M7C calibration box and verifies its
position, half-size, identity orientation, collision masks, name, and target
provenance. It reset/forwards the model, confirms all 42 B3 tripod joint values
bit-for-bit, freezes the measured values as targets, and repeats the B3 contact
gate. It never invokes `step`.

The run reconstructs and gates a fresh model, then submits one unchanging
42-joint target and six zero adhesion values for every transition. A fall or
rollover is recorded and does not stop, tune, settle, or retry the experiment.
Only an exception, corrupt count, or nonfinite state aborts without a completed
scientific result.

Raw telemetry is a compressed, non-object NPZ. Numeric state arrays and compact
UTF-8 JSON contact/category arrays cover root pose, body-up Z, qpos/qvel,
joints, targets, action, controls, contact identity/depth/force, support,
forbidden, self, and calibration contacts. The JSON summary includes exact
states at indices 0, 72, 130, and 1000; frozen M7 fall (half initial body
height) and rollover (body-up Z at or below zero) criteria; full support
statistics; and dedicated `LHCoxa`/`RHCoxa` evolution. The manifest records raw
path, byte size, SHA-256, environment paths, B3 digest, constants, and schema.

Exclusive creation and a completed-result precheck protect all canonical
outputs. An existing raw artifact also blocks execution. There is no MaleCNS
import or construction, neural clock, controller, trajectory, reward, learning,
optimizer, height sweep, collision-mask change, or adaptive correction.

## Windows commands

Run preflight first:

```powershell
python -m malecns_backend.embodiment.m7c_b4_stability --windows-preflight
```

After reviewing preflight only, the future one-shot experiment command is:

```powershell
python -m malecns_backend.embodiment.m7c_b4_stability --run-windows
```

**DO NOT RUN the second command until the preflight has been reviewed.**
