# LF target-attachment registration decision results

2026-10-25; fresh baseline3e842c2 (merged PR281). Static source/evidence review;
no new native model, simulation, alignment fit, force application or CNS run.

**ATTACHMENT_DECISION_VERIFIED_REFERENCE_REQUIRED**.
Decision: **no target endpoint registration authorized from the reviewed corpus**.
All eight target endpoint coordinates/transforms remain null; source observer
acceptance is preserved. This is a decision outcome, not a software-test failure.

## Evidence and scope

The original V1.1 evaluator still verifies all211paired observations. Source site
IDs4/11,8/15,6/13,7/14 and owners2/19 are fixed. Target bodies3/13 remain inventory
counterparts only. The active native LF mesh remains mirrored RFCoxa; no replacement
or source-coordinate transplant is made. Historical V1 setup failure is unchanged.

The [paper's A.2 methods](https://arxiv.org/html/2509.06426v2#A2) describe revising
foreleg meshes to match muscle-imaging data. That supports their source-model
context, not an independently established endpoint mapping to our exact target.
The dated review also checked the author project/code links and their inaccessible
original-muscle repository link. The reviewed references did not establish a
qualifying locked-target endpoint authority. This is not proof of global absence.

The local untracked registration export was inspected read-only. Its raw hash is
`a4e9b492c4c4acbfde2dad288d98df675d49b6ef0608d198003b69c2cdcbe893`;
canonical content matches the old cited export hash
`64c31caefeaaf38f2b5e22f69122062ac384c1d756bd16d0cce532d776995597`.
It records source reference mechanics, not independent target endpoint pairs.
Canonical correspondence does not satisfy or refresh an original scientific raw
lock. The external file and all historical source/evidence hashes remain untouched.

## Candidate arguments assessed without fitting

| Candidate | Current decision |
|---|---|
| Orientation agreement | Supports rotation convention, not endpoint locations |
| Copy source local positions | Target anatomical correspondence missing |
| Align body origins/frames | Mathematical transform can exist; anatomical meaning not established |
| Surface/ICP fit | No fit performed; independent labeled validation authority missing |
| Assume LF/RF mirror correspondence | Asset reflection does not establish fiber/attachment correspondence |
| Reuse Femur-origin sign landmark | Sign metric does not define a muscle insertion |

All six remain unauthorized by this review. No transform or target coordinate
was computed. New reference entries require a separately versioned scientific
review; citation strings or a filled request do not automatically admit a mapping.

## Concrete required input

`evidence/lf-attachment-decision-v1/run/reference-request.json` is a **reference
request, not an executable mapping**. It records source/target XML and compiled
identity locks, active mesh hashes/reflection, exact eight source endpoint IDs and
the missing fields. Required evidence includes annotated attachments or labeled
anatomical correspondences tied to those assets, provenance/revision, frame/origin/
length conventions, laterality/reflection context and uncertainty. A new validation
plan must precede registration residual/outcome inspection.

Next acquire and qualify those reference artifacts through authoritative published
data/model-development sources. Do not repeat pose sweeps or tune an alignment as
a substitute for missing anatomical correspondence. If qualification cannot find
the needed artifact, report the specific access/evidence blocker and request that
input instead of producing another observer-only campaign. No messages to authors
or others were sent or authorized by this review.

## Actual checks and roadmap

- Final58tests passed67.17s:18decision/request,20route-attachment and20V1.1endpoint
  tests. The real saved reconstruction runs with native construction/kinematics/
  forward/step/muscle dynamics, solver and live-audit entry points made fatal.
- Earlier57passed67.01s before adding the source-export provenance check. No
  native experiment, dependency/environment change, gain/seed/threshold change,
  or target registration occurred.
- Tamper tests reject target coordinates, transforms, admission flags, changed
  source IDs, fabricated reference-authority flags, changed review snapshots and
  removal of the historical failed-V1 raw lock.
- Windows Git Bash saved replay, staged whitespace check and LFS-pointer checks
  passed. No native measurements were rerun.

Current20/42,newadmissions0. The milestone remains a trustworthy LF muscle-force
interface. Target attachment references are now a specific evidence requirement;
physical unit/converter lineage, individual neuronal binding, activation conversion,
nonzero-velocity physiology and original raw scientific prerequisites remain
separate gates. Source geometry verification is not biological calibration,
independent balance or gait. No new Unity behavior is introduced.

## Windows Git Bash after merging

This verifies saved evidence and both decision/request artifacts; no native calls.

```bash
cd ~/Documents/FlyBrainUnity &&
git switch newBrain &&
git pull --no-rebase --no-edit &&
git lfs pull --include="malecns_backend/embodiment/interface_output/integrated_whole_leg_readiness.json,docs/evidence/lf-anatomical-crosswalk-v1/annotations.feather,docs/evidence/lf-pose-force-v1*/run/validation.json,docs/evidence/lf-activation-transient-v1/run/validation.json,docs/evidence/lf-activation-integrator-v1/run/validation.json,docs/evidence/lf-native-isolation-v1*/run/validation.json,docs/evidence/lf-synthetic-coupling-v*/run/validation.json,docs/evidence/lf-target-orientation-v1/run/validation.json,docs/evidence/lf-endpoint-frames-v1*/run/validation.json" &&
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" &&
"$PY" -m malecns_backend.embodiment.lf_attachment_decision \
  --report docs/evidence/lf-attachment-decision-v1/run/decision.json
```

Expected: `ATTACHMENT DECISION VERIFIED`, `REFERENCE_REQUIRED`,0/8supported target
correspondences, registration NOT AUTHORIZED,20/42,0new admissions. The negative
registration decision is intentional. Original raw prerequisites recorded/current
remain false at this checkpoint; no waiver. Unity can remain closed.
