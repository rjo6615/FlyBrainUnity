# M4C-3 LH→LM connectome pathway causal dissection

This milestone deliberately separates **Phase A observational selection** from
**Phase B engineered causal intervention**. The CLI never proceeds from
candidate discovery to interventions in one invocation.

## Phase A algorithm

The source is exactly the mapped LH chordotonal sensory population and the
targets are LM mapped tibia motor neurons `800911` and `801234`. Traversal uses
the validated CSR orientation: each row is presynaptic and each entry is a
postsynaptic dense index.

1. Run a fresh, seed-1, 500-ms ALL-SIX canonical condition and validate its
   recorded baseline.
2. Record sparse canonical spike times.
3. Perform directed forward BFS from all LH sensory indices to depth three.
4. For each target independently, perform reverse layer discovery to depth
   three without constructing a full transposed graph.
5. Retain non-source, non-target intermediates lying on a complete directed
   source-to-target route of at most three edges.
6. Mark a candidate `observed_active` only when its first canonical spike is
   before 35 ms. This is temporal compatibility, not causal evidence.
7. Deterministically prioritize observed-active candidates, then shorter
   complete routes, direct/dual LM contact, LH-side synapse convergence,
   absolute effective modeled weight, and body ID. At most six individuals are
   placed on the proposed Phase-B shortlist.

Candidate records separate connectome facts (annotations, paths and synapse
counts) from modeled facts (E/I sign, effective weight and canonical activity).
Type groups preserve explicit IDs and are eligible only at sizes 2–6. A group's
serialized `body_ids` are always sorted in ascending numeric body-ID order;
group membership is metadata and does not inherit candidate priority.

## Phase B semantics

Phase B accepts an inspected Phase-A JSON document. Every condition is a fresh
seed-1 ALL-SIX 500-ms run. A selected neuron remains in all arrays and retains
all inputs, state updates, threshold crossings, spike counts, graph edges,
weights, and thresholds. Its generated spike is recorded as counterfactual
activity but is omitted from the outgoing delay ring. No sensory stream is
removed. Sampling remains on the canonical common-random-number path.

Only `PhysicsError` is converted to a partial result; other exceptions
propagate. Bodies close in `finally`, and failed physics is neither retried nor
tuned.

The primary feedforward report is the separate inclusive 0–49 ms window. If a
condition physically diverges before 49 ms, the report flags the remainder of
that window as potentially feedback-contaminated. A separate full-run section
describes the 500-ms closed-loop result. Comparisons to the known −LH delta of
−18 spikes are descriptive and never represented as a mediation percentage.

## Windows commands

Run Phase A first and stop to inspect its candidate evidence:

```powershell
.\fly-brain-interactive\.venv\Scripts\python.exe -m malecns_backend.embodiment.lh_lm_pathway_audit --candidates --json malecns_backend\embodiment\pathway_output\lh_lm_pathway_dissection.json
```

Do **not** run Phase B until the Phase-A shortlist has been reviewed (and, if
desired, its `selected_body_ids` explicitly edited):

```powershell
.\fly-brain-interactive\.venv\Scripts\python.exe -m malecns_backend.embodiment.lh_lm_pathway_audit --interventions malecns_backend\embodiment\pathway_output\lh_lm_pathway_dissection.json --json malecns_backend\embodiment\pathway_output\lh_lm_pathway_interventions.json
```

No gait, CPG, descending controller, scientific constant, synaptic weight,
threshold, or physics parameter is introduced or changed by this milestone.
