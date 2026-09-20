# M6C-D canonical-result audit and evidence-lock record

## Audit disposition: blocked on absent raw evidence

The canonical path
`malecns_backend/embodiment/interface_output/integrated_whole_leg_readiness.json`
was absent from this checkout before any change was made. It is intentionally
ignored by Git because the canonical telemetry is approximately 184 MB. The
only surviving checkpoint says three conditions completed but remains
`IN_PROGRESS`; it is not a substitute for raw telemetry. Therefore this audit
does **not** invent a byte count, SHA256, channel values, provenance copied from
the result, or an observation-level conclusion. The handoff's classification,
milestones, and indices are recorded below as *reported, not independently
verified*. The raw artifact was not rewritten, normalized, regenerated, or run.

The tracked lock placeholder has status `EVIDENCE_NOT_MATERIALIZED`. Once the
unchanged external file is restored at its canonical path, run the read-only
streaming locker exactly once:

```powershell
.\fly-brain-interactive\.venv\Scripts\python.exe -m malecns_backend.embodiment.m6c_result_lock
```

It validates the identity fields and three ordered conditions, records raw
SHA256, exact bytes, schema, seed, duration, classification, status, execution
flag, M7 readiness, and M6A/M6B/Tier-A hashes, and exclusively creates (never
overwrites) the lock. Preserve the 184-MB JSON externally as immutable raw
evidence and retain the small lock in Git. Reviewed repository provenance is
M6A `722ee9b3b1d6a0fad2bf8ef0f02fc63f49277c5f44e3bccf27898e6c4ea673d9`,
M6B `02a4bbb7ec79ccf0967e9b8499c5a68d0ed8133a56688592ba13cfb2785285a2`, and
Tier-A `18aaafd51360e0a60b56f98c0b93e156e4cba2a27efd653111b04a5b8c329271`.
These are repository-file hashes, not a claim that the absent result embeds
them. Failed engineering Attempt 1 remains separately preserved in
`interface_output/m6c_attempt_1_state_access_abort.json`; its status must never
be merged with the canonical result.

## What can and cannot be audited

Static code verifies the frozen plan: seed 1; duration 500 ms; physics dt
0.1 ms; neural dt 0.5 ms; three ordered fresh condition calls; eleven motor
admissions; six sensory admissions; and 31 baseline-only actuators. The live
loop uses `range(final_step + 1)`, records states at indices 0 through 5,000,
performs at most 5,000 physics transitions, and updates neural state at each
positive multiple of five (1,000 updates). It checks qpos/qvel/ctrl finiteness,
asserts the 42-element neural-contribution vector, supplies zero adhesion, and
contains no gait/reference/reward/RL controller. It does include the frozen
pre-existing tactile contact encoder and six tibial encoders as candidate
external neural drive; this must not be described as “no drive.”

Only the missing condition telemetry can establish actual completion counts,
exact snapshots/equivalence, stability throughout, authorization counts,
step/update counts, per-channel behavior, physical states, sensory quantities,
and CNS quantities. Consequently the requested 11-row numeric channel table
cannot responsibly be produced here. In particular, the reported **10/11**
result and `joint_RFTibia` silence are not verified from available bytes and
must not be retuned or called experimental failure.

## C0–C12: preregistered meaning and exact implemented predicate

“Required for primary” below means required for the reported multi-leg primary
classification path; M7 readiness independently requires C0–C5, C8, and C9.

| ID | Frozen definition / exact predicate | Reported result | Primary | M7 | Interpretation |
|---|---|---:|---:|---:|---|
| C0 | snapshots equal, first trajectory rows equal for qpos/qvel/action/ctrl/CNS digest/spike count, and both controls report pre-intervention equivalence | true | yes | yes | matched starts |
| C1 | any admitted channel's accumulated mapped spike increments is nonzero | true | yes | yes | mapped motor activity exists |
| C2 | any admitted channel's peak absolute raw decoder value is nonzero | true | yes | yes | decoder output exists |
| C3 | at least one channel has peak admitted contribution greater than zero | true | yes | yes | a neural contribution crossed admission |
| C4 | an A-vs-B trajectory row differs in action or ctrl, overridden when the enabled result supplies its first-command index | true, reported index 130 | yes | yes | command divergence from all-motor-disabled control |
| C5 | an A-vs-B row differs in qpos or qvel, likewise overridable by the enabled result | true, reported index 131 | yes | yes | physical divergence from control |
| C6 | at least two admitted channels have peak admitted contribution greater than zero | true | yes | no | multi-channel admitted output |
| C7 | active admitted channels span at least two leg labels | true | yes for multi-leg claim | no | multi-leg admitted output |
| C8 | every condition reports unauthorized-contribution count zero | true | yes | yes | authorization boundary held |
| C9 | every condition reports physics-instability false | true | yes | yes | recorded finite-state check held |
| C10 | `enabled.feedback_milestones["C10"] is not None` | false | no | no | intended validated sensory divergence observation |
| C11 | `enabled.feedback_milestones["C11"] is not None` | false | no | no | intended later CNS divergence observation |
| C12 | `enabled.feedback_milestones["C12"] is not None` | false | no | no | intended subsequent motor-return observation |

