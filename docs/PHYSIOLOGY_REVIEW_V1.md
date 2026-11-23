# Published physiology Step P1: what does published physiology say about the front-leg motor network? (review protocol)

Designed 2026-11-23. **Status: protocol only** (no source has been read for this review yet). This
is a preregistered literature review, the first step under the evidence charter added to
`AGENTS.md` on the same date. No simulation, and no change to the live engine.

## Why this step

- The engine fidelity steps closed the untuned route:
  - **F1:** the live engine implements its own rules correctly. No defect, so nothing to fix.
  - **F2:** the only core activity seen in the live engine is a whole-CNS state. It needs the brain,
    the rest of the nerve cord and the ascending neurons together, it depends on the calibration's
    weakened inhibition, and its output stays tonic.
- **What is missing is physiology the connectome does not contain.** Which neurons in the leg motor
  network spike and which are graded? What are their intrinsic and synaptic properties? The live
  engine gives every neuron the same spiking model, with one parameter set fitted mostly to
  brain-level benchmarks.
- **The charter now allows evidence-based, separately versioned model changes.** Before any variant
  is built, P1 collects the evidence systematically. The questions, search, inclusion rules and
  decision rules are fixed first, so sources are not picked to fit a hypothesis.

## Scope

- **The front-left leg motor network as defined by R1:** 2,111 neurons, membership sha cdcfcd23….
  That is the 68 front-left motor neurons (MNs), their premotor interneurons, and the descending
  neurons (DNs) onto those, including the core cells E1 (IN17A001_L), E2 (INXXX466_L) and
  I1 (IN16B036_L).
- **The engine's global parameters**, as they apply to that network.
- **Out of scope for P1:** proprioceptive and antennal transduction, vision, neuromodulation (recorded
  only if met incidentally), and the brain.

## Questions (declared now)

| # | Question |
|---|---|
| Q1 | **Spiking or graded.** For the cell types and hemilineages in R1's network, is there published evidence that they fire action potentials, or signal with graded potentials? |
| Q2 | **Leg motor neurons.** What intrinsic properties are published for Drosophila leg MNs: resting potential, input resistance, membrane time constant, threshold or rheobase, firing-rate range, recruitment order? |
| Q3 | **Synaptic transmission in the nerve cord.** Sign and kinetics of cholinergic, GABAergic and glutamatergic transmission onto nerve-cord neurons; graded release; electrical synapses (which the connectome omits). |
| Q4 | **Validation targets.** Which published recordings of identified leg MNs or premotor neurons, under a defined stimulus we can reproduce (for example, activation of an identified DN), could serve as held-out physiological targets? |
| Q5 | **Model precedent.** Which published connectome-constrained models of the fly nerve cord or whole CNS exist? What neuron model and parameters did they use, and what were they validated against? |

## Search plan (declared now)

- **Sources:** public literature found through web search, PubMed, PubMed Central, bioRxiv and
  publisher pages. Read-only.
  - Where only an abstract is public, the entry is marked `abstract-level`.
  - No file is downloaded without the user's OK.
  - Queries contain no personal data.
- **Declared queries.** Each is run as written; additional wording is logged as such.

| Q | Queries |
|---|---|
| Q1 | `Drosophila ventral nerve cord nonspiking interneuron`; `Drosophila premotor interneuron whole-cell recording leg`; `Drosophila leg interneuron graded potential`; `Drosophila VNC interneuron action potential patch clamp`; grade C only: `locust nonspiking local interneuron leg`, `stick insect nonspiking interneuron` |
| Q2 | `Drosophila leg motor neuron patch clamp`; `Drosophila leg motor neuron recruitment size principle`; `Drosophila tibia flexor motor neuron intrinsic properties` |
| Q3 | `Drosophila GluCl inhibition central neurons`; `Drosophila ventral nerve cord glutamate inhibitory`; `Drosophila VNC gap junction premotor`; `Drosophila central synapse cholinergic EPSP kinetics` |
| Q4 | `Drosophila descending neuron activation leg motor neuron recording`; `DNg100`; `DNa02 Drosophila`; `DNg75 Drosophila`; `Drosophila leg premotor neuron recording walking` |
| Q5 | `connectome constrained model Drosophila ventral nerve cord`; `whole brain leaky integrate and fire Drosophila connectome`; `Drosophila connectome neural network model locomotion` |

- **Snowballing:** the references and citing papers of each included primary source, one level deep.
- **Stop rule:** per question, stop after the declared queries and the one-level snowball, or at 25
  included sources, whichever comes first.
- **Search log:** every query is recorded with its date, the hits screened and each decision (included,
  or excluded with a reason).

## Inclusion and grading (declared now)

- **Included:**
  - primary measurements;
  - preprints, flagged as preprints;
  - other insects, graded C and listed separately.
