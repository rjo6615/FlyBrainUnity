# Published physiology Step P3: hair plates — results

Reviewed 2026-11-23 under the preregistered protocol
`docs/evidence/hair-plate-review-v1/protocol.json` (sha d240f626..., commit bad2314, before any search
or annotation query). There were no amendments. The annotation query ran once, all 16 declared web
queries ran once, the strict second reads were done, and the result was computed once.

## Result: `INSUFFICIENT` (SNpp45 verdict `UNRESOLVED`)

| Target | Status (R1–R5) | Why |
|---|---|---|
| H1 CxHP8 | `SOURCE_ONLY` | Pratt et al. 2026 identify all 8 left front-leg CxHP8 axons in FANC (M-A). Hair-plate axons could not be identified in MANC. FANC has no crosswalk to our data. |
| H2 CxHP3, CxHP4 | `SOURCE_ONLY` | identified in FANC by entry nerve (dorsal prothoracic, prothoracic accessory) |
| H3 TrHP5–7 | `SOURCE_ONLY` | identified in FANC by position in the leg nerve, morphology and motor connectivity |
| H4 SNpp45 | no published identity that carries over | male CNS: subclass "hair plate", no plate number (M-C, method not checked); BANC: a mixed hair-plate type (does not carry over) |

- **E-targets (encoder validation): 0.** Pratt's CxHP8 tuning is quantitative and in *Drosophila*:
  calcium against thorax-coxa rotation, adduction and flexion, maximal at combined adduction and
  inward rotation, tonic. It cannot count while CxHP8 is not `MAPPED`.
- **C-targets (CNS validation): 0.** No *Drosophila* recording of identified downstream neurons
  exists. Pratt's reflex circuit is a FANC connectome prediction, tested with behavioural readouts.
