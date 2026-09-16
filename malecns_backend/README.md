# MaleCNS artifact audit and headless loader

This isolated package decodes and validates the processed Male CNS v1.0 files already in
`fly-brain-main/public/data`. It does not download or regenerate data, run neural dynamics, or
integrate Unity/FlyGym. Run from the repository root:

```bash
python -m malecns_backend.audit
```

`MaleCNSData` exposes signed 64-bit body IDs and exact bidirectional body-ID/dense-index lookup,
annotation IDs and labels, outgoing (presynaptic-row) CSR connectivity and counts, neuron sizes,
graded transmitter signs, and the body map. The entropy decoder is a direct Python port of the
JavaScript FLYN/FLYG v1 codecs. The audit also compares deterministic decoded edges to the included
flat processed `graph_w3.bin` source representation to make graph direction explicit.

## Scientific provenance

* **Dataset:** Male CNS v1.0.
* **Biological data:** neuron identities, connectivity, anatomical synapse counts, annotations,
  transmitter predictions, and neuron size.
* **Processing:** filtering to traced neurons and storage of directed pairs with at least 3 synapses.
* **Milestone 1 validation view:** directed pairs with at least 5 synapses, computed without mutating
  the stored graph. The current calibrated runtime override is 6, as documented below.

## Milestone 2: calibrated headless LIF runtime

Install `requirements.txt`, then run `python -m malecns_backend.neural_audit`. The command creates a
SHA-256-bound, memory-mappable NumPy cache only after canonical decoding and validation. Canonical
files remain authoritative; changing any source artifact invalidates the cache.

The authoritative runtime calibration is the merge of `lif.js` defaults, `brainmodel.js` defaults,
and the final overrides in `public/data/brain_params.json`: dt 0.5 ms, rest/reset -52 mV, threshold
-45 mV, membrane/synapse constants 20/5 ms, delay 1.8 ms (rounded to four 0.5-ms steps), refractory
3.76 ms, PSP scale 0.55, and minimum connection count **6**. The last three deliberately differ
from the older approximate values 2.2, 0.3, and 5. Conductance mode is active (0/-76.382 mV
reversals), inhibitory gain is 0.606, size exponent 0.609, Kenyon threshold offset 10.887 mV, and
L1--L5 bias 5.281 mV. Adaptation and depression are disabled (increments zero).

Fast transmitter table model assumptions are: unknown 0, acetylcholine +1, GABA -1, glutamate -1,
dopamine +1, serotonin +1, octopamine +1, histamine -1. The calibrated path uses the graded
per-neuron `ntsign.bin` instead; because `neuromod=true`, neuron types beginning `OA-` have fast sign
zero. This only implements that graph removal—not the excluded slow neuromodulation system.

For edge `k` in presynaptic row `j` targeting `q`, the stored magnitude is
`count[k] * min(boostCap, clamp(size[q]/regionalMedian,1/20,20)^(-sizeAlpha))`, or zero below the
cutoff or when `q` is sensory. Inhibitory rows additionally multiply magnitude by `inhGain`. At
arrival, signed input is `magnitude * gradedSign[j] * wSyn * resource[j]`.

State uses contiguous NumPy arrays for voltage, excitatory/inhibitory synaptic state, refractory
time, activity trace, spike count, external drive, adaptation, depression resource, bias and
threshold offset, plus a sparse delayed-spike ring. CSR propagation is source-row to target.

### Explicit reference differences

* Python uses seeded NumPy PCG64 for optional external Poisson drive; JavaScript uses `Math.random`
  and WASM uses xorshift32. Determinism is guaranteed within Python, not cross-engine for random input.
* The CPU port follows `lif.js` update order. The WASM forced-spike path adds one `dt` to refractory,
  integrates all neurons, and performs thresholding in a separate pass; these differ from `lif.js`.
  The parity fixture therefore has no random forced spikes and compares against the pure JS reference.
* Python updates all neurons rather than reproducing the JS sleep-list optimization. Float32 state and
  equation ordering are retained; parity tolerance is absolute/relative `2e-6`.
* `delay/dt=3.6` rounds to four (JavaScript semantics here are also four), producing delivery on the
  fourth subsequent step (2.0 ms effective discrete delay).
* Noise and WASM-only background events default to zero and are intentionally not exposed by this
  milestone runtime. No endogenous drive, neuromodulator dynamics, body, or behavior is present.
