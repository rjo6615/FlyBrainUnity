# M7F-VIS1 implementation evidence and scientific boundary

## Scope

This Unity-only viewer reads the already completed M7F binary export. It contains no MaleCNS, FlyGym, MuJoCo, stepping, force, collision, IK, animator, gait, walking, contact, or procedural-locomotion path. Presentation interpolation is serialized `false` and is never evidence.

## Frozen model evidence

The rig definition is a transcription of the repository's frozen `fly-brain-main/body/flybody/fruitfly.xml`; no trajectory was inspected to infer kinematics.

* Lines 92–190 define leg hinge axes and reference (`springref`) metadata. Extend hinges (coxa, femur, tibia, tarsus) use source local `(1,0,0)`, twist hinges (coxa yaw and femur roll) use `(0,1,0)`, and coxa abduct/roll uses `(0,0,1)`.
* Lines 460–704 define the six body trees, local body positions, local `w,x,y,z` quaternions, and joint element order. A coxa body declares abduct, twist, extend at one pivot; a femur body declares twist, extend; the tibia and tarsus bodies each declare extend. The Unity nested transform order preserves that XML order. The canonical replay's different array order is handled only by explicit name binding.
* A recorded MuJoCo hinge qpos is applied from the transform's captured zero-qpos reference rotation. `springref` is a passive-force reference and is therefore documented but is **not** subtracted from recorded qpos.

There are no unresolved axis, hierarchy, body-reference-orientation, or pivot-position mappings among the 42 exported hinges. Distal tarsus 2–5 hinges are not among the exported 42 and are intentionally not scientific transforms.

## Coordinate mathematics

Polar positions use the required basis map `B(x,y,z)=(x,z,y)` and `1 mm = 0.1 Unity unit`. Because `det(B)=-1`, hinge axes (axial vectors) transform as `det(B)B`, producing source x→Unity −x, source y→Unity −z, and source z→Unity −y. This avoids an invalid naïve axis/component swap.

Root MuJoCo quaternions are read as `w,x,y,z`, normalized, used to rotate source forward/up basis vectors, and those polar vectors are mapped through B. `Quaternion.LookRotation` reconstructs the unique proper Unity rotation. This is equivalent to the explicit basis conjugation while avoiding an invalid direct component permutation across a handedness reflection.

Each frame sets `referenceRotation * AngleAxis(recordedQpos, convertedAxis)`; rotations never accumulate. A direct seek is consequently frame-exact. Side-by-side offsets are added only after canonical coordinate conversion and never mutate replay arrays.

## Generated hierarchy and scene

For each LF/LM/LH/RF/RM/RH leg the scientific chain is `LegRoot → Coxa_roll(z) → Coxa_yaw(y) → Coxa(x) → Femur_roll(y) → Femur(x) → Tibia(x) → Tarsus1(x)`. Mesh and marker objects are presentation-only children. Body, eyes, wings, and segmented legs use Unity primitives whose automatically-created colliders are immediately removed.

`Fly Brain > M7F > Create Canonical Replay Scene` creates an unsaved scene with ReplaySystem (loader/controller/UI), two independently generated and strictly bound rigs, a collision-free visual reference ground, camera rig, directional light, condition labels, and persistent `CONTACT IDENTITY UNAVAILABLE` text. The user must review and explicitly save the scene; generation never writes replay evidence.

Camera modes expose orbit, follow, side, top, front, rear, and reset APIs; orbit uses right-drag and wheel zoom. The runtime UI retains play/pause/restart/frame-step/scrub, all requested speeds, enabled/disabled/side-by-side, interpolation (off by default), canonical navigation annotations, raw telemetry, contact unavailability, and provenance.

## Manual Unity review

1. Open the project in Unity 6000.3.10f1 and allow scripts/tests to compile.
2. Run EditMode tests in `M7FReplay.EditorTests`.
3. Choose **Fly Brain > M7F > Create Canonical Replay Scene**.
4. Confirm both generated rigs report **42 / 42 JOINTS BOUND** in the `M7FFlyRig` inspector/context workflow.
5. Review the unsaved hierarchy and presentation, then save it to a new scene path if accepted.
6. Enter Play mode; confirm interpolation starts off, both rigs remain synchronized, and the contact/provenance warnings remain visible.

The three protected Unity artifact copies (`m7f_manifest.json`, `m7f_enabled_replay.bin`, and `m7f_disabled_replay.bin`) are not generated or modified by this implementation.
