# LF source-route / target-attachment audit V1

Read-only source audit, 2026-10-25, baseline4702f8e (merged PR279). This inventories
attachment prerequisites after the accepted orientation assay. It does not create
muscle sites, establish anatomical homology, transplant coordinates, fit alignment,
select a path scale, apply forces or execute native/CNS transitions.

## Scope and decision rules

1. Verify the original source model/assets manifest and existing binding inspector.
   Retain the exact four selected tendon order, actuator attributes and route-node
   order. Resolve each route site uniquely in the source worldbody tree and its
   nearest containing body, not by string suffix or assumed endpoint role.
2. Record local site coordinates and body/mesh attributes literally. XML body
   ownership is not a compiled body/site ID or a functional/anatomical assignment.
   Keep unresolved compiled source IDs null; use recorded source/native IDs only
   where the existing authorities established them.
3. Inspect the exact target XML and original installed-input locks. Follow its
   actual mesh file/scale references, including negative scale/reflection. A
   stored LF-named mesh file need not be the active LF mesh. Never silently change
   the target asset or infer attachments from a matching body name.
4. Check the archived native orientation model's tendon count, compiled site-name
   inventory and exact Thorax/LFCoxa body identities. Runtime-created sensor sites
   are not muscle attachment authorities. Preserve the distinction between raw
   XML site inventory and compiled runtime sites.
5. Hash raw mesh assets and inspect binary-STL ordered vertices/facet count/bounds.
   The parser follows the [documented binary STL layout](https://www.loc.gov/preservation/digital/formats/fdd/fdd000505.shtml).
   Ordered-vertex hashes ignore header/normals/attributes but are not topology-
   independent shape hashes. Unequal hashes/counts do not prove non-homology or
   inability to register two surfaces. Do not fit a transform or adopt bounds as
   a correspondence. STL numeric coordinates do not establish physical units.
6. Inspect the existing coxa-yaw anatomical sign authority's landmark definition.
   Its named Femur body-origin displacement is a sign metric, not a validated
   muscle insertion landmark. Do not repurpose it as an attachment point.
7. Verification means the inventory and prior evidence reproduce, not that any
   target endpoint mapping is admitted. Per-site target correspondence, target
   coordinates, attachment transforms, length/velocity and force conversions
   remain null unless supported by an explicit authority. Original raw scientific
   prerequisites and all earlier failures stay unchanged.

## Reproducibility

Pinned source-extracts contain narrow data/hash records, not replacement models.
Normal replay uses those extracts, original installed-input/asset locks, binding
and source-pose authorities, and the saved native orientation evaluator. It
constructs no native model. Optional `--source-model` rechecks the entire original
source asset manifest and reparses the exact source XML/selected meshes. Target
XML/mesh extracts are rechecked against installed files. No dependency is added.

## Bounded next decision

If target attachment correspondence remains unresolved, do not transplant sites.
Predeclare a non-actuating **paired endpoint/body-frame observation**: resolve the
eight source site IDs and owner-body IDs in the locked compiled source; observe
their world positions and source Thorax/Coxa frames at the full existing15poses
and differences; independently reconstruct the two-point source path lengths and
derivatives against the old tendon-length/moment-arm record. Record native target
body/mesh frames at mapped poses, without assigning target muscle sites. Fixed
poses/epsilon/budgets must precede execution. No force application/integration/CNS.
This can establish a trustworthy geometric observer and expose frame/translation
differences; anatomical endpoint correspondence and physical unit/converter
lineage still require independent evidence before any target path/force coupling.