- **Crosswalks used:** male CNS ↔ MANC (P2's checked entry) and BANC ↔ male CNS. BANC joined by the
  preregistered rule: the annotation entry counted, and five hit BANC types carry over. But the two
  BANC types that hold hair-plate labels, SNpp45 and SNpp52, each reach two male CNS types (themselves
  and SNppxx), so neither carries over.

## Expectations

| | Expectation | Outcome |
|---|---|---|
| X1 | CxHP8 identified only in FANC; SNpp45 `UNRESOLVED` | held, but see the sensitivity note |
| X2 | BANC links hair-plate rows to male CNS types at group level | **wrong.** SNpp45, SNpp52, SNpp19, SNxx26 and SNxx28 are group-level. BANC's CoHP8 and CS types have a single matched row each, so the preregistered rule calls them neuron-level. |
| X3 | a quantitative *Drosophila* afferent result exists but cannot count | held (Pratt's CxHP8 tuning) |
| X4 | zero C-targets | held |
| X5 | label `INSUFFICIENT` | held |

**X1 sensitivity.** X1 holds because the three BANC identity entries (CoHP8, CoHP3, CoHP4) were not
counted. The second reader confirmed BANC's expert-review method sentence. It could not confirm
verbatim that reference 222 is Pratt 2026, and it read the "morphological comparison" wording as
applying to effector neurons. So the link from BANC's label to Pratt's plate was not confirmed. Had
these entries counted, X1 would be wrong (H1 sources FANC and BANC). The label and the SNpp45 verdict
would not change: the BANC entries span SNpp45, SNpp52 and CoHP8, which do not carry over as a set.

## What the annotation query found

All counts below are confirmed by the separate local reader.

**BANC names the coxa hair plates "CoHP3/4/8".** The CxHP spelling is absent. The labels sit mainly in
`peripheral_target_type`, and their nerves match Pratt's definitions:

| BANC label | Rows | BANC types | Entry nerve |
|---|---|---|---|
| CoHP8 | 25 | 12 SNpp45 + 3 SNpp52 (all ventral prothoracic) and 10 typed CoHP8 | 9 of the 10 CoHP8-typed rows enter via the leg nerve and 8 carry a "trochanter hair plate" tag: internally inconsistent |
| CoHP3 | 6 | 5 SNpp52, 1 SNpp45 | all dorsal prothoracic |
| CoHP4 | 4 | 3 SNpp45, 1 SNpp52 | all prothoracic accessory |

- 138 of BANC's 166 SNpp45 rows are hair-plate neurons, across front, middle and hind legs.
- The `fanc_cell_type` column also carries CoHP labels, and in places these disagree with the other
  columns.
- In the male CNS, 52 of 53 SNpp45 rows have subclass "hair plate". None names a hair plate number.

## Post-hoc observations (not preregistered, not counted)

These were computed after the result, from the same local tables. They do not change any label.

1. **Pratt's own criterion, applied in our data.** Pratt identifies CxHP8 as the only hair plate whose
   axons enter through the ventral prothoracic nerve (VProN). In the male CNS annotations, the only
   hair-plate neurons entering through the VProN are 12 SNpp45. SNpp52 enters via the dorsal
   prothoracic nerve in T1, and SNpp19 via the prosternal nerve. Applying a source's criterion to
   another dataset is our inference (M-C).
2. **BANC's neuron-level matches.** 11 of the BANC SNpp45 rows labelled CoHP8 have a `malecns_match`.
   All 11 point to male CNS SNpp45 neurons entering via the VProN. The single matched CoHP8-typed row
   (leg nerve) points to SNppxx. The CoHP4-labelled row with a match points to a VProN SNpp45.

Both are consistent with the Step A inference, SNpp45 = CxHP8, at least for its T1 VProN neurons. They
were seen after the outcome, so any use of them needs a new, separately versioned protocol that
declares this origin.

## Behaviour (Q5): reported only, never a target

Pratt 2026, *D. melanogaster*:
- **Activation** (ChrimsonR, tethered standing flies) moves the stimulated leg posteriorly and
  laterally: the coxa rotates outward, moves laterally and flexes. The other legs are unaffected.
- **Silencing** (GtACR1, walking) makes coxa adduction more medial at the swing-to-stance transition.
- **Chronic silencing** (Kir2.1, treadmill) shifts the anterior and posterior extreme positions
  medially and posteriorly, increases swing distance and splays the resting legs. Swing duration and
  inter-leg coordination are unchanged.

These are predictions for a later embodied test.

## Other insects (grade C: recorded, never counted)

- **Locust coxal hair plate** (Kuenzi & Burrows 1995). Long hairs are deflected as the leg swings
  forward. Stimulating them rotates the coxa posteriorly, excites the posterior rotator and adductor
  motor neurons (partly monosynaptically) and inhibits the anterior rotator. This is the same direction
  as our Step C reflex.
- **Cockroach trochanteral hair plate** (Pearson et al. 1976). Monosynaptic EPSPs and disynaptic
  IPSPs onto femur motor neurons.
- **Afferent classes** (log only, abstracts):
  - Wong & Pearson 1976, cockroach: type I dynamic and type II dynamic + static afferents; ablation
    causes overstepping.
  - Newland et al. 1995, locust tibial hair plate: phasic and phasotonic afferents.

## Second reads

20 entries, all second-read; 17 agree and 16 count (Step A is our own work, not a primary source).

| Source | Checked | Outcome |
|---|---|---|
| Pratt 2026 | 9 claims | all agree; caveats on the unread Methods tail |
| BANC paper | B3–B5; B1 except the identity of reference 222 | agree |
| BANC paper | B2 (as stated), B6 (absence of CoHP/CxHP) | not found / not confirmed |
| Grade-C abstracts | 4 | all agree |
| Local annotation output and Step A | 9 claims | all agree |

**Not counted:** BANC-H1, BANC-H2-CxHP3 and BANC-H2-CxHP4.

## Access failures (logged; none bypassed)

- Marin et al. MANC annotation: Europe PMC full text HTTP 500, and the eLife page served a client
  challenge.
- Berg et al. male CNS preprint: Europe PMC full text HTTP 500; the Cell version is paywalled.
- The Dryad dataset holding the numeric CxHP8 tuning was not downloaded.

## What this means

- **The hair-plate path is where the FeCO path was.** The published identities are in FANC, and FANC
  does not carry over. BANC's labels span types that do not carry over at type level. There is no
  validation target from published physiology, either for the encoder or for the reflex pathway.
- **The project's own SNpp45 = CxHP8 inference is neither supported nor contradicted** by a counted
  source. Post hoc, it is consistent with Pratt's nerve criterion and with BANC's neuron-level matches.
- **Pratt's tuning is the target the encoder would need.** If CxHP8 were mapped to SNpp45, Pratt's
  quantitative *Drosophila* tuning would make P3 `ENCODER_VALIDATION_AVAILABLE`. That is the single
  missing link.
- **Next step (user's choice):**
  - the declared conclusion write-up; or
  - a separately versioned, preregistered identity step for CxHP8 that fixes a neuron-level rule in
    advance. Its motivation is post hoc and must be declared, which lowers its evidential weight.
- No engine, encoder or weight changed, and no balance claim is made. Motor coordinates are unchanged
  (20/42 admitted, +4 conditional).

## Files

New:
- `malecns_backend/hair_plate_review.py`
- `tests/test_hair_plate_review.py`
- `docs/evidence/hair-plate-review-v1/`: `protocol.json`, `annotation_query.json`, `evidence.json`,
  `search_log.json`, `result.json`
- `docs/HAIR_PLATE_REVIEW_RESULTS.md`

Changed:
- `docs/HAIR_PLATE_REVIEW_V1.md`
- `docs/PROJECT_HANDOFF.md`
- `docs/UNITY_AND_BALANCE_ROADMAP.md`

Reproduce (Git Bash; the evaluate step refuses to overwrite, so write to a new path):

```bash
cd "$HOME/Documents/FlyBrainUnity" && PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
"$PY" -m pytest -q tests/test_hair_plate_review.py tests/test_identity_review.py
D=docs/evidence/hair-plate-review-v1
"$PY" -m malecns_backend.hair_plate_review evaluate --evidence $D/evidence.json --log $D/search_log.json --annotation $D/annotation_query.json --output .cache/p3-result-repro.json
```

The reproduced result should match `result.json`: `INSUFFICIENT`, `UNRESOLVED`, X1–X5 = true, false,
true, true, true. Evaluate re-runs the annotation query and refuses to continue unless the output is
byte-identical to the stored one.
