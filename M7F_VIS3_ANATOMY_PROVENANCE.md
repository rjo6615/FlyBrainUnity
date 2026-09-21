# M7F-VIS3 anatomical presentation provenance

## Scientific boundary

VIS3 does not change M7D/M7E, replay binaries, joint order, the authoritative rig or native reference JSON, the MuJoCo-to-Unity mapping, scale, quaternion conversion, or VIS2 tolerances. Presentation is a renderer-only child of validated scientific body transforms and never drives those transforms. `mj_step = 0`; no physics or IK is added.

## Authoritative Windows extraction

The sole source is FlyGym **1.2.1** `data/mjcf/neuromechfly_seqik_kinorder_ypr.xml`, SHA-256 `413b3a1dcb7537d08122e16f256f27ec0d8bb9f52c58670345b6c24c9e72e05a`. The completed Windows command was:

```powershell
py tools/import_m7f_vis3_anatomy.py `
  --flygym-root fly-brain-interactive\.venv\Lib\site-packages\flygym
```

It produced **69 meshes and 69 placements**. The checked-in manifest has 69 unique mesh names, all 69 referenced generated OBJ files exist, and there are exactly 69 OBJ files. Every extracted geom has role `visual`; no collision geometry is represented or inferred.

## Complete extracted inventory

Positions and quaternions below are model-derived MuJoCo-local values. Quaternion order is **w,x,y,z**. `mesh scale` is the source MJCF asset scale which VIS3A already baked into OBJ vertices together with the frozen presentation scale; Unity does not apply it again.

| Body | Mesh / OBJ stem | Source STL | Scientific parent | Local position (source xyz) | Local orientation (source wxyz) | Mesh scale baked by VIS3A | Role |
|---|---|---|---|---|---|---|---|
| `Thorax` | `mesh_Thorax` | `../mesh/Thorax.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `A1A2` | `mesh_A1A2` | `../mesh/A1A2.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `A3` | `mesh_A3` | `../mesh/A3.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `A4` | `mesh_A4` | `../mesh/A4.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `A5` | `mesh_A5` | `../mesh/A5.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `A6` | `mesh_A6` | `../mesh/A6.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `LHaltere` | `mesh_LHaltere` | `../mesh/RHaltere.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, -1000, 1000]` | `visual` |
| `LWing` | `mesh_LWing` | `../mesh/RWing.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, -1.455191698e-15]` | `[1000, -1000, 1000]` | `visual` |
| `RHaltere` | `mesh_RHaltere` | `../mesh/RHaltere.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `RWing` | `mesh_RWing` | `../mesh/RWing.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 1.455191698e-15]` | `[1000, 1000, 1000]` | `visual` |
| `LFCoxa` | `mesh_LFCoxa` | `../mesh/RFCoxa.stl` | `LFCoxa` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, -1000, 1000]` | `visual` |
| `LFFemur` | `mesh_LFFemur` | `../mesh/RFFemur.stl` | `LFFemur` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, -1000, 1000]` | `visual` |
| `LFTibia` | `mesh_LFTibia` | `../mesh/RFTibia.stl` | `LFTibia` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, -1000, 1000]` | `visual` |
| `LFTarsus1` | `mesh_LFTarsus1` | `../mesh/RFTarsus1.stl` | `LFTarsus1` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, -1000, 1000]` | `visual` |
| `LFTarsus2` | `mesh_LFTarsus2` | `../mesh/RFTarsus2.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, -1000, 1000]` | `visual` |
| `LFTarsus3` | `mesh_LFTarsus3` | `../mesh/RFTarsus3.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, -1000, 1000]` | `visual` |
| `LFTarsus4` | `mesh_LFTarsus4` | `../mesh/RFTarsus4.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, -1000, 1000]` | `visual` |
| `LFTarsus5` | `mesh_LFTarsus5` | `../mesh/RFTarsus5.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, -1000, 1000]` | `visual` |
| `LHCoxa` | `mesh_LHCoxa` | `../mesh/RHCoxa.stl` | `LHCoxa` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, -1000, 1000]` | `visual` |
| `LHFemur` | `mesh_LHFemur` | `../mesh/RHFemur.stl` | `LHFemur` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, -1000, 1000]` | `visual` |
| `LHTibia` | `mesh_LHTibia` | `../mesh/RHTibia.stl` | `LHTibia` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, -1000, 1000]` | `visual` |
| `LHTarsus1` | `mesh_LHTarsus1` | `../mesh/RHTarsus1.stl` | `LHTarsus1` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, -1000, 1000]` | `visual` |
| `LHTarsus2` | `mesh_LHTarsus2` | `../mesh/RHTarsus2.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, -1000, 1000]` | `visual` |
| `LHTarsus3` | `mesh_LHTarsus3` | `../mesh/RHTarsus3.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, -1000, 1000]` | `visual` |
| `LHTarsus4` | `mesh_LHTarsus4` | `../mesh/RHTarsus4.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, -1000, 1000]` | `visual` |
| `LHTarsus5` | `mesh_LHTarsus5` | `../mesh/RHTarsus5.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, -1000, 1000]` | `visual` |
| `LMCoxa` | `mesh_LMCoxa` | `../mesh/RMCoxa.stl` | `LMCoxa` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, -1000, 1000]` | `visual` |
| `LMFemur` | `mesh_LMFemur` | `../mesh/RMFemur.stl` | `LMFemur` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, -1000, 1000]` | `visual` |
| `LMTibia` | `mesh_LMTibia` | `../mesh/RMTibia.stl` | `LMTibia` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, -1000, 1000]` | `visual` |
| `LMTarsus1` | `mesh_LMTarsus1` | `../mesh/RMTarsus1.stl` | `LMTarsus1` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, -1000, 1000]` | `visual` |
| `LMTarsus2` | `mesh_LMTarsus2` | `../mesh/RMTarsus2.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, -1000, 1000]` | `visual` |
| `LMTarsus3` | `mesh_LMTarsus3` | `../mesh/RMTarsus3.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, -1000, 1000]` | `visual` |
| `LMTarsus4` | `mesh_LMTarsus4` | `../mesh/RMTarsus4.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, -1000, 1000]` | `visual` |
| `LMTarsus5` | `mesh_LMTarsus5` | `../mesh/RMTarsus5.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, -1000, 1000]` | `visual` |
| `RHCoxa` | `mesh_RHCoxa` | `../mesh/RHCoxa.stl` | `RHCoxa` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `RHFemur` | `mesh_RHFemur` | `../mesh/RHFemur.stl` | `RHFemur` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `RHTibia` | `mesh_RHTibia` | `../mesh/RHTibia.stl` | `RHTibia` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `RHTarsus1` | `mesh_RHTarsus1` | `../mesh/RHTarsus1.stl` | `RHTarsus1` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `RHTarsus2` | `mesh_RHTarsus2` | `../mesh/RHTarsus2.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `RHTarsus3` | `mesh_RHTarsus3` | `../mesh/RHTarsus3.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `RHTarsus4` | `mesh_RHTarsus4` | `../mesh/RHTarsus4.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `RHTarsus5` | `mesh_RHTarsus5` | `../mesh/RHTarsus5.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `RMCoxa` | `mesh_RMCoxa` | `../mesh/RMCoxa.stl` | `RMCoxa` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `RMFemur` | `mesh_RMFemur` | `../mesh/RMFemur.stl` | `RMFemur` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `RMTibia` | `mesh_RMTibia` | `../mesh/RMTibia.stl` | `RMTibia` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `RMTarsus1` | `mesh_RMTarsus1` | `../mesh/RMTarsus1.stl` | `RMTarsus1` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `RMTarsus2` | `mesh_RMTarsus2` | `../mesh/RMTarsus2.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `RMTarsus3` | `mesh_RMTarsus3` | `../mesh/RMTarsus3.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `RMTarsus4` | `mesh_RMTarsus4` | `../mesh/RMTarsus4.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `RMTarsus5` | `mesh_RMTarsus5` | `../mesh/RMTarsus5.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `RFCoxa` | `mesh_RFCoxa` | `../mesh/RFCoxa.stl` | `RFCoxa` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `RFFemur` | `mesh_RFFemur` | `../mesh/RFFemur.stl` | `RFFemur` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `RFTibia` | `mesh_RFTibia` | `../mesh/RFTibia.stl` | `RFTibia` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `RFTarsus1` | `mesh_RFTarsus1` | `../mesh/RFTarsus1.stl` | `RFTarsus1` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `RFTarsus2` | `mesh_RFTarsus2` | `../mesh/RFTarsus2.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `RFTarsus3` | `mesh_RFTarsus3` | `../mesh/RFTarsus3.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `RFTarsus4` | `mesh_RFTarsus4` | `../mesh/RFTarsus4.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `RFTarsus5` | `mesh_RFTarsus5` | `../mesh/RFTarsus5.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `Head` | `mesh_Head` | `../mesh/Head.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `LEye` | `mesh_LEye` | `../mesh/REye.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, -1000, 1000]` | `visual` |
| `REye` | `mesh_REye` | `../mesh/REye.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `Rostrum` | `mesh_Rostrum` | `../mesh/Rostrum.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `Haustellum` | `mesh_Haustellum` | `../mesh/Haustellum.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `LPedicel` | `mesh_LPedicel` | `../mesh/RPedicel.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, -1000, 1000]` | `visual` |
| `LFuniculus` | `mesh_LFuniculus` | `../mesh/RFuniculus.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, -1000, 1000]` | `visual` |
| `LArista` | `mesh_LArista` | `../mesh/RArista.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, -1000, 1000]` | `visual` |
| `RPedicel` | `mesh_RPedicel` | `../mesh/RPedicel.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `RFuniculus` | `mesh_RFuniculus` | `../mesh/RFuniculus.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |
| `RArista` | `mesh_RArista` | `../mesh/RArista.stl` | `Thorax` | `[0, 0, 0]` | `[1, 0, 0, 0]` | `[1000, 1000, 1000]` | `visual` |

