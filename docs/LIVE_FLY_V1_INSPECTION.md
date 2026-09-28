# Live Fly v1 runtime inspection

**Inspection date:** 2026-09-28  
**Scope:** static repository inspection only; no scientific simulation was executed.  
**Frozen checkpoint:** the requested object `ea81974f59ce9a67a382c20d605b385765f10b33` is not present in this shallow checkout, so ancestry against that object could not be verified locally. No existing experiment file was modified.

## A. Live Fly v1 pipeline

The canonical launch command is `python -m malecns_backend.live`. It constructs one `PoseServer`, then calls the continuous headless runner with that publisher (`malecns_backend/live/__main__.py:6-10`). The server is a viewer transport, not a second simulation.

| Stage | Exact implementation | Input | Output / state class | Mapping provenance | In the observed Live Fly v1 path? |
|---|---|---|---|---|---|
| 1. Construct validated runtime | `create_live_session()` in `malecns_backend/live/headless.py:28-44`; `_protocol()` / `_runtime()` in `_windows_m7d_corrected_spontaneous_adapter.py:24-51`; `_scientific_transition_kernel()` in `_windows_m8_live_condition.py:57-429 | M7D enabled condition, seed 1, frozen M6C inventory/admission records, B4 tripod pose, FlyGym 1.2.1/MuJoCo 3.2.7 contract | Persistent `ScientificSession`, `MaleCNSBrain`, FlyGym simulation, measured 42-joint baseline | Experimentally audited engineering construction; not a new Live Fly mapping | Yes |
| 2. Encode body feedback | Kernel lines 244-260; `SensoryEncoder.encode()` in `sensory.py`; six interfaces from `load_six_tibia_interfaces()` in `six_tibia.py:69-137` | Six measured tibia angles at FlyGym indices 5, 12, 19, 26, 33, 40 | Modeled chordotonal rates, stochastically sampled candidate events, then MaleCNS external drive | Sensor identity is annotation-derived; angle-to-rate transduction and event sampling are modeled | Yes. `proprioception_only=True` disables tactile input, not tibia proprioception |
| 3. Advance MaleCNS | Kernel `_windows_m8_live_condition.py:251-267`, calling `MaleCNSBrain.step()` (`neural.py:207+`) once every fifth 0.1-ms physics transition | Existing membrane/conductance/delay state plus delivered external sensory events | Fired dense neuron indices and cumulative `brain.spike_counts`; neural time advances 0.5 ms | Connectome/dynamics runtime; no Live-specific fallback source | Yes |
| 4. Observe motor activity | `MotorActivityObserver.update()` (`motor.py:30-54`), called by the kernel at lines 268-280 | Cumulative spike counts for each admitted population, sampled every 0.5 ms | Per-neuron increments, instantaneous rates, 40-ms Euler low-pass rates, and per-population arithmetic means | Engineering observation/filter over annotation-selected neurons | Yes |
| 5. Decode 11 motor contributions | Kernel lines 272-304; `_rate()` and `compute_raw_contribution()` in `_windows_isolated_tier_b_motor_validation_adapter.py`; `activation()` and `MatchedControlPipeline.update()` in `isolated_tier_b_motor_validation.py` / `tactile_motor_matched_control.py` | Positive- and negative-direction population mean filtered rates, per-joint safe bound and coordinate sign, fixed initial joint baseline | Bounded/slew-limited position offsets for 11 admitted indices; 31 other targets remain at baseline | Population-to-muscle roles are annotation-derived; femur coordinate signs are non-neural kinematic calibrations; nonlinear gain, baseline, limits and slew are modeled/engineering choices | Yes |
| 6. Apply physics action | Kernel line 428 | A full 42-position action: 11 baseline-plus-neural targets and 31 fixed baseline targets; adhesion is six zeros | FlyGym steps MuJoCo by 0.1 ms; updated observation and authoritative MuJoCo `qpos/qvel` | Physics-measured state; no gait, CPG, policy, default animation, or Unity physics | Yes |
| 7. Snapshot pose | `ScientificSession.snapshot()` (`scientific_session.py:115-130`) | Kernel state after a physics state | Root xyz, root quaternion in MuJoCo `wxyz`, all 42 measured joint positions, qpos/qvel and diagnostics | Direct physics state | Yes |
| 8. Publish pose | `run()` (`headless.py:67-85`) and `PoseServer.publish()` (`server.py:47-71`) | Initial snapshot and newest snapshot when 30-Hz wall-clock publisher is due | Newline-delimited UTF-8 JSON `hello`, then capacity-one `pose` packets over single-client TCP 127.0.0.1:8765 | Engineering transport only | Yes |
| 9. Receive in Unity | `LiveFlyClient.Run()` (`LiveFlyClient.cs:105-151`) and `LiveFlyProtocol.ParseHello/ParsePose()` (`LiveFlyProtocol.cs:38-64`) | TCP JSON | Validated CLR `LiveFlyPose` in a newest-pose slot | Engineering transport/validation only | Yes |
| 10. Display pose | `LiveFlyClient.Update()/Apply()` (`LiveFlyClient.cs:79-103`), `LiveFlyCoordinates` and `M7FFlyRig.ApplyLivePose()` (`M7FFlyRig.cs:104-127`) | Root xyz/quaternion and 42 measured radians | Root and joint **Transforms** of the M7F rig | Coordinate/scale/joint-axis presentation mapping; Unity interpolation is optional and disabled in the generated scene | Yes |

The scheduler is multi-rate: physics is 0.1 ms, neural/sensory/decoder updates are 0.5 ms, and transport publication is at most 30 Hz by wall clock. Unity can drop superseded display poses but cannot affect the simulation.

Exactly what Unity receives is a hello record containing protocol/version/session, the ordered 42 joint names, both time steps, units and coordinate convention, followed by pose records containing session ID, sequence, simulation seconds, root xyz, root quaternion `wxyz`, 42 joint positions, and three diagnostics (`physics_transitions`, `neural_transitions`, `finite`). It does **not** receive spikes, rates, motor contributions, contact forces, qvel, sensory events, or actuator controls.

Unity is not authoritative for physics. `M7FFlyRig` is explicitly transform-only; it rotates visual transforms from MuJoCo radians and never feeds Unity state upstream.

## B. Current motor decoder

There are **11 neural motor channels** and a **42-value FlyGym action vector**. “Channel” below means one admitted physical joint target, not one neuron or population. The remaining 31 action entries are held at the fixed initial measured pose.

| Channel (action index) | Decoder populations | Direction/sign status |
|---|---|---|
| `joint_LFTibia` (5) | +: `Ti extensor MN T1 left`; −: `Acc. ti flexor MN T1 left`, `Ti flexor MN T1 left` | Biological direction from body-map annotations; FlyGym coordinate sign +1. Mapping is SUPPORTED, not exact |
| `joint_LMTibia` (12) | +: `Ti extensor MN T2 left`; −: `Ti flexor MN T2 left` | M3D mapping marked EXACT; coordinate sign +1 |
| `joint_LHTibia` (19) | +: `Ti extensor MN T3 left`; −: `Acc. ti flexor MN T3 left`, `Ti flexor MN T3 left` | Annotation-derived/SUPPORTED; coordinate sign +1 |
| `joint_RFTibia` (26) | +: `Ti extensor MN T1 right`; −: `Acc. ti flexor MN T1 right`, `Ti flexor MN T1 right` | Annotation-derived/SUPPORTED; coordinate sign +1 |
| `joint_RMTibia` (33) | +: `Ti extensor MN T2 right`; −: `Acc. ti flexor MN T2 right`, `Ti flexor MN T2 right` | Annotation-derived/SUPPORTED; coordinate sign +1 |
| `joint_RHTibia` (40) | +: `Ti extensor MN T3 right`; −: `Acc. ti flexor MN T3 right`, `Ti flexor MN T3 right` | Annotation-derived/SUPPORTED; coordinate sign +1 |
| `joint_LFFemur` (3) | +: `Sternotrochanter MN`, `Tergotr. MN`, `Tr extensor MN` T1 left; −: `Acc. tr flexor MN`, `Tr flexor MN` T1 left | Biological grouping annotation-backed; physical coordinate sign **−1**, resolved by deterministic non-neural endpoint perturbation |
| `joint_LMFemur` (10) | Same five population families, T2 left | As above; sign −1 |
| `joint_LHFemur` (17) | Same five population families, T3 left | As above; sign −1 |
| `joint_RMFemur` (31) | Same five population families, T2 right | As above; sign −1 |
| `joint_RHFemur` (38) | Same five population families, T3 right | As above; sign −1 |

`joint_RFFemur` is notably **not** admitted, although later candidate work studies it. No coxa, coxa-roll, coxa-yaw, femur-roll, tarsus, adhesion, wing, or body-force channel is driven by the Live Fly v1 decoder.

### Numeric transformation

1. Cumulative spikes are differenced over 0.5 ms.
2. Each neuron gets `instantaneous_hz = increment * 1000 / 0.5`.
3. A 40-ms Euler filter updates each neuron: `filtered += (0.5/40) * (instantaneous-filtered)`.
4. Each named population is the arithmetic mean of its members. Multiple same-direction populations are pooled as a neuron-count-weighted directional mean.
5. Each directional rate uses `activation(r)=1-exp(-r*ln(2)/17 Hz)` (17-Hz half activation).
6. Raw anatomical antagonist output is `safe_bound * (activation(positive)-activation(negative))`, multiplied by the channel coordinate sign (tibia +1; admitted femurs −1).
7. `MatchedControlPipeline` adds that contribution to the **fixed initial measured baseline**, clamps it to the measured joint range, and limits target motion to 4 rad/s at each 0.5-ms update. The safe magnitude bound is computed from the joint limits and baseline and is capped by the modeled 0.25-rad decoder maximum.
8. The enabled M7D gate passes all 11 contributions unchanged; the control condition would zero only those contributions.

Thus the decoder consumes spikes only indirectly: its operative quantity is a 40-ms low-pass filtered firing rate derived from spike-count increments. There is no membrane-voltage decoder, hard activity threshold, learned weight matrix, normalization across channels, or gait phase. Nonlinearity, bounded magnitude, joint-range clipping and slew limiting are present. The fixed pose is a baseline, not a default animation.

## C. Closed-loop status

**Classification: partially closed-loop.** Within Python it is a genuine body → sensory neurons → MaleCNS → motor output → body loop, but only for a narrow interface:

* six measured tibia angles are encoded into the six annotation-backed chordotonal populations;
* those external events enter the same `MaleCNSBrain` that supplies the 11 decoder channels;
* the resulting 11 position contributions affect MuJoCo, whose next measured tibia angles feed the next neural update.

It is not fully closed-loop embodiment because only tibia angle proprioception returns. Contact/tactile feedback is explicitly excluded in the live session (`proprioception_only=True`); body root pose, velocity, loads/contact forces, femur/coxa/tarsus angles, vision, olfaction and other state are not encoded back. Unity has no return path at all. The precise break is after MuJoCo observation: the kernel selects only the six tibia joint angles for sensory encoding and discards the other physical measurements for neural input.

## D. Why the legs twitched

For the documented `python -m malecns_backend.live` + `LiveFly` scene path, there is no test animation or locomotion fallback. The visible chain is: spontaneous and sensory-influenced MaleCNS spikes → nonzero filtered activity in admitted tibia/femur motor populations → nonzero antagonist contributions → changes to 11 FlyGym position targets → MuJoCo joint motion → measured 42-joint snapshots → TCP poses → M7F transform rotations. The other 31 joints can still move passively under MuJoCo dynamics even though their commanded targets remain at baseline.

The Unity scene cannot originate twitching: the client only applies received physics poses, interpolation defaults off, and the rig is transform-only. The Python construction also explicitly uses no locomotion/reference controller and sends zero adhesion.

Static repository inspection cannot prove which executable/scene was used in a past viewing or authenticate that historical session. Therefore the strongest non-speculative conclusion is conditional: **if the run followed the documented Live Fly v1 command and scene, the twitch was authoritative MuJoCo motion driven by actual MaleCNS-derived decoder contributions (plus passive dynamics), not a Unity/default animation.** The runtime diagnostics (accepted session/sequence/sim-time and applied-pose counters) are the available way to establish that condition during a run.

## Existing scientific work and chronology

The Live transport/viewer was committed on 2026-09-24 and reused the already admitted M7D/M6C 11-channel runtime. The later repository work did not create the Live v1 decoder:

* The six-tibia interface established the six tibia motor/sensory identities and decoder lineage used by Live v1. LM is the exact validated reference; the other five are supported anatomical extensions.
* M6A/M6B/M6C established the whole-leg inventory, mechanical signs, isolated eligibility, and 11-channel admission that Live v1 imports. Coxa-yaw remained excluded because its coordinate sign was unresolved; later coxa-yaw anatomical/sign work did not add it to Live v1.
* The motor-population activity survey (2026-09-26) is a later read-only characterization. Its freeze reports 17 low-activity populations and explicitly says activity does not establish function or admission. It observes the existing decoder-used populations plus others; it did not choose Live v1 channels.
* The candidate-motor-channel experiment/validation (2026-09-25 onward) is later and independent of the frozen 11-channel admission. Its report explicitly confirms that Live v1 was unchanged; in particular its `joint_RFFemur` candidate is not a Live v1 channel.
* M8 extended spontaneous, LF proximal replay assessment/extraction, LF proximal motor recruitment, and the propagation-localization work are downstream characterization/validation efforts. They do not alter the Live v1 channel list or equations. The LF recruitment work targets evidence about already identified proximal populations; it is not the source of the decoder.
* Tactile/contact and six-tibia causal experiments establish or test narrower feedback paths, but Live v1 deliberately selects proprioception-only and does not enable tactile feedback.

Tracked committed artifacts and code are authoritative only to the extent of their own status fields and provenance locks. The inspection found no untracked files in this checkout. Large LFS-backed outputs that are present only as pointer text were not treated as readable evidence.

## E. Smallest Live Fly v2 gaps

1. **Add observational provenance/telemetry at the existing live boundary:** record the 11 population spike increments/filter states, directional rates, raw/admitted contributions, commanded targets, measured joints, six encoded sensory rates/events, and causal timestamps beside each pose. Do not alter equations.
2. **Make session identity scientifically reproducible:** emit hashes/versions for connectome, admission artifacts, initial state, FlyGym/MuJoCo, channel inventory, signs and decoder constants; fail closed on mismatch.
3. **Time-align transport and science:** associate every displayed pose with its exact physics transition and most recent neural transition rather than only 30-Hz wall-clock sampling; retain loss/drop counters.
4. **Characterize the existing 11 channels before expanding them:** quantify spontaneous activity, decoder occupancy, clipping/slew, command-to-measured response, and contribution/body causality. This is the proposed Experiment 3 below.
5. **Only after evidence, broaden feedback:** define and validate additional body measurements and their already-supported sensory targets. Full closure is not achieved merely by returning Unity state; MuJoCo should remain authoritative and sensory encoders should consume its measured state.

No new bridge, visualization, neural population, gain, sign, threshold, decoder weight, or Unity physics is required for these minimum gaps.

## F. Proposed Experiment 3: characterize the 11 Live v1 outputs

**Title:** Live Fly v1 11-channel motor-output observability assay.

**Scope:** a read-only, preregistered instrumentation experiment around the unchanged enabled Live v1 runtime. Use the exact current seed, initial pose, 0.5-ms neural cadence, 0.1-ms physics cadence, populations, signs, gains, filter, clipping, slew and sensory configuration. Do not add candidates (including RF femur or coxa-yaw) and do not tune on results.

**Paired conditions:** (A) existing enabled 11 contributions and (B) the existing matched gate that zeros only the 11 final contributions, each from a fresh equivalent state. The control already exists in M7D; Experiment 3 should expose it through a finite, artifact-writing runner rather than alter Live v1.

**Record per neural transition:** per-neuron spike increments for every currently decoded population; per-population and pooled-direction filtered Hz; activation values; raw signed contribution; admitted contribution; range/slew flags; 42-vector target. Record per physics transition: measured 42 joints, qpos/qvel, root pose, contacts, and command. Record six sensory rates, sampled candidates and delivered events.

**Primary outputs:** for each of the 11 channels, first activity/output/physical-response times, spike/rate distributions, nonzero duty fraction, positive-vs-negative balance, contribution distribution, saturation/slew occupancy, command-to-measured lag/correlation, and enabled-minus-control joint divergence. Also report passive motion on all 31 baseline-only joints. Classify each channel only as observed active/inactive, decoder-output/no-output, and physically divergent/non-divergent; do not infer natural behavior or biological sufficiency.

This is narrower and more interpretable than searching for new populations: it directly tests the exact motor signals that generated Live v1 commands.

## G. File plan (proposal only)

No implementation files are changed by this inspection. For Experiment 3, create only:

* `malecns_backend/embodiment/live_v1_motor_output_experiment.py` — inert preregistration/validation/CLI; no run on import.
* `malecns_backend/embodiment/_windows_live_v1_motor_output_experiment_adapter.py` — environment-specific runner that wraps the existing kernel without changing it.
* `malecns_backend/embodiment/LIVE_V1_MOTOR_OUTPUT_EXPERIMENT.md` — protocol, interpretation limits and run instructions.
* `tests/test_live_v1_motor_output_experiment.py` — zero-transition, inventory, equivalence, schema and fail-closed tests.
* A new `malecns_backend/embodiment/interface_output/live_v1_motor_output_experiment/` namespace for preregistration and, only after separately authorized execution, raw/manifest/report artifacts.

The preferred design requires **no modification** to MaleCNS, populations, sensory encoders, motor equations, FlyGym/MuJoCo construction, live TCP transport, or Unity. If the existing kernel cannot expose all required read-only values through its present optional detailed telemetry hooks, the only existing-file change should be a strictly observational callback parameter in `_windows_m8_live_condition.py`, defaulting to `None` and regression-tested to leave all state/actions bit-identical. That modification is not made here.
