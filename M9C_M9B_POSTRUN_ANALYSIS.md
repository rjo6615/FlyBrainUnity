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

The analyzer validates the complete frozen recorder inventory.  In particular,
the immutable M9B preflight snapshots establish the compiled MuJoCo model as
`nq=94` and `nv=93`; these are intentionally independent dimensions.  A free
joint stores orientation as a four-coordinate quaternion in `qpos` but has only
three angular velocity degrees of freedom in `qvel`.  The remaining contract is
15,001 state samples for qpos/qvel, 42 measured joints, 42 action commands, 48
compiled controls, root position/quaternion/up-vector, 36 three-axis contact
forces, six contact flags, six three-axis Tarsus5 positions, and two fall flags;
15,000 external-force transitions; and 3,000 neural samples with six encoded
sensory channels, scalar drive/spike counts, and 11 observer, decoder, admitted,
pre-zero, and post-zero motor channels.

Validation and force/control audits all precede creation of the output
directory.  Publication itself is exclusive-create and transactional: any
exception after directory creation removes all partial M9C files.  Therefore a
shape-validation exception cannot have published any M9C artifact, and a later
publication failure cannot leave a namespace that resembles completed output.

The summaries preserve signed components and per-channel values alongside
magnitudes. Return fractions are explicitly descriptive. Contact telemetry is
not treated as neural input, and classification language is restricted to the
three preregistered M9B labels.
