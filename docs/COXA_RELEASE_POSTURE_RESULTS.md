# Released-posture test with the conditional coxa channels — results (V1)

2026-11-02. One run of the preregistered protocol after commit bc38189 (protocol sha
166598304d7d…). Twelve fresh-process arms, 16:56–18:00 local time (about 5 min each), then
one evaluation.

- Report: `evidence/coxa-release-posture-v1/run/report.json`.
- Console logs are committed.
- The twelve raw arms (about 37 MB each) are kept local. Their SHA-256 values are in the
  report.

Results carry `COXA_CONDITIONAL_H1`.

## Integrity: INTEGRITY_ACCEPTED

All seven checks pass:

- **I1:** 12/12 arms COMPLETE.
- **I2:** common per-tick uniforms within each seed.
- **I3:** `R22_1` reproduces Step C R_ON exactly.
- **I4:** release events at state 5005 with exact after-records (22 rows for R22, 20 rows
  for K, KC and KF).
- **I5:** channel inventories and bounds hold. The largest offset is 0.2456 rad, within
  0.25.
- **I6:** within-seed prefixes are identical.
- **I7:** seeds applied.

## Labels

T_roll is the first sample after release (500.5 ms) with tilt > 90°. No arm is censored.

| Seed | R22 | K | KC | KF | K − R22 | KC − K | KF − K |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 578.8 | 573.6 | 572.1 | 575.6 | −5.2 | −1.5 | +2.0 |
| 2 | 591.8 | 576.3 | 582.9 | 567.4 | −15.5 | +6.6 | −8.9 |
| 3 | 582.6 | 578.1 | 567.5 | 589.9 | −4.5 | −10.6 | +11.8 |

All values are in ms. Every difference is below the 20 ms bar, and the signs are mixed.

| Question | Label |
|---|---|
| Q_ASSIST (K vs R22) | **NO_CONSISTENT_ASSIST_EFFECT** |
| Q_NEURAL (KC vs K) | **NO_CONSISTENT_LOOP_EFFECT** |
| Q_SIGN | **NOT_EVALUATED** (Q_NEURAL null) |
| Q_RESCUE | **NO_RESCUE**: every arm rolls over 67–91 ms after release |

All four labels match the preregistered predictions.

## Descriptive (not labelled; no claims rest on these)

**The loop acts throughout the fall without saturating.**
- KC and KF first change the coxa commands at samples 141–216 (14–22 ms), long before the
  release, as in the confirmation test.
- After release, the mean offsets are:
  - LF: +0.16…+0.17 (KC) and −0.17…−0.19 (KF);
  - LH: +0.21…+0.22 (KC) and −0.21…−0.22 (KF).
- The LH offset is within 0.01 rad of the bound in 2–9 % of samples; LF never is.
- The commands are present and sign-opposed, but they do not change when the body rolls
  over.

**Rollover direction.**
- In every arm, body z at T_roll points mostly along −x.
- The y component is consistent within each arm type across seeds:
  - R22: 0.06–0.12;
  - KC: 0.17–0.20;
  - K: 0.30–0.35;
  - KF: 0.33–0.38.
- So keeping the two servos, and the loop's sign, may shape *how* the body falls, not *when*.
  This was not a preregistered measure.

**Mean window tilt.**

| Arm | Mean tilt |
|---|---|
| R22 | 148–151° |
| K | 154° |
| KC | 155–156° |
| KF | 137–149° |

All of these are rolled over.

**Sensor and MN activity once the posture is lost.**
- **Kept servos keep the coxa joints in place.**
  - In K, the LF and LH hair plates stay saturated (120 Hz).
  - LF coxa MNs fire at 21–26 Hz, against 4.8–9.8 Hz in R22, where the LF coxa servo is
    released.
- **KC moves the joints off saturation.** It lowers the LF hair rate to 101–110 Hz.
- **KF has a cross-leg effect.**
  - The middle-left hair plate rises to 69–116 Hz (7 Hz in K).
  - Middle-left coxa MNs rise to 5.7–9.5 Hz (0.5–0.9 Hz in K).
  - Neither middle-leg coordinate has a channel, so this is an indirect, body-mediated
    effect.
- **Right-hind hair rate depends on the arm.** It is 4–12 Hz in K, 61–83 Hz in KC, 0–53 Hz in
  KF and 76–112 Hz in R22.

## Interpretation

- The two conditional coxa channels, and the two coxa servos they act through, do not
  change when the body rolls over once 20 other posture servos are released. The rollover
  happens in about 70–90 ms in every arm.
- This is the expected null. Two fore-aft joints on one side cannot hold a body whose other
  coxae, trochanters and tarsi have lost their assistance.
- The loop stays active and sign-specific throughout. Its commands reach the body, as the
  changes in hair-plate and cross-leg activity show. They do not reach the outcome measured
  here.

This does not revoke or strengthen the CONDITIONAL status, which no label here was designed
to change.

## Limits

- **Partial release.** The 20 v3 position servos remain on, as in Step C.
- **Offset-on-servo actuation.** K adds position assistance at two joints and is the
  matched control.
- **Three seeds** vary only stochastic sensory timing.
- **One measure.** T_roll is a single time point. The direction and tilt observations above
  are post hoc and descriptive, and would need their own preregistered question.
- **Coverage is unchanged:** 20/42 admitted, +2 conditional, counted separately.
  Independent balance and gait are not established.

## Process note

During the build, a test command was chained after `pytest | tail`, so a failing test did
not stop the commit or the launch. The failing test was the admission protocol-lock check.
Its cause was missing `-text` rules: the new evidence protocols were checked out as CRLF
in fresh worktrees.

- The committed blobs were always correct.
- The running arms did not read those files.
- Fixed in 117d1ac, which adds `-text` rules for the relay, admission and release-posture
  evidence. The bytes were restored and the hashes re-verified (3b97fbb8, 29b756b7,
  16659830).
- All 65 related tests pass.
- Main checkouts made before this fix may still hold CRLF copies until the files are
  re-checked-out.

## Files and checks

New files:

- `malecns_backend/live/coxa_release_posture.py`;
- `tests/test_coxa_release_posture.py`, 15 synthetic tests, passing;
- `docs/COXA_RELEASE_POSTURE_V1.md`;
- this file;
- `docs/evidence/coxa-release-posture-v1/{protocol.json,run/report.json,run/console_*.txt}`.

Also changed: `.gitattributes`, the handoff and the roadmap.

A smoke run of 5,100 steps (R22_2, K_2, KC_2) ran before the commit and was discarded.

```bash
cd "$HOME/Documents/FlyBrainUnity" && PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" && D=.cache/coxa-release-repro && mkdir -p $D && for a in R22_1 K_1 KC_1 KF_1 R22_2 K_2 KC_2 KF_2 R22_3 K_3 KC_3 KF_3; do PYTHONPATH="$PWD" "$PY" -m malecns_backend.live.coxa_release_posture --arm $a --output $D; done && PYTHONPATH="$PWD" "$PY" -m malecns_backend.live.coxa_release_posture --evaluate $D --step-c-dir docs/evidence/hair-plate-posture-v1/run --output $D/report.json
```

Expected run time is about 60 min. The expected output is INTEGRITY_ACCEPTED, the four null
labels and the T_roll values above.
