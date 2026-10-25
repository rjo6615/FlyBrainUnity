# Native isolation v1.1: lossless nonfinite metadata serialization

Prospective correction, before a second bounded campaign, 2026-10-25. V1 code,
protocol and inputs were committed b4efd68 before the first campaign. It reached
all27 observations and restored model identity, but json.dump(allow_nan=False)
failed on a native unbounded limit value (-inf). The unchanged partial record is
docs/evidence/lf-native-isolation-v1/run/validation.json,2353546bytes, raw SHA256
d6219a063538b270517ce0f9a9b86ea0bb7a3a135cc37ce93755323f9f9f0e54.
Its complete cases/models prefix is readable, but missing final counters/evaluation
means V1 cannot be accepted. Keep the malformed original bytes and source commit;
do not repair that historical file or infer missing counters from expected counts.

V1.1 changes ONLY evidence encoding: recursively represent nonfinite native float
values by explicit tagged objects {"native_nonfinite":"+inf"}, "-inf" or "nan".
Decode those tags back to original IEEE values before the existing numeric/hash
checks. Finite floats, arrays and identity hashes are unchanged. No conversion of
infinite metadata limits to arbitrary finite limits or dropped fields. Nonfinite
observed physical state/force still fails the unchanged finite-value checks.
Serialize a fully encoded strict-JSON string before exclusively writing the new
record. Add a round-trip test covering infinity/NaN metadata and finite arrays.

Commit this explanation, encoding correction and tests BEFORE the one V1.1
campaign. Use the same immutable package manifest, initializer, three arms, nine
probes, suppression rows, expected34forwards/3resets/0integration and acceptance
criteria as LF_NATIVE_ISOLATION_V1.md. No window/grid/tolerance/force/seed/neural
change or retry until pass. The repeat is necessary to capture the previously
unsaved native tables, counters and evaluation. Any integrity or physical failure
must remain a failure. Store separately under lf-native-isolation-v1_1/run/.

Preflight additionally verifies the original partial record's raw hash. Saved
review decodes tags and recomputes evidence checks without native execution.
V1 stays SERIALIZATION_FAILED / scientifically inconclusive regardless of V1.1.
No production hook, new admission, muscle coupling or Unity run is authorized by
this serialization correction. Current20/42; original raw prerequisites remain.
