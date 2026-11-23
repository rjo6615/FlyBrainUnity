# Published physiology Step P2 (identity-mapping review): results

Reviewed 2026-11-23, once, from the preregistered commit 5b4e526 (protocol
`docs/evidence/identity-mapping-v1/protocol.json`, sha 9c7919bc…, no amendments). 16 declared queries, a
one-level snowball (references, plus citing papers of the two central sources), 12 extracted entries.
Every entry got a separate second read, and the result was computed once by
`malecns_backend/identity_review.py`. Outputs: `evidence.json`, `search_log.json` and `result.json` in
the same folder. Design: `IDENTITY_MAPPING_REVIEW_V1.md`.

This is a literature review. No simulation was run, and the engine and P1's evidence and result are
unchanged.

## Verdict: `INSUFFICIENT`

Published identity work does not yet connect the physiology P1 found to our male CNS v1.0
connectome.

| Expectation | Outcome |
|---|---|
| X1 (a crosswalk male CNS ↔ MANC/FANC/BANC exists) | **held**: male CNS ↔ MANC, per type |
| X2 (13Bα and 10Bα not mapped to single types) | **held**: both `UNMAPPED` |
| X3 (FeCO subtypes identified in some connectome) | **held**: in FANC (`SOURCE_ONLY`) |
| X4 (`MAPPING_ONLY`) | **wrong**: `INSUFFICIENT`; no graded candidate reached type level |

**Integrity.** All 12 entries valid, ids unique, every entry second-read, search log complete. 9
entries count toward decisions. 3 disagree under the strict rule (below).

## Mapping per target

| Target | Status | Why |
|---|---|---|
| 13Bα, 10Bα, 9Aα, 9Aα2 (Agrawal 2020) | `UNMAPPED` | no source matches them to connectome neurons or types. Agrawal 2020 itself says EM reconstruction would make this possible. Syed 2026 types 13B neurons in EM (13B-1a…h etc.) but makes no link to 13Bα. |
| FeCO club, claw-flexion, claw-extension, hook-flexion, hook-extension | `SOURCE_ONLY` (FANC) | Lee et al. 2025 identify them among 80 front-left FeCO axons in FANC, by morphology against light-level driver-line images. No MANC or male CNS type names; MANC had only 22 T1L FeCO axons reconstructed. |
| Chen 2021 classes (8Aa, 9Ba, 9Bb, 10Ba, 13Ba, 13Bb, 19Aa, 19Ab, 20/22Ab) | `UNMAPPED` | 9Ba, 10Ba and 13Bb were reconstructed in a female nerve-cord EM volume and matched to light-level data by morphology. No IDs or type names were given, and the matching method could not be confirmed in the second read. Even with confirmation they would be FANC-only. |
| Tibia flexor MNs: fast, intermediate, slow (Azevedo 2020) | `UNMAPPED` | Cheong et al. 2026 type MANC motor neurons by muscle and match T1 leg MNs to FANC by NBLAST, but do not identify these three neurons. Phelps et al. 2021, which places the fast neuron in FANC by EM/light registration, could not be read (server error). |

**Crosswalk (Q1).**
- Male CNS v1.0 type pages carry an "Across-brain Mapping" label and a "MANC Type" field per type.
  This was confirmed on one page (ANXXX116 → ANXXX116). The page for IN13B001 returned 404.
- The male CNS paper (Berg et al., Cell 2026; paywalled) describes matching by NBLAST and connectivity
  co-clustering. That description was seen only in a tool summary of the preprint.
- **There is no FANC ↔ male CNS crosswalk.** So FANC-only identities cannot carry over under the
  protocol.

**Restated P1 results.**
- **D1:** 13B and 10B stay graded-unit candidates at **hemilineage** level only.
- **D2:** no motor neuron type is mapped, so the parameters stay class-level.
- **D5:** 0 targets.

