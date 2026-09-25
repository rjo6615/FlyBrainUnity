# Validation of three proposed MaleCNS motor channels

## 1. Executive summary

This task stopped at the requested fail-closed boundary. Identity reconstruction
and decoder-only tests passed for `joint_RFFemur` (action 24),
`joint_LFTarsus1` (6), and `joint_RFTarsus1` (27). The retained non-neural
endpoint captures reproduce a negative vertical displacement for positive
MuJoCo perturbations and therefore reproduce the historical coordinate sign
`-1`. They do **not**, however, retain the owning-body transform newly required
by this protocol. FlyGym and MuJoCo are not installed in this environment, so a
new independent compiled-model inspection could not be performed. Mechanical
validation is consequently incomplete for all three candidates.

No machine-readable *preregistration* was created: Phase J permits one only if
all sign validation succeeds. The committed JSON is instead a read-only
**validation record**, explicitly marked `preregistration_created: false`. No
channel was admitted, no canonical experiment was run, and silence caused no
tuning or population changes.

## 2–3. Exact mappings and ID/dense-index validation

The direct source is `fly-brain-main/public/data/bodymap.json`; its compiled
identity inventory is `malecns_backend/interface_map.json`, dataset **Male CNS
v1.0**, 165,122 neurons. Every source row occurred exactly once, its exact
annotation/actuator/direction agreed with the compiled row, every ID had one
dense index, and all IDs, indices, and opposing pools were duplicate-free and
disjoint. There were no missing IDs or unexpected resolutions.

| Channel / pool | Exact annotation | side / segment | body/root IDs | current dense indices | n |
|---|---|---|---|---|---:|
| RF Femur − | Acc. tr flexor MN T1 right | right / T1 | 807873, 1050306082, 1050349786 | 149013, 164683, 164687 | 3 |
| RF Femur − | Tr flexor MN T1 right | right / T1 | 816648, 817640, 818719, 820130, 820668, 903010, 914655 | 155875, 156489, 157046, 157561, 157697, 159230, 162321 | 7 |
| RF Femur + | Sternotrochanter MN T1 right | right / T1 | 801079, 803698 | 143581, 145568 | 2 |
| RF Femur + | Tergotr. MN T1 right | right / T1 | 804866, 817347, 909521, 924716 | 146511, 156301, 161362, 162567 | 4 |
| RF Femur + | Tr extensor MN T1 right | right / T1 | 818842, 838321 | 157103, 158670 | 2 |
| LF Tarsus1 − | Ta depressor MN T1 left | left / T1 | 817655, 819278, 1050403926, 1050660827, 1051062549 | 156498, 157269, 164697, 164725, 164766 | 5 |
| LF Tarsus1 + | Ta levator MN T1 left | left / T1 | 810541, 1050111955 | 151228, 164626 | 2 |
| RF Tarsus1 − | Ta depressor MN T1 right | right / T1 | 825721, 1050248133, 1050380236, 1050815462 | 158308, 164672, 164694, 164739 | 4 |
| RF Tarsus1 + | Ta levator MN T1 right | right / T1 | 817210, 820110, 820896 | 156216, 157553, 157751 | 3 |

“Tergotrochanter” is represented by the authoritative exact string `Tergotr.`;
it was not renamed. The source provides body IDs (the repository also calls
these root IDs), not a separate root-ID namespace.

## 4. Directional-pool reconstruction

RF Femur uses the same annotation-sign rule as the admitted LF, LM, LH, RM, and
RH femur mappings: `dir=+1` comprises Sternotrochanter, Tergotr., and Tr
extensor; `dir=-1` comprises Acc. tr flexor and Tr flexor. RF therefore has no
directional-rule exception. LF/RF Tarsus1 use only levator (+) versus depressor
(−); no population was inferred or added.

These signs are anatomical decoder directions. The separately applied physical
coordinate sign is `-1`; the grouping was not selected in response to activity.

## 5. Decoder-only results

All inputs were labeled `ENGINEERED_TEST_INPUT_NOT_BIOLOGICAL_EVIDENCE`. For
each candidate independently, tests covered positive-only, negative-only,
zero/zero, equal opposition, asymmetric opposition, asymptotic saturation,
4 rad/s slew, range clamp, baseline addition, and physical sign application.
The frozen transfer function was
`a(r)=1-exp(-r*ln(2)/17)` and
`raw=0.25*(a(positive)-a(negative))` radians, followed by coordinate sign `-1`.

All tests passed. Zero and equal input produced exactly zero; isolated inputs
produced opposite responses; saturation stayed at or below 0.25 rad; a 1 ms
step moved no more than 0.004 rad; zero contribution preserved the 0.123 rad
test baseline. Each 42-vector had either no nonzero entry or only the selected
index, leaving the other 41 exactly zero. Means of engineered 34 Hz pools of
sizes 2 and 7 were both 34 Hz, excluding accidental population sums. The audit
does not edit or invoke the existing 11-channel implementation, so its semantics
and inventory remain unchanged.

## 6. Physical sign revalidation

