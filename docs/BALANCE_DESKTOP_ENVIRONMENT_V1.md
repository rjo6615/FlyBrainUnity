# Desktop environment restoration and first bounded balance attempt

2026-10-26. The environment blocker is resolved. The experiment outcome is
**INCOMPLETE / INCONCLUSIVE_INTEGRITY**, with no accepted balance comparison.
This checkpoint carries the unchanged implementation from draft PR #287 onto a
fresh branch from `origin/newBrain`; it does not correct or bypass the failed
native identity guard. No automatic retry was made.

## Reconstructed environment

The old `fly-brain-interactive/.venv` targets a missing Python 3.10.11 executable.
Its NumPy and Arrow wheels have cp310 tags, so pointing Python 3.12 at those
packages would not repair it. The old environment was left unchanged.

The new isolated interpreter is:

```text
C:/Users/legen/Documents/FlyBrainUnity/.cache/malecns-balance-python312-v1/Scripts/python.exe
```

| Component | Verified installed version |
|---|---|
| Python | 3.12.14 |
| FlyGym | 1.2.1 |
| MuJoCo | 3.2.7 |
| dm_control | 1.0.27 |
| NumPy | 2.0.2 |
| SciPy | 1.15.3 |
| pyarrow | 25.0.1 |
| pytest | 9.1.1 |

The five balance-protocol environment requirements match. SciPy, Arrow and
transitive packages use the recorded desktop constraints where present. This is
a reconstructed balance environment, not a claim to satisfy every historical
LF numerical-assay environment manifest (which has separate version/file gates).
No system Python, old venv, neural calibration or physics parameter was upgraded.
The venv depends on the existing bundled Python base interpreter; it is local,
ignored by Git, and is not a portable environment archive.

147 old package versions were inventoried; the resolver selected 136 wheels for
the required packages and their dependencies. The complete resolver plan and
installation report remain in the new venv. [Wheel lock](evidence/balance-desktop-environment-v1/wheel-lock.json),
[hash-pinned requirements](evidence/balance-desktop-environment-v1/resolved-requirements.txt),
[desktop constraints](evidence/balance-desktop-environment-v1/desktop-constraints.txt)
and [setup receipt](evidence/balance-desktop-environment-v1/setup-receipt.json)
preserve exact versions, wheel URLs/hashes and setup provenance. Installation
used the full resolved lock with --require-hashes; pip check then found no broken
requirements. FlyGym, MuJoCo, dm_control, NumPy, SciPy and Arrow imports passed.
The initial sandbox network refusal and one local UTF-8 plan-reading error
occurred before installation; the successful plan/install records are retained.

## Checkout provenance correction

The first new-environment [static preflight](evidence/balance-desktop-environment-v1/preflight-01/report.json)
passed environment and neural-data checks but rejected M5D raw provenance.
Two old JSONs had CRLF-converted working bytes:

- `tactile_motor_closed_loop_100ms.json`: original lock
  `d684f38cd50edf6f494f00678d33a67c8cd89b50a34fd4815d5af90f05611e09`.
- `tactile_motor_matched_control_preflight.json`: original lock
  `15e83fa88aa3e7a6206ea7bb736cd1ec446874dcf44079e0b79bcbf39c594901`.

Both original Git blobs and index bytes match those unchanged locks. A guarded
one-off restoration required exact Git/index agreement, expected SHA, CRLF-only
working differences, exclusive backups and a final pre-write state recheck.
The converted originals and their hashes remain in
[checkout-byte-backups-01](evidence/balance-desktop-environment-v1/checkout-byte-backups-01/manifest.json).
Only the isolated worktree was restored; the primary checkout was not repaired.
New -text attributes preserve original bytes on future fresh checkouts. No
scientific content, acceptance criterion or expected hash was changed.

Original B4/M7/contact evidence was hydrated from the existing local LFS cache;
no replacement evidence was generated. The [second static preflight](evidence/balance-desktop-environment-v1/preflight-02/report.json)
passed the environment, original authorities, original design/code fingerprints
and seven original neural/calibration identities. Its zero native/CNS/scientific
counts describe that static preflight, not the later actual experiment totals.

## Actual bounded attempt and diagnosis

The one run used committed implementation
`266285f16452476d84e97ede070841b4acf673ed`, before any physics/CNS execution.
No runtime code was changed during or after the attempt. Original design, seed,
force, gains, mappings, physiology, sensory rules and safety history were fixed.

Evidence namespace:
`docs/evidence/balance-contribution-execution-v1/run-desktop-01/`.

| Planned arm | Actual result |
|---|---|
| NC | COMPLETE: 20,001 states, 20,000 physics transitions, 4,000 neural updates; terminal proposal retained/unapplied |
| WC | ERROR during initialization: one initial physical state, zero scientific physics transitions, zero neural updates |
| NP | Not started |
| WP | Not started |

NC's final native time was 1.9999999999997962 s and neural time 2000 ms, within
the declared tolerances. Its individual saved-record audit reconstructed.
That control alone is not a matched intervention or evidence of balance.
NC.json.gz (90,907,587 bytes) and WC.json.gz are original full/partial raw
records in LFS. [Report](evidence/balance-contribution-execution-v1/run-desktop-01/report.json)
and [attempt summary](evidence/balance-desktop-environment-v1/attempt-summary.json)
retain exact hashes, failure, counts, actual initialization entries and all 84
identity discrepancies. No no-push control was reused for a future attempt.

