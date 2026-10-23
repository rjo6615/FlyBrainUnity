# Live Fly Phase 4 Unity viewer

`LiveFlyClient` is an output-only presentation client for `live_fly_pose` v1. It
does not launch or control Python and sends no data. Python/MuJoCo remains the
authority for time, physics, neural execution, body pose, and all 42 joint
positions.

## Component setup

1. Use the existing M7F workflow to create an authoritative M7F fly, or add
   `M7FScientificFlyBuilder` to a GameObject and invoke **Rebuild**.
2. Add `LiveFlyClient` to a scene GameObject and assign that fly's `M7FFlyRig`.
3. Keep host `127.0.0.1`, port `8765`, **Connect On Start** enabled, and
   **Presentation Interpolation** disabled for direct/latest-pose validation.
4. Do not run an M7F replay controller against the same rig.

The Inspector exposes state, session ID, last sequence/simulation time, received
poses, and replaced poses. Connection and JSON work runs on a task. `Update`
alone converts and applies the newest capacity-one pose to Unity transforms.
The runtime overlay separately reports TCP connection, hello receipt and
acceptance, raw and pose lines, accepted/rejected poses, slot consumption, rig
application, and the last background transport/parser/validation error.

The legacy `UnityFlyBridge` is deliberately not auto-installed when a
`LiveFlyClient` exists. The Python Live Fly publisher is single-client; allowing
the legacy `fly_state` client to connect first would consume and ignore the v1
hello/pose stream while the real client remained connected only at the TCP
backlog and waited forever for a hello.

## Coordinates

This viewer deliberately reuses the validated M7F import convention rather than
introducing another model basis. The polar basis is
`B(x,y,z) = (x,z,y)`, and the established M7F presentation scale is
`1 source mm = 0.1 Unity unit`. Since `det(B) = -1`, source axial joint axes use
`det(B) B`; the existing rig already stores those converted local axes. For a
source rotation matrix `R_s`, root orientation is `R_u = B R_s B^-1`.
`M7FCoordinates.SourceQuaternionToUnity` implements this by converting the
rotated source forward/up vectors and reconstructing the proper Unity rotation.
The wire quaternion is explicitly decoded from `[w,x,y,z]` before conversion.

## Manual acceptance

1. In a terminal run `python -m malecns_backend.live` and wait for initialization.
2. Press Play in Unity. Confirm status becomes **Receiving** and note session ID,
   sequence, and simulation time.
3. Observe authoritative live body/articulated motion for at least 30 wall seconds.
4. Stop Unity; verify Python continues advancing.
5. Press Play again; verify the same session ID and a later simulation time.
6. Stop Unity, then press Ctrl+C in the terminal and confirm Python shuts down.

Unity Stop only cancels/closes its TCP client. It never terminates or resets the
manually managed Python process.

## Motor interface selection

The terminal launcher defaults to the original 11-channel v1 session. Select an
expanded inventory explicitly from the repository root:

```sh
python -m malecns_backend.live --motor-interface v2
python -m malecns_backend.live --motor-interface v3
```

v2 admits 17 motor channels; v3 admits 20, including `joint_RFFemur`,
`joint_LFTarsus1`, and `joint_RFTarsus1`. All versions retain the six tibia
proprioceptive sensory inputs. Admission does not guarantee nonzero neural
output or visible movement. The startup line reports the selected inventory.
Only run one publisher at a time on port 8765.

### Manual checks for interface selection

1. Run `python -m malecns_backend.live --help`; expect v1/v2/v3 choices and exit.
2. Run `python -m malecns_backend.live --motor-interface v4`; expect an argument
   error and no session or pose server started.
3. Run the command without options; expect `motor_interface=v1 motor_channels=11
   sensory_channels=6`. Stop with Ctrl+C after initialization.
4. Run with `--motor-interface v2`; expect 17 motor channels and six sensory
   channels. Stop it before the next check.
5. Run with `--motor-interface v3`; expect 20 motor channels and six sensory
   channels. Wait for initialization, then press Play in the Unity Live Fly scene.
   Expect **Receiving**, advancing simulation time, and no transport errors.
6. Observe the terminal motor contributions for the three candidate joints.
   Record any nonzero contributions; if absent, record the simulated observation
   duration. Absence alone does not prove a mechanical failure.
7. Stop and restart Unity; expect the same Python session ID and later simulation
   time. Stop Unity and Ctrl+C Python; expect normal shutdown.

## Passive v3 candidate diagnostics

