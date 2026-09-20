# M7C-A passive embodiment initial-stability audit

## Status and motivation

M7C-A is an engineering/physics audit, not a locomotion or neuroscience
experiment.  Canonical M7B reports the same first fall event in both conditions
at physics sample 72 (approximately 7.2 ms), with the immediately preceding
body position `[0.001368932028244034, 0.05517087463521892,
0.25380239387763176]` and quaternion `[0.9997482414823777,
0.022394013465577362, -0.00062463635735605, 0.001253651952592674]`.
The frozen initial height is 0.5 model metres, so the strict fall boundary is
0.25.  M7B also records that admitted neural motor activity did not precede the
event.  A longer run cannot repair an event that already invalidates the usable
pre-event window before the approximately 13 ms admitted-motor latency.

The raw archive is deliberately not stored in this checkout.  Its manifest
names `m7_raw.npz`, records 175,792,136 bytes, and locks SHA-256
`155ef633a319711d44fc471c1f46c24cec0b36ea6e7326556c5b987e912fed47`.
Consequently this checkout does **not** invent the missing sample-72 height,
joint, contact, action, control, qpos, or qvel values.  The local read-only
analyzer produces those values when supplied with that exact archive.

## Implementation path inspected

The canonical adapter calls `_windows_m6c_live_condition.run_condition`, which
calls `tactile_motor_loop_audit._make_live`.  That inherited M5 path:

1. Builds `flygym.Fly(enable_adhesion=False, control="position")` with contact
   sensors on Tibia and Tarsus1--5 for all six legs.
2. Builds FlyGym `FlatTerrain`, then adds the inherited static box geom
   `m5d2c_calibration_surface` with half-size `(0.025, 0.025, 0.002)`, initial
   position `(0, 0, -10)`, `contype=1`, and `conaffinity=1`.
3. Builds `SingleFlySimulation(..., cameras=[], timestep=0.0001)` and calls
   `reset()` once.  It supplies no initial root-position, orientation, or joint
   override: these therefore come from FlyGym/model defaults.
4. Finds `LMTarsus5`, reads its post-reset world position and conservative
   `geom_rbound`, and places the box top at the tarsus lower bound with a fixed
   0.0001 penetration.  It calls physics `forward()` to recompute derived
   geometry/contact state and verifies bit-exactly that qpos did not change.
5. Reads the 42 observed joints into `commands`.  Thus the frozen baseline
   target vector is the measured post-reset joint vector by construction.  The
   loop later passes `{"joints": commands, "adhesion": zeros(6)}` to each
   physics step.  “Neural disabled” is therefore position-served, not an
   actuator-free body, even though its initial target-minus-measurement vector
   is exactly zero.
6. Gravity, actuator gains/ranges, FlatTerrain geometry/friction/contact
   parameters, fly collision geometry, root pose, and initial joint pose are
   not overridden by M6/M7; they come from the installed FlyGym/MuJoCo model.
   M7C-A does not guess these version-dependent values: the zero-step artifact
   reads them from the instantiated model.

`reset()` is a FlyGym operation and may internally perform state mutation or
forward computation.  The repository does not own FlyGym's installed source,
so its internals must be recorded/version-audited in the validated Windows
environment.  After `_make_live` returns, canonical M7 records the t=0 state
before its first `sim.step`.  No settling loop exists.  The first explicit
physics action is issued only after that t=0 record.

## Zero-step inspection

`python -m malecns_backend.embodiment.m7c_initial_stability_audit
--preflight-windows` reconstructs that path without importing or constructing a
brain and without calling `sim.step`.  It records root qpos/qvel, quaternion and
up-Z, all 42 measured joints, the exactly copied baseline targets and
differences, ctrl, gravity, all model geoms and their positions/sizes/friction/
collision masks, every initial contact's pair/distance/position/normal, and the
calibration box.  `physics.forward()` is explicitly reported: it recomputes
derived state but advances neither time nor dynamics.  Both transition counts
are hard-locked to zero.

The box was originally an M5D-2C environment-only sensor-correspondence aid,
not a stance platform.  Its placement deliberately creates a conservative
0.0001 overlap below LMTarsus5.  Because it is a broad 0.05 by 0.05 box with
enabled collisions, contacts are not restricted by a geom-pair exclusion to
LMTarsus5; other collision-enabled geoms geometrically reaching it may interact
with it.  Whether that actually occurs, whether FlatTerrain simultaneously
supports other feet, and whether body geoms collide are answered by the
zero-step contact list—not by the box's intended purpose.