WC failed `recorded/native motor ID or address disagreement`. All 42 coordinates
have matching numeric actuator IDs, joint IDs, qpos addresses and dof addresses
against the old recorded M5A leads. The 84 differences are only the two full-name
fields per coordinate: historical `0/...` versus current `1/...`. This is not
new functional/anatomical qualification or permission to reassign IDs.

The preserved [installed source reference](evidence/balance-desktop-environment-v1/flygym-naming-reference.json)
shows FlyGym 1.2.1's `_existing_fly_names` registry and default-name allocation.
Closing NC does not make WC the first named fly in that Python process. The
adapter incorrectly treats old absolute instance-qualified names as identities
of every fresh runtime. The existing native inventory resolved/validated WC's
actual model before this additional comparison rejected it. Removing only this
guard would not suffice: raw initial/context/prefix equality also contains names
and must be addressed without weakening actual-model identity checks.

Initialization did real work even with WC scientific time zero. Each attempted
arm recorded one Fly constructor and data load, seven observed mj_forward entries
and three mj_resetData entries. NC's profile includes neural constructor/reset
entries; WC failed before brain construction. Profile keys aggregate same-named
Python methods: the two neural.__init__ entries are not a count of two CNS brains.
These are observed Python/C API entries, not an inventory of invisible native
internal calls. No extra live inventory model or duplicate CNS preflight was run.

The runner stopped after WC's error. Global integrity is inconclusive because
four-arm coverage is incomplete. Behavior is null in the report (not a measured
biological null). Unity replay eligibility is false. No pushed arm, causal
balance result, independent balance or gait was obtained. **No retry, favorable
window selection, parameter tuning, force increase or new motor admission.**

## Executed validation and next gate

- New environment: pip check and six package imports pass.
- 37 focused checks pass in 57.82 s: 23 balance engineering checks, 13 existing
  neural runtime checks and the actual calibrated JS/Python reference parity test.
  Those are synthetic/reference tests, distinct from the NC native/CNS run above.
- Six new real-Git checkout checks pass in 1.84 s: each original JSON under
  autocrlf true/input/false, with an unprotected control proving the newline
  policy is active. Both unchanged original hashes survive fresh checkout.
- Saved run hashes and evaluation reconstruct exactly, with FlyGym/MuJoCo/
  dm_control imports and CNS construction forbidden in the replay process.

Coverage remains **20/42**, new admissions **0**, LF target correspondence **0/8**.
The environment gate is passed; the active gate is the adapter's instance identity
and process-lifecycle contract. Before another scientific attempt, specify a
separately versioned engineering correction, test it, commit it and explain why
a fresh four-arm execution is warranted. Prefer genuinely fresh process state
per arm while retaining actual-model resolution and all strict original guards;
do not reset a live registry, invent native IDs or silently strip identity fields.
This correction and a new execution are **not implemented/run in this checkpoint**.
No automatic restart from WC or rerun of NC is authorized by a saved partial file.

## Changed files and manual Windows Git Bash checks

This fresh branch carries unchanged PR #287 implementation/history, plus:

- `.gitattributes`: preserve the two additional original raw JSONs and new setup evidence.
- `tests/test_balance_checkout_locks.py`: six real checkout regression cases.
- This document, `PROJECT_HANDOFF.md` and `UNITY_AND_BALANCE_ROADMAP.md`: actual
  environment, partial result, limits and concrete next gate.
- `docs/evidence/balance-desktop-environment-v1/`: package locks/receipt, both
  static reports, exact converted-byte backups, installed naming reference and
  attempt summary. `desktop-package-versions.json` retains the original inventory.
- `docs/evidence/balance-contribution-execution-v1/run-desktop-01/`: preflight,
  started commit, NC/WC raw gzip records and final incomplete report.

The old venv remains broken; use this verified interpreter rather than bare python:

```bash
cd ~/Documents/FlyBrainUnity
PY="$HOME/Documents/FlyBrainUnity/.cache/malecns-balance-python312-v1/Scripts/python.exe"
"$PY" -m pip check
"$PY" -c 'import flygym,mujoco,dm_control,numpy,scipy,pyarrow; print("imports OK")'
```

Expected: no broken requirements and imports OK. This does not start physics/CNS.
After the user merges the checkpoint PR:

```bash
git switch newBrain &&
git pull --no-rebase --no-edit &&
git lfs pull --include="docs/evidence/balance-contribution-execution-v1/run-desktop-01/*.json.gz"
"$PY" -m pytest -q -p no:cacheprovider tests/test_balance_checkout_locks.py
"$PY" -m malecns_backend.live.balance_contribution --evaluate \
  docs/evidence/balance-contribution-execution-v1/run-desktop-01
```

Expected: six checkout tests pass; saved evaluation exits 1 with
INCONCLUSIVE_INTEGRITY and unity_replay_eligible=false. That is the preserved
failure, not a reason to rerun it. No --live repeat command is supplied here.
Use the existing guarded byte-restoration safeguards for already-converted
primary working files; attributes alone may not rematerialize unchanged files.
