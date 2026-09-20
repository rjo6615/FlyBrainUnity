# M7F-VIS1C — authoritative FlyGym/MuJoCo kinematic cross-check

## Status and fail-closed conclusion

**Implementation complete; authoritative Windows execution pending.**  This Linux
checkout does not contain FlyGym or MuJoCo, so it cannot honestly publish numerical
MuJoCo errors or declare the Unity rig correct.  `--verify-mujoco` now fails closed
here and writes no cross-check result.  The one command in [Windows execution](#windows-execution)
will produce `m7f_mujoco_crosscheck.json` from MuJoCo 3.2.7.  Until that file reports
`status: COMPLETE`, the current VIS1B rig and its screenshots are **not validated**.

This is deliberate: no selection is made by comparing joint-name similarity, and
the incomplete `fly-brain-main/body/flybody/fruitfly.xml` is never passed to MuJoCo.

## Exact M7D physical-model provenance

The construction chain is:

1. `malecns_backend.embodiment.m7d_corrected_spontaneous.windows_preflight/run`
   enters `_windows_m7d_corrected_spontaneous_adapter._runtime`.
2. `_runtime` explicitly says it reproduces B4 and delegates to
   `m7c_b4_stability._make_sim`.
3. `_make_sim` calls `flygym.Fly` with `init_pose="tripod"`,
   `spawn_pos=(0, 0, 0.6045752232266313)`, Euler
   `spawn_orientation=(0, 0, 0)`, adhesion disabled, position control, and the
   ordered 36 tibia/tarsus contact placements.  It does **not** pass
   `xml_variant`.
4. The M7D execution boundary requires exactly FlyGym **1.2.1** and MuJoCo
   **3.2.7**.  In that installed FlyGym release, the `Fly` constructor's default
   `xml_variant` must be exactly `"seqik"`; the verifier checks the live signature
   rather than assuming it.
5. Therefore the selected installed source must be
   `flygym/data/mjcf/neuromechfly_seqik_kinorder_ypr.xml`.  The verifier requires
   that exact package resource, records its SHA-256 and absolute installed path,
   constructs the exact M7D simulation, and compiles the attached arena model's
   `to_xml_string()` plus `get_assets()` entirely in memory.  It never selects either the
   `deepfly3d` or `seqik...capsuletarsus` candidate.

This also establishes that the physical model is not simply a raw XML file loaded
by native MuJoCo.  FlyGym parses the selected MJCF through dm_control and adds the
requested position actuators/contact sensors before compilation.  The verifier
uses this assembled, arena-attached model, so those programmatic edits and the
root freejoint are included without
copying or changing installed resources.

### Model invariants enforced at run time

The verifier refuses to run unless all of the following hold:

* package versions are precisely FlyGym 1.2.1 and MuJoCo 3.2.7;
* the live `Fly` signature says the omitted `xml_variant` defaults to `seqik`;
* the exact installed seqik resource exists;
* the replay's 42 names equal the frozen order below;
* every name resolves once in the assembled native MuJoCo model and their qpos
  addresses are monotonically ordered;
* exactly one root freejoint exists and starts at `qpos[0]` (translation in
  `qpos[0:3]`, quaternion **wxyz** in `qpos[3:7]`); and
* all required `L{F,M,H}/R{F,M,H}` Coxa, Femur, Tibia, Tarsus1 and endpoint
  Tarsus2 bodies exist.

The exact controlled order is, independently for LF, LM, LH, RF, RM and RH:

`Coxa, Coxa_roll, Coxa_yaw, Femur, Femur_roll, Tibia, Tarsus1`, each prefixed by
`joint_<leg>`, for 42 total joints.  The compiled model supplies the authoritative
joint-to-body relation, local joint position/axis, body parent, local body pose,
limits, and within-body hinge order; none of those are inferred from the MaleCNS
file during verification.

The authoritative leg body chain queried from the compiled model is
`<leg>Coxa → <leg>Femur → <leg>Tibia → <leg>Tarsus1 → <leg>Tarsus2`.
The selected MJCF references the installed FlyGym STL geometry (including Thorax,
Head, wing, and per-leg segment STLs).  Mesh geometry is provenance/presentation
information only; it is not an acceptance criterion.

### Initialization and root handling

`init_pose="tripod"` is handled by FlyGym during simulation initialization in M7D;
the spawn position and Euler spawn orientation are likewise constructor inputs.
M7D then recorded the resulting root pose and 42 observed controlled joint
positions on every canonical frame.  VIS1C does not reset or step a simulation.
It assigns each selected frame's recorded root directly to the root freejoint and
each recorded joint value to its validated qpos address, then calls only
`mujoco.mj_forward`.

## MaleCNS XML versus the actual FlyGym model

The old MaleCNS XML is incomplete as a loadable model because its OBJ resources
are absent.  It remains readable as XML, so the Windows verifier compares its
kinematic fields against the **compiled assembled FlyGym model** for every one of
the 42 canonical mappings.  Each `malecns_comparison` row in
`m7f_mujoco_crosscheck.json` contains:

* joint name;
* parent and child body;
* within-body hinge order;
* joint local position and axis;
* body local position and quaternion;
* joint range; and
* one of `EXACT_MATCH`, `NUMERICALLY_EQUIVALENT`, `DIFFERENT`, or `MISSING` for
  every field.

The comparison necessarily covers the six leg attachment bodies because each
coxa row compares the compiled coxa local position/quaternion and its parent body
to the corresponding MaleCNS coxa attachment frame.  It is intentionally not
pre-populated with guessed results.  **All actual discrepancy classifications are
pending the authoritative Windows run.**  This is the required fail-closed result
when the installed model cannot be inspected in the current environment.

## Authoritative static forward kinematics

The verifier evaluates frames **0, 540, 541, 785, 1210, 1570, 2500, 3980, and
5000**.  For every frame it records the MuJoCo-derived root transform, all 42
`xanchor` world pivots and `xaxis` world axes, Coxa/Femur/Tibia/Tarsus1 `xpos` and
`xquat` transforms, and model-derived segment endpoints (the next body origin).
It compares these with the dependency-free VIS1B evaluator and reports per-frame
and overall maximum/RMS values for:

* pivot position error (model length units);
* axis angular error (radians);
* body position error (model length units);
* body orientation error (radians, quaternion sign invariant); and
* segment endpoint error (model length units).

Root position and orientation error are also emitted per frame.  The output
counters must read nine `mj_forward` calls and zero `mj_step`, physics-transition,
and neural-transition calls.  No `Simulation.step`, environment step, physics
step, brain step, trajectory generation, or inverse kinematics is used.

## Verifier repair

`tools/generate_m7f_kinematic_reference.py` now has two intentionally separated
paths:

* the dependency-free path remains byte-for-byte deterministic and preserves the
  checked-in VIS1B validation JSON;
* `--verify-mujoco` constructs M7D's installed FlyGym model, validates provenance
  and topology, uses native MuJoCo static FK, and writes the independent detailed
  result to `m7f_mujoco_crosscheck.json`.

The old attempt to load `fly-brain-main/body/flybody/fruitfly.xml` using
`MjModel.from_xml_path` has been removed.  No package asset is copied, no installed
file is modified, and no canonical replay artifact is written.

## Unity rig consequence and visual warning

The scientific Unity rig is **not changed in this commit**, because changing it
before obtaining the compiled FlyGym comparison would be another unsupported
model guess.  If any authoritative field is `DIFFERENT` or `MISSING`, or any FK
error exceeds the subsequently chosen numerical tolerance, the current rig must
be replaced from the emitted FlyGym definitions and its cylinders regenerated
from the emitted endpoints.  Existing Unity tests and the legacy JSON do not
override that requirement.

The reported scattered/detached magenta markers are therefore still an open
warning, not validation evidence.  The Windows numerical output will distinguish
physical-model/root-frame/scale/attachment errors.  Marker scale, overlap of two
conditions, and decorative anatomy registration remain presentation hypotheses;
the large decorative fly is never treated as scientific evidence.

## Windows execution

Run this **one exact command** from the repository root:

```powershell
.\fly-brain-interactive\.venv\Scripts\python.exe tools\generate_m7f_kinematic_reference.py --verify-mujoco --crosscheck-output m7f_mujoco_crosscheck.json
```

Expected output is two `wrote ...` lines.  The first identifies the installed
seqik MJCF and reports `mj_forward=9; mj_step=0`; the second reports `frames=9;
mj_step=0; physics transitions=0; MaleCNS updates=0`.  Any version, model default,
resource, joint order/mapping, root-freejoint, or body-hierarchy mismatch instead
raises an exception and does not write a completed cross-check.

## Files and tests

Changed files:

* `tools/generate_m7f_kinematic_reference.py` — exact FlyGym construction,
  provenance gates, native static FK, field comparison, and error report.
* `tests/test_m7f_kinematic_reference.py` — frozen provenance/order,
  classification, dependency-free determinism, and fail-closed tests.
* `M7F_VIS1C_MUJOCO_CROSSCHECK.md` — this report.

The checked-in canonical M7F replay binaries/manifest and existing validation JSON
are unchanged.  The commit hash is recorded by Git history for this report's
commit (a file cannot reliably contain the hash of the commit that contains
itself).

Tests actually run in the Codex environment:

* `python -m py_compile tools/generate_m7f_kinematic_reference.py` — passed;
* `python tools/generate_m7f_kinematic_reference.py --output /tmp/m7f_vis1c_reference.json`
  followed by `cmp` against the checked-in validation JSON — passed byte-for-byte;
* `PYTHONPATH=. pytest -q tests/test_m7f_kinematic_reference.py tests/test_m7d_corrected_spontaneous.py tests/test_m7c_b4_stability.py`
  — 15 passed, 2 skipped (the skips are the pre-existing unavailable live-runtime
  checks); and
* `git diff --check` — passed.

The authoritative Windows command has **not** been run in Codex and is not listed
as a passing test.

## Declarations

* M7D MODIFIED: **NO**
* M7D RERUN: **NO**
* M7E MODIFIED: **NO**
* M7E RERUN: **NO**
* M7F CANONICAL ARTIFACTS MODIFIED: **NO**
* M7F EXPORT RERUN: **NO**
* NEW SCIENTIFIC PHYSICS TRANSITIONS: **0**
* NEW NEURAL TRANSITIONS: **0**
* MJ_STEP CALLS: **0**
* UNITY PHYSICS DRIVES REPLAY: **NO**
* IK USED: **NO**
* VISUAL FITTING BY EYE: **NO**

**Next action:** run the authoritative Windows MuJoCo 3.2.7 static
forward-kinematics cross-check above, then use its field-level discrepancies and
error metrics—not screenshots—to decide and implement the Unity rig correction.
