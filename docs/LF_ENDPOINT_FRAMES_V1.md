# Paired LF endpoint/body-frame observation V1

Prospective protocol, 2026-10-25; baseline a734b56 (merged PR280). Commit this
protocol, runner and tests before ONE archived campaign. Preserve every outcome;
no retry, changed poses/epsilon/budgets, fitted alignment or target-site transplant.
No force application, activation solve, physics integration or CNS initialization.

## Inputs and exact ownership

Reuse the route/attachment audit, original source XML/full71-asset manifest,
binding inspector, source pose evaluator and native orientation authority. Original
scientific raw prerequisites remain false; this independent geometric observer
does not waive them. Require validated installed package/file locks unchanged.

Compile one original source model under MuJoCo3.2.7. Resolve all eight ordered
source site IDs by exact compiled names, with site_bodyid matching the source XML
owner (Thorax/LFCoxa). Validate compiled local coordinates against literal source
positions. Require each selected tendon has exactly the two declared SITE wraps
in order; native tendon/actuator/joint/DOF/activation indices match the accepted
source record. Preserve all model parameters. Source LFCoxa remains body19;
resolve Thorax/site IDs instead of inferring them from document ordering.

Construct one target with the existing locked native factory and verify complete
baseline identity/inventory/frames against native orientation. Resolve the exact
Thorax/Coxa mesh geoms and mesh IDs from the audit and compiled tables; target
active LFCoxa remains the mirrored RFCoxa asset. Do not substitute installed LF
meshes. Record body/geom/mesh arrays and names bound to full model identities.

## Whole fixed observation schedule

Reuse all15source offsets and existing +/-1e-6rad source-coordinate differences.
Source data: old full14-value reference qpos, replacing only source qpos0/1/2 by
the prescribed base or perturbation. All qvel/act/ctrl/applied buffers/time zero.
Call only mj_kinematics; obtain eight site world positions and Thorax/Coxa body
and compiled mesh-geom frames. No tendon/force pipeline is executed.

For each of these105source observations, observe fresh target data at the original
modeled q_G from that same old source sample (BASE or CHAIN minus/plus). Keep
every unselected target coordinate at native initialization, as in orientation.
Target states zero velocity/activation/control/applied buffers/time. Add one
target zero-LF reference. Record target body/compiled geom frames, with NO target
muscle sites or endpoints. Exactly105source+106target=**211 explicit kinematics**.
Initializer only: expected7forwards/3resets; zero probe forward/reset and all six
integration entry points forbidden through the existing accounting authority.
Compiler-internal operations are not explicit Python API calls.

MuJoCo may center/align meshes during compilation. Record compiled geom frames
as such, not as unmodified STL frames; include mesh_pos/quat/scale and geom local
pose tables. Do not derive a source-to-target transform from these observations.

## Prespecified integrity and engineering budgets

Require complete ordered15x7paired samples plus target reference, exact full state
before/after, finite proper rotations, unchanged source/target model identities,
source/assets/installed hashes, all time/velocity/control/activation/applied buffers
zero and exact211kinematics accounting. Source metadata and wrap/site/owner/mesh
tables must agree with compiled identities; target identity/addresses unchanged.
Record both selected source/target joint-limit checks at every sample. No clipping
or pose replacement; outside-range measurements yield a separate blocked result.

Reuse prior engineering budgets:1e-10 for world/local position reconstruction,
source lengths and archived source/target orientation;1e-7 for source length
derivatives. No budget is an anatomical/biological calibration tolerance.

- Reconstruct each source endpoint: body_xpos + body_xmat * compiled site_pos.
  Maximum difference from native site_xpos <=1e-10 source-length units.
- Four Euclidean two-endpoint distances reproduce old native source tendon
  lengths at all105source samples within1e-10.
- At each15base poses, negative centered length derivatives reproduce the old
  four source moment-arm columns within1e-7 source-length/rad.
- Source co xa orientations reproduce old saved source rotations; target co xa
  and Thorax orientations reproduce old orientation BASE/CHAIN/reference samples,
  within1e-10. This does not compare source/target positions as physical equality.
- Compiled geom world frames reproduce owning body frame plus compiled geom
  local pose within1e-10. Mesh preprocessing offsets/scales remain descriptive.

Record source and target thorax-relative coxa origins separately. No positional
match, source-target length scale, target path derivative or endpoint homology is
asserted. All velocities remain zero: this validates length gradients, NOT a
nonzero-velocity muscle law or source-target velocity transfer.

Incomplete/altered evidence: ENDPOINT_FRAME_INTEGRITY_FAILURE. Intact outside-range
samples: ENDPOINT_FRAME_OUTSIDE_LIMITS_TRANSFER_BLOCKED. Intact/in-range numerical
disagreement: ENDPOINT_FRAME_DISAGREEMENT_TRANSFER_BLOCKED. Only intact/in-range
and all numerical checks pass: ENDPOINT_FRAME_OBSERVER_VERIFIED_TRANSFER_BLOCKED.
Saved verification must reconstruct any intact outcome, including negative ones.

## Limits and next decision

Production remains20/42,new admissions0. This is a source geometric observer and
paired frame context, not target attachment registration or a moving-fly test.
Independent attachment/landmark correspondence, physical unit/converter lineage,
neural activation and original raw scientific gates remain. Next decide what
independent target attachment registration evidence the paired frames support;
retain null target endpoints unless an explicit authority justifies them.