## Structures represented

The authoritative inventory represents the thorax; abdominal A1A2, A3, A4, A5, and A6 meshes; head, left/right eyes, rostrum, haustellum, left/right pedicels, funiculi, and aristae; left/right wings and halteres; and all six legs. Each leg contains coxa, femur, tibia, and tarsus segments 1 through 5. This is an inventory statement only and makes no claim about gait, walking, reflex, natural motion, or biological function.

## Unity presentation architecture

For each manifest record the runtime constructs:

```text
Validated scientific body Transform (unchanged)
  -> Presentation — <mesh_name> (manifest local position/orientation, unit positive scale)
      -> <mesh_name> (MeshFilter + MeshRenderer only)
```

The project-contained loader accepts only the generated comment, `v`, and triangular `f` OBJ dialect, uses invariant-culture parsing, validates all indices, chooses a deterministic 16/32-bit index format, and recalculates normals/bounds. It loads from `StreamingAssets/M7FAnatomy` in Editor and canonical standalone builds without an external importer package.

VIS3A already baked source mesh scale, frozen presentation scale `0.1`, polar basis `B(x,y,z)=(x,z,y)`, and reflected triangle winding correction into each OBJ. Runtime vertices are consumed verbatim. Runtime applies only manifest geom position as `0.1 * B(position)` and geom quaternion with the unchanged `M7FCoordinates.SourceQuaternionToUnity` conversion. Both anchor and mesh retain `Vector3.one`; no negative scale, second scale, basis reflection, or winding reversal occurs.

