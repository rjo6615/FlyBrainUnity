# Audit v1.1 — retain exact multi-target annotation aliases

Pre-generation implementation correction. The first read-only audit (source
commit 0128b86) stopped with `duplicate exact population names`; its error record
is preserved in `docs/evidence/remaining-leg-admission-audit-v1/audit.json`.
No brain/physics runtime or scientific transition occurred and no channel was
admitted. Do not overwrite or describe that attempt as successful.

The assumption of global name uniqueness was wrong. For example, the two
`Pleural remotor/abductor MN T1 left` records have identical body IDs
[802509,803803] and dense indices [144657,145652], but distinct body-map targets
`coxa_T1_left` and `coxa_abduct_T1_left`. Unrelated antenna/proboscis names can
also repeat with different identities and are outside this leg audit's scope.

v1.1 groups records by name and resolves only requested leg candidates. Every
selected alias must retain the exact same complete unique body IDs/dense indices,
count and direction; every metadata tuple must match an exact bodymap record.
Require exhaustive equality of matching annotation records, reject same-name
different-identity candidates or missing/extra aliases, and retain all anatomical
target aliases in the output. No last-record-wins selection, preferred axis,
population union, averaging or silent alias removal. Exact identity criteria are
preserved; the incorrect global uniqueness requirement is replaced by exhaustive
candidate-specific identity validation. Shared-axis ambiguity remains blocked.

Flatten all source annotation aliases when checking exact missing Tarsus1 versus
related tarsus2; do not accidentally hide tarsus2 because its name also annotates
adhesion. All original audit classifications, raw-lock-failure reporting,
non-admission, neural parameters and scientific constraints remain unchanged.
Commit and test this correction before producing a new exclusive v1_1 output.
