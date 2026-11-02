# Coxa admission question V1 — results

Run 2026-11-02, once per arm, after the preregistration commit 0c94284 (protocol sha
3b97fbb8…). Design: `COXA_ADMISSION_QUESTION_V1.md`. Report:
`docs/evidence/coxa-admission-v1/run/report.json` (sha 088a642c…). Nine full CNS + physics
arms ran, each in a fresh process (about 5 min each), and then the evaluation ran once.
Nothing was retried, re-windowed or tuned.

**Part A (the CONDITIONAL tier) was approved by the user before the build.** This result
places two coordinates in that tier. **It is not an admission: motor coverage stays 20/42
admitted.** See `COXA_COORDINATE_STATUS.md`.

## Labels

| Coordinate | Seeds passed | Label | Flags | Status |
|---|---|---|---|---|
| `joint_LFCoxa` | 3/3 | **CONFIRMED** | none | **CONDITIONAL** |
| `joint_LHCoxa` | 3/3 | **CONFIRMED** | none | **CONDITIONAL** |

The predictions (both CONFIRMED) held.

**Integrity: `INTEGRITY_ACCEPTED`.** All six checks passed:

- **I1.** All nine arms completed.
- **I2.** Random numbers are identical within each seed.
- **I3.** `C0_1` reproduces the saved Step C A_ON exactly.
- **I4.** Channel inventories, definition hashes and bounds are correct.
- **I5.** Within each seed, arms are identical to C0 until the first coxa command.
- **I6.** The three seeds were applied and differ.

## Per-seed forward-component change vs C0 (window 520–2000 ms)

| Seed | LF CAND | LF FLIP | LH CAND | LH FLIP |
|---|---:|---:|---:|---:|
| 1 | −0.168 | +0.145 | −0.189 | +0.215 |
| 2 | −0.167 | +0.159 | −0.188 | +0.211 |
| 3 | −0.162 | +0.161 | −0.185 | +0.211 |
| D3, seed 1, all 13 H1 channels | −0.173 | +0.145 | −0.191 | +0.206 |

Every value is 7–11× the 0.02 bar.

## Descriptive measures

- **Isolation changes almost nothing.** With only the two channels enabled, the effect
  matches D3's all-channel effect. The fore-aft shift comes from these two channels, not
  from the yaw/roll channels.
- **The effect is stable across seeds.** The seeds change only the timing of stochastic
  sensory events, and the seed-to-seed spread is at most 0.016.
- **Cross-leg effects are small.**
  - Other legs moved by at most 0.033 (RF under FLIP).
  - LM moved by at most 0.027, though its encoder is silent.
  - RF and RH coxa MN rates stayed at 0.2–4.5 Hz.
- **Commanded offsets** (mean, max |c|):
  - LF about ±0.17–0.18 rad, max 0.225;
  - LH about ±0.20–0.22 rad, max 0.246.
  - LH spent up to 12 % of the window within 0.01 rad of the 0.25 rad cap (FLIP_1). That
    is below the 50 % `BOUND_LIMITED` threshold.
- **Sensory feedback.**
  - LH hair-plate rate fell under CAND in every seed (120 → 109.0, 100.9 and 105.6 Hz).
    This is the negative feedback a resistance reflex predicts.
  - LF stayed at the 120 Hz encoder ceiling (119.5–120).
  - Under FLIP, both stayed saturated at 120 Hz.
  - Hair-plate deliveries: CAND below C0 and FLIP above C0, in every seed.
- **Body tilt** (mean / peak):

  | Arm | Tilt |
  |---|---|
  | C0 | 3.8–4.2° / 5.7° |
  | CAND | 9.5–10.1° / 11.8–12.3° |
  | FLIP | 0.9° / 5.7° |

  There was no rollover. This is assisted posture, not a balance measure.
- **First coxa command:** sample 216 (seed 1), 141 (seed 2) and 146 (seed 3).

## Interpretation and limits

- **What is shown.** In this model and context, the rule-fixed H1 binding of the LF and LH
  fore-aft coxa channels closes a hair-plate → CNS → coxa loop. The loop moves the coxa
  posteriorly, reverses under a sign flip, and reproduces across three CNS seeds with the
  channels isolated. That meets CONDITIONAL criteria C1–C4.
- **The loop mostly works as a direction test, not graded feedback.** LF hair-plate input
  is at the encoder ceiling throughout, so its MN drive is near-tonic and the channel
  produces a near-constant setpoint offset. Only LH shows the sensor responding to the
  movement (a 9–16 % rate drop). This is consistency with the direction of the published
  CxHP8 resistance reflex. It does not show a graded reflex gain.
- **Seed range is narrow.** The three seeds vary only stochastic sensory event timing.
  The connectome, engine, initial state and posture are identical, so the confirmation
  shows reproducibility, not robustness across contexts.
- **The actuation is offset-on-servo.** The posture servos are on (assisted), so a shift is
  a servo setpoint shift, not muscle force or free posture.
- **CONDITIONAL is not admission.** It is a project policy. It does not satisfy the
  anatomical prerequisites (`LF_PROXIMAL_ADMISSION_PREREQUISITES_V1.md`) and must never be
  reported as admission. RFCoxa and RHCoxa_roll stay BLOCKED_BY_INPUT. All other coxa
  coordinates stay UNTESTED.

## Evidence

- **Committed:** `protocol.json`; `run/report.json`, `run/console_<arm>.txt` and
  `run/console_evaluate.txt`.
- **Raw arms** are local and uncommitted, in `docs/evidence/coxa-admission-v1/run/` of the
  main checkout.

| Arm | sha256 |
|---|---|
| C0_1 | 8fdcd56109acb9197a93385ee41b29e22313b55bd7bc30072c1cd3c37b46b03d |
| CAND_1 | 922db3a16443cec92ce91a4eb06f476d54b2bf35321eef14702a131aef5f3282 |
| FLIP_1 | da7892684d86cb513d5fcbbfa46d6751b949610981ad524f67829e29321d65ca |
| C0_2 | 5461e77c98a13971e7ef909d63ffa8c0514c1027774b3df93d510410e90a1cf5 |
| CAND_2 | 8563ca54c8726ea60a1f6e8e81caa0ffc5c0f351f8fcdb358731ff0d08cac9b1 |
| FLIP_2 | e6856bb6cc27fc6639a2179830cd4a2a0d29b33cfeee0ef321b54f558c49c572 |
| C0_3 | f201be76be2d82311238a9ec807be825945d3d3ac21163e82ea238b055c8ee1e |
| CAND_3 | 73ce387e0a6fabe68bf1ea79850c05ba100e19ed584a19b567019b2576a373ea |
| FLIP_3 | b41f148f8e89207ce8566ade131f2861f53621a074ecfc22883d405000fc6354 |
