# Distal reference V1.2: explicit timestamp and schema representation

V1.1 fixed non-finite floats but failed before opening its report on an original
Python datetime from the MaleCNS v0.9 reference table. Preserve its exclusive
`evidence/distal-tarsus-reference-v1_1/run/error.json`; do not overwrite/reclassify
the failed attempt. V1's partial report is also preserved unchanged.

Before another output attempt, the full two-source scalar/schema inventory was
inspected: BANC has strings, floats and nulls; the v0.9 table additionally has
booleans and timezone-aware datetime values (`_ctime`, `_mtime`, Arrow type
`timestamp[us, tz=UTC]`). No opaque objects or binary scalars were found.

V1.2 retains V1.1's distinct tagged non-finite representation and additionally
encodes datetime as a single-key object `__arrow_datetime_iso8601__` whose value
is `datetime.isoformat()`, preserving microseconds and UTC offset. Store all
original source Arrow field names/types in the report so timestamp unit/timezone
and other source typing remain explicit. Raw Feather remains primary authority.
Test exact datetime round-trip and all observed scalar classes before extraction.
No generic stringification, null imputation or field/row dropping is permitted.

Schema is `distal-tarsus-reference-v1.2`; new exclusive output is
`evidence/distal-tarsus-reference-v1_2/run/`. All original sources, query scope,
identity checks and no-admission criteria are unchanged. This is a representation
correction only; no physics/CNS experiment, scientific retest or activity ranking.
