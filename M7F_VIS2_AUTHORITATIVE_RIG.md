# M7F-VIS2 — authoritative FlyGym/MuJoCo Unity rig

## Status

The authoritative artifacts and the Unity numerical acceptance test are
implemented. The native source artifact is the completed Windows result already
checked in as `m7f_mujoco_crosscheck.json`. This Linux environment has no Unity
editor, so the nine-frame EditMode acceptance test is **implemented but not
executed here**. Consequently the scientific status remains:

> **UNITY SCIENTIFIC RIG: NOT YET VALIDATED**

No visual observation, old VIS1B result, or internal connectivity test is used
to promote that status. The status may become validated only when
`NineNativeMjForwardFramesAreTheNumericalAcceptanceGate` passes in Unity.

## Authoritative provenance and replay boundary

The physical source is FlyGym **1.2.1**, MuJoCo **3.2.7**, and
`neuromechfly_seqik_kinorder_ypr.xml` (SHA-256
`413b3a1dcb7537d08122e16f256f27ec0d8bb9f52c58670345b6c24c9e72e05a`).
The model is the compiled, arena-attached model assembled by the exact M7D
construction, not the MaleCNS XML and not an independent MJCF interpretation.

M7D recorder semantics are verified. The canonical 42 order is not MuJoCo qpos
order, but every canonical name maps uniquely to a scalar hinge and qpos address.
The replay arrays, names, timing, root poses, and binaries are unchanged. Unity
uses each artifact's `canonical_replay_index` and continues to apply absolute
recorded coordinates from immutable rest rotations; it never accumulates them.

## VIS1B invalidation and measured root cause

VIS1B is invalid. Its zero endpoint error was circular consistency within its
own MaleCNS-derived assumptions. Native MuJoCo measured maxima of
1.525786893500993 model units for pivots, 3.093124665521389 radians for axes,
1.525786893500993 model units for body positions, 3.1121285151398586 radians for
body orientations, and 1.7746643725040236 model units for endpoints.

The field-level comparison identifies **multiple concrete model-definition
differences**, not a coordinate-conversion-only problem:

| compiled field | different | exact | missing |
|---|---:|---:|---:|
| parent body | 42 | 0 | 0 |
| child body/name | 42 | 0 | 0 |
| body local position | 42 | 0 | 0 |
| body local quaternion | 42 | 0 | 0 |
| within-body hinge order | 30 | 12 | 0 |
| hinge axis | 30 | 12 | 0 |
| hinge local position | 0 | 42 | 0 |
| range | 0 | 0 | 42 |

Thus the dominant cause is the use of a different physical model with different
attachment/local poses, hinge order, and axes. The explicit presentation map
remains the verified reflection `RH Z-up [x,y,z] -> LH Y-up [x,z,y]`; axial
vectors use `-B axis`. That conversion does not explain or repair the source
model discrepancies.

## Artifacts and implementation

`m7f_authoritative_rig.json` contains the compiled freejoint-to-Thorax transform,
24 compiled leg-body records, and 42 joint
records: body/parent names, local positions and wxyz quaternions, segment
endpoints, joint type/position/axis/declaration order, canonical index, MuJoCo
joint ID, and qpos address. It also freezes versions, source and assembled
hashes, coordinate convention, and the 0.1 Unity-unit presentation scale.

`m7f_mujoco_reference_frames.json` contains the canonical root transform, 42
world pivots and axes, 24 body transforms, and 24 segment endpoints at frames
0, 540, 541, 785, 1210, 1570, 2500, 3980, and 5000. Its counters are nine
`mj_forward`, zero `mj_step`, zero physics transitions, and zero neural
transitions. These are sparse validation references, not replay trajectories.

The previous artifact is explicitly archived as
`m7f_vis1b_invalid_reference.json`; no Unity scientific code reads it. The new
builder reads JSON rather than MJCF, constructs exact parent/body transforms and
ordered hinge pivots, draws only modest pivot spheres and thin endpoint
cylinders, and uses no Rigidbody, ArticulationBody, collider, IK, or fitting.
The default scene presents one enabled condition and hides the duplicate control
until explicitly selected. Its only environment geometry is the non-colliding
ground plane.

The validator converts each native reference explicitly, evaluates the replay
at each of the nine frames, and compares root position/orientation, all pivots
and axes, all body positions/orientations, and all endpoints. It records maximum,
RMS, worst frame, and worst element for every category and throws if position
error exceeds `2e-5` Unity units or angular error exceeds `2e-4` radians.

## Files changed

* `tools/generate_m7f_kinematic_reference.py` — the one native run now emits the
  Unity artifacts together with the cross-check.
* `tools/build_m7f_vis2_artifacts.py` — deterministic, fail-closed packaging of a
  completed native result.
* `FlyBrainUnity/Assets/StreamingAssets/M7FValidation/*` — authoritative rig and
  reference artifacts plus explicitly invalid VIS1B archive.
* `M7FScientificFlyRigDefinition.cs`, `M7FScientificFlyBuilder.cs`,
  `M7FAuthoritativeRigValidator.cs`, `M7FFlyRig.cs`, and
  `M7FKinematicReferenceOverlay.cs` — JSON-driven construction, absolute replay,
  native overlay, and numerical validation.
* `M7FReplayTests.cs` and `tests/test_m7f_kinematic_reference.py` — provenance,
  determinism, fail-closed, presentation-boundary, and native-reference gates.

## Reproduction and tests

Run this **one exact command** from the repository root in the authoritative
Windows environment. It regenerates the native cross-check and both VIS2 JSON
artifacts; it never invokes `mj_step`:

```powershell
.\fly-brain-interactive\.venv\Scripts\python.exe tools\generate_m7f_kinematic_reference.py --verify-mujoco --crosscheck-output m7f_mujoco_crosscheck.json
```

Then run the Unity acceptance test manually:

```powershell
& "C:\Program Files\Unity\Hub\Editor\6000.0.58f2\Editor\Unity.exe" -batchmode -quit -projectPath .\FlyBrainUnity -runTests -testPlatform EditMode -testFilter FlyBrain.Tests.M7FReplayTests.NineNativeMjForwardFramesAreTheNumericalAcceptanceGate -testResults .\m7f_vis2_unity_results.xml
```

The exact Unity installation prefix may be adjusted if Unity Hub installed the
same version elsewhere. Passing output supplies the numerical results held in
the test's `M7FValidationReport`; until that command passes, no screenshot is
scientific validation. Generate the default scientific-rig-only view through
`Fly Brain > M7F > Create Canonical Replay Scene` after the test passes.

## Scientific declarations

* M7D MODIFIED: **NO**
* M7D RERUN: **NO**
* M7E MODIFIED: **NO**
* M7E RERUN: **NO**
* M7F CANONICAL REPLAY MODIFIED: **NO**
* M7F CANONICAL EXPORT RERUN: **NO**
* NEW SCIENTIFIC PHYSICS TRANSITIONS: **0**
* NEW NEURAL TRANSITIONS: **0**
* MJ_STEP CALLS: **0**
* UNITY PHYSICS DRIVES REPLAY: **NO**
* IK USED: **NO**
* VISUAL FITTING BY EYE: **NO**

The implementation commit hash is recorded by Git history for this report; a
file cannot contain the hash of the commit that contains that same file without
changing the hash.
