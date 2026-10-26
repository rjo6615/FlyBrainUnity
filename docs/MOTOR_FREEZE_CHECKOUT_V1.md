# Preserve original motor evidence bytes on Windows

Baseline: `origin/newBrain` at `42b9637` (PR #283). This is a checkout integrity
repair, not a new scientific assay or a replacement for missing anatomy.

## Defect and fixed boundary

The original remaining-leg audit records three failed raw locks. Each committed
Git blob still matches the SHA256 in its unchanged original freeze/manifest;
Windows `core.autocrlf` changes LF bytes into CRLF during checkout. Canonical
content correspondence alone correctly leaves the old raw checks failed.

The three exact paths are the result JSON files under:

- `interface_output/coxa_yaw_sign_validation/`
- `interface_output/coxa_yaw_anatomical_sign_bridge/`
- `interface_output/flymimic_flygym_proximal_registration/`

All are relative to `malecns_backend/embodiment/`. New exact `-text` attributes
prevent future checkout conversion. No result blob or expected hash is edited.
Pulling an attributes change may leave an existing working copy in CRLF form;
the explicit repair command addresses that case without a reset or clean.

Before any repair, all three original Git blobs must match their independently
recorded original freeze hashes; the index must match HEAD; and working files
must be either identical to Git or differ solely by CRLF conversion. Protecting
attributes must be active. Any other difference refuses the entire operation
before backup or file writes. No semantic JSON reserialization is accepted.

Repair saves all three pre-repair files byte-for-byte plus a SHA256 manifest in
an exclusive new backup directory, rechecks the checkout, and atomically replaces
only CRLF-converted copies with the original Git bytes. Existing backup paths
are never overwritten. An already-correct checkout is a no-op. Detected concurrent
edits refuse replacement; if an I/O error interrupts repair, backups remain and
earlier restored files may already have original bytes. The command is not an
exclusive cross-process file lock; avoid editing those files while it runs.

## Checks and scope

Regression tests use disposable real Git repositories with `core.autocrlf=true`,
`input` and `false`, exact original result bytes and the project's attributes.
A control without protection reproduces the raw-hash failure. Repair tests cover
content/staged/freeze/attribute mismatches, all-input prevalidation, exact backups,
backup collisions, repeated repair, detected edits during backup and atomic-write
failure. Tests do not create physics or CNS runtimes.

The actual isolated worktree starts with all three CRLF raw checks failed. Repair
must restore all three original raw hashes. The existing admission reviewer must
continue to preserve recorded historical failures and the full 22-row blocked
matrix: 20/42 admitted, zero new admissions and zero scientific transitions.
Old audit, decision and raw evidence files must have no Git content diff.

Actual results: **29 tests passed in 14.27 s** across the new checkout/repair
tests and existing remaining-leg admission audit tests. An earlier sandbox run
could not create pytest temporary directories; execution with available elevated
permission resolved that. The first combined run had 26 passes and one missing
canonical B4 evidence failure in the sparse worktree. Hydrating only the existing
B4/M7/readiness LFS inputs resolved it; no simulation was substituted or rerun.

The isolated working-copy repair passed all three original raw locks. The existing
saved reviewer independently reported recorded `False` / current `True`, unchanged
20/42 and 12/6/4 blockers, zero admissions/transitions. Exact raw backup checks,
original Git/freeze comparisons, final Git Bash repair/no-op/check commands,
Markdown local links/fences and whitespace checks passed. No historical result
content or expected SHA256 changed. The primary checkout was not repaired.

## Git Bash after merging

This command repairs checkout representation only. It does not run the fly.
Backups preserve the pre-repair bytes; do not commit the backup directory.

```bash
cd ~/Documents/FlyBrainUnity &&
git switch newBrain &&
git pull --no-rebase --no-edit &&
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" &&
"$PY" -m malecns_backend.embodiment.motor_freeze_checkout \
  --repair --backup-dir ".cache/motor-freeze-backup-$(date +%Y%m%d-%H%M%S)" &&
"$PY" -m malecns_backend.embodiment.motor_freeze_checkout
```

Expected: both commands report `Original motor/sign/registration raw locks: 3/3`.
Content or staged disagreements cause refusal; preserve the files and inspect
the reported path. The repair does not overwrite scientific edits to obtain a
pass. No historical report is regenerated. Read-only default check exits 1 when
raw locks remain unsatisfied and exits 0 for 3/3.

Optional regression check, expected 29 passing tests:

```bash
"$PY" -m pytest -q -p no:cacheprovider \
  tests/test_motor_freeze_checkout.py tests/test_remaining_leg_admission_audit.py
```

The full admission-review test also needs its existing canonical B4/M7 and
readiness evidence hydrated. This does not require a new simulation:

```bash
git lfs pull --include="malecns_backend/embodiment/interface_output/m7c_initial_stability/m7c_b4_stability_raw.npz,malecns_backend/embodiment/interface_output/m7_canonical/m7_raw.npz,malecns_backend/embodiment/interface_output/integrated_whole_leg_readiness.json" &&
"$PY" -m malecns_backend.embodiment.remaining_leg_admission_review \
  --report docs/evidence/remaining-leg-admission-audit-v1_1/audit.json
```

Expected: recorded historical raw freezes remain `False`, current three raw
freezes become `True`; motor coverage remains 20/42 with 22 blocked coordinates.
This statement concerns the three checked locks, not every scientific source
prerequisite. Target anatomical correspondence remains 0/8 in reviewed evidence;
force units, neural binding/activation and velocity transfer remain unresolved.
No new muscle-interface Unity behavior, independent balance or gait is established.
