# Milestone 4C-1: six-tibia pathway dissection

## Scope

This is a passive, observational rerun of the unchanged canonical M4B-2
CLOSED/MOTOR-OUTPUT-DISABLED pair (500 ms, neural step 0.5 ms, physics step
0.1 ms, control interval 1 ms, seed 7). It performs no ablation, stimulation,
tuning, or pathway intervention. Anatomical reachability, observed activity,
and temporal compatibility are reported separately and are **not** claims of
causation. Detailed isolated pathway diagnostics are unavailable; only the
committed M4B-1 aggregate comparisons are included.

## Architecture and fidelity

`PathwayObserver` is attached through an optional observer fan-out in the
existing simultaneous runtime. The default runtime path is unchanged. The
observer has no RNG and only reads/copies runtime arrays. Immediately before
delivery it applies the runtime's exact presynaptic sign, PSP scale,
depression resource, effective edge weight, and CSR orientation to account
for targeted delivered conductance increments. Immediately after a step it
copies voltage, threshold, refractory, adaptation, and conductance state for
audited mapped motor neurons. Because threshold-spiking voltage is reset
inside `MaleCNSBrain.step` before the callback, pre-spike voltage is explicitly
reported as unavailable rather than reconstructed.

Direct contributors require both a real presynaptic-row-to-postsynaptic-target
CSR edge and an observed presynaptic spike. Forward sparse BFS reports directed
anatomical distance separately from distance through observed-active neurons.
Shared reachability is labeled candidate convergence only.

The audit fails baseline reproduction unless all six sensory totals, mapped
motor totals, first motor times, peak offsets, and active/silent identities
match the canonical values. Major causal timestamps are retained for review.

## Memory and performance

There is no dense neuron-by-neuron adjacency matrix and no time-by-edge event
tensor. Incoming edges are retained only for selected mapped motor neurons;
time series are retained only for those neurons; active-neuron metadata is
sparse. Graph traversal uses one 32-bit distance vector per sensory
population. Wall time and process peak RSS are included in the JSON (RSS units
are platform-defined by Python's `resource` module).

## Run

From the repository root in the existing artifact/FlyGym environment:

```bash
python -m malecns_backend.embodiment.six_tibia_pathway_audit \
  --json malecns_backend/embodiment/pathway_output/six_tibia_pathway.json
```

The console is intentionally compact. The JSON contains baseline checks, a
per-leg active/silent comparison, exact population details, per-neuron
trajectories and threshold margins, modeled E/I/net delivery accounting,
ranked active direct contributors, directed anatomical/observed-active graph
distances, candidate convergence, provenance, and performance metadata.
