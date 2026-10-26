# Distal anatomical qualification — bounded result

Baseline2bcd103 (merged PR285). The current BANC references narrow an anatomical
question; they do not yet qualify four new motor populations. The user selected
balance-contribution design using the existing20motors as the next workstream.

The primary [MANC study](https://elifesciences.org/articles/96084), Results,
Serial leg motor neurons, Figure7D, explicitly reports unresolved T2/T3 tarsus
levator/depressor serial homologs. Its standard leg analysis excludes these
unmatched groups. Its source tables therefore cannot independently fill this gap
merely because an ID also appears in a BANC match field.

Two original public supplemental CSVs were acquired unchanged:

| Source | Rows excluding header | Bytes | Raw SHA256 |
|---|---:|---:|---|
| [Supplement3: MN/efferent light-level matches](https://cdn.elifesciences.org/articles/96084/elife-96084-supp3-v1.csv) |834|67297|`c46e3cec1a5114b8d981d5f0383012c8e7fcdebd6c4e3eaffe4ac3ba1def2e94`|
| [Supplement6: Serial leg MN groups](https://cdn.elifesciences.org/articles/96084/elife-96084-supp6-v1.csv) |264|24898|`b56b0563f6a6000b2a43fbc7ebec46297668e8e3b6c6d596843d5ad5aab83a65`|

The full existing43-row reference was preserved. Its20T2/T3 rows reference21
distinct MANC body IDs across BANC and original MaleCNS match fields. Every body
ID has exactly one Supplement3 row:16have only middle/hind-leg target labels;
5have other named proximal-muscle targets. Blank certainty, publication and
driver-line fields remain blank. None supplies the missing distal muscle match.
Supplement6 has no named tarsus levator/depressor rows. This is a source-table
scope finding, not evidence that the neurons or muscles do not exist.

For the concordant right-hind leads, MANC13144/MNhl65 and13740/MNhl64 are labeled
only `hind leg`, with no recorded light-level match certainty, publication or
driver line. For the duplicated right-middle lead, MANC14828 belongs to group13036
(MNml81), while200065 belongs to group103416(MNml77). A body ID is not its group ID.
These facts do not settle which BANC functional label is correct; no favorable
row is selected and no existing motor role is reassigned.

Pinned BANC pipeline revision5c333c12 was also reviewed: MANC metadata derives
cell-class labels from target fields; curation can inherit matched metadata from
the shared reference table; downstream rules translate class labels into target
names. This describes metadata derivation, not independent muscle tracing or a
proof of the captured snapshot's exact build history. See paths/limits in
`evidence/distal-anatomical-qualification-v1/qualification.json`.

**Decision: no sufficient target authority in the reviewed sources.** All four
distal populations remain unqualified, all new assignments false/null, production
20/42. New independent per-neuron anatomy or appropriately reviewed morphology
and complete antagonist membership would be needed. The result does not prove
that later independent annotations are absent elsewhere. No author contact,
physics/CNS initialization or simulation occurred in this qualification.

The new balance protocol is independent of these blocked motor additions; see
`BALANCE_CONTRIBUTION_V1.md`. It uses only the existing admitted20channels and
does not transplant muscle attachments or change neural parameters.
