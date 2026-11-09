# Engine fidelity audit, Step F1: results

Run 2026-11-08, once, from the preregistered commit 5c1819b (protocol
`docs/evidence/engine-fidelity-audit-v1/protocol.json`, sha ebb68ffc…). 288 simulations of 3 s,
2,484 s, run and evaluated once in the same process. Output: `run/result.json` and `run/console.txt`.
Design: `ENGINE_FIDELITY_AUDIT_V1.md`, including its build-time notes.

This was a **neural-only simulation**: no body or physics. The live engine, its calibration,
weights, signs and mappings were not changed. Part B's swaps existed only in model copies.

## Verdict: Part A `NO_DEFECT_FOUND`; Part B `NOT_THESE_RULES`

- **No implementation defect was found.** The engine implements its own declared rules on the real
  data for the front-left network.
- **None of the four swappable rules lets DNg75_R or DNa02_L engage the core**, alone or together.
- **Unplanned observation (reported, not gated).** DNg100_L already engages the core in the live
  engine, and that engagement disappears when the network is isolated or when inhibition is
  restored to full strength.

| Expectation | Outcome |
|---|---|
| XA (`NO_DEFECT_FOUND`) | **held** |
| XB (`NOT_THESE_RULES`) | **held**, for the two DNs that could count |
| XB's aside (if a single swap engages, S1 ISOLATED is most likely) | **wrong in direction**: isolation engaged nothing and removed DNg100_L's engagement |

**A correction to the design's framing.** The design's title and summary said that descending drive
does not reach the core. That holds for DNg75_R and DNa02_L. It does not hold for DNg100_L, whose
core rates in the live engine had not been looked at when F1 was designed. V1 had found its motor
output tonic, not that its core was silent.

**The pre-run amendment decided the label.** Before any protocol simulation, the build notes added
the rule that a DN already engaged in LIVE cannot count. DNg100_L is engaged in S0, S2 and S4. Under
the design's literal wording, S2 and S4 would have given `SINGLE_RULE_ENGAGES`, from a DN those swaps
did not switch on. The amended rule gives `NOT_THESE_RULES`. The amendment was made without
knowledge of the outcome, but its consequence is recorded here.

## Integrity

| Check | Result |
|---|---|
| Z1 sources, cache fingerprints, network membership | pass |
| Z2 S0 reproduces L1 exactly (DNg75_R, DNa02_L; 100 and 200 Hz; seeds 1–8; 32 simulations) | pass |
| Z3 each config differs from LIVE only in its declared rule | pass (table below) |
| Z4 288 simulations of 3 s | pass |

