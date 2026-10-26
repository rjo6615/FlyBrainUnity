# Distal tarsus reference findings

Baseline: `origin/newBrain` at `9d74d2c`, merged PR #284. This is new reference
acquisition for the four distal coordinates, independent of blocked LF target
attachments. Production remains **20/42**. No maps, signs, gains, admission flags,
neural parameters or dependencies changed; no CNS or moving-fly assay ran.

## Sources and scope

The [BANC publication](https://www.nature.com/articles/s41586-026-10735-w), Methods,
describes cross-dataset matching and limitations of morphology-only suggestions.
The author-maintained [pipeline](https://github.com/htem/bancpipeline) and
[access package](https://github.com/natverse/bancr) identify a public metadata mirror.
Its annotations supplied new distal reference leads absent from the old audit.

The publication archive returned HTTP403. The current mirror differs from the
documented publication file (51,450,978bytes,188,162rows,79columns, MD5
`8c8babff28b21c57ecc999e664560ef5`). We archived separate dated generations,
verified GCS sizes/MD5 and pinned SHA256; no original source was refreshed:

| Source | Generation | Bytes / rows / columns | SHA256 |
|---|---|---|---|
| `banc_888_meta.feather` |1787336614757441|57,503,026 /188,508 /81|`86ccf5df0c67419f8c5f43e93a7ed38d23a080e9f7fde26737290252f3780098`|
| `malecns_09_meta.feather` |1778087827887849|16,593,866 /165,114 /33|`1a75ae60fca67f76a97b95bab6c384f65b4f9115afd4834648146d16d46c75a4`|

Full object metadata, generation-pinned URLs, attribution and code/schema revisions
are in `evidence/distal-tarsus-reference-v1/source-provenance.json`. Both sources
are new Git LFS objects. Existing official MaleCNS v1.0 annotations remain at their
original hash. New data is not claimed identical to the publication deposit.

The schema documentation describes `*_match` as confidence flags, while observed
`malecns_match` values are decimal ID strings. We treat them as **unvalidated
reference IDs**, not confidence or verified individual homology. Top NBLAST
references stay separate. All dataset/version/label disagreements remain explicit.

The prospectively declared broad class/type-field query retains **43rows**:
30BANC tarsus levator/depressor types plus13external-label controls. All selected
original BANC and matched v0.9/v1.0 fields, runtime indices and existing actuator
annotations are preserved. BANC root IDs stay strings in their own dataset.
There is no activity/connectivity ranking, outcome selection or population union.

## Distal leads, not motor assignments

BANC and MaleCNS are different female/male specimens. Published cross-links and
retained dimorphism/side fields do not alone establish homologous motor function.

| BANC side / segment | Rows | Missing scalar MaleCNS references | Distinct reference IDs |
|---|---:|---:|---|
| Left middle T2 |5|3|822185,1050046221|
| Right middle T2 |5|1|801477,817990|
| Left hind T3 |6|2|823405,1050239701,1050272154|
| Right hind T3 |4|0|800358,808453,869369,1050091102|

Right-middle levator reference801477 (`MNml81`) is shared by two BANC rows with
different MANC references and a differing NBLAST suggestion. Do not choose one
or duplicate/average its contribution. Right-hind levator869369 (`MNhl65`) and
one depressor800358 (`MNhl64`) agree with recorded MANC references13144/13740;
this is a concordant lead, not proof of complete antagonist populations/function.
Other hind depressor references conflict with current `ltm MN`, accessory
trochanter-flexor or trochanter-extensor labels. No existing function is reassigned.
Missing left levator references stay missing; no laterality mirroring occurs.

Across all43rows:11missing scalar references,15rows sharing a referenced ID,
18available MANC cycle disagreements,17NBLAST differences and2explicit action-label
disagreements. Flags overlap; they are not pass thresholds or error-rate estimates.
All new populations, actuators, signs and gains stay null; all admission flags false.

## Preserved failures and corrected implementation

- V1 failed strict JSON on a source IEEE NaN. Its3,927-byte partial report remains
  intentionally incomplete JSON under `distal-tarsus-reference-v1/run/`, SHA
  `85f336e15ea0a469af934ee9ab8ed765aec381c26438b8151e5e2a464ad14418`.
  Separate failure metadata identifies it as unaccepted.
- V1.1 specified lossless tagged non-finites but failed on original datetime
  values before report creation; its error JSON remains unchanged.
- V1.2 added timezone-aware timestamps and source schemas and serialized43rows.
  The strict boundary test then exposed legacy admission review -> live FlyGym
  inventory/model construction. Its report is preserved, SHA
  `f58d163b36d96e094c0b304521e276cf4109b1eafb015f1bc017715f409f0726`.
  V1–V1.2 reached that path; constructor internals were not instrumented. Their
  zero-transition summaries do not prove zero native construction or zero
  constructor-side physics operations. No CNS experiment was invoked.
- V1.3 reuses existing `lf_force_static_reference.load`. All sources, query,
  43rows and conflicts are unchanged. Strict reconstruction forbids native/CNS
  imports, live enumeration, legacy audit construction and the transition kernel.
  Accepted static report SHA:
  `95a1c2fc3538436676a906186d427ab1ff38c1da4882fbd80ef7bf06962231a3`.

Each correction was specified before its new exclusive attempt. No failed output,
raw source/hash or acceptance criterion was overwritten. Null, IEEE non-finites
and datetime values are distinguishable; raw Feather and Arrow schemas are primary.

## Actual checks and next gate

**39passed in18.80s**:24distal reference tests plus15existing admission tests.
The real V1.3 saved reconstruction passes with native/CNS/live-audit entry points
forbidden. Synthetic tests cover exact IDs/no float coercion, missing/duplicate/
many-to-one identities, side/segment/type/MANC conflicts, alias retention, exclusive
failed outputs, tampering and lossless encodings. Earlier pure tests:20passed;
later combined boundary check:38passed/1failed, resolved by the existing static
reader without relaxing the guard. The legacy admission regression separately
constructs its inventory model; it is not a no-construction test.

Next independently qualify anatomical/morphology matches, the v0.9/v1.0 identity
bridge and complete antagonist membership for all four distal coordinates. Retain
every missing/conflicting reference. Qualified pools still need mechanical/action
sign and a separate admission protocol. LF attachments, physical scale and neural
activation remain unresolved. No new Unity behavior or independent balance/gait.

## Windows Git Bash after merging

The exact saved-review command passed under Windows Git Bash. All43records,
source schemas and disagreement flags are identical between V1.2 and V1.3;
the boundary correction changed no selected evidence. Failed-output SHA checks
and Markdown fence/local-link checks also passed.

Whitespace checking passes for source/tests/docs and accepted data. Full staged
`git diff --check` retains expected warnings in exactly two failed raw captures:
V1's interrupted line ends in a space, and V1.1's error file has original CRLF
bytes. Those captures are not reformatted or counted as clean/accepted reports;
the scoped check excludes only those two immutable failed-byte files.

```bash
cd ~/Documents/FlyBrainUnity &&
git switch newBrain &&
git pull --no-rebase --no-edit &&
git lfs pull --include="docs/evidence/distal-tarsus-reference-v1/*.feather,docs/evidence/lf-anatomical-crosswalk-v1/annotations.feather,malecns_backend/embodiment/interface_output/integrated_whole_leg_readiness.json" &&
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" &&
"$PY" -m malecns_backend.embodiment.distal_tarsus_reference \
  --report docs/evidence/distal-tarsus-reference-v1_3/run/reference.json &&
code docs/DISTAL_TARSUS_REFERENCE_RESULTS.md
```

Expected: `DISTAL REFERENCE VERIFIED: 43 source rows; current 20/42; admissions0;
CNS/physics0.` This checks saved static reference data, not a fly simulation.
Do not treat failed/limited earlier outputs as accepted reports.

Focused manual tests: `"$PY" -m pytest -q -p no:cacheprovider
tests/test_distal_tarsus_reference.py` (24passed). Adding
`tests/test_remaining_leg_admission_audit.py` gives39tests and additionally needs
existing B4/M7 raw LFS inputs; it includes legacy inventory construction.
