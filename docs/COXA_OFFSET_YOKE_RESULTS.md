# Open-loop coxa offset yoke: is the push amplification reflex or posture? — results (V1)

2026-11-03. One run of the preregistered protocol after commit 532b949 (protocol sha
309cade6…). Nine fresh-process arms ran from 19:20 to 20:03 local time, about 5 min
each, followed by one evaluation.

- **Report:** `evidence/coxa-offset-yoke-v1/run/report.json` (sha 5afb991f…).
- **Console logs:** committed.
- **Raw arms:** kept local in the main checkout's `docs/evidence/coxa-offset-yoke-v1/run/`.
  Their SHA-256 values are in the report.

These are physics and CNS runs, not mocks. Nothing was retried, re-windowed or tuned.

## Integrity: INTEGRITY_ACCEPTED

- **I1–I7:** all pass.
- **I2:** the push-response report (4c03a59e…) and all 18 reference arms match their
  preregistered hashes. The recomputed D values for the N and C references equal those in
  the push-response report.
- **I3:** `Y0_s` equals push-response `C0_s` over the whole run, in all three seeds. That
  covers every sample's qpos and all 42 applied commands, and every tick's spikes,
  uniforms and hair deliveries. So the four-index yoke plus the N configuration
  reproduces the closed-loop unpushed C arm exactly.
- **I5:** at every transition, the applied action equals the proposal with indices 0, 7,
  14 and 28 taken from the source, and the other 38 coordinates are as proposed. No arm has
  a hypothesis channel.

## Labels

| Push | Label |
|---|---|
| F (forward) | **OFFSETS_DO_NOT_REPRODUCE** |
| B (backward) | **OFFSETS_DO_NOT_REPRODUCE** |

D is in model mm·s. R_Y = D(Y)/D(N) and E = D(Y)/D(C). The amplification bar is
R_Y ≥ 1.10 in all seeds, and the equivalence band is 0.90 ≤ E ≤ 1.10.

| Push | Seed | D(N) | D(C) | D(Y) | R_Y | E |
|---|---|---:|---:|---:|---:|---:|
| F | 1 | 0.0335 | 0.0416 | 0.0460 | 1.37 | 1.11 |
| F | 2 | 0.0270 | 0.0552 | 0.0360 | 1.33 | 0.65 |
| F | 3 | 0.0419 | 0.0558 | 0.0394 | **0.94** | 0.71 |
| B | 1 | 0.0322 | 0.0418 | 0.0461 | 1.43 | 1.10 |
| B | 2 | 0.0439 | 0.0600 | 0.0307 | **0.70** | 0.51 |
| B | 3 | 0.0424 | 0.0526 | 0.0387 | **0.91** | 0.74 |

**The fixed setpoint schedule does not reproduce the amplification.**
- Replaying the unpushed C coxa commands with no neural coxa loop amplifies the push in
  seed 1 (R_Y about 1.4). In that seed, D matches the closed-loop C arm (E 1.10–1.11).
- In seeds 2 and 3, D falls well below the closed-loop C arm (E 0.51–0.74). In three of
  the four cases it is at or below the no-channel N arm (R_Y 0.70–0.94).
- The C arms amplified in every seed. So in two of three seeds, most of the
  amplification depends on the coxa commands being free to change after the push.

My prediction was OFFSETS_REPRODUCE, at moderate confidence. It was wrong.

## Correction to the push-response reading

The push-response results said "the loops did not respond to the push". That conclusion
came from window-mean hair-plate rates and offsets. This test measured the per-transition
commands, and they show the loops did respond.

| Measure (C arms, cleared window) | Value |
|---|---|
| Mean \|c(Cp) − c(C0)\| per coxa index | 0.009–0.033 rad |
| Transitions where the coxa command differs from C0 | 12,265–14,605 of 20,000, per index (all after the push, by I6) |
| For scale: the tonic LF/LH offset | about 0.17–0.21 rad |
| For scale: what the yoke removed (applied minus proposed, Y arms) | LF 0.17–0.18, LH 0.20–0.21, LM 0.007–0.009, RM 0.012–0.014 rad |

- **The modulation is small in amplitude but nearly continuous.** It cancels in window
  means, so the earlier measure missed it. The middle loops also modulate at about 0.01–0.03
  rad, even though their window-mean hair-plate rate rounds to 0 Hz.
- **Not all of this modulation is reflex.** Once the push changes the body trajectory,
  every closed-loop command can diverge. The test cannot separate reflex correction from
  chaotic divergence.
- **What it does establish:** for this pulse and posture, the fixed setpoints alone are not
  sufficient for the C arms' amplification in two of three seeds.
- **The tilt explanation is weakened.** The Y arms had the same posture as the C arms
  (mean tilt 8.7–10.4°, against C 9.1–10.2°). In seeds 2 and 3 they still did not
  amplify the push.

## Other descriptives (Y arms)

- **Peak orientation error:** 2.15–3.09°. Mean orientation error: 0.99–1.20°.
- **Peak root deviation:** 0.051–0.077 mm.
- **No arm recovered** into the inherited band (NOT_RECOVERED_IN_WINDOW).
- **Support:** the minimum was 4 contacts, with no rollover.
- **Signed fore-aft deviation:** the cleared-window means are −0.004…+0.022 mm.

## Consequence (declared in advance)

**OFFSETS_DO_NOT_REPRODUCE is recorded as is.** Fixed setpoints alone do not amplify
consistently, so the push-response mechanism reading was incomplete. Once the push
happens, freely changing coxa commands are needed for the C arms' amplification in two of
three seeds.

In every case:
- no channel, weight, threshold, gain, magnitude or seed changes;
- no coordinate status changes;
- coverage stays 20/42 admitted, +4 conditional.

## Limits

- **Position-assisted posture.** This is not independent balance.
- **Large seed-to-seed variability.** The ratios vary widely across seeds, and three
  seeds give no noise estimate.
  - E spans 0.51–1.11 and R_Y spans 0.70–1.43.
  - The 10 % bars are engineering resolutions.
- **Reflex or divergence cannot be separated.** The closed-loop commands after the push
  include both reflex modulation and chaotic divergence.
- **The yoke source embeds the loops' history before the push.** Only push-time freedom
  was removed.
- **One engineering pulse,** inherited from the push-response test.
- **The reference arms are local.** Verification depends on their hashes, which matched.

## Reproduce (Windows Git Bash, from the repository root)

This requires the push-response raw arms in `docs/evidence/coxa-push-response-v1/run/`.

```bash
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
for a in Y0_1 YF_1 YB_1 Y0_2 YF_2 YB_2 Y0_3 YF_3 YB_3; do
  PYTHONPATH="$PWD" "$PY" -m malecns_backend.live.coxa_offset_yoke --arm $a \
    --ref-dir docs/evidence/coxa-push-response-v1/run --output docs/evidence/coxa-offset-yoke-v1/run; done
PYTHONPATH="$PWD" "$PY" -m malecns_backend.live.coxa_offset_yoke \
  --evaluate docs/evidence/coxa-offset-yoke-v1/run --ref-dir docs/evidence/coxa-push-response-v1/run \
  --output docs/evidence/coxa-offset-yoke-v1/run/report.json
```

The arms take about 45 min in total. The expected result is INTEGRITY_ACCEPTED, with
both directions OFFSETS_DO_NOT_REPRODUCE and the arm hashes as in the report.