| Config | Options changed | Weights changed | Signs changed |
|---|---|---|---|
| S0 LIVE | none | 0 | 0 |
| S1 ISOLATED | none (edges outside R1's network zeroed) | 4,961,105 | 0 |
| S2 MINSYN5 | `min_synapses` | 1,121,805 | 0 |
| S3 INHGAIN1 | `inhibitory_gain` | 1,860,773 | 0 |
| S4 BINARYSIGN | `graded_sign` | 20,032 | 3,079 |
| S5 ALL | the three above, isolated | 4,991,697 | 3,079 |

## Part A: defect checks (gated)

| Check | Result | Detail |
|---|---|---|
| A1 configuration | pass | 11 mapped keys equal `brain_params.json` |
| A2 port parity | pass | existing `lif.js` parity test |
| A3 weights on real data | pass | 9,876 edges into E1, E2, I1 and the 68 MNs (6,256 nonzero); 0 mismatches, exact in float32 |
| A4 signs | pass | 2,090 known-transmitter neurons (777 negative, 1,313 positive), all with magnitude 1; 21 `unknown` MNs reported; no OA-type neuron in the network |
| A5 sizes and regions | pass | factors, medians and regions equal; no DN, AN or VNC neuron outside region 2 |
| A6 identities | pass | 3 DNs, 3 core cells, 68 MNs |
| A7 sensory mask | pass | removes only edges onto sensory targets: 76,574 in the whole graph, 56 inside the network |

Part A shows that the engine does what its rules say. It does not show that those rules are right
for the nerve cord.

## Part B: single-rule swaps (diagnostic, never adopted)

Median E1 / E2 / I1 rates over 250–3,000 ms (Hz), and the number of seeds (of 8) with E1 and E2 both
at 10 Hz or more. The bar is declared.

| Config | DNg100_L 100 Hz | DNg100_L 200 Hz | DNg75_R 200 Hz | DNa02_L 200 Hz |
|---|---|---|---|---|
| S0 LIVE | 26.2 / 40.9 / 7.5 (8) | 28.5 / 43.1 / 8.4 (8) | 0 / 0 / 0 (0) | 4.0 / 7.6 / 3.8 (0) |
| S1 ISOLATED | 0 / 0 / 0 (0) | 0 / 0 / 0 (0) | 0 / 0 / 0 (0) | 4.2 / 8.2 / 4.0 (0) |
| S2 MINSYN5 | 25.1 / 38.7 / 8.5 (8) | 27.3 / 42.0 / 9.1 (8) | 0 / 0 / 0 (0) | 4.2 / 4.2 / 0 (0) |
| S3 INHGAIN1 | 0 / 0 / 0 (0) | 0 / 0 / 0 (0) | 0 / 0 / 0 (0) | 4.2 / 4.2 / 0 (0) |
| S4 BINARYSIGN | 24.9 / 39.5 / 6.7 (8) | 27.5 / 42.4 / 6.9 (8) | 0 / 0 / 0 (0) | 4.0 / 7.6 / 3.8 (0) |
| S5 ALL | 0 / 0 / 0 (0) | 0 / 0 / 0 (0) | 0 / 0 / 0 (0) | 4.0 / 4.0 / 0 (0) |

At 100 Hz, DNg75_R is silent at the core in every config, and DNa02_L has at most 0.4 Hz.

**DNg100_L in more detail (reported):**
- In S0, it has 12 active front-left MNs in every seed. Its rhythm scores are 0.16–0.26, so the
  output stays tonic even with the core firing.
- About 2.3 % of the whole CNS is active (roughly 3,800 neurons).
- In S1 and in S3, it has no active MN and no core spike in any seed.

## Part C: how the core's inputs are weighted (description)

| Cell | LIF size factor | Size ratio s | Rate gain | Rate threshold | Edges only the 5-synapse floor keeps (in network) |
|---|---|---|---|---|---|
| E1 | 0.265 | 8.84 | 0.113 | 66.3 | 17 (12) |
| E2 | 0.371 | 5.09 | 0.196 | 38.2 | 8 (7) |
| I1 | 0.571 | 2.51 | 0.398 | 18.8 | 9 (8) |

Summed live input to each cell (mV of PSP per presynaptic spike, all sources):

| Cell | Excitatory, in network | Inhibitory, in network | Excitatory, outside | Inhibitory, outside |
|---|---|---|---|---|
| E1 | 651.7 | −297.9 | 30.8 | −22.5 |
| E2 | 331.4 | −165.7 | 4.5 | −4.9 |
| I1 | 122.1 | −53.8 | 16.7 | −1.3 |

- Almost all of the core's direct input comes from inside R1's network.
- Of the three DNs, only DNg75_R has a direct connection to any core cell: onto E1, 0.88 mV against
  the engine's 7 mV gap from rest to threshold.
- **The strongest 2-hop routes in the live weights:**
  - DNg100_L to E1 runs through DNg100_R and IN01A018_R;
  - DNg75_R to E1 runs through IN17A025_L;
  - DNa02_L to E1 and E2 runs through INXXX468_L.

  The rate model's top 2-hop routes share most of these intermediates (`result.json`).

## Reading (a hypothesis, not a result)

- **The audit gives no fix.** With no defect, no engine change is justified. The gap between the
  rate model and the live engine for DNg75_R and DNa02_L lies outside these four rules. The remaining
  candidates are the ones F1 could only describe: the unit type, the size rule and the drive form.
- **DNg100_L's core activity looks like a whole-CNS state, not a feed-forward route.** Nearly all of
  E1's direct input is inside the network, yet removing the rest of the CNS abolishes the
  engagement. So what is lost is probably further upstream or recurrent. It also needs the
  calibrated weakening of inhibition: at full inhibitory strength it is gone. That parameter was
  fitted mainly to brain-level benchmarks.
- This resembles the all-or-none ignition seen in the rate model (R2), but F1 did not test that.

## Declared consequence

`NO_DEFECT_FOUND` + `NOT_THESE_RULES`: the design's next step is a desk review of neuron-model
evidence for the core cells (spiking versus graded), before any simulation. The DNg100_L observation
raises a second question, which would need its own design: which part of the rest of the CNS
supports the engagement.

**In no case** does F1 show rhythm, balance, walking or a biological role. Part B's swaps are probes,
not proposed parameters.

## Limits

- One leg network (front-left) and three DNs, with DNg100_L excluded from Part B's label.
- Part B tests four rules singly and together, not every combination.
- The 10 Hz bar is declared, not derived. DNa02_L at 200 Hz is below it at 4–8 Hz.
- The unit type, size rule and drive form are described, not swapped.
- Part A checks the engine against its own rules on this network, not the rules themselves.
- Motor coordinates are unchanged (20/42 admitted, +4 conditional).

## Evidence

- `docs/evidence/engine-fidelity-audit-v1/protocol.json` (sha ebb68ffc…).
- `docs/evidence/engine-fidelity-audit-v1/run/result.json` and `run/console.txt` (committed).
