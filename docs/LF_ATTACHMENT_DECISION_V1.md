# LF target-attachment registration decision V1

Read-only decision review, 2026-10-25; baseline3e842c2 (merged PR281). No new
simulation, alignment, target endpoint construction or muscle-force coupling.
Verification of this decision is separate from anatomical registration acceptance.

## Decision rules

Reverify the accepted V1.1 endpoint observer through its original preflight and
evaluator, preserving failed V1 and every original scientific raw lock. Use the
existing route/asset inventory and exact compiled source/target identities.

For any target endpoint correspondence, require an independent reference tying
the source endpoint's anatomical identity to the exact target geometry and a
declared coordinate frame/length convention. A citation, file path, same body
name, good source length reconstruction or matching rotational delta alone is
not that correspondence. Do not manufacture a transform from measured origins.

Inspect the following candidate arguments without implementing their transforms:
orientation-only registration, identical local-coordinate copy, body-origin/frame
alignment, surface/ICP fitting, LF/RF symmetry assumption and existing Femur-origin
sign landmark. A mathematically defined frame transform may exist while its
anatomical correspondence is unsupported; do not conflate those questions.

With no qualifying endpoint authority in the reviewed corpus, leave all eight
target sites/coordinates/transforms null. Record NO_REGISTRATION_AUTHORIZED and
produce a reference-request artifact, explicitly not an executable mapping.
New reference entries require a separately versioned scientific review; filling
strings or coordinates in this request never automatically authorizes a mapping.

## Research scope

`reference-review.json` records dated human/agent source-review notes and URLs,
not downloaded authoritative target annotations or an automatic literature proof.
It is pinned for offline replay. Primary references inspected:

- [Paper v2, A.2](https://arxiv.org/html/2509.06426v2#A2): the authors describe
  replacing original foreleg meshes with muscle-imaging meshes. That is context
  for their revised body; exact correspondence to our locked target is not
  established by this review.
- [Author project](https://gizemozd.github.io/fly_mimic/) and
  [author code](https://github.com/gizemozd/FlyMimic): source reconstruction/model
  context. Demonstrations are not locked-target attachment records.
- The linked [original muscle-development repository](https://github.com/gizemozd/neuromechfly-muscles)
  returned404 in this inspection. This is an access limit, not proof of global
  absence. No author contact or other messages were sent.

Local corpus: accepted endpoint raw data, route/mesh extracts and audit, unit/
conversion-lineage review, original anatomical crosswalk and coxa-yaw sign metric.
Their original validators are reused. No new anatomical reference or calibration
is inferred from numeric source/target origin differences or asset hashes.
The local untracked registration export was also inspected read-only. It records
source bodies/joints/tendon mechanics, not independently labeled target endpoints.
Its canonical content matches the original cited export hash, while raw bytes
differ; neither the historical hash nor a scientific raw prerequisite is changed.

## Required next input and stop condition

The generated `reference-request.json` lists exact source site/body IDs and current
source/target model/mesh locks, with missing target correspondence and required
provenance fields. Seek annotated attachments or independently labeled paired
landmarks tied to those assets, including specimen/laterality/reflection context,
frame/origin/units, provenance/revision and uncertainty. A future registration
protocol must fix its validation criteria before inspecting residuals/outcomes.

Until qualifying reference evidence is acquired, do not run more pose sweeps or
fit meshes as substitutes. Next work is reference acquisition/qualification, not
another observer campaign. Missing anatomy is not resolved by tuning movement.
Physical force units/converter lineage, individual neuronal binding, neural
activation and original raw scientific prerequisites remain separate gates.
Production remains20/42; no new Unity behavior or independent balance established.