There are no C0–C9 timestamps stored in the milestone booleans themselves;
evidence indices live in comparison fields and channel summaries. Critically,
the canonical live condition unconditionally returns
`feedback_milestones: {}`. Thus **C10, C11, and C12 are false because their exact
predicate reads absent keys from an always-empty dictionary**, not because the
reducer proved absence of later sensory divergence, CNS divergence, decoder
divergence, physical re-divergence, mapped motor-state divergence, or mapped
motor-spike divergence. Separately, the top-level reducer scans trajectories
for sensory/delivered-drive and CNS-digest/aggregate-spike differences, but
does not feed those indices into C10–C12. This is a result-reduction/metadata
normalization defect, not a scientific protocol failure, and the preregistered
definitions and booleans must not be changed retrospectively.

## Reported A-vs-C sequence and limits of attribution

At physics dt 0.1 ms, the handoff's reported indices convert to:

| Aggregate | Index | time |
|---|---:|---:|
| Tier-B command divergence | 170 | 17.0 ms |
| femur physical divergence | 171 | 17.1 ms |
| “full-body” physical divergence | 171 | 17.1 ms |
| validated sensory-or-delivered-drive divergence | 175 | 17.5 ms |
| CNS-digest-or-aggregate-spike divergence | 325 | 32.5 ms |

For context, reported A-vs-B indices 130 and 131 are 13.0 and 13.1 ms.
These conversions assume trajectory index and recorded physics time agree;
the missing telemetry must verify its `time_ms` values.

The aggregates cannot answer the requested attribution. `command_c` compares
the entire action and ctrl arrays. The code assigns both femur and full-body
fields from the same broad qpos/qvel first-difference value; it does not prove
which femur or physical component differed. The sensory scan combines the
six-stream `sensory` mapping and `delivered_sensory_drive`, so the top-level
index alone cannot say which tibia/rate differed or whether delivered drive
diverged. The CNS scan combines the whole-state digest and aggregate spike
count, so it cannot identify a state quantity. No reducer checks subsequent
mapped motor state or mapped motor spikes. Those questions require the missing
rows; any more specific answer would be fabrication.

The weakest defensible wording from the reported aggregates is: *the enabled
and Tier-B-disabled recorded trajectories were reported to first differ in a
motor-command aggregate at 17.0 ms, a qpos/qvel aggregate at 17.1 ms, a
sensory-or-delivery aggregate at 17.5 ms, and a CNS-digest-or-spike aggregate at
32.5 ms.* This is not evidence of a natural reflex or biological gait
coordination.

## Stale and misleading metadata

`build_not_run_artifact` creates the limitation “Scientific M6C has not run.”
After science, `run_canonical` shallow-copies that NOT_RUN object and updates
status, execution, reductions, and readiness but never replaces `limitations`.
That explains the contradiction. The same inherited limitations about scope
and absent femur proprioception remain accurate. The completed report also
retains preregistration-shaped condition entries rather than replacing them
with completion summaries, and the checkpoint remains `IN_PROGRESS` after
the final result because no final checkpoint write occurs. Most importantly,
C10–C12 conflict in meaning with independently populated top-level divergence
indices for the reason above. These are metadata/result-normalization defects;
none justifies editing the raw evidence.

## Conditional final scientific claim

If and only if the raw lock and telemetry audit confirm the handoff, the
strongest defensible claim is:

> Under the preregistered modeled embodiment, simultaneously admitted,
> annotation-backed or previously validated MaleCNS motor interfaces produced
> causal multi-leg physical effects relative to matched neural-motor-disabled
> controls. In the Tier-B-femur-disabled comparison, a Tier-B-sensitive command
> aggregate preceded qpos/qvel divergence, followed by divergence in a
> validated modeled tibial-sensory-or-delivered-drive aggregate and later a
> MaleCNS-state-digest-or-aggregate-spike measure.

M6C does **not** establish natural walking, gait, biological muscle force,
biological function of individual neurons, natural reflexes, natural inter-leg
coordination, fully biological sensory transduction, or complete fly
embodiment. Until the raw evidence is materialized, even the conditional claim
is not promoted here to a verified result.

## Execution confirmations

* M6C RERUN: **NO**
* M6C RAW RESULT MODIFIED: **NO** (it was absent)
* M6C SCIENTIFIC PROTOCOL RETROACTIVELY CHANGED: **NO**
* M7 SCIENTIFIC RUN EXECUTED: **NO**
* M7 GAIT CONTROLLER ADDED: **NO**
* M7 REFERENCE TRAJECTORY ADDED: **NO**
* M7 AI/RL/REWARD CONTROLLER ADDED: **NO**
* M7 NEW SENSORY CHANNEL ADDED: **NO**
* M7 NEW MOTOR CHANNEL ADDED: **NO**
* M7 PARAMETER TUNING AFTER M6C: **NO**
