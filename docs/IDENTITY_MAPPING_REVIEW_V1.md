# Published physiology Step P2: which connectome types are the recorded cells? (identity-mapping review protocol)

Designed 2026-11-23. **Status: protocol only** (no source has been read for this review yet). This is a
preregistered literature review under the evidence charter in `AGENTS.md`. No simulation, and no change
to the live engine or to any earlier evidence.

## Why this step

P1 (`PHYSIOLOGY_REVIEW_RESULTS.md`) ended `EVIDENCE_PARTIAL`, held back by identity:

- **The graded candidates are only at hemilineage level.** 13Bα and 10Bα (Agrawal et al. 2020) have no
  detectable or identifiable action potentials, but neither cell type is linked to a connectome type.
  We cannot say which of our neurons they are: the male CNS data has 97 IN13B types and 33 IN10B
  types.
- **There are no held-out targets (D5 = 0).** The most promising candidate was Chen et al. 2021:
  calcium responses of identified nerve-cord classes when femoral chordotonal organ (FeCO) afferent
  subtypes are activated optogenetically. It fails only because neither the stimulated afferents nor
  the recorded classes are mapped to our connectome. Activating identified afferent types is
  something the neural-only engine can do.
- **The motor-neuron parameters are class-level only.** Azevedo et al. 2020's fast, intermediate and
  slow tibia flexor neurons are not matched to connectome neurons.

P2 asks:

> For the cells P1's evidence rests on, has published work identified them with connectome types or
> neurons, in a way that carries over to our male CNS v1.0 data? And are there published
> experiments that stimulate identified cells and record identified cells, in the adult leg nerve
> cord, with a neural readout?

## Targets of the mapping (declared now)

