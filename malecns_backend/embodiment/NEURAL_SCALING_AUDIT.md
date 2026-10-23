# Live v3 neural scaling and integration audit

## Outcome

The Python port used an averaged regional median where the checked-in JavaScript
reference selects the upper middle positive size. This PR corrects that specific
constructor discrepancy. No calibration values, motor mappings, thresholds,
membrane equations, or sensory inputs are tuned.

The effect on the current canonical nerve-cord region is about **+0.001515%** in
uncapped input scale (before Float32 rounding). This is a fidelity correction,
not an explanation or demonstrated remedy for silent right-tarsus neurons.
The full CNS experiment has not been repeated after the correction.

## Reference and checks

The reference is the repository's `fly-brain-main`, specifically:

- `src/ratenet.js: regionSizeRef`: superclass region selection, positive-size
  filtering, sorted upper middle selection, neutral reference for empty regions.
- `src/brainmodel.js`: size ratio clamp, exponent, boost cap, sensory masking,
  octopaminergic fast-sign removal, Kenyon threshold and lamina bias.
- `src/lif.js`: synapse cutoff, inhibitory gain, delayed delivery, conductance
  reversal factors, membrane time step, threshold/reset, refractory and decay.
- `public/data/brain_params.json`: final checked-in calibration overrides.

`tests/js/calibrated_lif_audit.mjs` calls the actual `createBrain` and
`brainScales`, using the actual calibration file. The Python test compares
constructor scales, masks, signs, weights, thresholds and bias; then compares
160 consecutive 0.5-ms steps with mixed excitatory/inhibitory input, graded sign,
repeated probability-one external events, postsynaptic spiking, refractory and
delayed recurrent delivery. Counts and fired IDs must agree exactly; voltage and
synaptic states use documented Float32 tolerances. No cross-engine stochastic
parity is claimed. This supplements the older seven-step current-based fixture.

The new test failed on input scales before the fix and passed after it.
The audited calibrated membrane equation, signed delivery, one-time inhibitory
gain, and PSP scale agree within this fixture's tolerance. This is not exhaustive
proof of all optional configurations or long-duration whole-network equivalence.
Python retains all-neuron integration and NumPy arithmetic; JS retains its
sleep-list optimization and double intermediates. Those differences are already
documented in `malecns_backend/README.md`.

## Canonical metadata comparison

Neuron identities and superclass IDs were decoded from `neurons.flyn`; sizes came
from `neuron_size.bin`. No neural simulation was used for this table. A separate
Node execution of the actual `decodeNeurons`, `regionSizeRef` and `brainScales`
confirmed the reference medians and selected scales below.

| Region | Positive sizes | Previous Python reference | JS / corrected reference |
|---|---:|---:|---:|
| Optic lobe | 103270 | 144580656 | 144580688 |
| Central brain | 37582 | 325134432 | 325140384 |
| Nerve cord / descending / ascending | 24068 | 542733696 | 542747200 |

| Body ID | Role in report | Corrected target input scale |
|---|---|---:|
| 817210 | Right tarsus levator motor | 0.9176123 |
| 820110 | Right tarsus levator motor | 0.7895589 |
| 820896 | Right tarsus levator motor | 1.0000000 |
| 825721 | Right tarsus depressor motor | 0.7802245 |
| 801079 | Responsive right femur motor | 0.3136378 |
| 1050111955 | Responsive left tarsus motor | 0.6189696 |
| 902679 | Silent selected intermediate | 0.3695129 |
| 46348 | Silent selected intermediate | 0.3579681 |
| 800022 | Active selected intermediate | 0.1941944 |
| 903285 | Sparsely active selected intermediate | 0.4042806 |

The silent right-tarsus motors do not have uniformly lower input scales than the
responsive examples. Their synaptic input and temporal patterns differ, so this
comparison does not isolate a causal effect of size.

## Interpretation of the uploaded pathway experiment

The three 10-second conditions each contain 20000 verified samples and reproduce
the earlier motor counts (right femur 3/1/3; left tarsus 2/1/1; right tarsus 0/0/0).
In the selected path 815569 -> 800022 -> 903285 -> 820110, spike counts are
363/144/0/0 at midpoint, 404/148/2/0 upward, and 392/40/0/0 downward.
This establishes sparse intermediate recruitment under the intervention, not
causation along that selected structural route.

The raw 903285 -> 820110 connection has six synapses and a static effective signed
weight of about +2.6055 in the pre-fix report. The motor's peak excitatory state
of about 7.4656 during the upward condition includes all inputs and must not be
attributed solely to those two intermediate spikes. Synaptic state is not a
membrane voltage increment: the conductance reversal factor, dt/tau_mem, leakage,
inhibition and temporal summation determine the voltage trajectory. In that
condition 820110 remained at least 6.2316 mV below threshold in post-step samples.
Peak excitation and inhibition need not occur together; their maxima cannot be
subtracted to infer net drive or inhibitory causality.

## Model scope still matters

The Python backend explicitly removes fast octopaminergic effects when
`neuromodulation=True` but does not run the separate slow hormonal/OA system.
This is a documented scope difference, not a newly found accidental omission.
The calibration file's `_source` states that its search used neuromodulation on
with fed OA tone. The reference `src/sim/neuromod.js` also updates conductances and
threshold offsets; therefore matching the fast LIF core does not mean the live
backend reproduces the complete reference fly's physiological context.

The live mode currently supplies six tibia sensory populations. The angle assay
prescribes synchronous angles and does not add contact, other senses, slow
neuromodulation, or body feedback. This audit cannot identify which missing
context, stimulus, or model assumption accounts for the remaining silence.
Further behavioral work should state those boundaries and test a specific
hypothesis rather than lower thresholds or boost individual joints to force
activity. No additional user simulation run is required to validate this fix.

## Manual verification

From the repository root, with Python/NumPy/pytest and Node available:

```bash
python -m pytest -q tests/test_calibrated_neural_parity.py tests/test_neural_runtime.py
```

Expected: 14 tests pass, including comparison against the actual JS reference.
No Unity, FlyGym, MuJoCo, or full-CNS replay is required. Existing v3 commands
remain available, but this PR makes no promise of new movement after the small
scaling correction.

Validation in the implementation environment: 51 tests and 12 subtests passed
across calibrated parity, neural runtime, live coverage, upstream diagnostics,
CLI, motor diagnostics, headless execution and pose transport. Broader selection:
69 passed, 4 failed, 1 deselected. All four failures reproduced with the original
`newBrain` neural module: three require unavailable FlyGym, and one asserts
byte equality between differing historical activation artifacts. The expensive
full-CNS supplemental-population check was interrupted during the initial broad
run and excluded from the completed broader selection. These failures were not
changed or hidden by editing scientific artifacts. Compilation and diff checks
also passed.
