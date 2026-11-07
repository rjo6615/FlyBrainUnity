# Rhythm, Step R8 (ignition source search): results

Run 2026-11-07 under the preregistered protocol
`docs/evidence/dng100-ignition-source-v1/protocol.json` (sha 528d96a2…). The protocol, module and
tests were committed and pushed in 017bf1b before any protocol simulation, and before the partner
list was computed.
- **Run:** one command in the background, 8 reproduction plus 2,336 protocol simulations,
  1,897 s, run once and evaluated in the same process.
- **Output:** `docs/evidence/dng100-ignition-source-v1/run/result.json` (sha e4415e49…), with
  `console.txt` alongside.
- **Design:** `DNG100_IGNITION_SOURCE_V1.md` (no amendments).

This was a **neural-only rate-model simulation** of R1's isolated network. There were no weight
changes and no body or physics; the live engine was not touched.

## Verdict: SINGLE_IGNITION_SOURCE (R1SIZE, primary); VNCSIZE DISTRIBUTED_IGNITION

- **Partners:** DNg100_L has 70 direct partners in R1's network.
- **Validity passed in both arms:**
  - R1SIZE: STIM 616.5 recruited, SHAM 615.5;
  - VNCSIZE: STIM 647, SHAM 646.5.
- **Group silencing:** silencing all 70 partners left 1 recruited cell (DNg100_L alone) in both
  arms, as expected.

**R1SIZE (drive 16,000).** Exactly **one** partner prevents the ignition: dense 3694, body
**13964**.
- **Identity:** cholinergic, with no instance name in the cache.
- **Connections:** 52 synapses from DNg100_L; 68 network targets.
- **Known role:** one of DNg100_L's two-hop intermediates to E1 (R2).
- **When silenced:** median recruited is 160 (146–173 across all 16 seeds), against 616 in STIM.
  The next-lowest partners stayed ignited (581, 586, 605).
- **Secondary verdict: NO_RHYTHM_UNMASKED.**
  - With 13964 silenced, the core goes silent: E1 is active in 1/16 replicates; E2 and I1 in
    none.
  - The MN score is 0.0005.
  - So preventing the ignition this way also cuts DNg100's drive to the core.

**VNCSIZE (drive 2,000).** **No single partner** prevents the ignition; the lowest median was
639.5.
- **Silencing 13964 does the opposite:** median recruited rises to 806 (in 14/16 seeds; 2 seeds
  fell to 74 and 95).
- **DNg100_L recovers from suppression:** its rate goes from 3.5 Hz in STIM to 20.8 Hz.
- The core remains I1-dominated and non-rhythmic (score 0.020).

| Expectation | Outcome |
|---|---|
| X1 (R1SIZE DISTRIBUTED_IGNITION) | **wrong**: a single source (13964) |
| X2 (VNCSIZE DISTRIBUTED_IGNITION) | **held** |
| X3 (no rhythm unmasked) | **held** |

**Integrity.** All pass:
- I1: hashes; network; DNg100_L's dense index resolved from its body ID; 70 partners.
- **I2: all 8 reproduction simulations matched exactly** (R7 at g = 1 in R1SIZE; R3 in VNCSIZE).
- I3: 4 new tests passed (44 together with R1–R7).
- I4: 2,336 simulations, matching 2 × (70 + 3) × 16.

## What this means (per the design's declared outcomes)

- **Declared consequence of SINGLE_IGNITION_SOURCE.** In this model with R1's sizes, DNg100's
  ignition runs through one direct partner, the cholinergic cell 13964. No rhythm was unmasked,
  because the same cell is also DNg100's route into the core. Removing it leaves both the
  network and the core quiet.
- **Reading (a hypothesis, not a result).**
  - With R1's sizes, DNg100 drives the core and ignites the network through one shared relay.
    The rhythm-driving DNs reach E1 by other routes (R4: DNa02_L shares none of DNg100's
    intermediates) without that ignition.
  - With cord-only sizes, the ignition is distributed, and 13964 even appears to restrain it.
    So the "single source" depends on the size definition that R1b found less faithful.
  - A partial reduction of 13964's drive, rather than silencing, might separate its two roles.
    That would be a weight intervention needing its own preregistration.
- **In no case** does R8 show walking, assign a biological role to cell 13964, or change the
  live engine, weights, mappings or motor admission.

## Limits

- **Direct partners only,** singly and as a whole group.
- **16 seeds per condition;** one drive per size version; R1's isolated network.
- **The single source is size-dependent:** found with R1's sizes, absent with cord-only sizes.
- **Cell 13964 has no instance name** in the cache; it is identified only by body ID and
  transmitter.
- **Reconstructed rate model;** R1's transmitter signs; 68 bodymap MNs.
- **Neural only:** no body or physics. Motor coordinates are unchanged (20/42 admitted, +4
  conditional).
