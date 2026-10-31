# Assistance campaign V1 — engineering results

2026-10-31. Implemented the complete eight-arm evaluator and fresh-process
controller/workers for the frozen assistance-contribution design. NO native
body/CNS construction, force-law qualification, scientific physics transition
or Unity run was performed. Coverage 20/42, 0 new admissions; independent
balance/gait unproven. All 20 neural position actuators still assist.

Fresh branch `codex/assistance-campaign-v1` from origin/newBrain at merged PR294
(0b4231167f7769a48aea47a38d9d75e6235ca398) in an isolated sparse worktree; the
primary checkout's local `FlyBrainUnity/Assets/Scenes/LiveFly.unity` edit is
untouched. No frozen source, protocol, lock, auditor or historical result changed.

## Changed files and purpose

- `malecns_backend/live/assistance_campaign.py`: controller/worker/evaluator
  (see [ASSISTANCE_CAMPAIGN_V1.md](ASSISTANCE_CAMPAIGN_V1.md)).
- `tests/test_assistance_campaign.py`: 46 synthetic/real-process engineering tests.
- `docs/ASSISTANCE_CAMPAIGN_V1.md`: implemented scope, gates and limits.
- `docs/evidence/assistance-campaign-v1/implementation.json`: source checkpoint.
- `.gitattributes`: exact JSON/txt bytes and LFS gz for future campaign evidence.
- This file, `docs/PROJECT_HANDOFF.md`, `docs/UNITY_AND_BALANCE_ROADMAP.md`.

## Actual checks

Validated desktop interpreter `fly-brain-interactive/.venv/Scripts/python.exe`;
no dependency change. New suite **46 passed in 174.56 s**. Covered: full
eight-arm synthetic acceptance (A arms accepted by the frozen constant-model
auditor and equal to piecewise; R arms piecewise), frozen auditor still rejects
R, piecewise phase violations (missing/early/late patch, A carrying MR),
selected force at terminal state 20000, mechanical/science sample mismatch,
qualification transfer mismatch, failed saved qualification, all declared
prefixes/RNG/pre-gate, pre-5006 mechanical divergence, exposure indices,
duplicate PIDs, unguarded/incomplete reports, tilt-label/posture-loss/contrast
rules, controller refusal, failed first qualification with partial retained,
transfer to every later arm, corrupt transfer, stop, construction-free default,
worker prerequisite/initialization/after-acquisition failures, tampered transfer,
invalid requests, two real child OS processes with verified ancestry and
transfer, CLI and static source checkpoint. All models/sessions are synthetic;
real child processes run a synthetic adapter; test counts are not native counts.

A first development run (40 passed, 2 failed, 732.59 s) is retained here: one
tamper fixture broke force projection before the neutralization check (fixed
the fixture to keep projection consistent); one failure was the source-identity
gate correctly rejecting a campaign because test/module sources were edited
during that run. Slow failure tests were then restructured to call the same
per-arm auditors/`compare_all` directly. Final regression results are listed in
the PR description. `--check` printed `ASSISTANCE CAMPAIGN SOURCE CHECK VERIFIED`.

## Limitations

The sparse worktree omits `graph_w3.bin`, so its real complete preflight is
expected to FAIL there; the campaign must run from a full checkout at the
committed implementation. Native 22-coordinate binding, force qualification,
per-state full-model hashing cost and raw size are unmeasured (prior arms took
~3.5 min each without mechanical capture). No saved-replay entry point for this
schema yet. Synthetic acceptance proves wiring, not native integrity or behavior.

## Windows Git Bash after merge

```bash
cd "$HOME/Documents/FlyBrainUnity" &&
git switch newBrain &&
git pull --no-rebase --no-edit &&
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" &&
"$PY" -m malecns_backend.live.assistance_campaign --check &&
"$PY" -m malecns_backend.live.assistance_campaign --output docs/evidence/assistance-campaign-v1/preflight-01
```

Expected: `SOURCE CHECK VERIFIED`, then JSON with `"status": "NOT_RUN"`,
`"preflight_verified": true` and `INCONCLUSIVE_INTEGRITY` (nothing executed),
exit 0. Only after that, the ONE campaign (hours; no retry):

```bash
"$PY" -m malecns_backend.live.assistance_campaign --output docs/evidence/assistance-campaign-v1/run-desktop-01 --live --review-note "User reviewed V1.1 saved full-body replay 2026-10-26: normal movement, no unexpected issues"
```
