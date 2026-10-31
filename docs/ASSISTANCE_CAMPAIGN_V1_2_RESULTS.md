# Assistance campaign V1.2 — V1.1 attempt retained, read-back corrected

2026-10-31. No native/CNS execution in this update. Coverage 20/42, 0 new
admissions; independent balance/gait unproven; all 20 neural servos assist.

## Retained V1.1 attempt (executed at 92652b5, user-approved)

`docs/evidence/assistance-campaign-v1_1/run-desktop-01`, 15:28-16:32 UTC:
ERROR / INCONCLUSIVE_INTEGRITY. A_NC COMPLETE: 20,001 states, 4,000 neural
updates, 20,001 mechanical samples, qualification passed in memory under the
V1.1 guard, ~62 min stepping, 560 MB raw + 175 MB qualification. Controller
transfer then raised `TypeError: float() argument ... not 'dict'`; 7 arms
unstarted; no retry. All 14 files committed byte-identically (raw via LFS);
report SHA256 9ec6bad3... locked by the V1.2 amendment.

## Changes (all three declared in the amendment before any V1.2 execution)

1. Saved-JSON read-back decodes the existing save's `__arrow_nonfinite_float__`
   markers exactly (the six adhesion actuators' +/-inf force ranges).
2. The trace audit's boundary-journal clock is compared at the adapter's own
   1e-12 clock bound instead of bit-exactly (accumulated MuJoCo clock differed
   from 5005*dt by -3.9e-14 s). Found by the first offline audit.

3. Per-state model identity uses exact byte comparison with snapshots of the
   recorded M0 and derived MR (~8 ms) instead of re-hashing all 379 model
   arrays (108.75 MB, ~55 ms) twice per state. The retained A_NC ran at a
   constant ~8.1 steps/s (~123 ms/step) vs ~97 steps/s without per-state
   hashing. Expected ~9-10 min stepping per arm, ~1.3-1.6 h for eight
   (estimate; not yet measured on the fly model). Equally strict; GPU would not
   help (Python checking cost; GPU physics would change validated numerics).

## Offline audit of the retained A_NC (diagnostic only, no behavior)

- `retained-v1_1-a-nc-audit.json` (commit 91fe155): qualification passed;
  identity true; scientific accepted by the frozen constant-model auditor and
  equal to piecewise; mechanical FAILED on the journal clock only. Retained.
- `retained-v1_1-a-nc-audit-02.json` (commit ed9d806): all passed, mechanical
  20,001 states, journal clock offset -3.885780586188048e-14 s.
- `retained-v1_1-a-nc-audit-03.json` (commit 4ec2076, after the snapshot
  change): all passed again.

Not campaign acceptance: one arm cannot exercise cross-arm prefixes/RNG or
comparisons, display/reference diagnostics were not run, and retained arms are
not reused. Reference comparison is diagnostic only and may report differences
caused by decoded non-finite values or new mechanical capture operations.

## Changed files

`malecns_backend/live/assistance_campaign_v1_2.py`,
`tests/test_assistance_campaign_v1_2.py`, `docs/ASSISTANCE_CAMPAIGN_V1_2.md`,
this file, `docs/evidence/assistance-campaign-v1_2/{protocol,implementation,
retained-v1_1-a-nc-audit,retained-v1_1-a-nc-audit-02}.json`,
`docs/evidence/assistance-campaign-v1_1/{run-desktop-01,preflight-01}/`,
`.gitattributes`, `docs/PROJECT_HANDOFF.md`, `docs/UNITY_AND_BALANCE_ROADMAP.md`.
Executed V1/V1.1 modules unchanged (their `--check` passes).

## Checks

251 passed in 592.94 s before the clock correction (V1.2 + V1.1 + V1 campaign,
native, trial, plan, controlled-live V1/V1.1, process, prerequisites); after it,
the V1.2 suite 15 passed in 185.34 s. After the snapshot change: 261 passed
and 1 failed in 626.73 s (a V1.2 policy-equality assertion that needed the new
field excluded; fixed), then the V1.2 suite 22 passed in 190.11 s. These include the real retained V1.1
qualification failing through the V1.1 reader and passing through V1.2. All three
`--check` commands verify; commit gate passes.

## Windows Git Bash after merge

```bash
cd "$HOME/Documents/FlyBrainUnity" && mkdir -p .cache/v1_1-evidence-precheck && mv docs/evidence/assistance-campaign-v1_1/run-desktop-01 docs/evidence/assistance-campaign-v1_1/preflight-01 .cache/v1_1-evidence-precheck/ && git pull --no-rebase --no-edit && diff -r .cache/v1_1-evidence-precheck/run-desktop-01 docs/evidence/assistance-campaign-v1_1/run-desktop-01 && diff -r .cache/v1_1-evidence-precheck/preflight-01 docs/evidence/assistance-campaign-v1_1/preflight-01 && echo IDENTICAL
```

```bash
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" && "$PY" -m malecns_backend.live.assistance_campaign_v1_2 --check && "$PY" -m malecns_backend.live.assistance_campaign_v1_2 --output docs/evidence/assistance-campaign-v1_2/preflight-01
```

Expected `IDENTICAL`, `V1.2 SOURCE CHECK VERIFIED`, then `"status": "NOT_RUN"`,
`"preflight_verified": true`, `INCONCLUSIVE_INTEGRITY`, exit 0. A live attempt
(estimated ~1.3-1.6 h, ~4.5 GB raw) requires explicit approval; no retry.
