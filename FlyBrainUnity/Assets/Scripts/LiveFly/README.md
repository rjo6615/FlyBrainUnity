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