**Functional connectivity (Q5).**
- **Chen 2021** is the only experiment found that stimulates identified cells and records identified
  cells in the adult leg nerve cord with a neural readout. Its subtype-specific pairs are confirmed:
  - club → 9Ba and 10Ba;
  - claw (extension) → 13Bb, but not claw (flexion);
  - hook (extension) → 13Bb;
  - hook (flexion) → 8Aa;
  - club → 9Bb only with picrotoxin.

  These pairs cannot become targets while neither side is mapped to our data.
- **Pratt 2026 (hair plates) and Syed 2026 (13A/13B):** behavioural readouts only.
- **The citing-paper snowball** (15 and 34 records) found nothing further. The only stimulus-plus-
  recording study was in stick insect.

## Disagreements (strict second-read rule)

| Entry | Reason |
|---|---|
| CH21-id-9Ba, CH21-id-10Ba, CH21-id-13Bb | the EM reconstructions are confirmed, but the EM-to-light matching method (STAR Methods) was not in the text the checker read verbatim |

These three would only have changed the classes from `UNMAPPED` to `SOURCE_ONLY` (FANC), not the
label.

## Process notes and deviations

- **Access.**
  - Europe PMC full texts returned HTTP 500 for Marin et al. 2023 (the MANC annotation paper) and
    Phelps et al. 2021.
  - bioRxiv returned HTTP 429 twice for Marin et al.
  - Europe PMC's citation service returned 503 on the first snowball attempt; a later attempt
    succeeded.
  - A Virtual Fly Brain redirect to another host was not followed.
  - The male CNS Cell paper is paywalled.
  - No check was bypassed and nothing was downloaded. Each failure is logged.
- **Missed sources may matter.** Marin et al. (MANC sensory typing) and Phelps et al. (FANC MN
  identification) are the sources most likely to contain identities this review missed. Neither
  would give a male CNS mapping for the FANC-only cells.
- **Pairs excluded.** Chen 2021 pairs reported only for pooled "claw" (13Ba, 8Ba, 19Aa, 19Ab,
  20/22Ab) were not listed, because the declared targets name claw subtypes.
- **Hair plates.** They are outside P2's declared targets. They matter to this project, which already
  models hair plates. Pratt 2026 found MANC hair-plate axons too poorly reconstructed to identify.

## What this means (per the declared outcome)

**`INSUFFICIENT`:** the identity layer between the published adult leg physiology and our male CNS
connectome is not yet in the literature. The cells are characterised in FANC (female nerve cord) by
light-level matching. Our data is male CNS, which is crosswalked to MANC, not to FANC.

This settles that the evidence-based variant path cannot proceed on published identities alone:
- the graded candidates stay at hemilineage level;
- there are no held-out physiology targets;
- so, under the charter, no engine variant can be validated yet.

**Options (judgments for the user, not declared rules):**
1. **Our own cross-dataset identity matching.** Match the FANC-identified FeCO subtypes and second-order
   classes to male CNS neurons by morphology and connectivity. This would be a new, preregistered method
   step with positive controls: types already matched across datasets. It needs public data downloads
   (each needs your OK) and probably a new analysis dependency (NBLAST tooling). Both are your
   decisions. The results would be our inference, graded below published identity.
2. **A hair-plate track.** The project already has a validated hair-plate encoder. A targets review
   aimed at hair plates (identities and any recordings) might fit better than the FeCO path.
3. **Stop the variant path here** and record the conclusion. The connectome-only model is faithful
   but insufficient (F1/F2). The published physiology supports specific changes (P1), but cannot yet
   be tied to our connectome's cells (P2).

**In no case** does P2 change the engine, or claim function or behaviour from anatomy.

## Limits

- Public literature and documentation only.
- Several key sources were unreachable, or paywalled (the male CNS Cell paper).
- The crosswalk was confirmed on one type page.
- An AI reviewer worked through web tools, with the declared safeguards.
- Motor coordinates are unchanged (20/42 admitted, +4 conditional).

## Evidence

`docs/evidence/identity-mapping-v1/`:
- `protocol.json` (9c7919bc…);
- `type_table.json` (11,751 types);
- `evidence.json` (12 entries with second-read notes);
- `search_log.json`;
- `result.json`.
