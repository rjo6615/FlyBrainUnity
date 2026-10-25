# LF anatomical crosswalk results

2026-10-25. Fresh branch from origin/newBrain c6495bb, merged PR #266. New primary
source research and executable extraction; no new CNS/physics experiments or
admissions. Current live-v3 remains 20/42. Prior results, raw failures, local edits,
neural parameters, mappings and production motor/tactile behavior remain unchanged.

## New evidence

The full author-hosted anatomical appendix was downloaded and relevant figures
and captions inspected, overcoming the previous web-reader size limit. Figure A2
explicitly leaves the four promotor neurons' individual muscle targets uncertain.
That is a limitation of the available primary evidence, not a missing sign that
can be chosen by us. See `LF_ANATOMICAL_CROSSWALK_V1.md` for exact page locations,
source hashes, attribution and the distinction between FANC atlas numbers and
MaleCNS body IDs.

The official raw MaleCNS v1.0 annotation table independently reproduces all five
LF class pools and all 13 exact existing body IDs, with no extra source members.
Type, original side-fallback rule, front-leg subclass, motor superclass, T1
neuromere and exit nerves agree. Complete selected original source rows and
cross-dataset annotation fields are preserved, including nulls.

| MaleCNS body ID | Recorded MANC body ID | Class |
|---:|---:|---|
| 800061 | 12686 | Tergopleural/Pleural promotor |
| 801173 | 19319 | Tergopleural/Pleural promotor |
| 807281 | 12396 | Tergopleural/Pleural promotor |
| 934091 | 13490 | Tergopleural/Pleural promotor |
| 802509 | 12096 | Pleural remotor/abductor |
| 803803 | 13628 | Pleural remotor/abductor |
| 813480 | 155853 | Sternal adductor |
| 806923 | 26566 | Sternal anterior rotator |
| 919509 | 17176 | Sternal anterior rotator |
| 801915 | 19667 | Sternal posterior rotator |
| 804851 | 17546 | Sternal posterior rotator |
| 808640 | 29689 | Sternal posterior rotator |
| 1050335829 | null | Sternal posterior rotator |

These are published annotation matches, not newly validated morphology matches
or a mapping to FANC MN numbers. For 1050335829, the source's MANC group 21241 is
retained as a group; it does not fill the missing body match. All four promotor
MaleCNS/MANC type fields remain broad. No body ID is assigned a model tendon.

## Implementation direction and limits

There is no evidence-backed way to split the broad promotor pool with these
sources; stop repeating the same audit to search for a favorable split. Four
single-class populations have independent class-level anatomical support. They
can support explicit modeled class-to-muscle hypotheses in a separate LF reference
adapter, with broad promotors kept unassigned. This does not establish individual
biological tendon membership or admission.

The next engineering design should validate force projection/isolation first in
a separate fixture, using synthetic known tensions and existing local covectors.
It must explicitly declare force units, activation/passive dynamics and supported
pose/range before scientific coupling. Preserve the production 20-motor interface;
do not silently add torque on top of position actuation or use moment-arm magnitudes
as gains. A future bounded neural-coupling experiment still needs independently
specified numerical/application gates and the original raw prerequisites. No such
experiment or new numerical decoder is authorized by this research report.

The new raw Feather source is 14483314 bytes in Git LFS (CC-BY, attribution in the
reference report). The 211577 source rows include non-runtime records; the neural
runtime is not enlarged. New `crosswalk.json` raw SHA256:
`a915c8951653c718a1dadec3f99f888b8cf50c7cc9155a047010f54d5944f9ff`.
The full PDF and rendered inspection pages remain local under this update's
`tmp/pdfs/`, outside the PR; its URL/hash/page locators are recorded for retrieval.
Atlas interpretation is human reference review, not an automated morphology test.

## Actual validation

- **45 passed in 12.63 s**: 14 new crosswalk tests, 16 existing LF reference tests,
  15 existing admission-audit tests. Includes the real complete official source
  hash/extraction and full upstream identity/audit recomputation, plus synthetic
  missing/extra/duplicate/class/nerve/side/segment/match defects and output protection.
- Actual derived source extraction passed in 8.36 s; actual user-facing saved
  report CLI verification passed in 7.80 s. No downloads are performed by the CLI.
- The exact review command also passed under Windows Git Bash in 6.60 s using
  the validated virtual environment. Post-merge pull/LFS commands are provided
  for the user; no merge or pull into their primary checkout was performed here.
- Existing validated Python already includes pyarrow/pandas; no dependency changes.
- Primary PDF read with the separate bundled PDF runtime and rendered with Poppler;
  figures/captions on PDF pages 15, 17, 18 and 19 visually inspected.
- Whitespace and new LFS object checks passed. No Unity Editor, physics stepping,
  neural initialization, spike-generation experiment or old frozen trial rerun.
  Historical original raw-freeze flags remain false in the Windows checkout; they
  are reported and not waived. Older broader test failures were not rerun here.

## Changed files

- `.gitattributes`: exact LFS rule for new official annotation source only.
- `docs/LF_ANATOMICAL_CROSSWALK_V1.md`: primary evidence, atlas limitations and
  proposed force-interface validation direction, with Git Bash commands.
- `docs/LF_ANATOMICAL_CROSSWALK_RESULTS.md`: findings, exact matches and checks.
- `docs/evidence/lf-anatomical-crosswalk-v1/annotations.feather`: unchanged official
  v1.0 raw source, separately archived through LFS.
- `docs/evidence/lf-anatomical-crosswalk-v1/crosswalk.json`: exact selected rows,
  dense IDs, published matches, atlas class sets and unresolved model assignments.
- `malecns_backend/embodiment/lf_anatomical_crosswalk.py`: source hash/exhaustive
  pool validation and CLI, reusing existing independent identity reviewer.
- `tests/test_lf_anatomical_crosswalk.py`: source, identity, namespace and integrity
  checks; no mocked result is presented as physics or new anatomical proof.
- `docs/LEG_MAPPING_STATUS.md`: class-level progress and unchanged 20/42.
- `docs/PROJECT_HANDOFF.md`: current checkpoint and concrete next engineering scope.

## Git Bash after merge

```bash
cd ~/Documents/FlyBrainUnity
git switch newBrain
git pull --no-rebase --no-edit
git lfs pull --include="docs/evidence/lf-anatomical-crosswalk-v1/annotations.feather"
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
"$PY" -m malecns_backend.embodiment.lf_anatomical_crosswalk --report docs/evidence/lf-anatomical-crosswalk-v1/crosswalk.json
code docs/LF_ANATOMICAL_CROSSWALK_RESULTS.md
```

Expected: CROSSWALK VERIFIED; 13 exact neurons / 12 recorded MANC body matches;
4 unresolved promotor neurons / 0 assigned model tendons; current 20/42; newly
admitted and CNS/physics transitions 0. Recorded/current old raw-freeze flags false
in CRLF checkout representation. No Unity run is needed.

Optional tests, using a fresh temp directory name:

```bash
"$PY" -m pytest -q -p no:cacheprovider --basetemp="$PWD/.pytest-tmp-crosswalk-manual-v1" tests/test_lf_anatomical_crosswalk.py tests/test_lf_proximal_binding_review.py tests/test_remaining_leg_admission_audit.py
# Expected: 45 passed. Source/reference checks, no physics/CNS experiment.
```