Run `python -m malecns_backend.live --motor-interface v3`. Each periodic
status now includes `candidates=[...]` for RFFemur, LFTarsus1, and RFTarsus1,
even when their output is zero. A final candidate summary is printed on Ctrl+C.

- `pos_hz` / `neg_hz`: latest pooled positive/negative filtered rates.
- `populations`: latest filtered rate for each exact annotated population.
- `raw_rad` / `final_rad`: latest raw decoder and final contribution.
- `samples`: cumulative complete neural telemetry records for that channel.
- `spikes`: cumulative observed spike increments across its unique neurons.
- `pos_steps` / `neg_steps`: updates with a positive filtered pool rate.
- `raw_steps` / `final_steps`: updates with nonzero raw/final output.
- `peak_final_rad`: maximum absolute final contribution since launch.

These counters update on every neural record, independently of terminal cadence.
Filtered rates can persist after a spike; rate-active steps are not spike counts.
Nonzero counters include arbitrarily small residual output; use the peak to judge
magnitude. Missing fields display `unavailable`, not silence. v1/v2 omit the
candidate section because those channels are not admitted. Storage retains only
three channel summaries and the latest record, with no growing history.

### Manual candidate investigation

1. Launch v3 and wait for initialization. Confirm all three candidates appear,
   including those with zero rates/output, and `samples` increases.
2. Let it run for at least 10 **simulated** seconds (about three wall minutes at
   the previously observed speed). Keep the `sim=` value with the results.
3. Check `spikes` and population rates. Zero spikes across observed samples
   indicate no observed firing in that window. Nonzero positive/negative rates
   with zero raw output can indicate decoder cancellation or its zero-response
   region; they do not by themselves establish a wiring fault.
4. If `raw_steps>0` but `final_steps=0`, investigate the downstream output path.
   If `final_steps>0`, brief output occurred even if the latest sample is zero;
   inspect `peak_final_rad` for its magnitude.
5. Confirm Unity still receives poses and advances time. Press Ctrl+C in Python;
   save the final candidate summary and last simulation time for comparison.
6. Optionally launch v1 or v2 after stopping v3; expect the existing motor status
   without candidate diagnostics. Only one publisher may use port 8765.

Diagnostics consume the existing read-only observer records. They add no neural
stimulation, admission changes, decoder tuning, or physics changes. Python
formatting and counting may add wall-time overhead.

## Optional upstream neuron investigation

For silent candidate populations, enable an independent identity/readout check
and per-neuron state measurements:

```sh
python -m malecns_backend.live --motor-interface v3 --upstream-diagnostics
```

The option requires v3. Without the flag, no probe is constructed. With it, the
probe checks exact population membership, body ID to dense-index round trips,
and observer index membership. On every neural update it compares the observer's
cumulative counts directly against the raw brain counts at those indices. A
mismatch stops the run with an explicit error instead of reporting silence.

Periodic `upstream_samples=... identity=verified readout=verified upstream=[...]`
text summarizes cumulative raw spikes, peak absolute excitatory/inhibitory
synaptic state, and minimum sampled threshold gap for each candidate. On Ctrl+C,
`LIVE final upstream={...}` contains the full JSON report for every neuron,
including body ID, dense index, annotated population, anatomical incoming edge
count, static effective positive/negative incoming edge counts, voltage extrema,
conductance extrema, input-active update counts, and latest external drive.

Effective graph counts use the runtime's filtered weights, presynaptic signs and
PSP scale. They do not incorporate dynamic depression or establish that those
presynaptic neurons fired. Input-active updates count nonzero sampled synaptic
state, including decaying residuals; they are not counts of new delivery events.

Voltage and conductance are sampled **after** integration, spike reset and
synaptic decay. The threshold gap is threshold plus adaptation and offset minus
post-step voltage. It is not a pre-reset voltage peak, and cannot establish how
close a neuron came to threshold immediately before a spike. In current-based
configurations the `g_exc`/`g_inh` arrays represent synaptic state rather than
conductance. These measurements do not change neural inputs or equations.

### Manual upstream tests

1. Run the command above; allow additional initialization time for the one-time
   incoming graph scan. Confirm `identity=verified readout=verified` and rising
   `upstream_samples`. If a mismatch is reported, save the complete exception.
2. Run at least 10 simulated seconds. Confirm Unity still receives poses.
3. Stop Unity, then Ctrl+C Python. Save the last `LIVE final` timing line and the
   complete `LIVE final upstream={...}` line (redirect terminal output to a file
   if copying the long JSON line is inconvenient).
