# Posture-sense inventory V1

Preregistered 2026-11-01 (`evidence/posture-sense-inventory-v1/protocol.json`, SHA-256
locked in `malecns_backend/embodiment/posture_sense_inventory.py`). Data-only: no
simulation, encoder, admission or behavioral claim.

Why: the V1.2 recordings show coxa motor neurons firing the same whether the fly is
upright or upside down; the only senses wired in are tibia angle (always) and foot
contact (off by default). This inventory asks which posture-relevant sensory
populations exist and could carry posture information to leg motor neurons.

For six organs from the official MaleCNS v1.0 annotations (hair plate, campaniform
sensilla, chordotonal organ, wind/gravity Johnston's organ, haltere, neck) it reports
exact identity matches in the simulated connectome, leg (entry nerve) and side,
overlap with the existing tibia and tactile encoders, direct and two-hop reach (edges
>= 6 synapses) to same-leg motor-neuron pools by joint class, and a declared body-signal
status. Each organ is classified READY_FOR_ENCODER_DESIGN, PARTIAL or BLOCKED by fixed
rules. Results: `POSTURE_SENSE_INVENTORY_RESULTS.md`.
