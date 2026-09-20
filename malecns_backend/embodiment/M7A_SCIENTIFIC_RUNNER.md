# M7-A frozen scientific runner implementation (science not run)

This implementation does not alter `M7_SPONTANEOUS_LOCOMOTION_PREREGISTRATION.md`
or its `M7.0` artifact.  The live adapter reconstructs the locked M6C admission
table from the raw-byte-locked M6A, M6B, and Tier-A evidence and verifies the
final M6C evidence lock before constructing either M7 condition.

## Physical initialization audit

The reused M6C `_make_live` path constructs `Fly(enable_adhesion=False,
control="position")` with FlyGym's default initial fly pose and joint
configuration. It uses a `FlatTerrain` arena plus the existing static
`m5d2c_calibration_surface`. At reset, that box is moved once to the underside
of `LMTarsus5`, MuJoCo is forwarded without advancing time, and an assertion
proves that placement did not change fly `qpos`. The actual qpos, qvel, body
position/quaternion, 42 joint positions, and model gravity are captured by V2
preflight rather than copied as platform-dependent literals.

Adhesion is disabled in the Fly constructor and every physics action supplies
six constant zeros. There is no automatic, scheduled, stance-dependent, or
controller-generated adhesion. The surface is not moved after reset. No
FlyGym locomotion, reference, gait, balance, RL, reward, or AI controller is
constructed; the simulation receives only baseline joint positions plus the
eleven individually decoded M6C contributions.

## Execution and artifacts

V2 preflight initializes the same two fresh runtime paths and then returns
before `brain.step()` or `sim.step()`. Science uses exactly two additional
fresh runtimes, seed 1, 5,000 ms, 50,000 physics transitions and 10,000 neural
updates. The control keeps brain stepping, tibial sensory encoding, observers,
decoders, RNG use, physics, and telemetry intact; its only intervention is to
replace the eleven admitted contributions with zero immediately before the
unchanged safety/application pipeline.

Canonical files are exclusively created in `interface_output/m7_canonical/`:

* `m7_raw.npz`: compressed arrays at physics and neural cadence;
* `m7_summary.json`: control-relative descriptive reduction and frozen
  nonexclusive movement categories;
* `m7_manifest.json`: shapes, dtypes, SHA256, provenance, and elapsed time.

An implementation failure is separately preserved as an exclusively created
`ABORTED_IMPLEMENTATION_*.json`, without behavioral classification. Offline
visualizers may consume qpos/body trajectory arrays in the NPZ; rendering is
not on the control path. Existing canonical files are never overwritten.
