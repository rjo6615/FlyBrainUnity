# Saved V1.2 assistance-campaign review in the existing Unity scene

`malecns_backend/live/assistance_campaign_v1_2_replay.py` displays recorded
MuJoCo poses from the accepted V1.2 eight-arm run through the existing
PoseServer, `tactile_replay.replay_snapshot` and the unchanged 42-coordinate
LiveFly wire protocol. No Unity scene, rig, controller, physics, CNS, campaign
module, frozen auditor or evidence is modified. No physics or CNS runs.

## Gate

The unchanged V1.2 evaluator (`assistance_campaign_v1_2.evaluate`) is re-run on
the saved folder. Its arm loader is wrapped so that each arm it reads (raw
SHA-256 checked, non-finite markers decoded) is also projected to poses by the
existing validated `balance_contribution_replay.pose_only` (actual recorded qpos
addresses, 42-coordinate order, complete 20,001-state clock, finite poses). The
arms are read once, not twice. Clips are returned only if:

- the report schema is V1.2;
- the reconstructed evaluation, serialized exactly as the campaign save wrote it
  (json_safe markers), equals the saved `report['evaluation']`;
- scientific integrity is accepted and `unity_replay_eligible` is true;
- all eight arms were projected in the fixed order.

Otherwise nothing is displayed and no server opens. Behavior is never a gate:
the R-arm rollovers are a valid accepted outcome and are shown as such. The
saved report's `unity_replay_entry_point` field remains the historical
`NOT_IMPLEMENTED_FOR_THIS_SCHEMA`; that evidence is not rewritten.

## Display

Default arms `A_NP,R_NP` (pushed, neural input on; full assistance versus the
22 baseline-only servos neutralized). `--arms ALL` or any comma-separated subset
of A_NC, A_WC, A_NP, A_WP, R_NC, R_WC, R_NP, R_WP is allowed. The console prints
each arm's declared policies (R neutralization after state 5005, W decoder
withdrawal from tick 1001, P push at states 5000-5199), the state-5006 marker,
the saved comparison labels between the selected arms, and the limits. Each
clip starts with an explicit REPLAY RESET to saved t=0, which is not a simulated
transition. Default 0.1x speed stretches 2 s to 20 s; the transport may
downsample display to 30 Hz without changing evidence.

This is one seed under partial position assistance: not independent balance,
walking, a new simulation or an ordinary live mode.

## Actual checks (2026-11-01)

- `tests/test_assistance_campaign_v1_2_replay.py` together with the existing
  `test_balance_contribution_replay.py` and `test_controlled_live_balance_replay.py`:
  42 passed in 1.90 s (synthetic; no native body/CNS, no Unity).
- Real evidence: `load_verified` on the local, untracked
  `docs/evidence/assistance-campaign-v1_2/run-desktop-01` (raw `*.json.gz` are not
  in Git) rebuilt the full V1.2 evaluation, matched the saved report exactly and
  projected all eight arms, 20,001 states each, in 905.6 s. Every arm starts at
  root height 0.6046 with identity orientation. Final root orientation is
  near-upright in the A arms and inverted in the R arms (R_NC 160.6 deg tilt),
  consistent with the saved behavior summary. No server was opened.
- `assistance_campaign_v1_2 --check`: SOURCE CHECK VERIFIED (sources unchanged).
- Not done: Unity Editor visual review; per-packet `validate_pose` over every
  real clip (covered for the projection path by the existing balance replay tests).

## Windows Git Bash

The raw archives exist only on the desktop where the run happened. Point
`--input` at the folder that holds `report.json` and all 17 `*.json.gz`.

```bash
cd "$HOME/Documents/FlyBrainUnity" && git switch newBrain && git pull --no-rebase --no-edit
```

```bash
cd "$HOME/Documents/FlyBrainUnity" && PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" && "$PY" -m malecns_backend.live.assistance_campaign_v1_2_replay --input docs/evidence/assistance-campaign-v1_2/run-desktop-01 --arms A_NP,R_NP --speed 0.1
```

Expected: about 15 minutes of re-verification, then a RECORDED server on
127.0.0.1:8765 looping A_NP then R_NP with policy and push markers. Open
`FlyBrainUnity/` in Unity 6000.3.10f1, open `Assets/Scenes/LiveFly.unity` and
press Play; the existing LiveFlyClient connects and applies the saved poses.
Do not run the ordinary live launcher at the same time. Ctrl+C stops playback.
If verification fails, the command exits with a ValueError and opens no stream.
