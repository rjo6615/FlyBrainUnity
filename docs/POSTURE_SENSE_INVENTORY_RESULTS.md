# Posture-sense inventory V1 — results

2026-11-01. One data-only run after commit 0bbc0d9 (2.4 s). No simulation, encoder or
admission. Raw output: `evidence/posture-sense-inventory-v1/run/inventory.json`.

| Organ | Annotated / matched | Leg+side assigned | Legs with 2-hop reach | Already encoded | Body signal | Class |
|---|---|---|---|---|---|---|
| Hair plate | 113 / 113 | 60 | 4 of 6 | 0 | joint angle, no encoder | PARTIAL |
| Campaniform sensilla | 426 / 426 | 12 | 4 of 6 | 0 | load, no transduction model | PARTIAL |
| Chordotonal organ | 425 / 425 | 392 | 6 of 6 | 392 (tibia encoder) | existing encoder | READY_FOR_ENCODER_DESIGN |
| Wind/gravity JO | 475 / 475 | n/a (antenna) | 178 neurons reach leg MNs in 2 hops | 0 | no transduction model | PARTIAL |
| Haltere | 205 / 205 | n/a | 163 neurons, 2 hops | 0 | no transduction model | PARTIAL |
| Neck | 2 / 2 | n/a | none | 0 | unverified | PARTIAL |

Every annotated neuron exists in the simulated connectome (100% identity match).

## Findings

- **Hair plates connect directly to coxa motor neurons.** In the four legs the rule
  could assign (T2, T3), hair plates make direct edges onto coxa-rotator (coxa_twist)
  MN pools: 13 neurons / 663 synapses (T2 left), 10 / 1,024 (T2 right), 7 / 331
  (T3 left), 6 / 224 (T3 right), plus femur pools (91-420 synapses). Every
  assigned hair plate reaches its leg's coxa pools within two hops. This is the
  strongest structural candidate for coxa position feedback. None is encoded today.
- **Front-leg hair plates were missed by the preregistered nerve rule.** Only one
  hair plate enters through ProLN; 35 enter through PrN, 12 VProN and 6 DProN, which
  the rule did not map to T1. PrN is the prosternal nerve (likely neck/prosternal
  hair plates), so a refined front-leg mapping needs its own justified protocol;
  V1's classification is kept.
- **Leg load sense is essentially unannotated.** Of 426 campaniform sensilla, 413
  enter through wing (ADMN) or haltere (DMetaN) nerves; only 2 per leg are leg CS.
- **Joint-angle sense is the only one already wired**: the tibia encoder uses 392
  of the 425 chordotonal neurons (33 ProCN neurons are not encoded).
- **Antenna (gravity/wind) and haltere neurons reach leg motor neurons in two hops**
  (178 and 163 neurons), but both need transduction models the body doesn't have.

## Consequence

The best-supported next sense is middle/hind-leg hair plates encoding coxa joint
angle: identities exact, leg/side assigned, direct anatomical path to coxa MNs, and
the coxa angles are measurable. Open questions for that protocol: which joint each
hair plate reports (coxal vs trochanteral plates), preferred-angle tuning (no
measured tuning is available, as with the existing tibia encoder), and the front
legs. Structural reach is not functional influence.

## Files and checks

New: `malecns_backend/embodiment/posture_sense_inventory.py`,
`tests/test_posture_sense_inventory.py` (5 synthetic tests passed in 0.68 s),
`docs/POSTURE_SENSE_INVENTORY_V1.md`, this file,
`docs/evidence/posture-sense-inventory-v1/{protocol.json,run/inventory.json}`;
`.gitattributes`, handoff, roadmap.

```bash
cd "$HOME/Documents/FlyBrainUnity" && git lfs pull --include="docs/evidence/lf-anatomical-crosswalk-v1/annotations.feather" && PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" && "$PY" -m malecns_backend.embodiment.posture_sense_inventory --cache .cache/malecns-v1 --output .cache/posture-inventory-repro.json
```

Expected: the classification above, in a few seconds.
