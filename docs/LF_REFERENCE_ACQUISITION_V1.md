# LF attachment reference acquisition V1

Checkpoint: 2026-10-25. Baseline: `origin/newBrain` at `1f42b02`, after
PR #282. This is a bounded reference-access and qualification report, not a
physics experiment, anatomical registration or new acceptance protocol.

## Question and qualification boundary

Can the public publication/code/data links supply independently labeled
attachment or anatomical-landmark correspondences for the exact source and
target assets identified in
`evidence/lf-attachment-decision-v1/run/reference-request.json`?
That existing request is the qualification boundary. A usable artifact must
identify its model/mesh revisions, point labels and carrier bodies, coordinate
frames, length units, laterality/reflection, provenance and uncertainty. A
source-only muscle model, raw image volume or another rig's configuration is
not by itself a correspondence to the locked target. New material requires a
separate scientific review; no citation or filled coordinate auto-admits a motor.

## Acquisition findings

The [author project page](https://gizemozd.github.io/fly_mimic/) links to
[FlyMimic](https://github.com/gizemozd/FlyMimic). GitHub repository metadata and
the main root listing were accessible. This identifies a source-code route,
not new target anatomical annotations. The original model-development link,
[neuromechfly-muscles](https://github.com/gizemozd/neuromechfly-muscles), returned
GitHub API **404** on this inspection. This does not distinguish private,
renamed, removed or otherwise unavailable content, and proves no global absence.

The [versioned paper, sections 3.1 and A.2](https://arxiv.org/html/2509.06426v2)
describes multiple imaging datasets and replacement of the original foreleg
meshes. Following its data references produced these bounded access results:

| Reference route | Observed access | Qualification result |
|---|---|---|
| [Kuan et al. original publication](https://www.nature.com/articles/s41593-020-0704-9), data availability | Accessible; links raw XNH data in BossDB, WebKnossos and ESRF | Imaging provenance lead; no exact locked-target attachment pairing acquired |
| [BossDB project](https://bossdb.org/project/kuan_phelps2020) | Browser extraction returned a JavaScript-required page | Volume/annotation contents not inspected or qualified |
| [WebKnossos leg dataset](https://wklink.org/8452) | Browsing tool could not access URL | Access unresolved; not a finding that annotations are absent |
| [ESRF public data portal](https://data.esrf.fr/public/10.15151/ESRF-DC-217728238) | Browsing extraction returned no readable content | Contents not inspected or qualified |
| [Dinges et al. original publication](https://onlinelibrary.wiley.com/doi/10.1002/cne.24987), data availability | Accessible; identifies a Sciebo share | Dataset lead; paper context is not exact target registration |
| [Sciebo share](https://uni-koeln.sciebo.de/s/zxPiRV0CjRd6GKq) | Browsing tool could not access URL | Contents not inspected or qualified |

No scan volumes or new annotation/model-development artifacts were acquired.
These tool-access limits do not establish that a human browser cannot open the
shares. Bulk raw imaging would still require segmentation and an independently
supported bridge to the exact target assets; downloading images alone does not
resolve that bridge. No authors or third parties were contacted.

## Repository contents checked after the user's pointer

The complete public recursive Git tree at
`9ea1131626cd76f7203b74076ef8f0e9cab30bef` contains 119 blobs and reports
`truncated=false`; its metadata is preserved in
`evidence/lf-reference-acquisition-v1/flymimic-tree.json`. The existing local clone
has the same HEAD. Its two untracked registration exports were left untouched.
The tree includes OpenSim models, converted MJCF, mesh STL files/archive and the
conversion PDF; no independently labeled source-to-target correspondence bundle
was identified in that tree. This scope is one exact main revision, not every
historical commit, private repository or file in the world.

The user was right that attachment information exists in this repository:
both existing OpenSim files contain 37 `PathPoint` entries, with named source
paths. These are **source-model attachment annotations**. They do not identify
corresponding attachment locations on our exact locked target meshes. That is
the remaining distinction; we do not need another copy of the same source sites.
Local read-only archive inspection found 138 entries in `meshes/stl.zip`, all
non-directory entries STL, and six policy/checkpoint entries in
`logs/demo_model.zip`. Neither archive supplies a separate landmark/annotation
bundle. No archives were extracted and no local FlyMimic files were changed.

## Additional upstream engineering lead (scope)

[FlyGym issue #276](https://github.com/NeLy-EPFL/flygym/issues/276) was accessible
through the connected GitHub tool (open; last updated 2026-06-24 at retrieval).
Its author describes FlyMimic as a distinct rig and warns against directly
overlaying its muscles onto a NeuroMechFly body. It discusses different topology,
mesh/frame conventions and source-rig configuration extraction. This supports
investigating rig identity before reuse, but is an engineering discussion,
not a measured registration of our locked assets. Its particular mesh counts,
mirroring direction and body equivalence claims were **not reproduced** here;
do not import them as facts about our installed FlyGym 1.2.1 target.

The exact retrieved issue body and selected metadata are preserved separately in
`evidence/lf-reference-acquisition-v1/flygym-276-snapshot.json`. This is a connector
response snapshot, not raw HTTP bytes or a new source/mesh lock. The proposed
upstream extraction configuration belongs to its own FlyMimic rig. It does not
authorize a dependency upgrade, body replacement, target-site assignment or new
neural mapping in this project.

Search results also advertised upstream musculoskeletal API/tutorial pages;
direct retrieval of both returned 404. Search snippets were not treated as
verified current API contents or a dependency recommendation.

## Decision and next required input

**REFERENCE_REQUIRED — no qualifying target correspondence artifact acquired.**
The previous 0/8 supported correspondence result and null target points stand.
No new motor admission: production remains 20/42. No force scale, neural parameter,
source hash, failed raw prerequisite or runtime behavior changed.

The concrete missing input is an accessible model-development/annotation bundle
or authoritative download/revision identifying the eight source sites
`4,11,8,15,6,13,7,14` and their independently supported target attachment or
landmark correspondence on the locked thorax/coxa assets, with frames, units,
laterality and uncertainty. The exact request above contains model and mesh locks.
If only source-scan annotations are available, their relationship to the target
must still be established. Request this artifact/access from the user; author
outreach needs explicit authorization. Do not substitute another observer-only
campaign, fitted transform, mirrored endpoint guess or source-body swap.

After correspondence qualification, physical scale/conversion lineage,
nonzero-velocity mechanics, exact neuron-to-tendon binding, activation physiology
and original raw prerequisites remain open. A supported bounded headless native
experiment precedes a meaningful Unity test of the new muscle interface.

## Validation and manual review

This update changes documentation, two reference snapshots and their byte-preserving
Git attributes only. Validation
checks whitespace, local documentation links, JSON decoding and recorded motor
totals. It executes no physics, CNS, native kinematics or mocked experiment.
Historical scientific evidence is not regenerated or overwritten.

Executed results: Markdown fence/local-link checks passed for all three changed
Markdown files (one relative Markdown link); both snapshot JSON and motor-total checks
passed; `git diff --check` passed; Git Bash file-presence/JSON/whitespace checks
passed using the existing validated Python environment. Static inline progress
markup checks passed for 20/42 accessible values; no browser layout test was run.
Sandboxed Git initially failed through its LFS subprocess; the same read-only Git
checks completed successfully with the available elevated execution permission.
No simulation/unit-test suite was run for this documentation-only change.

Preserved issue snapshot SHA256:
`7da1347fab159c57c644897e6ec89d4bf5c071a1e6d966a980577c2aaf277616`.

After merging this documentation PR, Git Bash:

```bash
cd ~/Documents/FlyBrainUnity &&
git switch newBrain &&
git pull --no-rebase --no-edit &&
code docs/UNITY_AND_BALANCE_ROADMAP.md docs/LF_REFERENCE_ACQUISITION_V1.md
```

Expected: updated roadmap and this report open in VS Code; motor coverage stays
20/42 and the anatomical reference gate stays unresolved. There is no new
simulation command or changed Unity behavior in this update. A successful Git
pull or document check does not satisfy a scientific prerequisite.