| # | Published cells | Source of the physiology |
|---|---|---|
| T1 | 13Bα | Agrawal et al. 2020 |
| T2 | 10Bα (and Chen 2021's 10Ba) | Agrawal et al. 2020; Chen et al. 2021 |
| T3 | 9Aα, 9Aα2 | Agrawal et al. 2020 |
| T4 | FeCO afferent subtypes: club, claw (flexion, extension), hook (flexion, extension) | Mamiya et al.; Chen et al. 2021 |
| T5 | Chen 2021's second-order classes (8Aa, 9Ba, 9Bb, 10Ba, 13Ba, 13Bb, 19Aa, 19Ab, 20/22Ab) | Chen et al. 2021 |
| T6 | Tibia flexor MNs: fast (R81A07), intermediate (R22A08), slow (R35C09) | Azevedo et al. 2020 |

## Questions (declared now)

| # | Question |
|---|---|
| Q1 | **Crosswalk.** Is there published evidence that male CNS v1.0 nerve-cord types correspond to MANC (and/or FANC, BANC) types? How was it established, and at what level (type, or per neuron)? |
| Q2 | **Interneuron identities (T1–T3, T5).** Has published work matched these driver-line cell types to connectome types or neurons (MANC, FANC, BANC or male CNS)? |
| Q3 | **Afferent identities (T4).** Are the FeCO subtypes identified with connectome sensory types or neurons? |
| Q4 | **Motor neuron identities (T6).** Are the fast, intermediate and slow tibia flexor MNs identified with connectome neurons or types? |
| Q5 | **Functional-connectivity targets.** Which published adult leg nerve-cord experiments stimulate identified cells (optogenetically or electrically) and record identified cells, with a neural readout (calcium or electrophysiology)? |

## Search plan (declared now)

- **Sources:**
  - public literature and public documentation pages, read-only;
  - open-access full texts through Europe PMC's public REST service, preferred because PMC and eLife
    served bot checks to the reading tools in P1;
  - bioRxiv and arXiv HTML.
- **Never:** bypass a bot check, captcha, login or rate limit; download a file without the user's OK;
  use accounts or tokens (so neuPrint and similar authenticated services are out of scope); put
  personal data in queries.
- **Declared queries** (web search, standard mode, each run once as written; extra wording logged):

| Q | Queries |
|---|---|
| Q1 | `male CNS connectome Drosophila ventral nerve cord cell types matched MANC`; `maleCNS connectome cell type annotation`; `MANC FANC cell type matching ventral nerve cord`; `BANC brain and nerve cord connectome cell types` |
| Q2 | `13B hemilineage leg proprioception connectome cell type`; `13Bα neurons femoral chordotonal organ connectome`; `10Bα neuron Drosophila connectome`; `9Aα interneuron vibration connectome Drosophila` |
| Q3 | `femoral chordotonal organ club claw hook connectome`; `FeCO axon types MANC`; `Drosophila leg proprioceptor connectome types` |
| Q4 | `tibia flexor motor neuron connectome fast slow Drosophila`; `Drosophila leg motor neuron identification FANC` |
| Q5 | `Drosophila ventral nerve cord functional connectivity optogenetics calcium imaging identified neurons`; `leg premotor neuron response optogenetic activation Drosophila`; `Drosophila ventral nerve cord whole-cell recording optogenetic activation interneuron` |

- **Snowballing:** one level, as in P1. References of each included source; for the central sources,
  citing papers through Europe PMC's citations service.
- **Stop rule:** per question, the declared queries and the snowball, or 25 included sources,
  whichever comes first.
- **Search log:** every query, hit screened, decision and access failure is recorded.

## Identity evidence (declared now)

| Level | Meaning |
|---|---|
| **M-A** | A source states that the recorded cell (driver line or light-level image) is a specific connectome type, or specific neurons. The match must be made by an explicit method: EM-to-light morphology matching, NBLAST, sparse labelling with EM reconstruction, or a cross-dataset typing procedure. |
| **M-B** | A source matches the recorded cell to a **set** of candidate connectome types. |
| **M-C** | Anything weaker: shared hemilineage, similar morphology described in words, or our own inference. Recorded, never decisive. Names alone never establish identity. |

**Carrying over to our data.** A type named in MANC, FANC or BANC counts as present in our data only if
both hold:
- Q1 finds a published crosswalk at type level for that dataset (for example, male CNS nerve-cord
  types transferred from or matched to MANC);
- the type name exists in our cache.

Without a crosswalk, a mapping stays at the source dataset and is reported as such.

## Decision rules (declared now)

Every entry is checked by a separate second read, under P1's strict rule: the core claim is confirmed
in text the checker read verbatim, and summary-only support counts as not found. Only checked M-A or
M-B entries count.

| Rule | Outcome per target |
|---|---|
| R1 `MAPPED` | at least one M-A entry gives a type (or neurons) present in our data, and no M-A entry conflicts |
| R2 `CANDIDATE_SET` | only M-B entries, with all candidate types present in our data |
| R3 `CONFLICTING` | M-A entries disagree |
| R4 `SOURCE_ONLY` | M-A or M-B in MANC, FANC or BANC, but no crosswalk to our data |
| R5 `UNMAPPED` | none of the above |

**What follows from the mapping (computed by code, as a new versioned result; P1's evidence and
result stay unchanged):**

- **D1 at type level.** For T1 and T2, P1's graded-unit candidate is restated for the mapped types (R1)
  or the candidate set (R2), with their count in R1's network. It stays at hemilineage level
  otherwise.
- **D5 targets.** A functional-connectivity experiment (from Q5, or Chen 2021 re-extracted under P2
  with correct class names) becomes a held-out target candidate when all three hold:
  - every stimulated cell type is `MAPPED`;
  - every recorded cell type is `MAPPED`;
  - the readout is quantitative at the level the model can produce: presence, sign, relative size
    or latency rank of the response.

  Each pairing of one stimulated type with one recorded type is one target.
- **D2 at type level.** For T6, P1's motor-neuron parameters are restated per mapped MN type.

| P2 label | Rule |
|---|---|
| `TARGETS_AVAILABLE` | at least 2 D5 targets |
| `MAPPING_ONLY` | fewer than 2 targets, but T1 or T2 is `MAPPED` or `CANDIDATE_SET` |
| `INSUFFICIENT` | neither |

## Expectations (recorded now)

- **X1:** a published crosswalk exists between male CNS nerve-cord types and MANC types (Q1).
- **X2:** 13Bα and 10Bα are not `MAPPED` to single types. At best they are `CANDIDATE_SET` or
  `SOURCE_ONLY`.
- **X3:** the FeCO subtypes (T4) are identified in at least one connectome (M-A), possibly only as
  `SOURCE_ONLY`.
- **X4:** the label is `MAPPING_ONLY`.

Wrong expectations are recorded as wrong.

## What each outcome means (declared now)

- **`TARGETS_AVAILABLE`:** design the held-out validation, a separate preregistered step. It would
  define how the targets are simulated (drive of the mapped afferent types; readout of the mapped
  recorded types, in the live engine v1 first, as a baseline) and the pass criteria, before any
  engine variant is built.
- **`MAPPING_ONLY`:** the graded candidates can be placed on specific types, but there is still
  nothing to validate a variant against. The next step would be a targets-only review, or the user's
  decision to stop the variant path here.
- **`INSUFFICIENT`:** published identity work does not yet connect this physiology to our connectome.
  That is a substantive result in its own right.
- **In no case** does P2 change the engine, or claim function or behaviour from anatomy. A mapping is
  an identity claim, not a physiological one.

## Limits

- Public literature and documentation only. Authenticated connectome services are out of scope, so
  mappings published only inside such services cannot be checked.
- Cross-dataset type matches are themselves inferences made by their authors. P2 records how they were
  made but does not re-verify them.
- An AI reviewer working through web tools, with P1's safeguards: declared queries, a full log, and a
  separate second read.
- Motor coordinates are unchanged (20/42 admitted, +4 conditional).

## Build and run plan (on approval)

1. `docs/evidence/identity-mapping-v1/protocol.json`: targets, questions, queries, levels, rules,
   expectations, locked by hash before any search.
2. A whole-dataset type table, `type_table.json`, structure only: every type name in our cache with
   its count and superclass, and which are in R1's network.
3. `malecns_backend/identity_review.py`: entry validator, R1–R5, the D1, D2 and D5 restatements, and
   the label as code. Unit tests on toy tables.
4. Run the declared searches once. Extract `evidence.json` and `search_log.json`. Do the second read,
   then compute once.
5. Record the results, handoff and roadmap.
