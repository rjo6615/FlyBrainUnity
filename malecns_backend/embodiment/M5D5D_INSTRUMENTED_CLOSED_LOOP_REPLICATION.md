# M5D-5D — instrumented closed-loop replication

## Status

**FAILED BEFORE SIMULATION.** The checked-in artifact preserves the first
Windows invocation's provenance failure as historical evidence. It is not
scientific evidence, did not enter simulation, and did not consume Scientific
Run #1. The first successful canonical Windows execution remains Scientific
Run #1.

## Frozen protocol and provenance

The protocol remains seed 1, 100 ms, 0.1-ms physics, 0.5-ms MaleCNS updates,
and zero retries. Both `CLOSED_LOOP_ENABLED` and `MOTOR_OUTPUT_DISABLED` retain
six-tibia proprioception, LM Tarsus5 tactile input, the same MaleCNS,
environment, common-random-number construction, observers, decoder, baseline,
clamps, slew limit and 42-element action construction. The only intervention
continues to be admission of the raw decoded contribution versus zero.

`verify_provenance()` locks the raw authoritative M5D-5B Scientific Run #2 and
M5D-5C JSON artifacts and canonical-LF hashes of the M5D-5B runner, reducer,
audit and M5D-5C implementation. It also verifies `COMPLETE`, the authoritative
classifications, provenance, physics stability and RNG alignment semantics.
Historical artifacts are never rewritten.

The M5D-5C artifact was generated with CRLF on Windows. Its former lock was the
SHA-256 of the LF checkout representation (`dc6f2b5a…`), while Windows observed
the authoritative CRLF bytes (`7dd802b8…`). Canonical-LF normalization of both
representations is identical, and parsing both produces the same JSON value.
The artifact is therefore retained with its authoritative Windows bytes and a
raw-byte lock; `.gitattributes` prevents Git from rewriting it. Implementation
sources continue to use canonical-LF locks.

## Shared update path

M5D-5D does not implement a simulator or scientific step. It calls the locked
M5D-5B `_run_condition` for each condition. Only after each condition returns
does `_pack` read those observations. It neither calls RNG nor changes ordering,
brain state, decoder state, commands, physics, or timing. The M5D-5B reducer is
also reused to establish exact pre-intervention equality and the causal prefix.

## Lossless telemetry

The generated compressed NPZ sidecar contains body IDs and, for every 0.5-ms
update in both conditions, time, the full MaleCNS membrane-state vector and a
lossless per-neuron spike-event/count matrix. It also contains the complete
M5D-5B trace at every 0.1-ms physical sample: qpos, qvel, qacc, contact forces,
semantic contacts, tibia angles, full action and MuJoCo ctrl; baseline,
previous and final targets; mapped motor increments, cumulative observer input,
filtered observer state, decoder state, activations, antagonist/raw/admitted
signals; all proprioceptive angles/rates/candidates/deliveries/draw counters and
RNG state identities; and tactile source vector/rate/generated, pending and
delivered events plus RNG identities. Tactile magnitude is exactly derivable
from its retained source vector. No outcome-dependent neuron selection occurs.

The post-audit resolves dense indices to body IDs, excludes directly driven
proprioceptive and tactile sets, computes first paired state/spike divergence
and spike totals, and traverses CSR rows strictly presynaptic to postsynaptic at
depths 1–5 toward mapped tibia motor targets. Anatomical eligibility remains
separate from observed dynamic recruitment. C1 and C13 are only resolved when
recorded evidence supports them.

## Replication guard

Interpretation requires exact pre-intervention equality and the M5D-5B Run #2
ordering: contribution < action/control <= body <= tibia source <= modeled rate
<= delivered proprioceptive input < downstream CNS divergence. Exact historical
floating-point times and spike totals are not required.

## Canonical command

From the repository parent on Windows with the required NumPy/FlyGym/MuJoCo
stack:

```powershell
python -m malecns_backend.embodiment.instrumented_proprioceptive_closed_loop_audit --live --seed 1 --duration-ms 100
```

CONNECTOME-DERIVED refers to anatomy and simulated MaleCNS dynamics; MODELED to
transduction, motor decoding and embodiment; OBSERVED to paired simulation
differences. This phase makes no claim of natural walking, biological
proprioception or reflex, emergent gait/CPG, natural coordination, or biological
muscle control.
