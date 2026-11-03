# Middle-leg coxa C3 confirmation on new seeds — results (V1)

2026-11-03. One run of the preregistered protocol after commit 3c677c2 (protocol sha
dd268b80…). Ten fresh-process arms ran from 13:43 to 14:33 local time, about 5 min
each, followed by one evaluation.

- **Report:** `evidence/middle-coxa-c3-v1/run/report.json` (sha 4c868949…).
- **Console logs:** committed.
- **Raw arms:** about 37 MB each, kept local. Their SHA-256 values are in the report.

These are physics and CNS runs, not mocks. Nothing was retried, re-windowed or tuned.

## Integrity: INTEGRITY_ACCEPTED; context precondition met

- **I1–I7:** all pass.
- **REPRO_1** (this module rerunning C2 `P0_1`) matches C2 `P0_1` exactly: every
  sample's qpos and commands, every tick's spikes, uniforms and hair deliveries, and the
  displacement record.
- **Seeds 4–6** are distinct from each other and from seeds 1–3.
- **Context precondition:** met. The P0 middle-leg hair-plate rate was 117.8–119.9 Hz
  for LM and 99.2–110.4 Hz for RM. The bar was 30 Hz.

## Labels

| Coordinate | Label | Seeds passing | Status | Flags |
|---|---|---|---|---|
| `joint_LMCoxa` | **CONFIRMED** | 3/3 | **CONDITIONAL** | none |
| `joint_RMCoxa` | **CONFIRMED** | 3/3 | **CONDITIONAL** | none |

Per-seed values. df is the change in the mean coxa forward component compared with P0
over the window; the bar is ±0.02. Hair-plate rates are in Hz.

| Leg | Seed | df PC | df PF | Hair rate P0 → PC / PF |
|---|---|---:|---:|---|
| LM | 4 | −0.033 | +0.089 | 117.8 → 56.0 / 119.7 |
| LM | 5 | **−0.031** | +0.096 | 119.6 → 63.7 / 120.0 |
| LM | 6 | −0.041 | +0.093 | 119.9 → 47.8 / 120.0 |
| RM | 4 | −0.046 | +0.174 | 105.2 → 8.6 / 116.1 |
| RM | 5 | −0.039 | +0.185 | 110.4 → 14.1 / 120.0 |
| RM | 6 | −0.032 | +0.193 | 99.2 → 12.5 / 120.0 |

**Both coordinates reproduce C2 on never-run seeds.** Under H1 they resist the imposed
forward displacement, and H1_FLIP reverses the effect, in every seed. The sizes match
C2 (C2: LM −0.030…−0.058 / +0.067…+0.087; RM −0.032…−0.038 / +0.186…+0.189). The
narrowest pass is LM seed 5, at −0.031.

## The C2 timing caveat, now measured (reported, not labelled)

**Channel offsets before the displacement are near zero.**

| Mean offset | Samples 1–5005 (before) | Window |
|---|---|---|
| PC and PF | −0.013…+0.002 rad | PC +0.039…+0.053; PF −0.089…−0.184 |

The channels do issue small commands early (first at samples 361–376), but almost all of
their output arrives after the hair plates are recruited by the displacement.

**Position differences before the displacement (400–500 ms) are mostly small, with one
exception.**
- In most seeds, |df| is at most 0.026 for both legs.
- **LM seed 4 is the exception:** PC was **+0.046** more forward than P0 before the
  displacement, larger than its window effect (−0.033) and of the opposite sign.
- The likely cause is that small early commands make the trajectories diverge physically
  before the stimulus.
- This means the pre-stimulus trajectory difference can be as large as the 0.02 bar in
  some seeds. In that seed it worked against the pass, not for it.
- This is recorded as a limit on how precisely the bar measures. It does not change the
  label.

## Other descriptives

- **Graded feedback, as in C2.** With PC the hair-plate rate fell from saturation to 9–64
  Hz. With PF it stayed at or near 120 Hz.
- **Motor neurons followed the sensor.**
  - With the displacement alone (P0), middle coxa MNs fired at 8.6–11.5 Hz (left) and
    20.5–26.6 Hz (right).
  - With PC they fell to 4.5–5.1 Hz and 4.6–5.6 Hz. With PF they were near P0.
- **Other legs and posture.**
  - Other legs changed little: |df| ≤ 0.011.
  - Tilt stayed at 4.0–5.0° mean, with no rollover.
  - No offset was bound-limited. The largest near-bound fraction was 0.03 %, in RM PF_4.

## Status change (declared in advance)

`joint_LMCoxa` and `joint_RMCoxa` are now **CONDITIONAL**, labelled `COXA_CONDITIONAL_H1`
and counted separately. Their evidence under the Part A tier:

| Criterion | Evidence |
|---|---|
| C1 | D2 H1 binding, rule-fixed |
| C2 | PR #316, 3/3 seeds |
| C3 | this test, 3/3 new seeds, isolated, separately preregistered |
| C4 | integrity in both tests |

- **Totals: 20/42 admitted (v3, unchanged); +4 conditional.**
- **LM and RM are the first bilateral conditional pair.**
- CONDITIONAL channels may be enabled only through the labelled hypothesis session path.
  Any later preregistered failure revokes the status.

## Limits

- **The displacement is an engineering perturbation** applied through the servo
  equilibrium, in an assisted posture. Actuation is offset-on-servo.
- **The encoder threshold is walking-derived and unchanged.**
- **The seeds vary only stochastic sensory timing.**
- **The pre-stimulus divergence in LM seed 4 shows how noisy the bar can be.**
- **CONDITIONAL is not admission,** and none of this is balance or gait.

## Files and checks

New:
- `malecns_backend/live/middle_coxa_c3.py`
- `tests/test_middle_coxa_c3.py` (16 synthetic tests)
- `docs/MIDDLE_COXA_C3_CONFIRMATION_V1.md`
- this file
- `docs/evidence/middle-coxa-c3-v1/{protocol.json,run/report.json,run/console_*.txt}`

Also changed: `.gitattributes`, `COXA_COORDINATE_STATUS.md`, the handoff and the roadmap.

Checks: 68 tests passed (C3 and C2 plus the coxa admission, D3 loop and Step C tests). A
5,100-step smoke run of `P0_4` ran before the commit and was discarded.

```bash
cd "$HOME/Documents/FlyBrainUnity" && PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" && D=.cache/middle-coxa-c3-repro && mkdir -p $D && for a in REPRO_1 P0_4 PC_4 PF_4 P0_5 PC_5 PF_5 P0_6 PC_6 PF_6; do PYTHONPATH="$PWD" "$PY" -m malecns_backend.live.middle_coxa_c3 --arm $a --output $D; done && PYTHONPATH="$PWD" "$PY" -m malecns_backend.live.middle_coxa_c3 --evaluate $D --c2-dir docs/evidence/middle-coxa-displacement-v1/run --output $D/report.json
```

The rerun takes about 50 min. The expected output is INTEGRITY_ACCEPTED, with both
coordinates CONFIRMED and CONDITIONAL and the values above.
