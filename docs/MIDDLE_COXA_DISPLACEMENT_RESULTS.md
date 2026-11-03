# Middle-leg coxa resistance reflex under an imposed forward displacement — results (V1, C2 step)

2026-11-03. One run of the preregistered protocol after commit f91fd74 (protocol sha
9854e0af…). Nine fresh-process arms ran from 11:52 to 12:37 local time, about 5 min each,
followed by one evaluation.

- **Report:** `evidence/middle-coxa-displacement-v1/run/report.json` (sha 7c988f2f…).
- **Console logs:** committed.
- **Raw arms:** about 37 MB each, kept local. Their SHA-256 values are in the report.

These are physics and CNS runs, not mocks. Nothing was retried, re-windowed or tuned.

## Integrity: INTEGRITY_ACCEPTED; context precondition met

- **I1–I7:** all pass. P0_1–3 reproduce coxa-admission C0_1–3 exactly up to the
  displacement at state 5005. The shift record is exact (kp = 45 on both servos), and the
  bounds hold.
- **Context precondition:** met. The mean middle-leg hair-plate rate in P0 was 119.9–120
  Hz for LM and 93.5–113.4 Hz for RM. The bar was 30 Hz.

## Labels

| Coordinate | Label | Seeds passing | Flags |
|---|---|---|---|
| `joint_LMCoxa` | **C2_PASSED** | 3/3 | none (no BOUND_LIMITED, ROLLOVER or NO_DRIVE) |
| `joint_RMCoxa` | **C2_PASSED** | 3/3 | none |

Per-seed values. df is the change in the mean coxa forward component compared with P0;
the bar is ±0.02. Hair-plate rates are in Hz.

| Leg | Seed | df PC | df PF | Hair rate P0 → PC / PF |
|---|---|---:|---:|---|
| LM | 1 | −0.045 | +0.076 | 119.9 → 32.5 / 102.4 |
| LM | 2 | **−0.030** | +0.087 | 120.0 → 58.7 / 119.1 |
| LM | 3 | −0.058 | +0.067 | 120.0 → 33.2 / 119.7 |
| RM | 1 | −0.032 | +0.188 | 93.5 → 13.0 / 119.9 |
| RM | 2 | −0.038 | +0.186 | 97.6 → 7.5 / 118.8 |
| RM | 3 | −0.037 | +0.189 | 113.4 → 17.2 / 118.8 |

Under the H1 binding, both middle coxae pushed back against the imposed forward
displacement in every seed. The flipped binding pushed them further forward in every
seed. LM seed 2 is the narrowest pass, at −0.030.

## Descriptive (not labelled; no claims rest on these)

**The sensor follows the loop's own correction.** These are the measured hair-plate
rates, not labels.
- With PC, the hair-plate rate fell from saturation to 7–59 Hz.
- With PF it stayed at or rose to saturation. RM went from 94–113 to about 119 Hz.
- This is the first time in the coxa track that the closed loop has driven the modeled
  sensor down from saturation and held it in its graded range. Only LH had shown a small
  drop before (120 → 101–109 Hz).

**The two bindings behave asymmetrically, which is the signature of feedback sign.**

| Mean offset after the event | LM | RM |
|---|---|---|
| PC (posterior) | +0.040…+0.042 | +0.035…+0.060 |
| PF (forward) | −0.083…−0.084 | −0.177…−0.180 |

- PC corrects the displacement, which reduces its own drive, so its offsets stay small.
  That is negative feedback.
- PF moves the coxa further into the sensor's range, which increases its drive, so its
  offsets become large. That is positive feedback.
- Even so, no offset was bound-limited. The largest was 0.24, and RM PF_2 was near the
  bound in only 0.07 % of samples.

**Motor-neuron activity tracks the sensor.**
- With the displacement alone (P0), middle-leg coxa MNs fired at 10–13 Hz (left) and
  24–26 Hz (right).
