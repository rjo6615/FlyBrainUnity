# Push response and offset yoke on six new seeds: results (V1)

Run 2026-11-04 under the preregistered protocol
`docs/evidence/coxa-push-replication-v1/protocol.json` (sha 01a6ea1c…, preregistration commit
80ad349). Each of the 55 arms ran once in a fresh process. The evaluation ran once. Design:
`COXA_PUSH_REPLICATION_V1.md`. Report: `docs/evidence/coxa-push-replication-v1/run/report.json`
(sha cdb953a153a859f4d2d4c37fb6f8258a7833ce2c5cc4cdcad3f235284d95c474).

This is not an admission test. No coordinate status changes. The earlier push-response and
offset-yoke reports, labels and texts are not edited; they remain the results for seeds 1–3.

## Integrity: `INTEGRITY_ACCEPTED`

| Check | Result |
|---|---|
| I1 completeness (55 arms COMPLETE, 20,001 samples, 4,000 ticks) | pass |
| I2 reproduction (`REPRO_N0_1` equals push-response `N0_1` in every sample and tick; both earlier report hashes verified) | pass |
| I3 common random numbers within each seed | pass |
| I4 exact force; `_0` arms apply none | pass |
| I5 channels and bounds | pass |
| I6 yoke (source hash, `Y0_s` = `C0_s`, applied = proposal + source coxa, no hypothesis channel) | pass |
| I7 prefixes and seeds (tick-1 uniforms of 7–12 distinct from each other and from 1–3) | pass |
| Pulse precondition (all 12 `NF_s`/`NB_s` resolved) | pass |

The `REPRO_N0_1` file hash (daaf14c9…) differs from the `N0_1` file hash (849b97cf…). I2 is a
content comparison of samples and ticks and passed; the files differ only in their labelling
fields (`schema`, `arm`, `protocol_sha256`), checked directly.

## Labels (six new seeds, per direction)

| Question | F | B | Prediction |
|---|---|---|---|
| Q1 does LOOP_AMPLIFIES replicate? | `AMPLIFICATION_DIRECTIONAL` | `AMPLIFICATION_DIRECTIONAL` | DIRECTIONAL or REPLICATES — **correct** |
| Q2a yoke rule unchanged | `OFFSETS_DO_NOT_REPRODUCE` | `OFFSETS_DO_NOT_REPRODUCE` | (earlier label) — **replicates** |
| Q2b sign of E | `FREE_COMMANDS_INCREASE_D` | `FREE_COMMANDS_INCREASE_D` | NO_CONSISTENT_SIGN — **wrong** |

Q1 is DIRECTIONAL, not REPLICATES, because one seed per direction fell under the original
1.10 bar (F seed 8, R = 1.047; B seed 9, R = 1.090). R > 1 in 6/6 in each direction (exact
one-sided sign test p = 1/64 per direction).

## Per-seed ratios

D in model mm·s, states 5,201–20,000, each pushed arm against its own `_0` control.

**R = D(C)/D(N)**

| Seed | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|
| F | 1.25 | 1.05 | 1.55 | 1.97 | 1.44 | 1.25 |
| B | 1.19 | 1.36 | 1.09 | 1.42 | 1.92 | 1.63 |

**E = D(Y)/D(C)**

| Seed | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|
| F | 0.75 | 0.93 | 0.64 | 0.72 | 0.86 | 0.78 |
| B | 0.99 | 0.76 | 0.90 | 0.82 | 0.81 | 0.74 |

**R_Y = D(Y)/D(N)**

| Seed | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|
| F | 0.94 | 0.97 | 0.99 | 1.42 | 1.24 | 0.97 |
| B | 1.18 | 1.03 | 0.98 | 1.16 | 1.55 | 1.20 |

## Pooled spread, seeds 1–3 and 7–12 (reported only, Q3)

Labelled as pooled. It does not relabel either earlier test.

| Direction | Ratio | n | Median | Range | Mean log | SD log |
|---|---|---|---|---|---|---|
| F | R | 9 | 1.33 | 1.05–2.04 | 0.354 | 0.222 |
| F | E | 9 | 0.75 | 0.64–1.11 | −0.245 | 0.178 |
| F | R_Y | 9 | 0.99 | 0.94–1.42 | 0.109 | 0.179 |
| B | R | 9 | 1.36 | 1.09–1.92 | 0.315 | 0.169 |
| B | E | 9 | 0.81 | 0.51–1.10 | −0.221 | 0.218 |
| B | R_Y | 9 | 1.16 | 0.70–1.55 | 0.094 | 0.240 |

