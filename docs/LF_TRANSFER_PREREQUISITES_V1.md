# LF source-to-body transfer prerequisite review V1

This is a read-only evidence inventory, not a new physical experiment or an
admission protocol. Scope and decision rules are fixed before generating its
saved review. Reuse the existing static identity authority, source-binding
record and V2 saved-report evaluator. Do not instantiate a model, advance physics,
integrate activation, initialize CNS, or connect a production actuator.

## Question and rules

What supports transferring the four single-class LF tendon hypotheses into the
native body, and what evidence is still needed? Keep all five populations and
seven tendon hypotheses in the anatomical review, including unresolved promotors.

1. Verify historical software evidence using its original locks/evaluator. V2
   acceptance establishes only the declared synthetic constant-coefficient test.
2. Compare exact selected source parameters with the existing binding authority.
   Positive explicit `gainprm[2]` overrides the default automatic force scale;
   never substitute the default `force=-1` interpretation for these four muscles.
3. Inventory units without assigning a conversion. Gravity and mesh scale are
   clues, not a complete length/mass/time convention. An observation divided by
   1000 is not an established actuator-force conversion. Unresolved conversion
   fields stay null, rather than becoming unity by default.
4. Separate the modeled finite-angle rotation map and source finite differences
   from actual anatomical attachment/length/velocity registration on the target.
   Frozen reference-pose gains/biases are not a moving-muscle force law.
5. Keep exact body IDs/dense indices, null individual tendon assignments, missing
   neural conversion and original failed raw prerequisites explicit. Canonical
   content correspondence does not satisfy an original raw scientific lock.
6. A review verifies only if source locks, original checks and reconstructed
   report agree. Verification may succeed while transfer remains blocked. No
   number of verified software checks substitutes for missing scientific evidence.

## Source context and reproducibility

`source-context.json` is a narrow XML/code snapshot from this local inspection.
It records the original XML raw hash already used by the binding authority and
the complete raw hashes of two inspected source files. It does not vendor the
model, certify upstream conversion lineage, or assert the current external clone
is unchanged. Normal saved review uses this pinned snapshot, with no network or
external clone dependency. Optional `--source-model` verifies the exact original
XML and selected attributes again, without compilation or mesh loading. The
FlyGym simulation source hash is checked against the existing native input lock.

Primary interpretive sources, inspected 2026-10-25:

- [MuJoCo 3.2.7 units](https://mujoco.readthedocs.io/en/3.2.7/overview.html#units-are-unspecified):
  base units are user chosen; force and torque require consistent derived units.
- [MuJoCo 3.2.7 muscle model](https://mujoco.readthedocs.io/en/3.2.7/modeling.html#muscle-actuators):
  explicit peak force differs from automatic inertial scaling; force depends on
  normalized muscle length, velocity and activation.
- [FlyMimic paper V2, section 6](https://arxiv.org/html/2509.06426v2#S6):
  maximum isometric force and contraction velocity were estimated/optimized, not
  directly measured. These are model assumptions, not MaleCNS calibration.
- [Author repository](https://github.com/gizemozd/FlyMimic): conversion from
  OpenSim through MyoConverter is described. The linked
  `gizemozd/neuromechfly-muscles` repository was inaccessible during this review;
  this limits this inspection and does not prove the source is absent.

## Bounded next decision

Next: a source-unit and parameter-conversion lineage audit. Locate the original
OpenSim model, converter revision/configuration and any post-conversion edits
corresponding to the exact locked XML. Build a dimensional ledger for length,
mass, time, inertia, force, moment arm and torque on both source and target.
Trace the four explicit peak forces, length ranges and activation constants.
Record missing lineage rather than assigning a conversion or tuning behavior.
This can establish a declared modeled transfer without claiming measured biology;
it cannot resolve anatomy/neural conversion or waive original raw prerequisites.

Only after that decision should a separately specified length/velocity and
finite-angle target-registration assay be considered. No moving-fly coupling or
new Unity behavior is authorized by this review.