- With PC they fell to 3.5–3.7 Hz and 3.6–7.0 Hz. With PF they were essentially
  unchanged.
- The LM posterior-MN inhibition predicted from the connectome did not prevent
  hair-driven recruitment.

**Other legs and posture.**
- Other legs changed little: |df| ≤ 0.014 in LF, LH, RF and RH.
- Body tilt stayed at 4.1–4.9° mean, with no rollover.

**Caveat on timing.** The first coxa command came at samples 461–1,581 (46–158 ms). That
is **before** the displacement at 500.5 ms, while the middle hair plates were still silent
at rest. So the channels also carry some activity that is not driven by the hair plates,
and PC/PF diverge from P0 physically from those samples onward. The labels compare
window means (520–2,000 ms), after the displacement. The pre-displacement part of the
offsets is not separated out here.

## Interpretation

- Both middle-leg coxa coordinates pass the C2 falsification step: the H1 binding resists
  an imposed forward displacement, and its sign reversal reverses the effect, in all three
  seeds.
- With the left-front and left-hind coxae, this gives the first **bilateral** pair of coxa
  channels that behave as a resistance reflex.
- The sensor responds to the loop's own correction in both directions. In effect the
  loop is regulating the coxa near the sensor's threshold: the forward-limit encoder
  stops the leg going forward and the loop pulls it back.
- This was an engineering probe in an assisted posture. It is not balance, and it does
  not admit these coordinates.

**Consequence (declared in advance).**
- `joint_LMCoxa` and `joint_RMCoxa` are now **"C2 passed, awaiting C3"**.
- They count nowhere until a separately preregistered C3 confirmation on CNS seeds 4–6
  passes.
- Coverage stays 20/42 admitted, +2 conditional.

## Limits

- **The displacement is an engineering perturbation** applied through the servo
  equilibrium. It is a probe stimulus, not a biological input.
- **Assisted context, with offset-on-servo actuation.**
- **The encoder threshold is walking-derived and unchanged.** The target was set one
  band past saturation.
- **Three seeds** that vary only stochastic sensory timing.
- **The channels act before the displacement,** as described in the timing caveat above.
- **C2 only.**

## Process note

The design text gave the bias change as `−kp·Δ`. That would have shifted the servo
equilibrium backward. It was corrected to `+kp·Δ` before registration, and the
protocol records the correction. The declared equilibrium shift Δ was not changed.

The smoke run (5,100 steps, P0_2 and PC_2) confirmed the event, the exact after-record,
the inventories (20 and 22 channels) and the direction of the shift. It was then
discarded.

## Files and checks

New:
- `malecns_backend/live/middle_coxa_displacement.py`
- `tests/test_middle_coxa_displacement.py` (15 synthetic tests)
- `docs/MIDDLE_COXA_DISPLACEMENT_V1.md`
- this file
- `docs/evidence/middle-coxa-displacement-v1/{protocol.json,run/report.json,run/console_*.txt}`

Also changed: `.gitattributes`, `COXA_COORDINATE_STATUS.md`, the handoff and the roadmap.

Checks: 67 tests passed (the new tests plus the coxa admission, D3 loop, Step C and release
tests).

```bash
cd "$HOME/Documents/FlyBrainUnity" && PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" && D=.cache/middle-coxa-repro && mkdir -p $D && for a in P0_1 PC_1 PF_1 P0_2 PC_2 PF_2 P0_3 PC_3 PF_3; do PYTHONPATH="$PWD" "$PY" -m malecns_backend.live.middle_coxa_displacement --arm $a --output $D; done && PYTHONPATH="$PWD" "$PY" -m malecns_backend.live.middle_coxa_displacement --evaluate $D --c0-dir docs/evidence/coxa-admission-v1/run --output $D/report.json
```

The rerun takes about 45 min. The expected output is INTEGRITY_ACCEPTED, with both
coordinates C2_PASSED and the values above.
