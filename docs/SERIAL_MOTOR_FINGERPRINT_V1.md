# Serial motor fingerprint V1 — blind test on known leg motor neurons

Preregistered 2026-11-01 in `evidence/serial-motor-fingerprint-v1/protocol.json`
(SHA-256 locked in `malecns_backend/embodiment/serial_motor_fingerprint.py`).
Protocol, code and tests are committed before the single run.

Question: does a motor neuron's presynaptic cell-type input fingerprint identify
its annotated MaleCNS motor population in a different leg, without that leg's
labels? Partner types are MANC-style serial names shared across segments, so
fingerprints are comparable between legs.

Method: incoming synapse counts grouped by presynaptic type (untyped excluded),
L1-normalized; nearest reference-population centroid by cosine. Primary task:
the 12 same-side, different-segment leg pairs. Contralateral pairs are
descriptive. A 1000-permutation label-shuffle null (seed 20261101) tests
chance. PASS needs pooled serial type accuracy >= 0.70, p <= 0.01, joint
accuracy >= 0.60 for each admitted class (tibia, femur, femur_twist) and
T1-reference serial accuracy >= 0.70. Fewer than 10 scorable serial neurons in an
admitted class is INCONCLUSIVE.

This is offline connectome analysis only. Labels are annotations, not muscle
tracing, and may have been made partly from connectivity. A PASS would only
justify a separate protocol using the method to propose middle/hind Tarsus1
candidates; it admits nothing. Results: `SERIAL_MOTOR_FINGERPRINT_RESULTS.md`.
