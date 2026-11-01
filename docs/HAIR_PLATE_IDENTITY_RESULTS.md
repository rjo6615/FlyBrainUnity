# Hair-plate Step A — results: MATCH_ALL

2026-11-01. One connectivity-only run after commit d5e84d0. Raw output:
`evidence/hair-plate-identity-v1/run/result.json`.

| Leg | SNpp45 neurons | Posterior direct syn. | Anterior direct syn. | Top target | Net 2-hop anterior | Match |
|---|---:|---:|---:|---|---:|---|
| T1 left | 7 | 826 | 0 | Pleural remotor/abductor (445) | -269,742 | yes |
| T1 right | 5 | 194 | 0 | Pleural remotor/abductor (153) | -68,461 | yes |
| T2 left | 12 | 662 | 0 | Sternal posterior rotator (642) | -283,495 | yes |
| T2 right | 11 | 1,056 | 0 | Sternal posterior rotator (1,024) | -368,379 | yes |
| T3 left | 8 | 317 | 22 | Sternal posterior rotator (309) | -201,650 | yes |
| T3 right | 9 | 213 | 0 | Sternal posterior rotator (213) | -161,376 | yes |

One SNpp45 neuron entering via ProLN (821165) was excluded by the declared T1 rule.

## What it shows

- In all six legs, SNpp45 hair plates excite posterior-moving coxa motor neurons
  directly and (almost) never anterior-moving ones, and their two-hop network
  inhibits the anterior set: the published CxHP8 pattern, reproduced in a different
  (male) connectome with no tuning.
- The direct target differs by segment: front legs mostly the remotor/abductor,
  middle/hind legs almost entirely the sternal posterior rotator.
- Reported, not gated: the net two-hop drive onto the posterior set is also negative
  in every leg, and in T2 more negative than onto the anterior set. The reference
  predicts net excitation of posterior movement; here posterior excitation comes from
  the direct connection while the disynaptic network inhibits broadly.

## Consequence (declared in advance)

MATCH_ALL -> Step B encodes SNpp45 as a coxa forward-limit sense in all six legs.
Limits: structural evidence; the posterior/anterior population sets are a declared
mapping of the reference's FANC modules; middle/hind identity rests on serial type
plus this wiring match, not direct recordings.

## Files and checks

New: `malecns_backend/embodiment/hair_plate_identity.py`, `tests/test_hair_plate_identity.py`
(4 synthetic tests passed), `docs/HAIR_PLATE_IDENTITY_V1.md`, this file,
`docs/evidence/hair-plate-identity-v1/{protocol.json,run/result.json}`; `.gitattributes`,
handoff, roadmap.

```bash
cd "$HOME/Documents/FlyBrainUnity" && PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" && "$PY" -m malecns_backend.embodiment.hair_plate_identity --cache .cache/malecns-v1 --output .cache/hair-plate-identity-repro.json
```

Expected: `"verdict": "MATCH_ALL"`, all six legs true, in seconds.