- **Not counted as evidence:** reviews and textbooks. They are used for pointers only.
- **Recorded with equal weight:** contradicting, null and failed results.
- **Identity grade:**
  - **A**, the published cell is matched to a connectome type that exists in our data (for example a
    MANC or maleCNS type name, or a stated body ID);
  - **B**, a stated hemilineage or cell class present in R1's network;
  - **C**, another insect, or an analogy.
  A driver-line name alone gives no identity unless the source links it to a connectome type.
- **Extraction fields, per finding:**
  - citation and DOI, and whether it is a preprint;
  - species and stage;
  - preparation (in vivo or ex vivo) and method (patch, sharp electrode, imaging);
  - the cell identity as published, our mapping and its grade;
  - the measure, its values with units, and n;
  - a short summary in our own words (no long quotations);
  - whether the full text or only the abstract was read.
- **Checking:** every extracted value is checked against its source in a second, separate read, and
  the check is recorded.

## Decision rules (declared now)

| Rule | When it applies |
|---|---|
| D1, graded-unit candidate | A cell group in R1's network (exact type, grade A, or hemilineage, grade B) has at least one primary Drosophila recording showing no action potentials under the recorded conditions, and no grade A or B recording of the same group showing spikes. If both exist, the group is `CONFLICTING` and stays spiking. |
| D2, parameter replacement | A global engine parameter can be replaced for a class (for example, MN membrane time constant) only by measured Drosophila values at grade A or B, with n reported. Otherwise it stays `inherited`. |
| D3, synaptic sign or kinetics | The sign or kinetics of a transmitter class in the nerve cord change only with grade A or B Drosophila evidence for that class. Otherwise the engine's rule stays. |
| D4, electrical synapses | Recorded. They can enter a variant only with a published connectivity source for them; otherwise they are marked out of reach. |
| D5, held-out target candidate | A recording qualifies if the cell is identified at grade A or B, the stimulus is reproducible in our model, and the readout is quantitative (rate, sign, latency or recruitment order). |

| P1 label | Rule |
|---|---|
| `EVIDENCE_SUFFICIENT_FOR_VARIANT` | at least one change supported by D1, D2 or D3, **and** at least 2 D5 targets |
| `EVIDENCE_PARTIAL` | a supported change but fewer than 2 targets, or targets but no supported change |
| `EVIDENCE_INSUFFICIENT` | neither |

The label is computed by code from the checked extraction table, not by judgment.

## Expectations (recorded now)

- **X1:** there is no grade A physiology for E1, E2 or I1 themselves.
- **X2:** grade B evidence exists that at least one class of Drosophila nerve-cord interneuron
  signals with graded potentials.
- **X3:** published intrinsic properties and recruitment data exist for at least some Drosophila
  leg MNs (Q2).
- **X4:** the P1 label is `EVIDENCE_PARTIAL`, because supported changes are likelier than
  reproducible held-out targets.

Wrong expectations are recorded as wrong.

## What each outcome means (declared now)

- **`EVIDENCE_SUFFICIENT_FOR_VARIANT`:** design engine variant v2, with every value
  provenance-tagged, and a separate preregistered held-out validation against the D5 targets.
  Behavior tests come only after that validation.
- **`EVIDENCE_PARTIAL`:** either design a variant validated only on what targets exist, with that
  limit stated, or run a second, narrower review aimed at the gap. That choice is the user's.
- **`EVIDENCE_INSUFFICIENT`:** published physiology does not yet support a variant for this network.
  That would be a substantive result in its own right.
- **In no case** does P1 change the engine, or claim function or behavior from anatomy.

## Limits

- Public literature only. Paywalled papers are read at abstract level, which limits extraction.
- The reviewer is an AI working through web tools. It can make extraction errors (mitigated by the
  second, separate check) and has prior knowledge up to mid-2026 that could bias which sources it
  notices. The declared queries, the stop rule and the full search log are the guard against that.
- Cross-species evidence (grade C) is recorded but never enough alone for a decision.
- Identity mapping depends on published type names. Names that do not resolve to our connectome
  give grade B or C at best.
- Motor coordinates are unchanged (20/42 admitted, +4 conditional).

## Build and run plan (on approval)

1. `docs/evidence/physiology-review-v1/protocol.json`: questions, queries, stop rule, inclusion,
   grades, decision rules and expectations, locked by hash before any search.
2. `malecns_backend/evidence_review.py`: a validator for the extraction table (required fields,
   valid grades, mapping to R1's network, the second-read check) and the D1–D5 and label rules as
   code. Unit tests on toy tables.
3. Run the declared searches once. Write `search_log.json` and `evidence.json`. Do the second-read
   check, then compute the label once.
4. Record the results, handoff and roadmap.
