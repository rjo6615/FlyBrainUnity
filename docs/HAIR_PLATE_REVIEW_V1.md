# Published physiology Step P3: hair plates — identities and validation targets (review protocol)

Designed 2026-11-23. **Status: reviewed 2026-11-23: INSUFFICIENT** (CxHP8 and the other hair plates are
identified only in FANC; SNpp45 verdict UNRESOLVED; 0 targets). See `HAIR_PLATE_REVIEW_RESULTS.md`. This is a preregistered literature and dataset-annotation review under the
evidence charter in `AGENTS.md`. No simulation, and no change to the engine, the hair-plate encoder or
any earlier evidence.

## Why this step

- **P2 stopped the FeCO path.** The recorded leg interneurons and femoral chordotonal afferents are
  identified only in FANC (female nerve cord) or not at all, and FANC has no crosswalk to our male
  CNS data. There are no held-out targets.
- **Hair plates are the sense this project is furthest along with:**
  - **Step A** (`HAIR_PLATE_IDENTITY_RESULTS.md`): the male CNS type **SNpp45** shows the published
    CxHP8 output pattern in all six legs. It excites posterior-moving coxa motor neurons directly and
    inhibits anterior-moving ones in two hops.
  - **Step B:** a validated encoder that maps coxa forward position to SNpp45 drive.
  - **Step C:** in the live engine, hair-plate input raises posterior coxa motor neuron rates (+14
    Hz) with anterior ones flat. That is the published "push the leg back" direction, emerging from
    the wiring with no tuning. It is the closest thing to a corrective reflex this project has
    measured.
