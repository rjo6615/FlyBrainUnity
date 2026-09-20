# M7C-B Windows physics-only initial-support calibration

## Boundary and current status

M7 remains immutable. This is a new engineering calibration, not an M7 rerun
and not a walking or locomotion test. The implementation imports no MaleCNS
runtime, constructs no brain, changes no neural parameter/decoder/sensory
model, and adds no gait, balance, reference, reward, RL, or AI controller.
Adhesion remains disabled and the inherited calibration surface remains at its
canonical world pose. **Neither candidate has been executed.**

The validated Windows facts currently available are FlyGym 1.2.1, MuJoCo
3.2.7, the reported installed module path, the Fly constructor signature, and
11/11 passing predecessor tests. The constructor defaults establish that
`spawn_pos=(0,0,0.5)` and `init_pose="stretch"` are FlyGym defaults; they are
not described as accidental project settings.

## Installed FlyGym 1.2.1 source inspection

Codex cannot access the user's Windows virtual environment, and this container
has neither FlyGym nor MuJoCo. The new `--inspect-flygym` mode therefore walks
the *installed Windows 1.2.1 package*, hashes and lists pose resources, records
the exact `stretch` source/resource lines, constructor signature, named pose
resources, and source evidence concerning standing, walking/locomotion,
`spawn_pos`, settling, adhesion, inverse kinematics, and supported-pose helper
APIs. It performs no simulation.

The zero-transition `--windows-preflight` embeds the same inventory in its
report. Until that command supplies installed-source evidence, the answers to
whether 1.2.1 has a standing preset/helper, whether examples use another pose
or spawn height, settle, enable adhesion, or use inverse kinematics remain
explicitly **not established from the installed distribution**. We do not use
newer-version assumptions. If preflight finds an explicit standing pose or
supported-pose helper, it fails closed before physics and requires review of a
Candidate C amendment. Candidate C is not invented merely to fill a slot.

## Geometry correction and final two-candidate freeze

Schema 1 computed a putative lower support bound as `center_z -
max(geom_size)`. For these mesh AABB half-extents that expression is not
rotation invariant. It can place a rotated mesh through the plane and therefore
is not the requested nonpenetrating support geometry. That candidate was never
executed. Schema 2 prominently records the obsolete schema/hash and correction
rather than silently modifying it.

For an AABB with half-extents `(a,b,c)`, the enclosing-sphere radius is
`sqrt(a²+b²+c²)`. This is rotation invariant and matches MuJoCo's mesh
`geom_rbound`; the preflight independently compares the frozen translation to
the six live `model.geom_rbound` values. From the immutable M7C-A zero-step
centers and extents, the minimum `Tarsus5 center_z - enclosing_radius` is
`1.4035507742524747`. Ground is at z=0, so the one frozen translation is
`-1.4035507742524747` and its root z is `-0.9035507742524747`.

The complete final set currently contains two candidates:

1. **`canonical_control`** — `init_pose="stretch"`, spawn position
   `(0,0,0.5)`, orientation `(0,0,0)`: no differences from canonical M7.
2. **`distal_tarsus_support_translation`** — the same pose, orientation,
   controller, surface, and adhesion configuration; only `spawn_pos.z` changes
   to `-0.9035507742524747`. This is one preregistered geometry derivation, not
   a sweep, optimization, or outcome-adaptive choice.

## Windows preflight

Preflight loads and exactly reconstructs the tracked preregistration, validates
the audit and candidate hashes, requires FlyGym exactly 1.2.1, records MuJoCo's
version and installed-source inventory, and creates a fresh model for each
candidate. It calls initialization/reset/forward only. It checks finite state,
live mesh bounds, candidate identity, body penetration, the fixed calibration
surface, disabled adhesion, absent controllers, and the exact 0.0001 s / 100 ms
/ 1000-transition plan. It calls `sim.step()` zero times, constructs zero
brains, and executes zero neural and zero physics transitions.

```powershell
.\fly-brain-interactive\.venv\Scripts\python.exe -m malecns_backend.embodiment.m7c_initial_support --windows-preflight
```

A pass ends with:

> M7C-B WINDOWS PREFLIGHT PASS — CANDIDATES FROZEN — ZERO PHYSICS TRANSITIONS — ZERO NEURAL TRANSITIONS — ENGINEERING RUN NOT EXECUTED

For a source-only inventory before preflight, use:

```powershell
.\fly-brain-interactive\.venv\Scripts\python.exe -m malecns_backend.embodiment.m7c_initial_support --inspect-flygym
```

## Physics-only runner (do not run yet)

`--run-windows` refuses to start unless the tracked preregistration matches
byte provenance and a passing zero-transition preflight matches its hash. Every
candidate gets a fresh FlyGym/MuJoCo simulation. Its measured reset joints are
held by baseline position control for exactly 1000 transitions at 0.1 ms (100
ms total), with a constant zero adhesion action. Compact output contains the
initial, 13 ms, and 100 ms states; fall/rollover first times; height/body-up
extrema; displacement; contact/support and initial self-contact evolution; and
finite-state validation.

**DO NOT RUN YET:**

```powershell
.\fly-brain-interactive\.venv\Scripts\python.exe -m malecns_backend.embodiment.m7c_initial_support --run-windows
```

M7 CANONICAL RESULT MODIFIED: NO
M7 SCIENTIFIC RERUN: NO
M6C RERUN: NO
MALECNS BRAIN CONSTRUCTED: NO
NEURAL TRANSITIONS EXECUTED: 0
NEURAL PARAMETERS CHANGED: NO
MOTOR DECODER CHANGED: NO
SENSORY MODEL CHANGED: NO
GAIT CONTROLLER ADDED: NO
BALANCE CONTROLLER ADDED: NO
ADHESION CONFIGURATION CHANGED: NO
CALIBRATION SURFACE CONFIGURATION CHANGED: NO
CANONICAL RAW MODIFIED: NO
M7C-B PHYSICS EXPERIMENT EXECUTED: NO
NEXT ACTION: RUN WINDOWS PREFLIGHT ONLY