FlyGym represents adhesion as an enabled Fly feature plus a six-element action.
Canonical construction disables that feature and nevertheless supplies a
constant-zero six-element command.  This establishes the configuration, but
does not establish slip or causality.  Whether ordinary FlyGym stance depends
on adhesion, and whether any initial feet slip, requires model/contact evidence
or a later controlled physical comparison.

## Canonical first-10-ms analysis

`m7c_canonical_first10ms` is independent of the scientific runner and all
FlyGym/neural modules.  Before opening, it requires the frozen SHA.  It uses
`numpy.load(..., allow_pickle=False)`, rejects missing, object, nonnumeric,
nonfinite, shape-inconsistent, or incomplete telemetry, snapshots file size,
mtime, and digest to detect mutation, and restricts output to 0--10 ms.  For
each condition and sample it emits time, body XYZ/quaternion/up-Z/height, qpos,
qvel, all 42 joints, action, ctrl, contact-force telemetry/nonzero count, and
both predicate components.  It reports the exact first strict height crossing
and nonpositive-up-Z crossing and requires exact equality of every recorded
physical field between conditions over the window.

Contact-force observations do not identify geom pairs; pair-level foot/body
contact is available only in live MuJoCo state and therefore belongs to the
zero-step artifact.  The analyzer states this limitation rather than
fabricating pair identities from force rows.

## Findings and conservative classification

Evidence presently available in this checkout supports only these findings:

* The initial recorded root is `(0, 0, 0.5)` and the strict frozen fall boundary
  is height `< 0.25`.
* Both conditions first satisfy the fall predicate at sample 72 / about 7.2 ms;
  their sample immediately before that crossing is identical and has height
  `0.25380239387763176`.
* The event precedes admitted MaleCNS output.
* Baseline targets are initialized from measured joints, so there is no target
  mismatch at target creation.  Active position servos can still react to
  gravity/contact displacement after dynamics begin; existing summary evidence
  does not isolate that reaction from settling.
* The calibration surface deliberately overlaps the conservative LMTarsus5
  bound and changes the support geometry.  Presence and potential interaction
  are supported; contribution to the 7.2-ms event is not.
* Zero adhesion is confirmed.  Its contribution remains plausible only in the
  ordinary-language sense and is **not** assigned a supported cause label.

**Cause classification: `CAUSE_NOT_RESOLVED`.**  The missing raw archive and
zero-step model artifact prevent a complete local geometry/trajectory audit,
and observational evidence alone does not isolate gravity/contact settling,
servo response, surface effects, pose instability, or adhesion.

## M7C-B preregistration design (design only; do not run in M7C-A)

Decision rule: first obtain both M7C-A artifacts.  If zero-step evidence shows
only the intended LMTarsus5/box contact and no penetration/body contact anomaly,
the minimum M7C-B is a matched, neural-motor-disabled, physical-only two-level
comparison of **calibration surface present versus absent**, holding installed
FlyGym version, reset state, initial pose, baseline measured targets, adhesion,
timestep, terrain, and all other physics fixed.  This is the first variable
chosen because the box is a repository-added support intervention rather than a
FlyGym default.  Do not simultaneously vary adhesion, pose, height, targets, or
settling.  Predeclare mechanical viability through at least the established
~13 ms neural latency; 100 ms may be recorded as an engineering safety window,
not retroactively made an M7 scientific threshold.

If zero-step evidence instead shows body/terrain penetration, unintended box
contacts, or nonzero baseline mismatch, stop and preregister a two-level test of
that single evidenced defect versus the frozen configuration.  An adhesion
comparison is justified only after the audit documents foot slip/contact loss.
Any correction is a new protocol/version and can never replace canonical M7.

## Limitations and exact local diagnostic commands

Run these from the repository root in the validated Windows environment.  They
are diagnostics over initialization/existing evidence, **not an instruction to
rerun M7**:

```powershell
python -m malecns_backend.embodiment.m7c_initial_stability_audit --preflight-windows
python -m malecns_backend.embodiment.m7c_canonical_first10ms --raw malecns_backend\embodiment\interface_output\m7_canonical\m7_raw.npz
python -m pytest tests\test_m7c_initial_stability_audit.py -q
```

M7 CANONICAL RESULT MODIFIED: NO
M7 SCIENTIFIC RERUN: NO
M6C RERUN: NO
NEURAL PARAMETERS CHANGED: NO
MOTOR DECODER CHANGED: NO
SENSORY MODEL CHANGED: NO
PHYSICS PARAMETERS CHANGED: NO
SCIENTIFIC TRANSITIONS EXECUTED: 0
CANONICAL RAW MODIFIED: NO