| Coordinate | compiled actuator → joint | local axis | neutral (rad) | effective target range (rad) | +ε minus −ε endpoint displacement | outcome |
|---|---|---|---:|---|---|---|
| LF Tarsus1 | actuator 6 `1/actuator_position_joint_LFTarsus1` → joint 7 | [0,1,0] | 0 | [−1e6,1e6] | [4.43317e−5, 0, −1.08597e−4] | historical −1 reproduced from capture; incomplete independent audit |
| RF Femur | actuator 24 `1/actuator_position_joint_RFFemur` → joint 59 | [0,1,0] | −2.2689280276 | [−1e6,1e6] | [1.31137e−4, 0, −3.37410e−4] | historical −1 reproduced from capture; incomplete independent audit |
| RF Tarsus1 | actuator 27 `1/actuator_position_joint_RFTarsus1` → joint 62 | [0,1,0] | 0 | [−1e6,1e6] | [4.43317e−5, 0, −1.08597e−4] | historical −1 reproduced from capture; incomplete independent audit |

The deterministic perturbation was independently evaluated per coordinate at
ε=0.0001 rad; no bilateral or cross-joint inference was used. The endpoint
subtractions exactly reproduce their stored displacements and negative Z
projections. However, the capture lacks owning-body `xmat`, segment rotation,
and neutral endpoint fields. Repeating compilation/perturbation is impossible
without the absent dependencies. Under the stated rule, none proceeds and the
overall mechanical result is **MECHANICAL_FAILURE (incomplete evidence)**.

## 7. Historical-silence investigation

The immutable 500 ms M6B result classifies all three as
`NO_MAPPED_MOTOR_ACTIVITY`; each retained summary has peak absolute raw and
admitted contribution exactly 0.0. This establishes aggregate silence in that
run and rules out physical admission as its cause. The present exact ID audit
finds no current dense-index mismatch (C) or filter mismatch (D).

M6B did not retain per-neuron counts, increments, filtered rates, or directional
means for these silent channels. It is therefore not scientifically possible
to distinguish genuine neuron-level zero (A), very low activity (B), decoder
cancellation (E), an insufficient 500 ms window (F), or an unrecorded historical
plumbing issue (G). The result is **not invented or upgraded**: historical
aggregate silence is genuine, while its neuron-level cause remains unresolved.

## 8. Fixed observation window

A future observation is fixed at **1,000 ms**, exactly 2× the historical 500 ms
duration, chosen before viewing any new activity. It must not be extended after
start. Any later longer duration requires a separate preregistration.

## 9. Proposed isolated experiment (design only; not preregistered/run)

For each candidate separately, create fresh ENABLED and ZEROED simulations
from identical MaleCNS state, sensory state/model, seed 1, physics, decoder
state, baseline policy, initialization, neural timestep, and physics timestep.
Require bit-exact equality through intervention. Compute the full raw decoder
in both conditions; immediately before physical application retain only the
candidate contribution in ENABLED and replace only it with exactly zero in
ZEROED. Admit at most one candidate. Keep the current 11 channels under the
explicit **zero-neural-contribution policy** used by historical isolated Tier-B
validation; all other entries are zero. Authorize exactly one of indices
6/24/27 per pair and assert all other 41 entries are zero at every transition.

Record timestamps/transition indices; per-neuron cumulative counts, increments,
instantaneous and filtered rates; both pool means; raw antagonist and signed
contribution; full 42-vector; baseline, commanded coordinate and ctrl; all joint
qpos/qvel; root pose; limits and warning state. Primary activity evidence is
numeric, never visual. No gait controller, stabilization, trajectory, target,
hidden force, changed sensory input, tuning, substitution, or result-dependent
rerun is permitted.

## 10. Predefined outcomes

* **IDENTITY_FAILURE**: any required row/ID is absent, ambiguous, unexpected,
  duplicated inappropriately, overlaps its opponent, or disagrees with source.
* **MECHANICAL_FAILURE**: compiled transmission, transform, perturbation, or
  sign is unresolved/inconsistent (the current blocking classification).
* **SOFTWARE_FAILURE**: any deterministic decoder, isolation, safety, vector,
  baseline, or 11-channel regression check fails.
* **SUPPORTED_AND_ACTIVE**: identity/mechanics/software pass and any exact
  nonzero decoded contribution occurs in the fixed window.
* **SUPPORTED_BUT_SILENT**: those validations pass, every candidate neuron
  increment and contribution is exactly zero throughout the fixed window.
* **DECODER_CANCELLATION**: at least one neuron/pool is active while the raw
  antagonist remains exactly zero, or within a preregistered numeric tolerance
  that must be frozen before execution.
* Nonzero sub-threshold activity without measurable decoder output is reported
  separately as **SUPPORTED_LOW_ACTIVITY**, not silently called zero.

## 11. Permanent-admission policy

Historical M6B/M6C admission required isolated motor causality; the three
silent channels were consequently not admitted. The preferred rule—allowing
permanent admission after valid identity, correspondence, decoder, and safety
despite silence—is scientifically coherent, but differs from that historical
causality gate. It is therefore a methodological policy change and must be
explicitly reviewed, versioned, and documented. This audit recommends that
`SUPPORTED_BUT_SILENT` be *eligible for scientific mapping admission only after
that policy amendment*, never automatically admitted by this task. Silence is
not a mapping failure, and it must not trigger tuning.

## 12–16. Artifact, files, commands, status, and assurances

No preregistration path or preregistration SHA-256 exists because Phase J's
precondition failed. The validation record is
`malecns_backend/embodiment/interface_output/candidate_motor_channel_validation.json`;
its SHA-256 is recorded in the delivery response after the final committed
bytes are checked.

Files added are the audit module, its generated validation JSON, this report,
and focused tests. Commands used are recorded in the delivery response. The
final Git status is also reported there.

Confirmed: the current 11-channel Live Fly runtime was not changed; none of the
three channels was admitted; no canonical experiment was run; no canonical
artifact was modified; and the proposed 14-channel interface was not built.