D(N) between seeds: F mean 0.0309, SD 0.0061; B mean 0.0320, SD 0.0073 mm·s (coefficient of
variation about 20–23 %). Across all nine seeds R > 1 in 9/9 per direction; E < 1 in 8/9
per direction (seed 1 is the exception in both).

A seed-to-seed SD of about 0.17–0.24 in log ratio means a single seed's ratio has a typical
scatter of roughly ±20–25 %. The earlier 10 % bars (yoke band 0.90–1.10, R ≥ 1.10) are
narrower than that scatter.

## Descriptives

- **Recovery** (`metrics.response`): all 12 C and all 12 Y pushed arms are
  `NOT_RECOVERED_IN_WINDOW`; N arms recovered in 4/12 (3 F, 1 B).
- **Tilt (mean, per arm):** N 3.5–4.2°, C 8.9–10.5°, Y 9.1–10.4°. Y tilts like C, as before.
- **C-arm loop modulation:** mean |c(Cp) − c(C0)| per coxa index 0.006–0.029 rad, differing in
  11,325–14,795 of 20,000 transitions. The same order as seeds 1–3.

## What this means (by the declared rules)

- **Q1 DIRECTIONAL.** On fresh seeds the conditional fore-aft coxa channels consistently make
  the body easier to displace fore-aft after this pulse, in this assisted posture. The
  magnitude scatters widely (1.05–1.97), so the earlier 10 % bar is not reliably met. This is a
  body-level property of the current conditional wiring; it is not a balance contribution.
- **Q2a DO_NOT_REPRODUCE + Q2b FREE_COMMANDS_INCREASE_D.** Replaying the unpushed coxa
  commands (fixed posture) gives D close to N in F (R_Y median 0.99) and only partly toward C in
  B; letting the coxa commands run free after the push raises D in 6/6 seeds per direction.
  By the declared reading, the amplification depends consistently on the coxa commands being
  free after the push, not on posture alone.
- **My Q2b prediction (NO_CONSISTENT_SIGN) was wrong.** Seed 1 is the only seed of nine with
  E > 1, in both directions.

## What this does not show

- **Reflex vs divergence is not separated.** Free closed-loop commands respond to the
  push-induced sensory change through some route. A structured corrective reflex with the
  wrong sign and a generic sensitivity of a closed loop (small perturbation → diverging
  neural trajectory → more body deviation) both predict E < 1. This test cannot distinguish
  them.
- Position-assisted posture; not independent balance.
- Seeds vary only stochastic sensory timing.
- One engineering pulse; only the four fore-aft conditional channels. X (H1_FLIP) was not
  repeated, so Q_SIGN remains a seeds 1–3 result.
- The sign test needs unanimity at n = 6; a moderate effect cannot be told from none.
- The reproduction arm checks the environment, not biological validity.
- Coverage unchanged: 20/42 admitted, +4 conditional.

## Reproduce (Windows Git Bash, from the repository root)

Raw arms are local only (`docs/evidence/coxa-push-replication-v1/run/*.json.gz`, about 2 GB).
One arm, e.g. `CF_7` (a `Y` arm needs its `C0_s` source):

```bash
PYTHONPATH="$PWD" "$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" -m malecns_backend.live.coxa_push_replication --arm CF_7 --output docs/evidence/coxa-push-replication-v1/run
```

```bash
PYTHONPATH="$PWD" "$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" -m malecns_backend.live.coxa_push_replication --arm YF_7 --source docs/evidence/coxa-push-replication-v1/run/C0_7.json.gz --output docs/evidence/coxa-push-replication-v1/run
```

Evaluation (once all 55 arms exist):

```bash
PYTHONPATH="$PWD" "$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" -m malecns_backend.live.coxa_push_replication --evaluate docs/evidence/coxa-push-replication-v1/run --repro-ref docs/evidence/coxa-push-response-v1/run/N0_1.json.gz --output docs/evidence/coxa-push-replication-v1/run/report.json
```

Expected: `INTEGRITY_ACCEPTED`; F and B both `AMPLIFICATION_DIRECTIONAL`,
`OFFSETS_DO_NOT_REPRODUCE`, `FREE_COMMANDS_INCREASE_D`.
