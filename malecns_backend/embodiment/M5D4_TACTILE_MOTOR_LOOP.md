# M5D-4 — closed-loop physical tactile → MaleCNS → motor → body

## Status

The checked-in artifact is **`NOT_RUN`**. This development container does not
provide NumPy, FlyGym, or MuJoCo, so no physical or causal outcome is claimed.
M5D-3 is neither executed nor modified. Its source/protocol artifacts and the
locked tactile/contact/motor-map inputs are SHA-256 checked before any run.

### Provenance lock types

The static manifest in `tactile_motor_loop.py` deliberately distinguishes two
lock types:

* **Source/protocol locked:** canonical LF bytes are hashed, so Git's Windows
  CRLF checkout policy cannot masquerade as a scientific change. Any other
  byte change fails closed.
* **Live-result locked:** `interface_output/tactile_propagation.json` must pass
  an exact COMPLETE/P7 semantic manifest (including configuration, population,
  physical matching, spike counts, and divergence times). The manifest has a
  literal SHA-256 fingerprint; it is not generated from the current file.

The obsolete checked-in NOT_RUN M5D-3 artifact is intentionally rejected. The
authoritative Windows result must be present before `--live` can proceed.
Provenance validation runs before population, decoder, physics, or neural
runtime construction and is repeated after the run.

## Locked interfaces

The physical source is exactly FlyGym `contact_forces[11]` (LM Tarsus5). The
`m5d2c_calibration_surface` is placed with 0.0001 model-unit penetration without
changing fly qpos. Contact is accepted only when the exact unordered Tarsus5 ↔
surface MuJoCo geom pair exists; `magnitude > 1e-12` is the engineering sensor
threshold.

The unchanged M5D-2 encoder addresses all 378 neurons in `tactile T2 left`, with
no subsampling. It emits a modeled 120 Hz maximum, 20 ms linearly decaying onset
transient, does not retrigger during sustained contact, and rearms on release.
Both conditions construct a fresh encoder and MaleCNS with seed 1 and deliver
candidate events through `MaleCNSBrain.set_external_drive`.

Only the existing M4A/M4B tibia interfaces can cross the physical actuation
boundary:

| Leg | actuator index |
|---|---:|
| LF | 5 |
| LM | 12 |
| LH | 19 |
| RF | 26 |
| RM | 33 |
| RH | 40 |

Coxa, coxa-roll, coxa-yaw, femur, femur-roll, and tarsus1 populations may be
observed but are never actuated. No new mapping, gait logic, reflex logic,
behavior controller, or direct tactile-to-motor route is present.

## Matched intervention

`TACTILE_MOTOR_ENABLED` and `TACTILE_MOTOR_DISABLED` each start from a fresh,
identically seeded physical and neural runtime. Both receive tactile input, run
MaleCNS, observe mapped tibia motor spikes, update the same 40 ms low-pass
observer, and compute the same established decoder candidate. Disabled differs
only at the physical boundary: it holds the current measured tibia positions
instead of applying the decoded contribution.

The reused decoder computes population instantaneous Hz and filtered Hz, pools
only explicit audited extensor/flexor roles, uses
`1 - exp(-Hz * ln(2) / 17)`, subtracts flexor activation from extensor
activation, applies the locked 0.25 rad maximum modeled offset, actuator-range
clamp, ±4 rad/s slew limit, and final clamp. No gain or limit is retuned.

## Equivalence and causal analysis

Every telemetry row records exact contact metadata, selected force, all qpos,
six tibia qpos, tactile rate/candidates/deliveries, a digest of complete neural
state, mapped-motor increments, decoder state, decoded contribution, and applied
contribution. Before the first nonzero applied contribution, these fields are
compared with strict equality. A mismatch produces
`PRE_MOTOR_EQUIVALENCE_FAILED` and suppresses a motor-causality claim.

After application, analysis independently locates first six-tibia qpos, full
qpos, LM force, exact-contact, tactile-rate/event, downstream-state/spike, and
subsequent mapped-motor differences. Sensory/CNS/motor feedback milestones are
only admitted at or after their causal prerequisites. Reports include 25, 50,
75, and 100 ms per-leg differences, final/max differences, six-tibia L2 and RMS,
and separate full-body qpos differences. Coupled DOFs are explicitly not direct
neural actuation.

C0–C8 are engineering stages only. Even C8 would not establish natural touch
response, withdrawal, gait, coordination, intent, learning, or biological
appropriateness.

## Failure handling

NaN/Inf or a MuJoCo exception terminates that condition without retry, timestep
change, gain adjustment, or duration extension. The report records condition,
last valid/failing times, exception, and qpos/qvel/qacc and classifies the run
`PHYSICS_UNSTABLE`. JSON is strict, deterministically sorted, and atomically
replaced.

## Live validation

From the repository root on the validated Windows environment:

```powershell
.\fly-brain-interactive\.venv\Scripts\python.exe -m malecns_backend.embodiment.tactile_motor_loop_audit --live --duration-ms 100 --json malecns_backend\embodiment\interface_output\tactile_motor_loop.json
```
