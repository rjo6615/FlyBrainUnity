# Hair-plate Step B — results: ENCODER_READY (with a rest-pose caveat)

2026-11-01. One static run after commit 0ddff0f (FlyGym body built, no CNS, no physics
stepping). Raw output: `evidence/hair-plate-encoder-v1/run/result.json`.

All preregistered checks pass: anterior check (Head at +x, 0.9997), identity equals Step A
(7/5/12/11/8/9 SNpp45 per leg), threshold below saturation in every leg, 11.1% of
recorded poses active per leg, monotonic tuning, finite rest-pose rates.

| Leg | Recorded walking forward component | Threshold / saturation | Standing-pose forward | Standing-pose rate |
|---|---|---|---:|---:|
| LF | -0.653 to -0.161 | -0.214 / -0.161 | 0.009 | 120 Hz |
| LM | -0.392 to 0.184 | 0.160 / 0.184 | -0.037 | 0 |
| LH | -0.682 to -0.253 | -0.304 / -0.253 | -0.020 | 120 Hz |
| RF | -0.653 to -0.161 | -0.214 / -0.161 | -0.004 | 120 Hz |
| RM | -0.392 to 0.184 | 0.160 / 0.184 | -0.012 | 0 |
| RH | -0.682 to -0.253 | -0.304 / -0.253 | -0.275 | 68.5 Hz |

## Findings

- **Caveat: our standing pose is beyond the recorded walking forward limit** in the front
  and hind legs. Their coxae point further forward at rest (B4 standing posture) than at
  any point in the recorded walking step, so the encoder fires tonically, at or near its
  maximum, from t = 0 in four legs, and is silent in the middle legs. By the encoder's own
  definition that is correct ("at the forward limit"), and it makes a concrete Step C
  prediction: those hair plates should push the front and hind coxae backward. It also
  means the walking-derived threshold may not transfer to this engineered standing pose.
- **The FlyGym `Coxa` coordinate is the forward/backward axis.** In every leg, +0.1 rad
  on `joint_<leg>Coxa` moves the coxa backward (forward component -0.095 to -0.100);
  `Coxa_roll` and `Coxa_yaw` barely change it (|change| <= 0.0005). So positive `Coxa` =
  posterior (retraction) in the body frame. This is a geometric fact about the model,
  not a motor mapping, but it bears on the unresolved coxa motor sign question.

## Files and checks

New: `malecns_backend/embodiment/hair_plate_encoder.py`, `tests/test_hair_plate_encoder.py`
(5 tests on a toy MuJoCo body; with Step A's 4, 9 passed in 0.70 s; one test-fixture
angle was corrected before commit), `docs/HAIR_PLATE_ENCODER_V1.md`, this file,
`docs/evidence/hair-plate-encoder-v1/{protocol.json,run/result.json}`; `.gitattributes`,
handoff, roadmap.

```bash
cd "$HOME/Documents/FlyBrainUnity" && PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" && "$PY" -m malecns_backend.embodiment.hair_plate_encoder --cache .cache/malecns-v1 --output .cache/hair-plate-encoder-repro.json
```

Expected: `"status": "ENCODER_READY"` and the table above.
