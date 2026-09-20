# M7C-B3 analytic tripod support-height derivation

## Status, provenance, and hard boundary

The analytic, zero-transition Windows audit is implemented but **not executed
on this host**. The required FlyGym 1.2.1/MuJoCo 3.2.7 Windows environment is
not installed here. Consequently, the checked-in JSON fails closed: it does
not invent an analytic `dz`, corrected height, reconstructed contacts, or
future-physics eligibility. Its M7C-B2 source artifact SHA-256 is
`f3066cfab26fc00e2f1cf192b8cf9af89b06e8b0afca4df5603167ff730a72b1`;
the installed tripod pose SHA-256 recorded by B2 is
`8d71c1536c2a0fc55bfb574999eab5bff3568c3f38fe032a4b594a0bcb59a640`.

Run exactly this command on the validated Windows checkout:

```powershell
.\fly-brain-interactive\.venv\Scripts\python.exe -m malecns_backend.embodiment.m7c_b3_tripod_support_height --windows-audit
```

The runner contains no MaleCNS import. It uses a `StepForbidden` simulation
proxy, reset plus MuJoCo forward evaluation only, and never calls `sim.step()`.
It constructs the source tripod at `(0, 0, 0.5)` and at most one fresh
reconstruction at the single analytically selected height. It performs no
sweep, optimization, controller evaluation, stability tuning, or dynamics.

## Floor-contact geometry

FlyGym's floor-collision configuration permits all five tarsal collision
segments of every leg: `LFTarsus1` through `LFTarsus5`, `LMTarsus1` through
`LMTarsus5`, `LHTarsus1` through `LHTarsus5`, and the corresponding RF, RM,
and RH geoms (30 geoms total). This is consistent with the established B2
floor contacts on LFTarsus4 as well as tarsus-5 geoms. B2's treatment of
Tarsus1--4 as “proximal” was therefore unsuitable for the B3 support-height
derivation.

Forbidden floor-contact geometry is every other fly collision geom, including
body, head, thorax, abdomen, coxa, femur, tibia, wings, halteres, antennae, and
any other non-tarsal geom. The Windows runner computes transformed mesh-vertex
or analytic primitive minima for fly geometry even when collision masks are
zero, because FlyGym may arrange collisions with explicit MuJoCo contact
pairs. `geom_rbound` is not used as the support measurement.

## Exact analytic derivation

For source minimum world heights `z_i`, material tolerance `1e-6`, distal
penetration tolerance `1e-3`, and contact tolerance `1e-6`, the solver forms:

* `forbidden_required_dz = max(0, max_i(-1e-6 - z_i))` over forbidden geoms;
* `distal_penetration_required_dz = max(0, max_j(-1e-3 - z_j))` over all
  permitted tarsal support geoms;
* one contact interval `[-1e-6-z_j, +1e-6-z_j]` for each support geom,
  intersected with nonnegative `dz`;
* feasible intervals by intersecting each contact interval with both lower
  bounds above.

If the union is empty, the audit reports
`TRIPOD_SIMPLE_VERTICAL_TRANSLATION_INFEASIBLE` and does not reconstruct a
second simulation. Otherwise, it selects the smallest lower boundary in the
union, reports `TRIPOD_ANALYTIC_SUPPORT_HEIGHT_FOUND`, and uses
`spawn_z = 0.5 + dz`. This is exactly one deterministic analytic result, not a
stability choice.

## Reconstruction and reporting

The fresh reconstruction records the exact 42 observed tripod joint values
and requires exact array equality with the source reconstruction. It records
every MuJoCo contact, every measured fly collision-geometry minimum, finite
state, root position, the separated geometry gate, and future-physics
eligibility. Adhesion remains disabled and the inherited calibration surface
is constructed unchanged. The Windows result must separately report ground,
calibration-surface, and self contacts; a calibration contact is never silently
treated as floor support.

The established `LHCoxa`/`RHCoxa` penetration is approximately
`0.0008327005648158468` model units. Vertical translation cannot change it.
FlyGym's `self_collisions="legs"` intentionally enables leg self contacts for
MuJoCo constraint handling, but zero-transition geometry evidence cannot prove
that this initial contact resolves acceptably. The conservative classification
is therefore `SELF_COLLISION_REQUIRES_DYNAMICS_VALIDATION`, not catastrophic
invalidity and not validation. No collision mask or pose is changed.

## Eligibility correction

M7C-B2 now centralizes a fail-closed `candidate_eligible` decision. Eligibility
requires `geometry_gate.valid`, `VALID_SUPPORT_CONTACT`, and the negation of
`NO_SUPPORT_CONTACT`; the canonical stretch pose can no longer be marked
eligible without support. Regression tests cover that exact inconsistency.

## Immutable conclusions in this checkout

M7 MODIFIED: NO  
M7 RERUN: NO  
M6C RERUN: NO  
PHYSICS TRANSITIONS: 0  
NEURAL TRANSITIONS: 0  
TRIPOD JOINT POSE CHANGED: NO  
ADHESION CHANGED: NO  
CALIBRATION SURFACE CHANGED: NO  
M7C-B DYNAMICS EXECUTED: NO

**NEXT ACTION:** Run only the M7C-B3 Windows zero-transition analytic support audit.
