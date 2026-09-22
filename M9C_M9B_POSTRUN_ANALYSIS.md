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

## Recorded-clock validation repair

M9B does not generate timestamps with `np.arange`.  At the start of every
physics-loop iteration it evaluates `float(physics.data.time * 1000)` and writes
that binary64 scalar to physics telemetry.  MuJoCo's seconds clock has been
advanced once per preceding transition, so the 15,001 physics state samples
have indices 0 through 15,000 and nominal times 0 through 1500 ms.  On each
positive iteration divisible by five, the recorder writes that **same** scalar
to neural telemetry before writing it to physics telemetry.  Thus the 3,000
neural samples are exactly the recorder's physics samples `[5::5]`, with nominal
times 0.5 through 1500 ms; they are not a zero-origin `arange(3000) * 0.5`
clock.

The former M9C validation independently constructed physics timestamps as
`np.arange(15001) * 0.1` and neural timestamps as
`np.arange(3000) * 0.5`, then required `np.array_equal`.  A synthetic binary64
reproduction of the recorder (`time_s += 0.0001`, followed by `time_s * 1000`)
has shape `(15001,)`, dtype `float64`, first value `0.0`, and last value
`1499.9999999998513`.  Compared with the former physics reference (last value
`1500.0`), its first unequal element is index 8 (`0.8000000000000002` versus
`0.8`, one ULP), and its maximum absolute difference is
`1.48929757415317e-10` ms.  Its neural subsample has shape `(3000,)`, first
value `0.5`, last value `1499.9999999998513`, and differs immediately from the
former zero-origin reference (`0.5` versus `0.0`).  The stopped physics failure
was therefore a harmless reconstruction-operation difference; the still-hidden
neural check additionally contained a genuine expected-origin/indexing error.
Against the correctly indexed independent neural expression
`np.arange(1, 3001) * 0.5`, its first mismatch is index 1
(`1.0000000000000002` versus `1.0`, one ULP) and its maximum absolute
difference is `1.4870238373987377e-10` ms at index 2996.

M9C now validates the scientific clock contract directly: exact float64 dtype
and sample counts, finiteness, strict monotonicity, integer sample-index origin
and endpoint, nominal dt at every sample and between adjacent samples, and the
neural-to-physics `[5::5]` correspondence.  Its per-sample tolerance is derived
from IEEE-754 round-to-nearest: half an ULP for every repeated seconds-scale
addition plus one ULP for constructing the nominal reference.  Adjacent-step
and neural/physics bounds are composed only from those per-index bounds.  No
general-purpose or empirically selected `allclose` tolerance is used.

## Exact-floating-point comparison audit

* **Category B, repaired:** physics and neural timestamps were independently
  reconstructed decimal sequences.  They now use the bounded semantic checks
  above.
* **Category A, retained:** clocks recorded by separate conditions must remain
  byte-identical.  Those are peer recordings of the same deterministic frozen
  clock, not reconstructed expected values.
* **Category A, retained:** the external-force arrays and their 5000--5199
  active transition indices are the exact commanded protocol.  Zero controls,
  the `1.024` force value, and equality between the two perturbed schedules are
  therefore exact requirements.
* **Category A, retained:** disabled post-gate motor vectors are required to be
  exactly zero; tolerance would weaken the causal boundary.
* **Category A, retained:** initial body position, quaternion, and 42 joint
  positions are compared only across the four recorded state-zero samples.
  M9C does not reconstruct spawn position, quaternion, or joint targets from
  JSON or dt arithmetic, so exact peer equality remains appropriate.
* Protocol JSON comparisons (dt values, force vector/direction, transition
  indices, initialization metadata, and interface definitions) are exact
  frozen-schema identity checks rather than computed floating-point telemetry
  comparisons and remain unchanged.

The summaries preserve signed components and per-channel values alongside
magnitudes. Return fractions are explicitly descriptive. Contact telemetry is
not treated as neural input, and classification language is restricted to the
three preregistered M9B labels.
