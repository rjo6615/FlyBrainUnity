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
* **Runtime calibration to be used later:** directed pairs with at least 5 synapses, computed as a
  view without mutating the stored graph.

No modeled neural dynamics are executed in this milestone.
