# Assistance campaign V1.1 — failed V1 attempt retained, guard corrected

2026-10-31. No new native/CNS execution in this update. Coverage 20/42, 0 new
admissions; independent balance/gait unproven; all 20 neural servos assist.

## Retained V1 attempt (executed at 953b607, user-approved)

`docs/evidence/assistance-campaign-v1/run-desktop-01`, 13:48–14:00 UTC:
INCOMPLETE / INCONCLUSIVE_INTEGRITY. Controller complete prerequisites verified
before and after. A_NC (fresh process, venv redirector ancestry verified) loaded
the CNS and built FlyGym, then failed in adapter binding with
`ValueError: mechanical capture mutated native data`: 1 recorded state, 0 physics
transitions, 0 neural updates, 0 mechanical samples, qualification not started
(`A_NC.qualification.json.gz` holds null). Seven arms unstarted. All 14 files are
committed byte-identically (raw gz via LFS); report SHA256
50ad9eae2643ead943d64cfc474d728df6e122f27883b120a2d711b3087376ba is locked by the
V1.1 amendment. Construction-free `preflight-01` (verified) is also committed.
No retry was made.

## Defect and correction

The V1 guard hashed every exposed numeric MjData buffer, including arena-backed
scratch that changes between reads without any call (diagnosed on standalone toy
MuJoCo 3.2.7 models only). A three-field exclusion was drafted first and failed
its own real-MjData tests (four further unstable buffers), so the guard was
redefined as `mjSTATE_INTEGRATION`. See [ASSISTANCE_CAMPAIGN_V1_1.md](ASSISTANCE_CAMPAIGN_V1_1.md).

## Changed files

- `malecns_backend/live/assistance_native_v1_1.py`: integration-state guard,
  named changes, V1.1 qualify/Intervention (same budget/probes/tolerances).
- `malecns_backend/live/assistance_trial_v1_1.py`: Trial subclass/run_arm.
- `malecns_backend/live/assistance_campaign_v1_1.py`: controller/worker/evaluator
  reusing V1 helpers; amendment, failed report and V1 checkpoint locks.
- `tests/test_assistance_campaign_v1_1.py`: real toy-MjData and synthetic tests.
- `docs/ASSISTANCE_CAMPAIGN_V1_1.md`, this file,
  `docs/evidence/assistance-campaign-v1_1/{protocol,implementation}.json`.
- `docs/evidence/assistance-campaign-v1/{run-desktop-01,preflight-01}/`.
- `.gitattributes`, `docs/PROJECT_HANDOFF.md`, `docs/UNITY_AND_BALANCE_ROADMAP.md`.

Executed V1 modules/manifests are unchanged (`assistance_campaign --check` passes).

## Checks and limits

Final suite results are in the PR description. Real MuJoCo tests use a toy
model, not the fly: the guard equals `mj_getState(mjSTATE_INTEGRATION)`, is
stable over 1,000 reads with captures/steps (islands on and off), names a
mutated field, and the failed capture path passes 200 times. Whether any other
check fails on the real fly model is unknown until the next attempt; the guard
now names changed fields. Hashing cost and raw size remain unmeasured.

## Windows Git Bash after merge

The primary checkout holds untracked copies of the two committed folders, so a
plain pull refuses to overwrite them. They were verified byte-identical (14
files) when copied. Move them aside, pull, then compare and delete the copy:

```bash
cd "$HOME/Documents/FlyBrainUnity" && mkdir -p .cache/v1-evidence-precheck && mv docs/evidence/assistance-campaign-v1/run-desktop-01 docs/evidence/assistance-campaign-v1/preflight-01 .cache/v1-evidence-precheck/ && git pull --no-rebase --no-edit && diff -r .cache/v1-evidence-precheck/run-desktop-01 docs/evidence/assistance-campaign-v1/run-desktop-01 && diff -r .cache/v1-evidence-precheck/preflight-01 docs/evidence/assistance-campaign-v1/preflight-01 && echo IDENTICAL
```

Expected `IDENTICAL`; then `.cache/v1-evidence-precheck` may be removed.

```bash
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" && "$PY" -m malecns_backend.live.assistance_campaign_v1_1 --check && "$PY" -m malecns_backend.live.assistance_campaign_v1_1 --output docs/evidence/assistance-campaign-v1_1/preflight-01
```

Expected: `V1.1 SOURCE CHECK VERIFIED`, then `"status": "NOT_RUN"`,
`"preflight_verified": true`, `INCONCLUSIVE_INTEGRITY`, exit 0. A live attempt
(`--output docs/evidence/assistance-campaign-v1_1/run-desktop-01 --live
--review-note ...`) requires explicit approval; no retry.
