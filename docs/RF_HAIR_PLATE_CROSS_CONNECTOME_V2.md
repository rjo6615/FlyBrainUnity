# Right-front hair-plate deficit: cross-connectome check by neuron-level match — design (V2)

Designed 2026-11-03. This is the design only. No code has been written, and no match
between any MaleCNS hair-plate neuron and BANC has been looked up. The protocol, code and
tests will be hash-locked and committed before the single run.

## Why a V2

V1 (`RF_HAIR_PLATE_CROSS_CONNECTOME_RESULTS.md`) ended `INCONCLUSIVE_INTEGRITY`.

- 21.7 % of BANC `SNpp45` rows fell outside the nerve rule.
- After the run, it became clear that the design assumption was false: BANC's `SNpp45`
  label covers a broader population than MaleCNS's (T2: 48/37 against 12/11).
- Counting type names across connectomes therefore does not compare like with like.

V2 keeps V1's question and its bars, but changes how neurons are identified. **It
follows each of the model's own hair-plate neurons into BANC by the neuron-level
matches that BANC itself records.** V1 stays as recorded. This is a new version, not a
rerun with the bar moved.

## Question (unchanged from V1)

Does BANC show the same right-front (RF) versus left-front (LF) hair-plate deficit as
MaleCNS, in neuron count and neuron size? Here "the same neurons" means the BANC
counterparts of the model's own T1 SNpp45 neurons.

## What was already seen (disclosed)

Before writing this design, the following was seen:

- **V1's post-hoc diagnostics (type-name rule, not neuron identity):**
  - BANC T1 primary-rule counts: 8 L, 4 R;
  - median cable: 1,346 µm L, 1,027 µm R;
  - all single-prothoracic-nerve counts: 22 L, 26 R.
  These rows may overlap the V2 matched set.
- **Whole-table formats of the BANC match columns.** These were not filtered to any cell
  type:
  - `malecns_match`: single MaleCNS body IDs as strings, never a list;
  - `manc_match`: MANC body IDs as strings, occasionally comma-separated lists;
  - in the MaleCNS v1.0 annotations, `mancBodyid` is a float.
- **No anchor has been looked up.**

To keep V1's knowledge from shaping V2, **all label bars are copied unchanged from V1**,
where they were fixed before any BANC per-leg value was seen.

## Anchors (fixed)

The anchors are the MaleCNS `SNpp45` neurons that the model uses, taken from the
committed annotations (sha 2177e246…) with the Step A sensory-set rule:

- **T1 (labelled):** 7 left and 5 right, all VProN.
- **Reported separately:** the left ProLN neuron excluded in Step A (821165).
- **Context only:** T2 (12 L, 11 R) and T3 (8 L, 9 R) anchors, reported and not labelled.

## Bridges (fixed; both used, and their union is the counterpart set)

- **B1, direct:** BANC rows with `malecns_match` == the anchor body ID.
- **B2, via MANC:** BANC rows whose `manc_match` contains the anchor's `mancBodyid`
  (taken from the MaleCNS v1.0 annotations). The list is split on commas and compared
  as integers.

Rules for building the counterpart set:

- A BANC neuron is identified by `root_id`. A counterpart that several anchors share is
  counted once per side.
- A counterpart's side is its BANC `side` column. If that is missing, it is the side in
  its nerve name. If both are missing, the counterpart is reported and not used.
- BANC `cell_type` is reported but not required, because V1 showed that its type labels
  do not correspond.

## Integrity (all required, else `INCONCLUSIVE_INTEGRITY` with no labels)

1. **I1 Sources.**
   - The BANC file (86ccf5df… = provenance), the MaleCNS annotations (2177e246…) and the
     Step A result (e652a0c2…) all match their hashes.
   - The anchors reproduce the Step A counts: 7, 5, 12, 11, 8, 9.
2. **I2 Bridge version validity.** At least 90 % of all distinct non-null BANC
   `malecns_match` IDs exist as a `bodyId` in the v1.0 annotations. This guards against
   a body-ID version mismatch, since BANC's matches may be to MaleCNS 0.9.
3. **I3 Coverage.** At least 75 % of T1 anchors on each side have at least one
   counterpart. That means at least 6 of 7 LF and at least 4 of 5 RF.
4. **I4 Side consistency.** At least 80 % of distinct T1 counterparts have the same side
   as their anchor. If not, the matches do not respect laterality and counts by side
   mean nothing.
5. **I5 Size field.** Every used T1 counterpart has a finite, positive
   `l2_cable_length_um`.

