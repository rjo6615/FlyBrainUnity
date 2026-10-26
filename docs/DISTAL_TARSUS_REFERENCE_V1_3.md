# Distal reference V1.3: static admission boundary correction

V1.2 serialized a complete reference report, but its real reconstruction test
with FlyGym/MuJoCo/CNS imports forbidden failed: the reused legacy
`remaining_leg_admission_review.verify` reaches live actuator enumeration, which
constructs a FlyGym/compiled native model. Preserve V1.2's report unchanged;
it does not satisfy this investigation's no-construction scope. V1 and V1.1
also reached that legacy path before their serialization failures.

Those attempts report zero scientific transitions, but constructor internals were
not instrumented. Do not infer zero constructor-side physics operations, native
calls or model constructions from their summaries. No CNS experiment was invoked.
This boundary limitation is explicit; do not rewrite historical reports to hide it.

Before a new output attempt, V1.3 replaces only that call with the existing
`lf_force_static_reference.load` reader. It already reconstructs the original
locked static admission table, 22 blocked rows, exact LF identities and official
crosswalk without live enumeration, simulated physical records or new validation
criteria. Reuse its returned table and original raw-lock status.

Keep the same raw source snapshots, source selection, ID references, disagreements
and V1.2 lossless data representation. Preserve all43rows; no mapping or anatomy
claim is upgraded. Add the reused static reader to the reconstruction fingerprint.
The strict test continues to block FlyGym, MuJoCo and neural imports and also
forbids legacy audit construction, live enumeration and the transition kernel.

Schema is `distal-tarsus-reference-v1.3`; output uses a new exclusive
`evidence/distal-tarsus-reference-v1_3/run/` namespace. No automatic retry,
native pose campaign, neuronal/physics parameter change or source-lock refresh.