4. Zero effective incoming edges indicates no static incoming pathway under the
   current weight/sign filters. Nonzero edges with zero input-state peaks means
   no input was observed at the post-step sampling points. Nonzero input-state
   peaks with zero raw spikes supports input arriving without observed firing;
   compare voltage and threshold-gap measurements before inferring a cause.
5. Run v3 without the flag after stopping the first process. Expect the existing
   candidate counters and no upstream section. `--upstream-diagnostics` with v1
   or v2 must report an argument error before opening the pose server.

The probe retains fixed per-neuron summaries and no time-series history. It may
reduce wall-clock speed; compare runs using simulation time.

### Direct presynaptic activity and sensory paths

The same `--upstream-diagnostics` command now also traces each candidate's
effective direct inputs. Periodic `inputs(...)` summaries compare the channels:
`exc_active_inputs` / `inh_active_inputs` count active source-to-target pairs
(shared sources count once for each target); `sensory_reached` counts candidate
neurons with a positive-edge structural path from any of the six currently
configured tibia sensory populations. Missing source configuration is reported
as unavailable.

The final `LIVE final upstream={...}` report adds two fields per motor neuron:

- `presynaptic`: unique excitatory/inhibitory source counts, how many sources
  fired, their cumulative spikes since probe construction, and a representative
  source's exact body ID, dense index, type, count, and static effective weight.
  The representative maximizes spike count times absolute static weight. When
  all sources are silent, it identifies the largest static source weight instead.
  Parallel edges from one source are combined before counting or ranking.
- `sensory_path`: a shortest directed path over positive effective edges from
  any current sensory source, with source leg, hop count, and body IDs. Equal
  shortest paths use source/graph iteration order; the chosen source leg does
  not establish biological dominance or prove that other legs lack paths.
- `sensory_path_spikes`: cumulative raw spike increments since probe
  construction for each body ID in the reported path, in the same order. Use
  these to locate the first silent node on that chosen route; an empty tuple
  means no path is available. A path's active nodes still do not establish
  causal transmission along its particular edges.

Positive-only paths exclude inhibitory and disinhibitory mechanisms. A
`no_positive_path` result therefore does not mean no functional network route
exists. A positive path does not prove that its neurons fired or that an input
was sufficient to recruit the motor neuron. Presynaptic spike counts are source
events, not delivered events: synaptic delay, depression, and event withholding
can separate them from motor-neuron input. Static ranking is not a causal
contribution estimate. The existing measured `g_exc`/`g_inh` peaks remain the
evidence that synaptic state changed at the target.

Manual test: after initialization, confirm each channel includes `inputs(...)`.
Run for at least 10 simulated seconds, then Ctrl+C and save the final upstream
JSON and timing line. Compare RFTarsus1 and LFTarsus1: are the right-side
excitatory sources silent, and are positive sensory paths present? For active
inputs, inspect the representative source IDs and counts. Initialization adds
a read-only graph search; default v3 without the diagnostic flag is unchanged.

### States at intermediate and sensory pathway nodes

The optional probe now samples each distinct non-motor node on the selected
paths once per neural update. This reuses the motor state sampler; it does not
admit those nodes as motor outputs or alter their inputs. The final JSON adds:

- `pathway_nodes`: exact body IDs, dense indices and types, raw spike counts,
  incoming effective-edge inventory, input-source activity, excitatory/inhibitory
  state peaks, voltage extrema and sampled threshold gaps for sensory and
  intermediate nodes. Shared nodes appear once, even across multiple paths.
- For sensory nodes, `encoded_rate_samples`, latest `encoded_rate_hz`,
  `peak_encoded_rate_hz` and `encoded_positive_steps` describe the existing
  encoder's rates after its cutoff. Unavailable rates are null, distinct from
  observed zero rates. `external_candidate_steps` counts the brain's external
  candidate-event updates before withholding; `external_delivered_steps` counts
  its delivered external-event updates. These counters are separate from raw
  spikes, which can also arise from neural integration.
- `pathway_edges`: each selected directed edge's anatomical synapse count and
  summed static effective weight. This excludes dynamic depression and is not
  a measurement of delivered current.
- `pathway_identity_verified`: every additional path node's body ID round trip
  passed. The existing `readout_verified` flag compares motor observers with raw
  counts; path nodes are measured directly without installing motor observers.

