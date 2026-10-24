# Tactile disturbance and recovery v1

Specified before new outcomes, 2026-10-24. Question: from the same pre-push neural
and physical state, does continued modeled tactile delivery change the response
to a fixed lateral thorax pulse relative to withdrawing tactile input? Undisturbed
controls distinguish withdrawal effects from disturbance-specific effects.

## Four cells, three new runs

| ID | Tactile before/at 500.0 ms | Tactile from 500.5 ms | Force |
|---|---|---|---|
| ON_C | enabled | enabled | zero; reuse archived matched-pair ENABLED |
| OFF_C | enabled | withheld | zero; fresh |
| OFF_P | enabled | withheld | fixed pulse; fresh |
| ON_P | enabled | enabled | fixed pulse; fresh |

Fresh order is OFF_C, OFF_P, ON_P, seed 1, two seconds / 20000 physics transitions /
4000 neural updates / 20001 observations each. No retry or automatic force sweep.
Reuse ON_C only after verifying its full archive/source/evaluation and exact
reproduction of every new arm's physical and neural prefix through 500.0 ms.
Do not rerun an unchanged undisturbed control merely to duplicate costly evidence.
The older always-withheld arm is not a valid no-push control for this new design.

All arms start with the existing 20 motor channels and 1877 tactile / 392
proprioceptive neurons, normal supported live-v3 physics, unchanged encoder,
calibrated neural parameters and the previous assay's common 2269-slot external
RNG schedule. Tactile candidates are sampled in every arm irrespective of delivery.
At the first neural step after pulse onset (500.5 ms), OFF switches only the
existing external delivery mask. No neural, joint-gain, threshold, contact,
collision, support, adhesion or reference-controller parameter is revised.
Ordinary live mode remains unchanged; no balancing machinery is added.

## Preselected disturbance and application audit

Reuse M9B's existing engineering pulse: world force [0, 1.024, 0] in native model
units, zero torque, at the uniquely resolved exact Thorax body COM, outgoing
transitions 5000 through 5199. There are exactly 200 applied transitions, impulse
0.02048 native-force seconds. Use the existing kernel force callback and
`m9b.force_at_transition`; do not add an alternative physics loop or actuator rule.
Verify the existing M9A/M9B engineering provenance (already checked before this
protocol). That historical calibration used another motor context; it establishes
the pulse's origin, not guaranteed effectiveness or biological disturbance scaling
in the present tactile-enabled body. Do not change magnitude to obtain a response.

Initial/reset force is zero. Observation i records force applied during outgoing
transition i-1: nonzero rows 5001..5200, first affected state 500.1 ms, first
observed cleared-force state 520.1 ms. Record all nonzero applied body wrenches
with exact IDs and require the complete expected sparse array, including all zero
torques and absence of other body forces; generalized applied force stays zero.
External force is applied only to Thorax, never directly to a distal sensor body.

The old no-force contact audit must remain unchanged and rejects forced rows by
design. Retain its full result, and separately replace that one requirement with
the stricter exact planned-wrench audit in this versioned protocol. Preserve all
other identity, force-reconstruction, telemetry, configuration, finite-physics,
zero-adhesion and coverage checks. Unexpected collisions or positive calibration-
surface forces make ground-context interpretation inconclusive; never filter them.

## Matching and causal boundaries

Require the complete matched-delivery prerequisite and current source hashes,
same initial neural/model/encoder/motor/physical state, exact prefix through
physics index 5000 and neural index 1000 in all four cells, and common CNS uniform
hash/RNG state at every subsequent neural tick. Within each push/no-push pair,
verify identical pre-force trajectories. Within each ON/OFF pair, require identical
pre-step neural/offered-candidate and physical/encoder states through the first
post-500-ms eligible tactile event that OFF withholds. Differences after either
intervention can be outcomes and must not be rejected just for diverging.

Verify all offered/eligible/delivered identities, actual refractory eligibility,
phase-specific masks, intact proprioceptive delivery and actual motor observer
readouts. Preserve the silent right-front tarsus result if it persists. A change
in motor spikes and passive movement of a coordinate are distinct observations.

## Predeclared descriptive recovery criteria

