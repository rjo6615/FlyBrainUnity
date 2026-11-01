# Stage 1 — DNg100 rhythm V1: results

2026-11-01. One run of the preregistered protocol after commit 2bf3541 (2,747 s,
432 neural simulations of 3 s). Neural activity only; no body, physics, mapping or
admission change. Raw output: `evidence/dng100-rhythm-v1/run/{result.json,console.txt}`.

## Verdict: NOT_REPRODUCED

| Criterion | Required | Observed | Met |
|---|---|---|---|
| C1 rhythm | best-rate score >= 0.5 and > control 80th pct | 0.196 at 100 Hz (control p80 0.216) | no |
| C2 frequency | 5-20 Hz at best rate | 2.8 Hz | no |
| C3 necessity | E1 and E2 silenced < 0.5 | 0.224 / 0.192 | yes, but vacuous: no rhythm to abolish |
| C4 drive scaling (secondary) | Spearman > 0 | -0.5 over 3 feasible rates | no |

Rhythmicity by DNg100 rate: 25 Hz no active MN; 50 Hz 0.158 (4/16 seeds feasible);
100 Hz 0.196; 200 Hz 0.190. Baseline: no active front-left MN. E1 = IN17A001_L
(800173), E2 = INXXX466_L (800863), selected by the declared synapse rule.

## What our engine does instead (descriptive)

- **DNg100 does reach the front-left leg.** At 100 and 200 Hz it recruits the same
  12 of 68 front-left motor neurons in all 16 seeds. Only 2 of 20 random
  cholinergic descending neurons recruited any front-left MN (best scores 0.211,
  0.217), so the pathway is relatively specific.
- **The output is tonic, not rhythmic.** At 100 Hz the recruited MNs fire steadily:
  coxa promotor ~118, ~99 and ~22 Hz; accessory tibia flexor ~73 and ~61 Hz;
  tibia extensor ~59 Hz; sternal anterior rotator ~42 Hz; femur reductor ~38 Hz
  (x2); trochanter flexor and sternotrochanter below 8 Hz. Tibia flexor and
  extensor co-activate rather than alternate.

## Interpretation

Our calibrated whole-CNS LIF engine carries a specific DNg100 -> front-leg motor
pathway but does not generate the predicted rhythm. Possible reasons, untested:
fixed calibrated parameters (vs the preprint's sampled ones), the 6-synapse floor,
conductance-based inhibition or spiking dynamics, or whole-CNS context. The
preprint's own result is a single unreviewed model and could also be wrong. Any
follow-up that changes parameters to look for a rhythm would be a new, separately
versioned question, and must not tune the engine until it oscillates.

Consequence for the roadmap: Stage 3 (emergent stepping from DNg100) is not
expected to work with the engine as-is. Stage 2 (coxa hypotheses for posture)
does not depend on a rhythm.

## Files and checks

New: `malecns_backend/embodiment/dng100_rhythm.py`, `tests/test_dng100_rhythm.py`
(6 synthetic tests passed in 4.78 s), `docs/DNG100_RHYTHM_V1.md`, this file,
`docs/evidence/dng100-rhythm-v1/{protocol.json,run/result.json,run/console.txt}`;
`.gitattributes`, handoff, roadmap.

Reproduce (Git Bash, ~45 min; output path must not exist):

```bash
cd "$HOME/Documents/FlyBrainUnity" && PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" && "$PY" -m malecns_backend.embodiment.dng100_rhythm --cache .cache/malecns-v1 --output .cache/dng100-rhythm-repro.json
```

Expected: `"verdict": "NOT_REPRODUCED"` with the numbers above.