The periodic line ends with `pathway_nodes=... silent_intermediates=...`.
For the recorded right-front routes, inspect nodes `902679` and `46348` and
edges from sensory neuron `815843` in the final report. Excitatory-state peaks
above zero with no spikes support subthreshold recruitment at that node. Zero
encoded rates explain why a selected sensory source has no external drive from
that encoder during the observed window. Positive encoded rates with no
delivered events require examining sampling and refractory behavior; they do
not alone prove a bug. These conclusions apply to the selected routes and
observed window, not every possible pathway or behavioral condition.

Manual run from Git Bash (avoids a `tee` pipeline losing shutdown output):

```sh
python -u -m malecns_backend.live --motor-interface v3 --upstream-diagnostics > v3-pathway-nodes.txt 2>&1
```

The terminal stays blank while output goes to the file. Allow roughly six wall
minutes, then Ctrl+C once and wait for the prompt. Confirm the final timing line
records at least 10 simulated seconds and that `LIVE final upstream={...}`
contains `pathway_nodes` and `pathway_edges`. Check Unity receiving during the
run and verify v3 without the optional flag still omits these diagnostics.

### Offline proprioceptive coverage and recruitment assay

Run from the repository root after installing the normal Python backend dependencies.
This assay does not require Unity, FlyGym, or MuJoCo. It does not change the live launcher.

Fast encoder-only coverage (no full CNS load):

```bash
python -m malecns_backend.live.sensory_coverage --output v3-sensory-coverage.json
```

Expected: six legs, 392 sensory neurons, each with a positive peak rate somewhere
on the 101-point grid through its audited joint range. Preferred angles reflect
frozen population-list order, **not measured individual biological tuning**.
The sampled grid is a coverage calculation, not a simulated physical movement.

Matched open-loop neural comparison:

```bash
python -u -m malecns_backend.live.sensory_coverage --neural --duration-s 10 --output v3-sensory-recruitment.json
```

Allow initialization and all three conditions to finish; no Ctrl+C is needed.
Each condition resets the CNS and per-leg sensory RNGs to seed 1, uses the
unchanged default neural configuration and the live two-stage sensory event
pathway, and runs for 10 **simulated** seconds. The three conditions are:
fixed range midpoint, slow full-range sweep up, and slow full-range sweep down.
All six legs follow the same normalized schedule. The midpoint is an engineered
control, not a replay of the measured resting posture. This is a prescribed
sensory-input intervention; physics and motor commands are absent.

Manual review: compare `neural_conditions[*].sensory` delivered events and spikes,
then compare per-neuron `candidate_motors` spikes across the same-duration
conditions. Zero motor spikes are a valid result, not a test failure. Increased
recruitment demonstrates responsiveness under this stimulus only; it does not
establish balance, walking, a unique cause, or a remedy for the live posture.
One seed is exploratory evidence; do not infer reliable effects from a small
count difference. Share the JSON after completion. Full CNS execution can be slow.

To trace recruitment through selected sensory-to-motor pathways in those same
three conditions, enable the existing upstream probe in the offline assay:

```bash
python -u -m malecns_backend.live.sensory_coverage --neural --pathway-diagnostics --duration-s 10 --output v3-recruitment-pathways.json
```

`--pathway-diagnostics` requires `--neural`. This is optional and adds per-step
measurement overhead. Allow all three conditions to finish; no Unity or Ctrl+C
is needed. Each condition creates fresh observers and a fresh probe after the
seed reset, preventing measurements from accumulating across conditions.

Manual checks for each `neural_conditions[*].pathway_diagnostics`:

- `samples` equals `neural_steps`; all three identity/readout verification flags
  are true. Candidate motor spike counts agree with `candidate_motors`.
- `channels.joint_RFTarsus1` identifies the selected positive sensory path and
  ordered `sensory_path_spikes` for each motor. Look up intermediate body IDs in
  `pathway_nodes` to compare spikes, voltage gap, excitation/inhibition peaks,
  and active presynaptic sources between conditions.
- Sensory path nodes contain encoded-rate peaks, rate-sample counts, and actual
  delivered-event counts. Compare these with the per-condition `sensory` rows.
- Silent intermediates with excitation and a remaining threshold gap indicate
  subthreshold activity in that condition. A zero-excitation node suggests
  inspecting its presynaptic activity. Neither observation establishes a unique
  causal bottleneck or justifies changing thresholds or weights.

The report reuses the live probe: selected shortest positive paths are structural
examples, not exhaustive or proven causal routes. Inhibitory/disinhibitory routes
may also matter. Voltage is sampled after spike reset and conductance decay, so
its maximum is not a pre-spike peak. The two other candidate channels remain in
the report for comparison. Share `v3-recruitment-pathways.json` after completion.
