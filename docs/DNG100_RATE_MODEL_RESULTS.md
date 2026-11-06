# Rhythm, Step R1 (the preprint's DNg100 rate model on our connectome): results

Run 2026-11-06 under the preregistered protocol
`docs/evidence/dng100-rate-model-v1/protocol.json` (sha 3785bbeb…). The protocol was
committed and pushed in 2ba19bd before any protocol simulation.
- **Run:** one command, 592 replicates, 87 s, run once and scored in the same process.
- **Output:** `docs/evidence/dng100-rate-model-v1/run/result.json` (sha 24062901…), with
  `console.txt` alongside.
- **Design:** `DNG100_RATE_MODEL_V1.md`. It includes the build-time amendments: scored MNs are
  kept regardless of transmitter, and timing used one driven replicate with seed 0.

This was a **neural-only rate-model simulation** of an isolated 2,111-neuron front-left network
built from our maleCNS wiring. No body or physics were involved, and the live engine was not
touched.

## Verdict: RATE_RHYTHM_NOT_REPRODUCED

| Criterion | Required | Observed | Met |
|---|---|---|---|
| C1 rhythm | DNG100 score ≥ 0.5 and > control 80th percentile | 0.0 (control p80 0.067) | no |
| C2 frequency | 5–20 Hz | none (no MN with a qualifying peak) | no |
| C3 necessity | SIL_E1, SIL_E2, SIL_I1 each < 0.5 | 0.0 / 0.0 / 0.0 | yes, but **vacuous** (see below) |

| Prediction | Outcome |
|---|---|
| P1 (C1 holds) | **wrong** |
| P2 (SIL_I1 < 0.5) | held, vacuously |
| P3 (5–20 Hz) | **wrong** |

**Integrity.** All pass:
- I1: the source hashes, the network body-ID hash and the control draw matched at run start;
  the run would have stopped otherwise.
- I2 and I3 passed before the run (13 tests).
- I4: all 592 replicates are present.

## What happened: the preprint's drive rule never engaged the circuit

The verdict follows the preregistered rules. The diagnostics show **why** there is no rhythm:
the DNg100 drive that the preprint's adjustment rule selects barely spreads through our
network. So R1 did **not** test whether an engaged E1–E2–I1 core oscillates.

**DNG100 (64 replicates).**
- Every replicate met the rule's "≥ 5 recruited neurons" bound after 2 or 3 doublings:
  - I_stim 1,000 in 37 replicates and 2,000 in 27;
  - a median of 7 recruited neurons, at most 46.
- **58 of 64 replicates had no active front-left MN.** The other 6 had 1–3 active MNs: Pleural
  remotor/abductor (9 MN-instances) and Tr flexor (2).
  - Peak MN rates were 0.09–3.3 Hz.
  - None had a rhythmic peak, so the score is 0 and there is no frequency.
- No replicate had both tibia flexor and extensor active, so no phase could be computed.

**The core cells were never active.** SIL_E1, SIL_E2 and SIL_I1 are **bit-identical** to
DNG100 in every replicate. Silencing a cell whose rate is already zero changes nothing. So
C3 "held" without anything to abolish.

**Controls (20 network ACh DNs, 16 replicates each).**
- 19 of 20 met the rule at I_stim 125–2,000. Control 21341 never reached 5 recruited neurons,
  even at 256,000.
- Only three controls recruited MNs:
  - DNg12_e_R (index 9205): about 475 neurons and 21 MNs, score 0.067, 9.9 Hz;
  - DNg12_e_L (11053): about 470 neurons and 20 MNs, score 0.070, 9.7 Hz;
  - DNg12_e_L (39896): about 30 neurons and 3 MNs, score 0.053, 4.8 Hz.
- All are tonic, far below 0.5.

**Baseline.** No neuron was active.

**Size scaling is a likely contributor** (structural fact, not tested). With
s = size / VNC median (542,747,200):

| Cell | s |
|---|---|
| DNg100_L | 30.7 |
| E1 | 8.8 |
| E2 | 5.1 |
| I1 | 2.5 |
| DNg12_e controls (for comparison) | 1.7–1.9 |

- In the model, a = a*/s and θ = θ*·s. At I = 250, DNg100_L sits only just above its
  threshold (θ ≈ 230), with a slope of a ≈ 0.033, so it fires below 1 Hz.
- Large downstream cells need proportionally more input.
- 49 neurons in the network have s > 20; the preprint caps nothing.
- Whether our size units and median match the preprint's MANC volume normalisation was **not
  verified**: the preprint does not report its median value.

## What this shows

- With the preprint's model, parameters and stopping rule applied to our wiring as
  reconstructed here, **DNg100_L does not drive the front-left motor neurons, rhythmically or
  otherwise.** The run stops at a drive that recruits a handful of neurons.
- This differs from Stage 1 V1 (LIF engine). There, DNg100 recruited 12 front-left MNs
  tonically.

## What this does not show

- **It does not show that our wiring lacks a rhythm generator.** The E1–E2–I1 core was never
  active, so its dynamics were not probed. C3 is vacuous.
- **It does not separate wiring from engine**, which was the question R1 was designed to
  answer. Under the declared drive rule, the comparison never reaches the core. The declared
  reading of NOT_REPRODUCED ("the preprint's rhythm does not transfer to our wiring") is
  therefore **not supported** by these data. The verdict is recorded as computed; this caveat
  is added after seeing the diagnostics.
- **Not a test of the preprint.** This is our reconstruction:
  - b comes from ratenet.js;
  - "recruited" is read as active network neurons;
  - the MN set and connectome differ;
  - 64 replicates instead of 1,024.
- **Neural only.** No body, gait or balance. No motor coordinate status change (20/42
  admitted, +4 conditional).

## Possible next steps (not run; each would be its own versioned design)

Raising drive until something oscillates would be tuning, so it is not an option. Questions
that could be designed instead:
- **Size-normalisation fidelity.** Check whether our size units, region median and the
  absence of a cap match the preprint's MANC volume normalisation. This could use only local
  data, by comparing the size distributions of matched cell types. If it shows a demonstrated
  implementation defect, correct it with evidence and re-ask R1 as a v2.
- **Descriptive recruitment map.** At fixed, declared drives, record where DNg100's signal
  stops, layer by layer to E1/E2/I1 and the MNs. Report it, without a rhythm criterion.

## Reproduce

```bash
P="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
PYTHONPATH="$PWD" "$P" -m malecns_backend.embodiment.dng100_rate_model --cache "$HOME/Documents/FlyBrainUnity/.cache/malecns-v1" --output /tmp/r1_repro.json
```

This takes about 1.5 minutes. The output path must not exist. It is deterministic, so expect
`"verdict": "RATE_RHYTHM_NOT_REPRODUCED"` with the numbers above.
