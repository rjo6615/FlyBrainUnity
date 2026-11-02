# Right-front coxa MN excitation — results (V1)

2026-11-01. The protocol, analysis code and tests were committed (a259a83) before the run,
and the analysis ran once. It is data only: it replays the Step C held-posture arms A_OFF
(hair plates off) and A_ON (hair plates on). Nothing was simulated, rerun or changed.

- Result: `docs/evidence/rf-coxa-excitation-v1/run/result.json`
- Console log: `docs/evidence/rf-coxa-excitation-v1/run/console.txt`

## Labels

| | Result |
|---|---|
| Integrity | `INTEGRITY_ACCEPTED`: all 15 checks pass |
| Replay | `REPLAY_EXACT` in both A_OFF and A_ON (36 posterior coxa MNs) |
| Attribution check | Per-partner contributions sum to the replayed excitation |
| **Q1** | **`HAIR_EVOKED`**: hair plates evoke 99.5 % of LF's other excitation and 68 % of LH's |
| **Q2** (RF vs LF) | **`ACTIVITY_GAP`**: wiring −0.06, activity −3.83 (log terms) |
| **Q2b** (RF vs LH) | **`ACTIVITY_GAP`**: wiring −1.09, activity −3.74 |
| **Q3** | **`PRE_EXISTING_ASYMMETRY`** by the rule, but it is degenerate (see below) |

The pool-level repeat (descriptive) gives the same four labels.

## What it shows

- **The wiring is there.** RF's best posterior MN has almost the same available
  excitatory input weight as LF's (397 vs 420, 5 % less). The gap is activity: the
  partners deliver about 46× less.
- **LF's extra excitation is a hair-plate relay.** In A_OFF, LF's best MN gets almost no
  other excitation (0.04). In A_ON it gets 8.6. Of that, 6.7 comes from interneurons
  that are directly downstream of LF's own hair plates. The main ones are left-side
  IN03A066 (31 Hz), IN03A075 and IN03A080.
- **The right-side copies of those interneurons are wired to RF but stay silent.** The
  right-side IN03A066 neurons connect to RF's best MN with *more* weight than the left
  ones have onto LF (60.9 vs 43.9). In A_ON they fire at 0 Hz, and so do the right
  IN03A075 and IN03A080 neurons.
- **LH works differently.** Part of its other excitation is baseline (7.05 in A_OFF).
  Most of the hair-evoked part comes from a broader network, such as INXXX464 and
  IN03A010, rather than from direct hair-plate targets.

## About the Q3 label

The rule compares RF with LF in A_OFF. It found RF 0.000 against LF 0.043, which is
below the 0.67× bar, so the label is `PRE_EXISTING_ASYMMETRY`. Both values are
effectively zero, though: in A_OFF neither leg has meaningful other excitation, and the
gap appears only once the hair plates are on. The rule lacked a minimum baseline size.
That is a flaw in how the rule was written, and it is recorded here. The label stands
as registered and is not reinterpreted into a pass.

## Post-hoc, exploratory (not preregistered)

After seeing the result, I counted the hair-plate synapses onto those three relay
interneuron types (floored, edges ≥ 6). This is a single connectivity count, labelled
exploratory.

| Type | LF hair plates → left copies | RF hair plates → right copies |
|---|---:|---:|
| IN03A066 | 98 | 26 |
| IN03A075 | 46 | 10 |
| IN03A080 | 37 | 12 |

The RF hair plates do reach the right-side copies, but with about a quarter of the
synapses. This is consistent with one structural deficit, the small RF hair-plate
neurons, acting twice: directly on the MNs, and through a relay that receives too
little input to fire. It is a hypothesis, not a tested result.

## Interpretation and limits

- Within the model, RF's missing other excitation is **not missing wiring**. It is silent
  partners, and on the left those partners are recruited by the hair plates. The
  preregistered Q3 label does not confirm the "consequence" reading (because of the
  degenerate rule above). The exploratory synapse count supports it without testing it.
- Limits:
  - Passive replay of one seed of one assisted-posture run. Attribution is not causal
    importance.
  - The connectome factors cannot separate real anatomy from reconstruction artifact.
  - Nothing was changed. Motor coverage stays 20/42.
- **A causal test would be an intervention**, with its own versioned protocol. For
  example: drive the right relay interneurons, or silence the left ones in a matched
  pair of runs.

## Reproduce

```bash
cd "$HOME/Documents/FlyBrainUnity" && PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" && "$PY" -m malecns_backend.embodiment.rf_coxa_excitation --cache .cache/malecns-v1 --step-c-dir docs/evidence/hair-plate-posture-v1/run --output .cache/rf-coxa-excitation-repro.json
```

Expected output, within a few minutes:
- `INTEGRITY_ACCEPTED`
- `REPLAY_EXACT` in both arms
- `HAIR_EVOKED`
- `ACTIVITY_GAP` (twice)
- `PRE_EXISTING_ASYMMETRY`