Primary comparisons are within phase-matched controls: ON_P-ON_C and OFF_P-OFF_C.
Use the existing normalized shortest-arc quaternion observer. Report a time-resolved
factorial contrast and complete trajectories; raw ON/OFF separation alone is not
disturbance attribution. Norms/recovery times are nonlinear descriptive contrasts,
not a linear estimator of a unique motor mechanism.

For each push/control pair, record orientation error (degrees), root-height error
(model mm), linear-velocity error (native model mm/s), angular-velocity error
(rad/s), absolute body up/height, exact-ground distal support count, and recovery.
Record full force-on [500,520] ms and cleared-force [520.1,2000] ms windows using
integer indices, without selecting a successful subwindow.

The pulse is a resolved perturbation only if peak shortest-arc error exceeds
0.25 degrees OR peak root position deviation exceeds 0.005 model mm. These
resolution floors reuse M10B/M10C values; they are not biological limits.

Prospective engineering recovery bands: orientation error <=5 degrees, absolute
root-height error <=0.05 model mm, linear-speed error <=1 model mm/s, angular-speed
error <=1 rad/s, body up_z>0.5, root height > half the initial height, and at least
three exact-ground distal contacts. Require 100 ms continuously in all bands
(1001 consecutive stored states), starting no earlier than the first cleared-force
state. Record entry and confirmation times. If the response never left the relative
error bands, label NO_BAND_EXIT rather than claiming recovered balance. If no
100-ms interval qualifies before the fixed end, label NOT_RECOVERED_IN_WINDOW.

Qualify the pre-push reference as an upright supported baseline only if all states
400..500 ms have up_z>0.5 and height above half the initial value, and mean exact-
ground contact count in that window is >=3. Failure is reported without changing
criteria. These are deliberately limited static-support engineering definitions;
dynamic stability or locomotion need other tests.

Verify the leading free-joint addresses before interpreting root state. Convert
its body-local angular qvel to world axes with the normalized root quaternion
before subtracting pushed/control angular velocities; linear free-joint velocity
is already world-oriented. See the versioned
[MuJoCo floating-object conventions](https://mujoco.readthedocs.io/en/3.2.7/overview.html#floating-objects).
Do not compare vector components expressed in differently oriented local frames.

Report post-force mean/integral and peak orientation error, height error, velocity
errors, support losses, rollover/low-height samples and recovery status. An
orientation-attenuation label requires lower peak AND mean error with continued
tactile delivery by >0.25 degrees; amplification uses the reverse inequalities;
otherwise the label is MIXED_OR_UNRESOLVED. Report the other metrics independently,
never hide deterioration in a composite score. Insufficient pulse effect,
unqualified baseline, no band exit or absent withdrawal exposure limits functional
interpretation. Integrity can pass with null, amplified or unrecovered outcomes.

This experiment tests the contribution of continued tactile delivery under one
modeled disturbance. It does not by itself distinguish every passive mechanical
effect from active motor stabilization, establish biological balancing, or prove
gait. A subsequent motor-application control may still be required. No automatic
ACTIVE_BALANCE_PROVEN or walking classification is permitted.

## Evidence, execution and review

Reserve a new output directory exclusively before initialization. Save each fresh
arm's full raw trace separately as gzip JSON, including partial/errors, plus a
manifest with raw/compressed hashes, source locks, baseline reference and complete
analysis. Preserve all old evidence. An interruption stops further fresh runs and
preserves what was collected; other errors remain failures without retries.
The protocol/implementation must be committed before scientific execution.

Use the existing validated Python path in Git Bash:

```bash
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
"$PY" -m pytest -q tests/test_tactile_recovery.py
"$PY" -m malecns_backend.live.tactile_recovery --output-dir tactile-recovery-dry
echo $?  # expected 1, NOT_RUN
"$PY" -m malecns_backend.live.tactile_recovery --live --output-dir tactile-recovery-v1
echo $?  # 0 only on complete verified integrity; recovery success is not required
```

The live command is for the predeclared three fresh runs or a separately planned
independent replication, not repeated attempts to obtain recovery. No force/seed/
window/threshold knobs. Current validated environment is FlyGym 1.2.1 / MuJoCo
3.2.7. Keep the prior known historical tactile-contact artifact test failure
visible; do not refresh its checksum or alter its unchanged population evidence.
Unity review, if provided, must label recorded conditions and clip resets clearly,
use measured poses, and neither rerun CNS nor imply the replay reset is a jump.