The presentation validator fails closed on a count other than 69, duplicate placements, missing OBJ files, missing scientific parents, non-visual roles, negative scales, Rigidbody, Collider, ArticulationBody, CharacterController, Unity Joint, Animator, or Animation. Presentation components have no update loop and never write a scientific transform.

The scene generator builds authoritative anatomy for both selectable conditions, starts in canonical Enabled-only mode, uses a neutral non-colliding ground and replay camera, and retains playback/frame/time/condition controls. The old procedural scientific cylinders, pivot markers, reference markers, and axes are renderer-disabled by default. The explicit **Scientific Skeleton** UI toggle enables that diagnostic overlay without changing scientific transforms. Side-by-side remains available but is not the default.

## Acceptance

Run the separate `FlyBrain.Tests.M7FVis3AnatomyTests` EditMode suite, then the unchanged `FlyBrain.Tests.M7FReplayTests.NineNativeMjForwardFramesAreTheNumericalAcceptanceGate` on Windows. Do not state **VIS3 ANATOMICAL PRESENTATION VALIDATED** until both pass there. Linux source/static checks do not replace visual inspection or Windows Unity acceptance.

From the repository root in PowerShell (set `UNITY_EDITOR` to the installed Unity 6 editor executable), the exact commands are:

```powershell
& $env:UNITY_EDITOR -batchmode -nographics -projectPath .\FlyBrainUnity -runTests -testPlatform EditMode -testFilter FlyBrain.Tests.M7FVis3AnatomyTests -testResults .\m7f_vis3_unity_results.xml -logFile .\m7f_vis3_unity.log -quit

& $env:UNITY_EDITOR -batchmode -nographics -projectPath .\FlyBrainUnity -runTests -testPlatform EditMode -testFilter FlyBrain.Tests.M7FReplayTests.NineNativeMjForwardFramesAreTheNumericalAcceptanceGate -testResults .\m7f_vis2_regression_results.xml -logFile .\m7f_vis2_regression.log -quit

& $env:UNITY_EDITOR -projectPath .\FlyBrainUnity -executeMethod M7FCanonicalReplaySceneGenerator.CreateCanonicalReplayScene
```

The final command opens Unity and deterministically constructs the finished viewer in a new in-memory scene; save it only if desired. It reads, but does not regenerate, canonical replay/scientific artifacts.

## License and distribution

FlyGym/NMF model assets remain governed by the upstream distribution and repository license. The extraction selects only meshes referenced by the authoritative MJCF and copies no unrelated package code or data.