## Measures

For each side:

- **n:** the number of distinct T1 counterparts on that side whose anchor is on the
  same side.
- **Size:** the median and the summed BANC L2 cable of those counterparts.

**Reported only:**
- each anchor's counterparts and which bridge found them;
- whether B1 and B2 agree when both find a counterpart;
- the counterparts' BANC `cell_type`, nerve and proofread flag;
- unmatched anchors;
- cross-side counterparts;
- the counterparts of 821165;
- the same measures for T2 and T3.

## Labels (bars copied from V1)

**Q_COUNT** uses d = n(R) − n(L).

| Label | Rule |
|---|---|
| `COUNT_DEFICIT_REPLICATED` | d ≤ −2 |
| `COUNT_SYMMETRIC` | \|d\| ≤ 1 |
| `COUNT_REVERSED` | d ≥ +2 |

**Q_SIZE** uses r = median cable(R counterparts) / median cable(L counterparts).

| Label | Rule |
|---|---|
| `SIZE_DEFICIT_REPLICATED` | r ≤ 0.67 |
| `SIZE_SYMMETRIC` | 0.85 ≤ r ≤ 1/0.85 |
| `SIZE_REVERSED` | r ≥ 1.5 |
| `SIZE_INDETERMINATE` | otherwise |

**Q_RF** combines the two exactly as in V1:

| Label | Rule |
|---|---|
| `RF_DEFICIT_REPLICATED` | both COUNT and SIZE replicated |
| `RF_DEFICIT_NOT_REPLICATED` | COUNT symmetric or reversed, and SIZE symmetric or reversed |
| `RF_PARTIAL` | otherwise |

**Q_SIZE is the more informative label in V2.** The counts are bounded by matching. A
BANC right-front neuron that has no MaleCNS counterpart cannot appear, so a neuron
missing from MaleCNS cannot show up as a count deficit here. The size test is the direct
one. If MaleCNS RF neurons are under-traced, their BANC counterparts should be
normal-sized relative to LF counterparts. If they are genuinely small, their
counterparts should be small too.

## What each outcome means (declared now; unchanged from V1)

- **RF_DEFICIT_REPLICATED:** favours real anatomy, or a bias that both reconstructions
  share. `joint_RFCoxa` stays BLOCKED_BY_INPUT, documented as a likely property of the
  fly.
- **RF_DEFICIT_NOT_REPLICATED:** specific to MaleCNS (individual variation or
  under-tracing). Any input substitution would be a separately designed and labelled
  engineering question, made only on the user's decision.
- **RF_PARTIAL:** recorded as is.

In every case:
- no weights change;
- `COXA_COORDINATE_STATUS.md` gets one evidence line;
- coverage stays 20/42 admitted, +2 conditional.

## Predictions (expectations, not criteria)

- **I3 coverage may be the weak point.** Matching under-traced neurons is harder, so
  RF anchors may lack counterparts. That would itself be suggestive, but it ends
  INCONCLUSIVE by the rule.
- **If integrity passes, SIZE_SYMMETRIC is somewhat more likely.** A one-leg 2.6× size
  deficit (MaleCNS median 358 vs 918 synapses) looks more like tracing than anatomy.
  V1's type-name diagnostic (ratio 0.76) is not neuron-level evidence either way.

## Limits

- **Two animals.** The result can show replication, not population anatomy.
- **Size proxies differ** between datasets, so sizes are compared only as within-BANC
  ratios.
- **The matches are BANC's own annotations,** made by its curators with methods not
  audited here. An unmatched anchor is ambiguous.
- **Count is matching-bounded.** BANC-only neurons are invisible to it.
- **Structural only.**

## Build and run plan (on approval)

1. **Protocol.** Write `docs/evidence/rf-hair-plate-banc-v2/protocol.json`, including the
   disclosure above.
2. **Code.** Write `malecns_backend/embodiment/rf_hair_plate_banc_v2.py`. It reuses V1's
   source checks, `summary`, `q_count`, `q_size` and `q_rf`, and Step A's
   `sensory_sets`. It is read-only.
3. **Tests.** Write `tests/test_rf_hair_plate_banc_v2.py` using synthetic tables. It
   covers:
   - both bridges and comma-split lists;
   - counting shared counterparts once;
   - the side fallback;
   - each integrity fault.
4. **Commit and hash-lock, then run once.** The run takes seconds. Then write the results,
   the one-line status evidence, the handoff and the roadmap.
