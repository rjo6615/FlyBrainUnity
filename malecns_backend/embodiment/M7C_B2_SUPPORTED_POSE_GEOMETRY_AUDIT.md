# M7C-B2 supported initial-pose geometry audit

## Status and boundary

**Prepared, not executed.** This checkout is not the validated Windows FlyGym
1.2.1/MuJoCo environment. No M7 or M6C evidence was changed or rerun, no
MaleCNS object was imported or constructed, and no neural or physics transition
occurred. In particular, the old M7C-B `--run-windows` mode was not invoked.
The checked-in JSON is deliberately explicit about unavailable measurements
rather than presenting Linux reconstruction or invented values as Windows
facts.

Run only:

```powershell
.\fly-brain-interactive\.venv\Scripts\python.exe -m malecns_backend.embodiment.m7c_b2_pose_geometry_audit --windows-audit
```

The runner wraps each fresh simulation in `StepForbidden`: any call to
`sim.step()` raises. `reset()` plus MuJoCo forward evaluation initializes and
inspects geometry but does not advance simulation time.

## Installed FlyGym 1.2.1 pose provenance

The frozen M7C-B Windows preflight established FlyGym 1.2.1, MuJoCo 3.2.7 and
these installed package resources:

| pose/source | installed relative path | SHA-256 |
|---|---|---|
| stretch | `data/pose/pose_stretch.yaml` | `99207214c9b98a376deefb960546f3030e37fc22788e83e5be23e8c4024dff1a` |
| tripod | `data/pose/pose_tripod.yaml` | `8d71c1536c2a0fc55bfb574999eab5bff3568c3f38fe032a4b594a0bcb59a640` |
| zero | `data/pose/pose_zero.yaml` | `339b4ca89a5c727872505812c55ccc5411d858ee2b40aa466aeb5c18018093b2` |
| KinematicPose source | `state/kinematic_pose.py` | `40d275c91bd2f32cfd792ac934100ba6ad457d31cf901069832e79d967879fec` |

The exact YAML joint mappings, comments/provenance, and installed-example
mentions are intentionally collected by the Windows audit from those hashed
files. They are currently `null` in the artifact because the package is absent
on this host. This avoids treating online or newer FlyGym source as
authoritative. The static `tripod` resource is audited as KinematicPose data;
loading it neither creates a gait phase engine nor supplies forces, adhesion,
reference motion, feedback, or dynamic locomotion assistance. Its origin in a
walking snapshot is not evidence that it stands unsupported.

## Zero-transition audits

Three fresh simulations are fixed in advance:

1. `stretch`, explicit canonical `spawn_pos=(0, 0, 0.5)`;
2. `tripod`, FlyGym 1.2.1's unmodified constructor-default spawn position;
3. `zero`, FlyGym 1.2.1's unmodified constructor-default spawn position.

For each, the Windows audit records root position/quaternion, all qpos/qvel,
all 42 observed controlled joint positions, every collision-enabled fly geom's
minimum height, all contacts and penetration depths, and the full separated
gate result. Mesh minima use transformed mesh vertices. Primitive minima use
analytic support functions. `geom_rbound` is retained for reporting but is not
mistaken for usable standing contact. Usable distal support means an actual
collision-enabled Tarsus5 geom/contact pair.

### Established stretch finding

At canonical height, the prior conservative Tarsus5 lower bounds were LF
1.8254, LM 1.4191, LH 1.40355, RF 1.8254, RM 1.4191, RH 1.40355, with no distal
support and the known LHCoxa/RHCoxa self-contact. The previous translation
`-1.4035507742524747` (spawn z `-0.9035507742524747`) is **rejected**: its
zero-step contacts show material coxa/femur/tibia ground penetration. It must
not enter dynamics.

Tripod and zero geometry, calibration-surface interactions, self contacts and
eligibility remain unreported until the command above runs. This fail-closed
state is not a claim that either pose is valid or invalid.

## Corrected geometry gate

The gate reports, separately:

- `VALID_SUPPORT_CONTACT`
- `NO_SUPPORT_CONTACT`
- `BODY_GROUND_PENETRATION`
- `PROXIMAL_LEG_GROUND_PENETRATION`
- `EXCESSIVE_DISTAL_PENETRATION`
- `SELF_COLLISION_PRESENT`
- `CALIBRATION_SURFACE_CONTACT`
- `MIXED_SUPPORT_SURFACES`

Material body, coxa, femur, tibia, or Tarsus1--4 penetration below `-1e-6`
model length fails. Tarsus5 contact is separately reported; penetration beyond
`-1e-3` fails. The latter narrow tolerance permits a solver contact shell at
initialization, not arbitrary embedding. Nonfinite state, changed calibration
geometry, mixed support surfaces, absent support, and excessive distal
penetration all fail closed. Self-collision is always exposed; candidate
eligibility additionally requires Windows review for whether it is
catastrophic.

The inherited calibration box remains at position
`(-0.05264855858702331, 2.2303476629745846, 1.4171913587929754)` with half-size
`(0.025, 0.025, 0.002)`. Exact equality is checked after model construction.
It is never removed or moved.

## Analytic height rule

Only a pose with sensible geometry and no default distal support receives one
calculation: `dz = -min(actual Tarsus5 mesh-vertex z)`. There is no sweep,
optimizer, survival objective, or adaptive candidate generation. The same
translation is applied analytically to every non-distal minimum. If any body,
coxa, femur, tibia, or Tarsus1--4 minimum would fall below `-1e-6`, the pose is
classified `GEOMETRICALLY_INCOMPATIBLE_WITH_SIMPLE_VERTICAL_TRANSLATION` and no
alternative adjustment is invented.

## Immutable conclusions for this preparation

M7 MODIFIED: NO
M7 RERUN: NO
M6C RERUN: NO
MALECNS BRAIN CONSTRUCTED: NO
NEURAL TRANSITIONS: 0
PHYSICS TRANSITIONS: 0
GAIT/BALANCE CONTROLLER: NONE
ADHESION CHANGED: NO
CALIBRATION SURFACE CHANGED: NO
M7C-B DYNAMICS EXECUTED: NO

**NEXT ACTION:** Run the M7C-B2 zero-transition Windows pose-geometry audit only.