- **Two weak points.**
  - The identity SNpp45 = CxHP8 is **our own inference** from a wiring-pattern match (grade M-C under
    P2's rules), not a published identity.
  - The encoder's tuning was derived from walking kinematics, because no measured tuning was
    available at the time.
- **The question.** If published work identifies hair-plate afferents in a connectome that carries
  over to our data, and has measured their tuning, then the encoder (and later the reflex) could be
  validated against physiology.

P3 asks:

> Are published hair-plate afferent types identified with connectome types that carry over to our
> male CNS data, in particular, is CxHP8 SNpp45? Has their physiology been measured in a way we can
> reproduce, either afferent tuning to joint angle (for the encoder) or responses of identified
> downstream neurons (for the CNS)?

## Targets (declared now)

| Target | Published cells |
|---|---|
| H1 | CxHP8 (front-leg coxa hair plate; Pratt et al. 2026) |
| H2 | CxHP3, CxHP4 (other coxa hair plates named by Pratt et al. 2026) |
| H3 | TrHP5, TrHP6, TrHP7 (trochanter hair plates named by Pratt et al. 2026) |
| H4 | our model's SNpp45 neurons (all six legs): which published hair-plate identity, if any, do they carry? |

Other hair-plate types named by included sources are recorded as reported. They are not targets.

## Questions (declared now)

| # | Question |
|---|---|
| Q1 | **Identity.** Are H1–H3 identified with connectome neurons or types (FANC, MANC, BANC, male CNS), by what method? Is any published identity given for SNpp45 (H4)? |
| Q2 | **Crosswalk to our data.** P2's checked male CNS ↔ MANC type-level crosswalk is reused. New: does BANC's own annotation (`malecns_match` and type fields in the BANC v888 metadata already in this repository) link BANC hair-plate neurons to male CNS types, at what level? |
| Q3 | **Afferent physiology.** What has been measured for hair-plate afferents: tuning to joint angle, threshold angle, rate and adaptation? Measured in *Drosophila* first; other insects are grade C. |
| Q4 | **Downstream physiology.** Are there recordings of identified downstream neurons (premotor or motor) responding to hair-plate stimulation, with a neural readout? |
| Q5 | **Behaviour (reported only).** What do hair-plate activation or silencing do to leg movement? Recorded as predictions for a later embodied test. Never a validation target. |

## Sources and search plan (declared now)

- **Literature:**
  - public pages, read-only;
  - Europe PMC REST for full text, as P1 and P2 did; bioRxiv and arXiv HTML;
  - no bypass of bot checks, captchas, logins or rate limits; no downloads without the user's OK;
    no accounts or tokens; no personal data in queries.
- **Dataset annotations (local, already in the repository with provenance; read-only):**
  - `docs/evidence/distal-tarsus-reference-v1/banc_888_meta.feather` (BANC v888 metadata);
  - `docs/evidence/lf-anatomical-crosswalk-v1/annotations.feather` (male CNS v1.0 annotations).

  The declared query: every row whose text fields mention `hair plate`, `hairplate`, `HP` as a
  standalone token, `CxHP` or `TrHP`, plus every row typed `SNpp45`. For each, report its type,
  side, nerve and soma fields and its `malecns_match` / `manc_match` values. The query is fixed now
  and run once. Its output is a dataset-annotation entry, not a literature entry. Hashes of both
  files are recorded in the protocol.
- **Declared web queries** (web search, standard mode, each run once as written; extra wording
  logged):

| Q | Queries |
|---|---|
| Q1 | `Drosophila hair plate CxHP8 connectome`; `Drosophila leg hair plate neurons FANC reconstruction`; `hair plate sensory neurons MANC male nerve cord`; `SNpp45 Drosophila` |
| Q2 | `BANC malecns_match annotation`; `BANC brain and nerve cord connectome cross-dataset matching male CNS` |
| Q3 | `Drosophila hair plate proprioceptor calcium imaging joint angle`; `insect hair plate afferent joint angle tuning`; `cockroach hair plate receptor response`; `stick insect hair plate afferent` |
| Q4 | `hair plate activation motor neuron response Drosophila`; `hair plate reflex interneuron recording insect leg` |
| Q5 | `Drosophila coxa hair plate silencing walking`; `hair plate proprioception leg posture Drosophila` |

- **Snowball:** one level. References of each included primary source, and citing papers of Pratt
  et al. 2026 through Europe PMC.
- **Stop rule:** per question, the declared queries and snowball, or 25 included sources.
- **Search log:** every query, hit, decision, access failure and the annotation query output.

## Identity and decision rules (declared now)

- **Identity levels and carry-over:** P2's levels (M-A, M-B, M-C) and its rules R1–R5 (`MAPPED`,
  `CANDIDATE_SET`, `CONFLICTING`, `SOURCE_ONLY`, `UNMAPPED`), unchanged.
  - **Crosswalks:**
    - male CNS ↔ MANC (from P2's checked entry);
    - BANC ↔ male CNS, only if this review's annotation query is second-read and shows a type- or
      group-level `malecns_match` for the hair-plate rows. P2-style "names alone" still never
      count.
  - **Our own Step A match (SNpp45 shows the CxHP8 pattern)** is recorded as M-C: our inference,
    never decisive.
- **SNpp45 verdict (H4)**, reported on its own:

| Verdict | Rule |
|---|---|
| `SUPPORTED` | H1 is `MAPPED` to SNpp45 |
| `CONTRADICTED` | H1 is `MAPPED` to a different type, or a checked source places SNpp45 elsewhere |
| `UNRESOLVED` | otherwise |

- **E-targets (encoder validation).** A published afferent recording counts when all three hold:
  - the afferent type is `MAPPED`;
  - the stimulus is a joint angle or movement the body model can reproduce (coxa or trochanter
    angles);
  - the readout is quantitative: a tuning curve, threshold angle, or rate against angle.
- **C-targets (CNS validation).** As P2's D5: activation of a `MAPPED` hair-plate type, with a
  quantitative neural readout in a `MAPPED` downstream type. Each pair is one target.
- **Counting:** only primary entries confirmed by a separate strict second read. Grade C
  (other-insect) evidence is recorded, never counted.

| P3 label | Rule |
|---|---|
| `TARGETS_AVAILABLE` | at least 2 C-targets |
| `ENCODER_VALIDATION_AVAILABLE` | at least 1 E-target, and fewer than 2 C-targets |
| `MAPPING_ONLY` | at least one of H1–H3 `MAPPED`, but no targets |
| `INSUFFICIENT` | none of the above |

## Expectations (recorded now)

- **X1:** CxHP8 is identified only in FANC (`SOURCE_ONLY`), so the SNpp45 verdict is `UNRESOLVED`.
- **X2:** the BANC annotations link BANC hair-plate rows to male CNS types at group level, as the
  RF V2 step saw for SNpp45.
- **X3:** at least one quantitative *Drosophila* hair-plate afferent result exists (CxHP8 calcium
  against coxa angle, Pratt et al. 2026), but it cannot count while CxHP8 is not `MAPPED`.
- **X4:** zero C-targets.
- **X5:** the label is `INSUFFICIENT`.

Wrong expectations are recorded as wrong.

## What each outcome means (declared now)

- **`TARGETS_AVAILABLE`:** design a held-out CNS validation of the hair-plate reflex pathway: live
  engine v1 first, as a baseline.
- **`ENCODER_VALIDATION_AVAILABLE`:** design a preregistered check of the existing Step B encoder
  against the measured afferent tuning. That is a validation of the sensory model, not of an engine
  variant. If the encoder fails it, a corrected encoder is a separately versioned step.
- **`MAPPING_ONLY`:** the encoder's identity question is settled, but there is nothing to validate
  against yet.
- **`INSUFFICIENT`:** hair plates sit where the FeCO path sat. The variant path has no validation
  target from published physiology. The conclusion write-up (option 3 after P2) becomes the natural
  next step, unless the user chooses our own cross-dataset matching.
- **In no case** does P3 change the engine or the encoder, or make a balance claim. A mapping is an
  identity claim; afferent tuning is a sensory property.

## Limits

- Public literature and documentation, plus two annotation tables already in the repository. Their
  annotations are their authors' inferences.
- The RF V2 step found BANC's `malecns_match` to be group-level, not per-neuron, for SNpp45, so at
  best it supports type-level identity.
- Behaviour (Q5) is reported only, by charter.
- The same AI-reviewer safeguards as P1 and P2: declared queries, a full log and a separate strict
  second read.
- Motor coordinates are unchanged (20/42 admitted, +4 conditional).

## Build and run plan (on approval)

1. `docs/evidence/hair-plate-review-v1/protocol.json`: targets, questions, queries, the annotation
   query, rules, expectations, and the sha256 of both annotation files, locked before any search or
   query.
2. `malecns_backend/hair_plate_review.py`. It reuses P2's validator and mapping rules
   (`identity_review`), parameterised by the P3 target list, and adds the SNpp45 verdict, E-targets,
   C-targets, the label and the annotation query as code. Unit tests on toy tables.
3. Run the annotation query and the declared searches once. Extract `evidence.json` and
   `search_log.json`. Do the second read, then compute once.
4. Record the results, handoff and roadmap.

## Build-time notes (before any search or annotation query)

Protocol: `docs/evidence/hair-plate-review-v1/protocol.json` (sha d240f626...). It locks the sha256 of both
annotation tables (BANC 86ccf5df..., male CNS 2177e246...), P2's evidence (7ffb175e...) and
P2's type table (3a675064...). No amendments to the targets, questions, queries, rules or expectations.

**Seen before registration (disclosed):** the column names and types of both tables (schema only, no row
values), RF V2's group-level SNpp45 links, Step A, and P2's reading of Pratt et al. 2026 (CxHP8 imaged
during passive movement, reconstructed in FANC because the axons could not be found in MANC). The last
informed X1 and X3.

**As built:**
- **Reuse.** P2's levels, R1-R5 (`identity_review.mapping`), crosswalk and counting rules are called
  directly, and P2's checked male CNS <-> MANC entry is read from P2's evidence file. P2's validator is
  bound to P2's target list, so P3 has its own validator built on P2's field lists and constants.
  `identity_review.py` is unchanged.
- **Targets as code.** Six afferent targets (CxHP8, CxHP3, CxHP4, TrHP5-7) plus SNpp45 (H4). Downstream
  cells named by Q4 sources are written `D:<name>` and mapped by the same rules, so a C-target's readout
  cell can be MAPPED.
- **New entry kinds:** `annotation` (Q2, exactly one, tied to the query output by hash),
  `afferent_tuning` (Q3) and `behaviour` (Q5).
- **Annotation query.** All string-typed columns are searched. The hair-plate pattern also accepts the
  spellings `hair_plate` and `hair-plate`. `HP` is case-sensitive and must not touch a letter on either
  side. SNpp45 rows are matched by exact type. The reported fields add BANC's own `malecns_cell_type`,
  `manc_cell_type`, `fanc_cell_type` and function fields to the design's list; they are reported only.
- **BANC link.** Per BANC cell type among the hit rows: `group` if a male CNS body ID is shared by two or
  more rows, `neuron` if not, `none` without IDs. A type carries over only if it reaches exactly one male
  CNS type and every ID resolves. BANC-sourced identities are translated all or nothing.
- **Annotation names.** A table annotation that names a target is M-C (names alone), unless a checked
  source states the method that produced it.
- **SNpp45 verdict.** H4 entries state what a source places SNpp45 as (`snpp45_is`). A contradiction takes
  precedence over support. H1 MAPPED to a set that contains SNpp45 and other types is UNRESOLVED.
- **Grades.** Grade C if and only if the species is not *D. melanogaster*. E-targets need *D. melanogaster*.
- **No smoke run on real data.** The annotation query is itself a measurement and runs once. The module
  has 6 unit tests on toy tables. It refuses a changed protocol, annotation table, P2 evidence or type
  table, and writes the query output and the result once (exclusive create).
