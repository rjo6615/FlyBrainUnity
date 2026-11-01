# Serial motor fingerprint V1 — results

2026-11-01. One run of the preregistered protocol, executed after commit 59d7724.
Offline connectome analysis only: no physics, CNS, Unity, mapping or admission
change. Coverage remains 20/42. Raw output: `evidence/serial-motor-fingerprint-v1/run/result.json`.

## Verdict: FAIL (preregistered criteria)

| Criterion | Required | Observed | Met |
|---|---|---|---|
| a. Pooled serial type accuracy | >= 0.70 | 0.621 (612 scored) | no |
| b. Permutation p (1000, seed 20261101) | <= 0.01 | 0.001 (null mean 0.062, max 0.109) | yes |
| c. Serial joint accuracy, tibia / femur / femur_twist | each >= 0.60 | 0.818 / 0.941 / **0.100** | no |
| d. T1-reference serial type accuracy | >= 0.70 | 0.595 (195 scored) | no |

Inputs: 328 labeled leg motor neurons, 0 ambiguous, 1 excluded for zero typed
input; 1,837 presynaptic type features. Source hashes matched the protocol.

## What the numbers show (descriptive)

- Real but partial signal: serial accuracy is about 10x the shuffled-label null,
  and joint-level serial accuracy is 0.79. The fingerprints carry serial
  identity, but not reliably enough at the preregistered bar.
- Per joint class (serial type / joint accuracy): coxa_twist 0.96 / 0.96, femur
  0.65 / 0.94, tibia 0.66 / 0.82, tarsus2 and adhere_claw 0.62 / 0.86, coxa 0.36,
  coxa_abduct 0.25, femur_twist 0.10.
- Adjacent segments transfer better than T1<->T3: T1L->T2L 0.76 and T2R->T3R 0.73,
  but T1L->T3L 0.42 and T3L->T1L 0.42.
- Contralateral (same segment, descriptive): type 0.86, joint 0.93.

These patterns were seen after the run. Using them (e.g. adjacent-segment
chaining or per-class features) would be a new question and needs a separately
versioned protocol; V1's thresholds and features are not changed.

## Consequence

The method is not validated for proposing middle/hind Tarsus1 candidates; the
front-to-hind (T1 -> T3) transfer it would need is among the weakest. The 22
coordinates remain blocked. Limits: annotations are not muscle tracing; one
dataset; one feature definition.

## Changed files and checks

New: `malecns_backend/embodiment/serial_motor_fingerprint.py`,
`tests/test_serial_motor_fingerprint.py` (8 synthetic tests passed in 0.23 s),
`docs/SERIAL_MOTOR_FINGERPRINT_V1.md`, this file,
`docs/evidence/serial-motor-fingerprint-v1/{protocol.json,run/result.json}`;
`.gitattributes`, `docs/PROJECT_HANDOFF.md`, `docs/UNITY_AND_BALANCE_ROADMAP.md`.

Reproduce (Git Bash; output path must not exist, writes are exclusive):

```bash
cd "$HOME/Documents/FlyBrainUnity" && PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" && "$PY" -m malecns_backend.embodiment.serial_motor_fingerprint --cache .cache/malecns-v1 --output .cache/serial-fingerprint-repro.json
```

Expected: `"verdict": "FAIL"` with the numbers above, in a few seconds.
