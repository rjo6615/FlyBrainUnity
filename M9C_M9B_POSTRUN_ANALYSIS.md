# M9C — read-only post-run analysis

`malecns_backend.embodiment.m9c_m9b_postrun_analysis` implements the frozen M9B
four-condition analysis. It loads existing numeric telemetry only, validates all
canonical identities and protocol details, verifies the force and disabled-motor
boundaries, and computes `A_P-A_C`, `B_P-B_C`, and their difference-in-differences.

The analyzer intentionally has no automatic or command-line execution path. On
the reviewed Windows scientific checkout, call `analyze()` exactly once. The new
output directory is exclusive-create and contains analysis, report, and manifest
JSON. Existing output, any provenance mismatch, malformed telemetry, or force
schedule mismatch fails closed. It never constructs FlyGym, MuJoCo, or MaleCNS,
and its physics and neural transition counters are both zero.

The summaries preserve signed components and per-channel values alongside
magnitudes. Return fractions are explicitly descriptive. Contact telemetry is
not treated as neural input, and classification language is restricted to the
three preregistered M9B labels.
