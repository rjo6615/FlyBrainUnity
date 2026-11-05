# Antennal gravity sense, Step B (kinematic JO C/E encoder): results

Run 2026-11-05. The run used the preregistered protocol
`docs/evidence/antennal-gravity-encoder-v1/protocol.json` (sha 0e97fe33…), committed in
2e2def7 before the run. It ran once and was evaluated once.
- The run is geometry only: the exact B4 runtime, imposed whole-body rotations, and
  `mj_forward` only, with no CNS and no physics stepping.
- One smoke run beforehand completed (exit 0). Its output was discarded unread.
- Raw output: `docs/evidence/antennal-gravity-encoder-v1/run/result.json` (sha 35ff3da4…),
  with `console.txt` alongside.
- Design: `ANTENNAL_GRAVITY_ENCODER_V1.md`.

## Verdict: `ENCODER_READY`

| Check | Result |
|---|---|
| B0: frame well-posed at rest | pass. Anterior fraction 0.9997. t̂·x̂_head = 0.966 on both sides (≥ 0.7). \|r⊥\| = 0.144. Gravity (0, 0, −9810). |
| B1: sets equal Step A | pass: C 31 L / 22 R, E 157 L / 110 R, all matched |
| B2: \|d\| ≤ 1 everywhere | pass: range −0.61 to +0.36 over all poses |
| B3: mirror at zero roll | pass: max \|d_L − d_R\| = 3.5e-9 |
| B4: monotonic in pitch | pass on both sides |

## Measured drive

At rest, the runtime head is level: the Head x axis has a world z component of 0, so the
rest pose equals the zero pose.

| | Left | Right |
|---|---:|---:|
| Rest d | −0.144 | −0.144 |
| Rest rate, G1 | E 17.2 Hz, C 0 | E 17.2 Hz, C 0 |
| Rest rate, G1_FLIP | C 17.2 Hz, E 0 | C 17.2 Hz, E 0 |
| Pitch slope at 0 (per rad) | 0.965 | 0.965 |
| Roll slope at 0 (per rad) | +0.215 | −0.215 |
| n̂ in Head frame | (0.143, −0.019, −0.990) | (0.143, 0.019, −0.990) |
| t̂ in Head frame | (0.966, −0.215, 0.144) | (0.966, 0.215, 0.144) |

These rest rates are labelled with the left/right synapse asymmetry (C 5.31×, E 2.54×), as
reconstructed. The per-neuron rates are equal on both sides, but the right sets have far
fewer output synapses.

d over the pitch grid (−30° to +30°), identical on both sides:

```text
-0.607 -0.538 -0.465 -0.389 -0.309 -0.227 -0.144 -0.059 0.026 0.111 0.195 0.278 0.359
```

**Pitch direction.** Positive pitch about world +y is nose-down: the Head x axis z
component goes from +0.5 at −30° to −0.5 at +30°. Nose-down raises d, meaning the arista is
pulled anteriorly. d crosses zero between +5° and +10° nose-down, because the a3 axis is
tilted about 8° from vertical.

**Roll.** d_L − d_R over the roll grid runs from −0.215 at −30° to +0.215 at +30°, and is
antisymmetric. **So the sense carries a small roll signal.** Under the declared rule it stays
descriptive. Step C will not read any left-minus-right difference as roll sensing, because
the asymmetric wiring alone could produce one.

## Predictions (recorded before the run): all three held

| Prediction | Outcome |
|---|---|
| Level-stance d about −0.1 to −0.2; under G1, E low tonic and C silent | held: −0.144; E 17.2 Hz, C 0 |
| Nose-down raises d steeply, slope near 1 per rad | held: 0.965 per rad |
| Roll slope about 0.2 per rad, opposite sign on each side | held: ±0.215 per rad |

The predictions came from hand arithmetic on the same MJCF geometry, and the runtime rest
head is level. Their agreement therefore confirms the implementation and frame conventions.
It is not independent evidence about the fly.

## What this shows and does not show

- **Shows:** a defined, mirror-consistent drive for the exact JO C/E sets. It is dominated
  by pitch, carries a small antisymmetric roll component, and is computed from the live
  head and antenna pose with no use of mass or antenna joint angles.
- **Does not show:**
  - function or zone sign. G1 is arbitrary, and Step C tests G1 against G1_FLIP;
  - the real deflection magnitude;
  - that the CNS uses the signal.
- **Consequence for Step C.** At rest, one zone fires tonically at about 17 Hz on each side,
  whichever assignment is used. Any comparison of OFF with G1 or G1_FLIP therefore includes
  this tonic input as well as any tilt-dependent part. Step C's design must separate the
  two: for example, by comparing tilt directions within an arm, not only arm against arm.
- **The imposed rotations are static.** Neck and antenna joints stay at their initial
  values. In live runs the passive neck spring may move the head, and the encoder will read
  that.
- No motor coordinate status changes: 20/42 admitted, +4 conditional.

## Files and checks

New files:
- `malecns_backend/embodiment/antennal_gravity_encoder.py`. It reuses Step A's
  `populations` and the B4 `_runtime`, and provides `encode`/`apply` for Step C;
- `tests/test_antennal_gravity_encoder.py`: 6 toy MuJoCo body tests. They pass together
  with the Step A and hair-plate encoder tests (17 passed);
- the protocol, `run/result.json` and `run/console.txt`;
- this file.

Also updated: `.gitattributes`, the design status line, the handoff and the roadmap.

Reproduce in Git Bash, from the repository root. The connectome cache is local.

```bash
PYTHONPATH="$PWD" "$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" -m pytest -q tests/test_antennal_gravity_encoder.py tests/test_antennal_gravity_identity.py tests/test_hair_plate_encoder.py
```

```bash
PYTHONPATH="$PWD" "$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" -m malecns_backend.embodiment.antennal_gravity_encoder --cache "$HOME/Documents/FlyBrainUnity/.cache/malecns-v1" --output .cache/antennal-gravity-encoder-repro.json
```

Expected: 17 passed, then `ENCODER_READY` with rest rate 17.2 Hz, pitch slope 0.965 and
roll slope ±0.215, in under a minute.
