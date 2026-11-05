# Antennal gravity sense, Step A (JO zone C/E identity and wiring): results

Run 2026-11-04. The run used the preregistered protocol
`docs/evidence/antennal-gravity-identity-v1/protocol.json` (sha dcbe4e5c…), which was committed
in a0a1777 before the run. It ran once and was evaluated once. It is data only: no
simulation, no encoder, no admission. The raw output is
`docs/evidence/antennal-gravity-identity-v1/run/result.json` (sha 5b735be5…), with
`console.txt` alongside it. The design is in `ANTENNAL_GRAVITY_SENSE_V1.md`.

## Verdict: `IDENTITY_READY`

| Check | Result |
|---|---|
| A1: every C/E bodyId maps to exactly one simulated neuron | pass (none unmatched, none duplicated) |
| A2: each set has ≥ 10 neurons | pass: C 31 L / 22 R, E 157 L / 110 R |
| A3: weighted C-vs-E direct-target overlap < 0.5 per side | pass: **0.071 left, 0.039 right** |
| A4: C and E each reach a descending neuron within 2 hops, per side | pass |

## What it shows

- **The zones are strongly segregated.** C and E share only 4–7 % of their weighted direct
  targets on each side. This matches the published separation of C and E into distinct
  AMMC zones. It is a structural match only.
- **There is a direct path to descending neurons.** All four sets synapse **directly** onto
  descending neurons (DNs):

  | Set | DNs with a direct edge |
  |---|---|
  | C left | 44 |
  | C right | 18 |
  | E left | 101 |
  | E right | 83 |

  The strongest direct targets recur on both sides and in both zones: DNp73, DNp18, DNg29,
  DNp33 and DNg99 (C), and DNp73, DNp18, pIP1, DNbe001 and DNg29 (E). For example, E-left
  sends 1,219 synapses to DNp73 and 1,056 to DNp18. A gravity signal would therefore reach
  the descending pathway in one synapse, not only through the leg circuits.
- **Leg motor-neuron reach (2 hops, reported).** Reach is mostly ipsilateral (same side) and
  much larger for E than for C. E-left reaches LF/LM/LH MN pools through 48/71/85 neurons,
  and E-right reaches RF/RM/RH through 16/40/37. C reaches through 0–8 neurons per leg.
- **A4 is a weak check.** Within two hops, every set reaches hundreds of DNs (437–795). A4
  was certain to pass for any well-connected population. It establishes reachability, not
  specificity.

## A left/right asymmetry that Step B must handle

| Zone | Neurons, left/right | Output synapses (edges ≥ 6), left/right |
|---|---|---|
| C | 31 / 22 = 1.41 | 8,881 / 1,672 = **5.31** |
| E | 157 / 110 = 1.43 | 80,370 / 31,621 = **2.54** |

The synapse asymmetry is much larger than the neuron-count asymmetry. Right-side neurons
are not only fewer but also far less connected. This fits incomplete right-side
reconstruction: all 475 carry `statusLabel = "RT Hard to trace"`, and 92 of the 96 untyped
JO-unclear neurons are on the right. The 92 right `JO-unclear` neurons overlap only a little
with the typed right C (0.090) and E (0.012) sets. This is descriptive and is not used to
assign them.

The design's table counted JO-mz (2 left) as untyped (6 left). By the preregistered rule,
JO-mz falls under "other" types (36 left, not 34). So untyped is 4 left and 92 right, 96 in
all. The C and E sets are unaffected.

**Consequence.** An encoder that drives these sets symmetrically would give the CNS a left
input roughly 2.5–5 times stronger than the right for the same stimulus. In a live test,
that bias could look like a roll signal. The bias would be built in by the reconstruction,
not by the body. Step B must declare a handling rule **before** it inspects any output.
Options include:
- using the sets as reconstructed, and labelling the bias;
- restricting a live test to a quantity that does not compare left with right, such as
  pitch;
- running each side as its own arm.

Choosing a rule after seeing outcomes would be tuning.

## Limits

- This is structural only. Reach and segregation do not show function or transduction.
- The published structure is cited from memory (Kamikouchi et al. 2009) and treated as a
  hypothesis.
- Zone sign (which zone prefers which deflection) is not addressed. Step B tests it as G1
  against G1_FLIP.
- Identity completeness: every neuron is "RT Hard to trace", and right-side typing is
  incomplete.
- Nothing here changes motor coverage: 20/42 admitted, +4 conditional.

## Files and checks

New files:
- `malecns_backend/embodiment/antennal_gravity_identity.py`, which reuses
  `posture_sense_inventory` (`adjacency`, `motor_pools`, `sha`);
- `tests/test_antennal_gravity_identity.py`: 6 synthetic tests, which pass together with
  the 5 `posture_sense_inventory` tests (11 passed);
- the protocol and run output;
- this file.

Also updated: `.gitattributes`, the design status line, the handoff and the roadmap.

Reproduce in Git Bash, from the repository root. The connectome cache is local.

```bash
PYTHONPATH="$PWD" "$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" -m malecns_backend.embodiment.antennal_gravity_identity --cache "$HOME/Documents/FlyBrainUnity/.cache/malecns-v1" --output .cache/antennal-gravity-identity-repro.json
```

Expected: `IDENTITY_READY`, with overlaps of 0.071 (left) and 0.039 (right), in under a
minute.
