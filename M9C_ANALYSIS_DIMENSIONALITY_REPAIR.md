# M9C rank-aware analysis repair audit

## Root cause and canonical shapes

The audited recorder contract fixes `physics_tarsus5_world_position` at
`(15001, 6, 3)`: 15,001 physics states, the ordered identities LF, LM, LH,
RF, RM, and RH, and XYZ coordinates.  Factorial subtraction is elementwise,
so `delta_A`, `delta_B`, and `interaction` each remain `(15001, 6, 3)`.
`_contrast_summaries` formerly passed each entire contrast to `_summary`.
There, `np.linalg.norm(value, axis=-1)` reduced XYZ only and produced
`(15001, 6)`.  Indexing the time axis as `magnitude[i]` therefore produced a
six-element leg vector, which cannot be converted by `float(...)` to a scalar.

The repair makes the interpretation of every supported rank explicit:

* `(T,)` is one signed scalar time series;
* unnamed `(T,D)` is one component vector time series, with an L2 magnitude
  over its component axis;
* named `(T,N)` is N signed scalar time series, summarized separately by name;
* named `(T,N,D)` is N vector entities, summarized separately by name with an
  L2 magnitude over D for each entity.

Higher ranks, named/unnamed rank mismatches, identity-count mismatches, and
time-axis mismatches fail closed.  Named telemetry also has a clearly labelled
descriptive aggregate: the Euclidean root-sum-square across all named channels,
or across all named entities and vector components.  The named per-channel or
per-entity results are the primary interpretable output.

## Complete caller and reduction audit

The `_summary` callers comprise:

* scalar `(T,)`: delivered sensory drive count, aggregate CNS spikes, and the
  three shortest-arc orientation series;
* single vectors `(T,3)`: root position, body-up vector, root linear velocity,
  and root angular velocity;
* named scalar channels `(T,N)`: 42 joint positions, six contacts, two
  fall/rollover flags, six sensory encodings, and each set of 11 mapped motor
  observer, decoder, and admitted-contribution channels;
* named vector entities `(T,6,3)`: the six distal-tarsus XYZ positions.

No other shape reaches these functions.  Scalar absolute value and
single-vector/per-entity L2 magnitude now always produce `(T,)`, so peak index,
peak time, sampled magnitude, and return fraction are scalar and unambiguous.
Per-channel scalar summaries retain signed values.  Per-leg vector summaries
retain signed XYZ values and calculate magnitude over XYZ only.

`first_divergence` intentionally uses `any` over every non-time axis to answer
the preregistered trajectory-level question; callers that require identity
(contact detail and all named summaries) also compute it on individual channel
or entity slices.  It does not alter the contrast.  Contact difference duration
is already computed per leg.  Channel ranking compares each named summary's
own scalar peak magnitude.  Quaternion norms operate only on their final four
component axis before producing scalar angular series.  No reviewed `max`,
`argmax`, norm, first-divergence, or return-fraction operation now accidentally
retains an entity axis or silently collapses identity.

## Scientific and publication boundaries

The factorial definitions, classification logic, thresholds, causal milestone
definitions, force protocol, clocks, recorder schema, and M9B artifacts are
unchanged.  No new scientific criterion is introduced; the aggregate L2 is
explicitly descriptive.

The failed canonical invocation necessarily failed while constructing the
in-memory `physical` dictionary, before the original `output_dir.mkdir(...)`
publication point.  Filesystem inspection during this repair found no
`interface_output/m9c_m9b_postrun_analysis` directory, temporary file, final
JSON, or manifest.  Thus there is nothing to remove or recover.  If a future
publication fails, output is now written under the M9C-only sibling staging
namespace `.m9c_m9b_postrun_analysis.tmp-<pid>`, which is removed on failure;
the completed directory is exposed by one rename.  Recovery, if interrupted
outside Python before cleanup, is limited to verifying and removing only that
M9C staging directory.  The M9B namespace must never be touched.

This repair and its tests execute no canonical analyzer and no scientific
simulation: physics transitions = 0 and neural transitions = 0.
