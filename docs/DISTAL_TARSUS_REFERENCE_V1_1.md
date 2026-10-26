# Distal reference V1.1: lossless non-finite source representation

V1 source extraction reached strict JSON serialization and failed on an IEEE
NaN in an original source field. Preserve its partial `run/reference.json`
under `evidence/distal-tarsus-reference-v1/`; it is not a valid completed report.
The source artifacts and their hashes stay unchanged.

Before a new output attempt, V1.1 specifies recursive lossless JSON encoding:
finite floats retain numeric values; Arrow null remains JSON null; IEEE NaN and
positive/negative infinity become objects with the reserved single key
`__arrow_nonfinite_float__` and values `NaN`, `+Infinity`, `-Infinity` respectively.
Original raw Feather files remain the primary source. The tag is an export
representation, not an imputed measurement or an annotation confidence.

Keep V1's prospective question, exhaustive class/type-field selection, all source
rows/fields, conflicts, unmatched references and all no-admission requirements.
No row, scalar field or contaminated sample is dropped to permit serialization.
This corrects data representation, not acceptance or a scientific result.

Use schema `distal-tarsus-reference-v1.1` and a new exclusive namespace
`evidence/distal-tarsus-reference-v1_1/run/`. Serialize fully in memory before
opening a report file; future extraction/encoding failure writes error metadata
in its own attempt namespace. No automatic retry or overwrite.
