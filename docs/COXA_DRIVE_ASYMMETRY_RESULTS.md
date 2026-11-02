# Right-front coxa drive asymmetry — results (V1)

2026-11-01. The protocol, analysis code and tests were committed (2c1ca42) before the
run, and the analysis ran once. It is data only: the connectome, the engine weight
rule and the spikes recorded in the Step C A_ON run. Nothing was simulated, rerun or
changed.

- Result: `docs/evidence/coxa-drive-asymmetry-v1/run/result.json` (sha256 695951fd…)
- Console log: `docs/evidence/coxa-drive-asymmetry-v1/run/console.txt`

## Labels

| | Result |
|---|---|
| Integrity | `INTEGRITY_ACCEPTED`. Every check passed (hashes, Step A counts, engine weights and signs, inputs). |
| Replay | `REPLAY_EXACT`: all 62 coxa MNs reproduce every recorded window spike (955 spikes) from the recorded input spikes. |
| **Q1** | **`RF_DIRECT_SUFFICIENT`**: by the preregistered mean-field rule, the best RF MN reaches g = 8.98, against a threshold of g* = 8.09. This needs the caveat below. |
| **Q2** (RF vs LF) | **`SYNAPSES_PER_SOURCE`** |
| **Q2b** (RF vs LH) | **`SOURCE_COUNT`** |
| **Q3** | **`INHIBITION_NOT_DECISIVE`**: RF MNs receive almost no inhibition (ratio 0.00, against LF 0.08) |
| Engine share | **0.09**: the 6-synapse floor plus size scaling explain 9 % of the RF/LF deficit |

## Where the drive is lost (RF vs LF)

The RF pool weight is 0.21× LF's (log −1.55). Split into factors:

| Factor | log-ratio | Class |
|---|---:|---|
| Synapses per source (39 vs 118) | **−1.07** | connectome |
| Source count (5 vs 7) | −0.34 | connectome |
| Size scaling | −0.10 | engine |
| 6-synapse floor | −0.04 | engine |
| Transmitter sign | 0.00 | annotation |

Against LH the per-source synapse count is the same (about 40 per source). The only
real difference is the number of sources (5 vs 8, log −0.47).

## What the replay shows (measured, window 520–2000 ms)

| Leg | Best posterior MN | Rate | Hair-plate g | Other excitatory g | Inhibitory g |
|---|---|---:|---:|---:|---:|
| LF | 146498 | 81.1 Hz | 19.6 | 8.6 | −2.2 |
| LH | 144071 | 83.1 Hz | 11.3 | 22.1 | −5.7 |
| RF | 146868 | 4.1 Hz | **6.0** | **0.2** | 0.0 |

- **The caveat on Q1.** The rule assumed each hair plate delivers 120 Hz. In the engine,
  forced events are blocked during the 3.76 ms refractory period, so delivered drive is
  about two-thirds of that in every leg (LF 19.6 measured vs 31.0 mean-field). On that
  basis the RF best MN sits **below** threshold (6.0 < 8.09). The label is the
  preregistered one and stands. The rule's rate assumption was the flaw, and it is
  recorded here, not corrected.
- **RF has a second gap the factor analysis cannot see.** RF coxa MNs receive almost
  no other excitatory input (0.2), whereas LF gets 8.6 and LH 22.1 from the rest of
  the network. In LH, the other excitation is twice the hair-plate drive. So LH works
  with few synapses because the rest of the network excites it. RF works with few
  synapses and nothing else.
- **Inhibition is not the cause.** RF MNs are essentially uninhibited.

## Anatomy or reconstruction? (indicators only)

- **The RF hair-plate neurons are small overall, not just in their MN output.** Each
  RF SNpp45 neuron makes 320–378 raw output synapses in total. LF's are mostly
  680–1,320 (one has 10), and the right T2/T3 hair plates are mostly 400–1,400.
- **The status labels don't separate the cases.** All five RF neurons are labelled
  "Reviewed", as are all but one of LF's.
- **The pattern is consistent with two explanations, and the data can't decide.** One
  is a genuinely smaller RF hair-plate field. The other is under-traced RF arbors in the
  reconstruction. What can be said is that it is not a whole right-side effect: RM's
  pool is the largest of all six legs.

## Other observations (descriptive)

- **LM and RM have large hair-plate pools but stay quiet.** Their hair plates are silent
  in Step C because the encoder sits below its threshold at rest. LM's posterior MNs
  are also inhibited (−5 to −7).
- **RH's posterior MNs are silent.** Their hair-plate input is close to zero, and they
  carry net inhibition.

## Interpretation and limits

- Within the model, RF's weakness has three parts:
  1. Fewer synapses per hair-plate neuron, because the neurons are small. This is the
     main structural cause.
  2. One or two fewer hair-plate neurons than LF or LH.
  3. Almost no other excitatory drive onto RF coxa MNs, which in LF and LH adds
     substantially to the hair-plate input.
- Engine choices (the floor and size scaling) account for only 9 %.
- Limits:
  - One seed, one assisted-posture run, and passive decomposition. Mean-field g is a
    modeled prediction.
  - Connectome factors cannot separate real anatomy from reconstruction artifact.
  - Nothing was changed. Any intervention, such as a different encoder rate or a
    compensated RF pathway, would need its own versioned protocol and a stated
    scientific question.

## Reproduce

```bash
cd "$HOME/Documents/FlyBrainUnity" && PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" && "$PY" -m malecns_backend.embodiment.coxa_drive_asymmetry --cache .cache/malecns-v1 --step-c-raw docs/evidence/hair-plate-posture-v1/run/A_ON.json.gz --output .cache/coxa-drive-asymmetry-repro.json
```

Expected output, within a few minutes:
- `INTEGRITY_ACCEPTED`
- `REPLAY_EXACT`
- `RF_DIRECT_SUFFICIENT`
- `SYNAPSES_PER_SOURCE`
- `SOURCE_COUNT`
- `INHIBITION_NOT_DECISIVE`
- engine share 0.091
