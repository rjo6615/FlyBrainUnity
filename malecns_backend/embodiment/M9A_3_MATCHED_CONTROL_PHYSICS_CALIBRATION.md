# M9A-3 — matched-control physics-only perturbation calibration

## Status and claim boundary

**Attempt 1 is permanently classified as an incomplete execution.** It ran
only candidate 0.256 (P, then C), failed in `_reduce_pair()`, completed no
reduction or selection, and ran no later candidate. Its two raw files remain
immutable, read-only failed-attempt evidence in
`interface_output/m9a_3_matched_control_calibration`; their byte sizes and
SHA-256 identities are recorded in `m9a_3_attempt_1_provenance.json`.

**Attempt 2 is a distinct, preregistered, NOT RUN experiment.** Its exclusive
output namespace is
`interface_output/m9a_3_matched_control_calibration_attempt_2`. The scientific
protocol below is unchanged from Attempt 1; only the reducer defect and attempt
identity/output isolation have changed. M9A and M9A-2 remain historical
evidence and are neither rerun nor reinterpreted as success.
M9A-3 calibrates an external physical disturbance only. It does not test
balance, stabilization, reflexes, walking, gait, biological function, MaleCNS,
or whether any neural system responds favorably.

Every magnitude has two fresh runs from the frozen corrected M7D/B4 state: P
receives the authoritative Thorax COM force and C receives exactly zero force.
Both receive identical fixed 42-joint commands, zero adhesion, cadence, model,
versions, and duration. MaleCNS, sensory encoding, motor decoding, neural
transitions, CPG/gait/stabilization control, reward/RL/AI, reference
trajectories, hidden assistance, and adaptive tuning are prohibited.

## Frozen ladder and quantitative rationale

The ordered candidates are **0.256, 0.512, 1.024, and 2.048 native force
units**. This conservative factor-two geometric ladder begins twice above the
M9A-2 ceiling. At 0.128, the forensic comparison found approximately
0.000411825 mm maximum root-position and 0.210191 maximum root-velocity
difference, exact divergence at 500.1 ms, monotonic dose response, and no
contact-pattern difference. Local proportional extrapolation predicts position
signals of approximately 0.000824, 0.001647, 0.003295, and 0.006589 mm. The
ladder is frozen before Windows execution; no observed outcome can add, remove,
or alter a candidate.

## Matched-control measurement

At each timestamp the reducer computes **P minus C**, thereby cancelling the
shared passive trajectory that dominated older own-pre-state displacement
metrics. It records vector and Euclidean root-position and linear-velocity
divergence, shortest-arc quaternion orientation angle, body-up tilt difference,
angular-velocity divergence, authoritative six-contact XOR, per-leg distal
tarsus divergence, and first exact physical divergence. P and C timestamps,
initial state, complete pre-force physical trajectories, and actuator commands
must be bit-identical. Any mismatch fails closed.

P targets the unique compiled body whose terminal component is exactly
`Thorax`, in world +Y at its COM with zero torque, on the 200 outgoing 0.1-ms
transitions from 500 ms inclusive through 520 ms exclusive. C is forced to zero
on every transition. Both are observed to 1500 ms, leaving 980 ms after force.
The repaired reducer reconstructs that schedule solely from integer transition
indices: P is nonzero exactly at indices 5000–5199. Recorded accumulated times
are checked against `index * 0.1 ms`, but never decide force-window membership.

## Frozen selection rule

Choose the lowest candidate satisfying all of the following, or select none:

1. finite P and C and at least `1e-9` post-500-ms continuous divergence;
2. contact-pattern divergence **or** root-position divergence `>= 0.005 mm`,
   quaternion orientation divergence `>= 0.25 deg`, or any distal-tarsus
   divergence `>= 0.01 mm`;
3. no launch, fall, or rollover through 750 ms;
4. P-vs-C maxima no greater than `0.5 mm` root position, `30 deg` orientation,
   and `5.0` root linear velocity;
5. each trajectory remains within `1.5 mm` absolute root displacement,
   `60 deg` absolute tilt, and `10.0` absolute root linear speed; and
6. at least 980 ms of post-force observation.

The 0.005-mm root threshold is about 12.1 times the strongest established
0.128 signal and is predicted to be reached only near the top of the ladder;
the orientation/tarsus/contact alternatives catch a physically meaningful
postural disturbance that translation alone misses. The `1e-9` gate separates
a resolved signal from exact equality. Safety limits are deliberately much
larger than the meaningful thresholds while bounding launch, rollover, and
unsafe kinematics.

The M9A-2 `>=25% return` rule is removed. Passive return is not required to
calibrate a safe disturbance, and selecting for it would condition the future
M9B enabled-versus-motor-disabled recovery question on an irrelevant passive
property.

## Evidence and execution boundary

The protocol verifies SHA-256 and byte size for every earlier M9A and M9A-2
evidence file used here and both M9A-3 Attempt-1 raw files. New Attempt-2 raw
P/C files, report, and manifest use its exclusive namespace and exclusive
creation. Attempt-1 files can therefore never be overwritten by Attempt 2.

Static/unit tests and Windows preflight perform zero transitions. The live
command below is documented for separately authorized future Windows use only;
**do not run it now**. There is no M9B route.

```powershell
python -m malecns_backend.embodiment.m9a_3_matched_control_calibration --windows-preflight
# FUTURE SEPARATE AUTHORIZATION ONLY:
python -m malecns_backend.embodiment.m9a_3_matched_control_calibration --run-windows
```

The preflight is dedicated to Attempt 2 and constructs only fresh physics
runtimes for static initialization/identity inspection. It executes zero
physics transitions, zero neural transitions, and never constructs MaleCNS.
