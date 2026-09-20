# M7F-VIS1B exact kinematic visual audit

## Finding

The transform-only 42-DOF hierarchy was kinematically well ordered, but its
visible scientific geometry was not a representation of that hierarchy.  The
builder created hand-sized cylinders with guessed rotations and made every
`*_DistalReference` equal to its proximal pivot.  Thus addressing tests passed
while every scientific segment endpoint was wrong.

The repaired hierarchy is, independently for LF/LM/LH/RF/RM/RH:

`thorax -> leg attachment/body quaternion -> abduct(z) -> twist(y) -> extend(x)
-> femur body quaternion -> twist(y) -> extend(x) -> tibia body quaternion
-> extend(x) -> tarsus1 body quaternion -> extend(x)`.

MJCF `body pos` is installed as a translation in the parent body frame, and
`body quat` is installed before that body's ordered hinge transforms.  Hinge
axes are axial vectors; the reflection `(x,y,z)->(x,z,y)` therefore uses
`-B axis`.  Recorded qpos is always applied from captured rest rotations, never
accumulated.  This audit found no world-as-local, double-quaternion, root
attachment, canonical-order, or qpos accumulation defect in the invisible
transform hierarchy.

## Numerical result

The old distal-reference endpoint error at frame 0 was exactly the segment
length: LF 0.004370/0.006970/0.005103/0.002356, LM
0.002810/0.008300/0.006682/0.003423, LH
0.002447/0.007790/0.007152/0.003372, RF
0.004360/0.006980/0.005153/0.002278, RM
0.002820/0.008400/0.006652/0.003392, and RH
0.002442/0.007700/0.007212/0.003383 Unity units (coxa/femur/tibia/tarsus1).
The repaired endpoints and next-body pivots are the same transform point, so
their construction error is 0 (test tolerance `1e-6` Unity units) at frames
0, 540, 541, 785, 1210, 1570, 2500, 3980, and 5000.  Positions are compared at
`1e-6`; Unity quaternion/basis tests use `1e-5` degrees/vector units.

The checked-in JSON contains 24 body records and 42 joint pivot/axis records
for each selected frame, in frozen MJCF model/world coordinates.  It records
the root, body orientation, endpoint, parent, pivot, and world joint axis.

## Evaluation boundary and reproduction

The artifact in this commit was produced by direct, deterministic evaluation
of the MJCF transform tree.  It called neither MuJoCo nor FlyGym:
`mj_forward=0`, `mj_step=0`, physics transitions=0, MaleCNS updates=0.

Dependency-free Windows generation:

```powershell
py -3 tools\generate_m7f_kinematic_reference.py
```

Optional MuJoCo static-forward evaluation (once `mujoco` is
installed) is:

```powershell
py -3 tools\generate_m7f_kinematic_reference.py --verify-mujoco
```

That option assigns recorded qpos and calls `mj_forward` nine times.  It never
calls `mj_step`; it does not write canonical replay artifacts.

## Unity verification

1. Open `FlyBrainUnity` in the Unity version in `ProjectVersion.txt`.
2. Run Edit Mode tests (`Window > General > Test Runner > EditMode > Run All`).
3. Select `Fly Brain > M7F > Create Canonical Replay Scene`.
4. Confirm each scientific coxa/femur/tibia/tarsus cylinder joins the next
   pivot at frame 0 and after seeking each selected frame.
5. Joint markers remain present but inactive by default. Enable individual
   marker GameObjects only for debug; each has local position zero at its
   owning validated pivot.

The decorative `PresentationAnatomy` remains explicitly non-scientific.  The
scientific cylinders are generated only between frozen-model reference points;
there is no IK, controller, Unity physics, or fitting by eye.
