# M5D-5C — Post-feedback motor pathway audit

## Status

**COMPLETE — `MIXED_OR_UNRESOLVED` (diagnostic audit only).** M5D-5C read the
authoritative M5D-5B artifact without rerunning either scientific condition.
It changed no neural, sensory, decoder, physics, duration, drive/noise, or
behavior parameter. M5D-5B remains `CLOSED_LOOP_TO_CNS_CONFIRMED`.

The diagnostic cannot localize the absence of C13. The artifact persists
aggregate downstream counts, milestones, and per-leg physical/rate series,
but does not persist the paired per-neuron identities/state trajectories,
mapped-motor state trajectories, decoder observer/filter trajectories, or
tactile trajectories needed by the requested pathway analyses. Missing
measurements are reported as `INSUFFICIENT_TELEMETRY`; none are reconstructed.

## Immutable evidence and provenance

`interface_output/proprioceptive_closed_loop_100ms.json` is locked using its
raw-byte SHA-256. The M5D-5B reducer, audit entry point, and Windows adapter are
locked using canonical-LF SHA-256. Semantic validation additionally requires:

* schema `M5D-5B.0`, status `COMPLETE`, classification
  `CLOSED_LOOP_TO_CNS_CONFIRMED`;
* verified provenance, aligned RNG streams, and stable physics;
* exactly 392 directly driven proprioceptive neurons; and
* non-null C6 physical, C7 tibia-source, C8 modeled rate, C9 candidate, C10
  delivered, C11 downstream state, and C12 downstream spike milestones.

Any mismatch fails closed. The authoritative artifact is never written by the
audit. `.gitattributes` prevents Git from transforming its bytes.

## Observed post-feedback evidence

After C10 at 22.0 ms, the authoritative aggregate records 14,212 downstream
non-proprioceptive state-divergent neurons (first at C11, 24.0 ms), 1,274
downstream non-proprioceptive spike-divergent neurons (first at C12, 26.0 ms),
and 4,564 aggregate differing downstream spike events. The 392 directly driven
proprioceptive neurons were excluded, as were directly driven tactile neurons
where applicable. No subsequent mapped-motor population divergence was
observed through the recorded 100-ms window.

The artifact does **not** retain body IDs, annotations, or per-neuron spike
differences for that responsive population. Consequently, it cannot supply
valid source vertices for a connectome traversal. Although the repository's
MaleCNS graph and the existing 12 mapped tibia extensor/flexor populations (49
neurons total) are available, traversing from guessed source neurons would
fabricate evidence. Anatomical reachability, direct weights, strongest sources,
two-hop intermediaries, and depth layers 1–5 therefore remain
`INSUFFICIENT_TELEMETRY`.

## Dynamic and mapped-motor diagnosis

The persisted result establishes no C13 mapped-motor divergence and lists no
affected mapped-motor population after feedback. It does not persist paired
membrane states, mapped motor spikes by update, observer states, filter states,
activations, or raw decoded contributions. M5D-5C therefore cannot distinguish
no dynamic propagation, a premotor stop, mapped-motor subthreshold divergence,
an uncaptured mapped-motor spike divergence, or decoder-filter suppression.
The evidence-driven outcome is `MIXED_OR_UNRESOLVED`, not one of those narrower
diagnoses.

C1 is null while C2 is 13.5 ms. Because the needed originating population,
spike-at-update, activation, antagonist, and immediately preceding/current
filter telemetry are absent, the result is `C1_TELEMETRY_INSUFFICIENT`.

## Tactile attribution

M5D-5B states that LM Tarsus5 tactile transduction remained active and
unchanged, but it persists no paired tactile physical-source, rate, candidate,
or delivered-spike series. Their timing cannot be compared with C7–C12.
Sensory attribution is therefore `INSUFFICIENT_TELEMETRY`; this audit does not
claim that proprioception uniquely caused downstream CNS divergence.

## Scientific language boundary

**CONNECTOME-DERIVED** refers only to MaleCNS anatomical connectivity and
simulated neural dynamics. **MODELED** refers to proprioceptive/tactile
transduction, motor decoding, and physical embodiment. **OBSERVED** refers only
to condition-dependent differences recorded in authoritative M5D-5B.
An anatomical path is not evidence of functional recruitment.

This audit makes no claim of natural walking, biological proprioception,
biological reflexes, emergent gait, CPG discovery, natural coordination, or
biological muscle control.

## Offline execution

```bash
python -m malecns_backend.embodiment.post_feedback_motor_pathway_audit_audit
```

This command validates and reduces existing evidence only; it has no live-run
option and never imports or invokes the M5D-5B experimental adapter.
