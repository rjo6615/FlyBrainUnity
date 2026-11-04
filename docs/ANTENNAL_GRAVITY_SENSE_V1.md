# Antennal gravity sense (Johnston's organ zones C and E): track design (V1)

Designed 2026-11-04. The user chose "richer senses" after the coxa track reached its ceiling
(`COXA_REMAINING_COORDINATES_AUDIT.md`, PR #321). This is the design only. No code exists,
nothing has run, no encoder exists, and no coordinate status changes. **Step A** is
specified in full here, and its protocol will be hash-locked before it runs. **Steps B
and C** are outlined only. Each will get its own design and preregistration later.

## Why this sense

The body tilts. In the assisted posture with the conditional coxa channels, mean tilt is
9–10°, against about 4° without them (`COXA_PUSH_REPLICATION_RESULTS.md`). But the CNS
receives no signal about orientation relative to gravity. The only senses encoded today are:
- tibia angle (chordotonal);
- the coxa forward limit (hair plates);
- claw contact (tactile).

Balance cannot emerge from neural activity if nothing tells the CNS which way is down.

The posture-sense inventory (`POSTURE_SENSE_INVENTORY_RESULTS.md`) compared the candidates.

| Organ | Exact local identities | Encoded | Notes |
|---|---|---|---|
| Johnston's organ, wind/gravity | 475 (subclass `wind_gravity`, all matched in the simulated connectome) | no | 178 reach leg motor neurons in 2 hops |
| Haltere | 205 | no | A gyroscope needs haltere oscillation, which the body does not model |
| Leg campaniform sensilla | 2 per leg | no | Too sparse; the load signal is a proxy (M5D-1) |
| Neck | 2 | no | No reach |

Of these, Johnston's organ has the most exact identities. It has no oscillation requirement,
and the signal it needs (head orientation relative to gravity) is fully determined by body
state that the simulation already records.

## Biology this rests on (published work as recalled; nothing downloaded)

The following are **reference claims from the literature, cited from memory**. They are
used as hypotheses to test, not as validated facts about this model.
- Johnston's organ (JO) in the antennal second segment senses rotation of the third segment
  (funiculus) relative to the second (pedicel).
- Zones A/B respond to vibration (sound). Zones C/E respond to sustained deflection (gravity,
  wind). Silencing C/E impairs gravity-dependent behaviour (Kamikouchi et al. 2009,
  *Nature*). Wind direction is also encoded (Yorozu et al. 2009, *Nature*).
- **C and E respond to opposite directions of deflection.** Which zone prefers which
  direction is **held as a hypothesis**, G1, and tested against its flip, G1_FLIP. The design
  does not rely on recall for that sign.
- C and E terminate in distinct zones of the antennal mechanosensory and motor centre
  (AMMC).

## Local facts (inspected for this design)

These come from `docs/evidence/lf-anatomical-crosswalk-v1/annotations.feather` (MaleCNS
v1.0), filtered on subclass `wind_gravity`, entry nerve AN, and zone taken from `type`.

| Zone | Left | Right |
|---|---|---|
| C (CL, CM, CA1, CA2) | 31 | 22 |
| E (EV1–6, ED1, ED2) | 157 | 110 |
| B, D, F, A (other) | 34 | 23 |
| `JO-unclear` | 6 | 92 |

- **Typing is asymmetric.** 92 of the 98 untyped neurons are on the right. Typed C+E is
  188 left vs 132 right. A naive encoder would therefore give the CNS a built-in left/right
  bias, which is a reconstruction or annotation artefact rather than biology. Step A
  measures how large it is, and Step B must declare how to handle it before any live run.
- **Status label.** Every one of the 475 neurons carries `statusLabel = "RT Hard to trace"`.
  This is recorded as a limit on identity completeness.
- **Body model.** The FlyGym MJCF has Head, Pedicel, Funiculus and Arista bodies, with hinge
  joints (`joint_<L/R>Funiculus` and its roll/yaw variants) at zero stiffness. A passive
  physical antenna would have no restoring spring and no defensible mechanics, so the
  transduction will be kinematic: gravity expressed in the head and antenna frame, computed
  from recorded body state. It will not be simulated antenna motion.

## Step A: identity and wiring (data only; specified now)

**Question.** In the simulated connectome, are the JO-C and JO-E neurons present with exact
identities on both sides, and does their wiring match the published structure?

**Populations.** Exact `bodyId` sets, by zone and side:
- C = types starting `JO-C`; E = types starting `JO-E`;
- side from `rootSide`;
- `JO-unclear` and the A/B/D/F types are excluded from the encoder sets by this rule. They
  are reported.

**Graph.** This reuses the posture-sense inventory's graph: the simulated CSR with
presynaptic rows and edges of at least 6 synapses (the engine's `min_synapses` floor). It
reuses that inventory's code and source fingerprints, and adds no new loader.

**Checks (all required for `IDENTITY_READY`):**
- **A1 Identity.** Every C and E body ID maps to exactly one dense index in the simulated
  connectome.
- **A2 Bilateral.** Both zones are present on both sides, with at least 10 neurons in each of
  the four sets.
- **A3 Zone segregation (published AMMC structure).** For each side, compare the C and E
  sets' direct postsynaptic targets (edges ≥ 6). The synapse-weighted overlap,
  Σ min(w_C, w_E) / Σ max(w_C, w_E) over targets, must be below 0.5.
- **A4 Downstream reach.** On each side, at least one C neuron and at least one E neuron
  reach a `descending_neuron` within 2 hops.

**Reported, not gated:**
- the 2-hop reach to leg motor-neuron pools, by leg;
- the named descending neurons reached (exact IDs and types);
- the C/E left–right count ratio, and the same ratio over each set's total output synapses;
- the direct-target overlap between `JO-unclear` (right) and the typed right C and E sets,
  as a descriptive hint at what the untyped neurons might be (it is never used to assign
  them).

**Verdict.**
- `IDENTITY_READY` if A1–A4 all pass.
- `IDENTITY_PARTIAL` if A1 and A2 pass but A3 or A4 fails. Step B would then need a
  documented decision.
- `NOT_READY` otherwise.

Step A shows only structural consistency. It does not show function.

## Step B: static encoder (outline; its own design and preregistration later)

Step B would mirror the hair-plate Step B. It would be geometry-only, with no CNS.
- **Signal.** For each antenna, the gravity unit vector expressed in the funiculus frame,
  projected onto the funiculus rotation tangent. The rotation axis would come from the MJCF
  `joint_<side>Funiculus` axis, and the lever from the funiculus-to-arista offset. This
  turns head orientation into a signed deflection drive d ∈ [−1, 1].
- **Tuning.** Tonic and one-sided per zone, with the full gravity component reaching the
  existing encoders' 120 Hz engineering maximum. G1 assigns +d to one zone and −d to the
  other; G1_FLIP swaps them.
- **To be declared before inspecting results:**
  - how the left/right typing asymmetry is handled. Options are to use the sets as typed (a
    declared bias), or to report per-neuron rates without normalising;
  - whether the head is fixed to the thorax in the runtime.
- **Descriptive output.** The rest-pose rates, and the rate change per degree of pitch and
  roll on each side. If roll does not change the left and right signals differently, the
  sense cannot report roll, and the design says so.

## Step C: live on/off (outline)

Step C would be a matched comparison in the existing assisted-posture context:
- arms: JO_OFF / JO_G1 / JO_G1_FLIP, across new seeds;
- a preregistered question about whether head-orientation information reaches leg motor
  neurons (for example, whether MN activity depends on imposed tilt sign).

It would not be a balance claim, and it would admit no coordinate.

## What this track can and cannot do

- **Can:** add a gravity-referenced sense with exact identities, and test whether its
  information reaches motor output. That is a prerequisite for emergent balance.
- **Cannot:** add motor coordinates. It also cannot show balance by itself, or validate the
  sign without the G1_FLIP contrast.
- **Kinematic transduction.** The transduction is a modeled, kinematic stimulus. Real
  antennal mechanics, and therefore the actual magnitude of gravity-driven deflection, are
  not modeled. The 120 Hz scale is an engineering choice.

## Step A build and run plan (on approval)

1. Write `docs/evidence/antennal-gravity-identity-v1/protocol.json`. It holds the
   population rule, the graph, the A1–A4 thresholds and the reported items, and it is
   hash-locked in code.
2. Write `malecns_backend/embodiment/antennal_gravity_identity.py`, reusing
   `posture_sense_inventory` (loading, adjacency and reach). Write
   `tests/test_antennal_gravity_identity.py` with synthetic graphs covering every check
   boundary.
3. Commit, run once (seconds, data only) and evaluate once. Record the results, the handoff
   and the roadmap.
