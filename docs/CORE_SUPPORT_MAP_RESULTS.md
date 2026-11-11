# Engine fidelity Step F2 (core support map): results

Run 2026-11-10, once, from the preregistered commit e0a04ff (protocol
`docs/evidence/core-support-map-v1/protocol.json`, sha 60359bb6…, no amendments). 136 simulations of
3 s, 1,121 s, run and evaluated once in the same process. Output: `run/result.json` and
`run/console.txt`. Design: `CORE_SUPPORT_MAP_V1.md`, including its build-time notes.

This was a **neural-only simulation** (no body or physics) in the live, calibrated whole-CNS LIF
engine. Lesions existed only in model copies. The live engine was not changed.

## Verdict: `NEEDED_NOT_SUFFICIENT`

DNg100_L's core engagement needs **three** groups outside the front-left network: the **central
brain**, the **rest of the nerve cord (VNC)** and the **ascending neurons (AN)**. Removing any one of
them abolishes it. No group is enough by itself, when added alone to the network.

| Expectation | Outcome |
|---|---|
| X1 (VNC is needed) | **held** |
| X2 (`LOCALISED` to VNC) | **wrong**: VNC is needed but not enough alone; BRAIN and AN are needed too |
| X3 (the SENSORY sham holds) | **held**: MINUS_SENSORY equals LIVE exactly; ONLY_SENSORY equals ISOLATED exactly; no sensory neuron fired |

## Integrity

| Check | Result |
|---|---|
| Z1 sources, cache, network membership, group sizes, identities | pass |
| Z2 LIVE = F1 S0 exactly; LIVE_VIA_WEIGHTS = LIVE exactly; ISOLATED = F1 S1 exactly (8 seeds each) | pass |
| Z3 lesion audits (kept edges equal LIVE, removed edges zero, signs and configuration unchanged) | pass, all 17 |
| Z4 136 simulations of 3 s | pass |

## All conditions

Medians over seeds 1–8. Rates are over 250–3,000 ms. "Engaged seeds" means E1 and E2 were both at
10 Hz or more in the same seed. Active neurons are counted over the whole 3 s run.

| Condition | Engaged seeds | E1 / E2 / I1 (Hz) | Active MNs | Active: network / BRAIN / VNC / AN / DN / OPTIC |
|---|---|---|---|---|
| LIVE | 8 | 26.2 / 40.9 / 7.5 | 12 | 365 / 996 / 2,206 / 123 / 23 / 22 |
| ISOLATED | 0 | 0 / 0 / 0 | 0 | 8 / – / – / – / – / – |
| MINUS_OPTIC | 8 | 26.7 / 38.9 / 4.9 | 12 | 382 / 1,006 / 2,266 / 129 / 25 / 20 |
| **MINUS_BRAIN** | **0** | 0 / 0 / 0 | 1 | 45 / 107 / 760 / 34 / 1 / 1 |
| **MINUS_VNC** | **0** | 0 / 0 / 0 | 0 | 42 / 137 / 106 / 5 / 7 / 8 |
| **MINUS_AN** | **0** | 0 / 0 / 0 | 0 | 54 / 135 / 623 / 24 / 7 / 5 |
| MINUS_DN | 8 | 26.0 / 38.0 / 6.5 | 12 | 389 / 1,439 / 2,211 / 121 / 24 / 22 |
| MINUS_SENSORY | 8 | identical to LIVE | 12 | identical to LIVE |
| MINUS_OTHER | 8 | identical to LIVE | 12 | identical to LIVE |
| ONLY_OPTIC | 0 | 0 / 0 / 0 | 0 | 8 / – / – / – / – / 1 |
| ONLY_BRAIN | 0 | 0 / 0 / 0 | 0 | 46 / 144 / – / – / – / – |
| ONLY_VNC | 0 | 0 / 0 / 0 | 0 | 19 / – / 622 / – / – / – |
| ONLY_AN | 0 | 0 / 0 / 0 | 0 | 8 / – / – / 1 / – / – |
| ONLY_DN | 0 | 0 / 0 / 0 | 0 | 8 / – / – / – / 1 / – |
| ONLY_SENSORY | 0 | identical to ISOLATED | 0 | identical to ISOLATED |
| ONLY_OTHER | 0 | 0 / 0 / 0 | 0 | 8 / – / – / – / – / – |

Every condition is all-or-none: 8 of 8 seeds engaged, or 0 of 8.

**Reported, not gated:**
- **Where LIVE's activity is.** About 3,700–4,400 neurons fire per seed. Medians: 2,206 in the rest of the cord, 996 in the
  central brain, 365 in the network, 123 ascending, 23 outside descending and 22 optic.
- **No non-monotonic pairs.** No group was enough alone, so none could be enough while another was
  needed.
- **OTHER was silent in LIVE**, so MINUS_OTHER behaves as a second sham. It also equals LIVE exactly.
- **MINUS_DN**, which removes the 414 descending neurons outside the network, leaves the engagement
  intact and raises central-brain activity (median 1,439 active, against 996).

## Reading (a hypothesis, not a result)

- **The engagement looks like a cord–brain–cord loop.** It needs the rest of the cord, the ascending
  neurons and the central brain together. None of them can carry it alone. The descending neurons
  outside the network are not needed. But R1's network already contains the descending neurons that
  synapse onto front-left premotor neurons (924 before R1's unknown-transmitter filter), so a return path from the brain to the cord
  remains inside the network.
- **One reading** is that DNg100_L's drive recruits cord neurons. Ascending neurons then carry that
  activity to the central brain, and descending neurons return it to the cord. With the calibrated
  weakening of inhibition, the loop settles into an active state in which E1 and E2 fire. F2 did not
  test the loop as a whole, or which neurons in each group carry it.
- **What this means for interpreting the live engine.** Core activity in the live engine is not a
  local leg circuit responding to a command. It is a large recurrent CNS state, all-or-none across
  seeds, and it depends on inhibition being weakened. Its output stays tonic. The balance track's
  closed-loop motor responses may involve such states too; F2 did not test that.

## Declared consequence

`NEEDED_NOT_SUFFICIENT`: the support is a combination. The natural next question is whether the three
needed groups together (network + BRAIN + VNC + AN) are enough, and which neurons in each carry the
loop. That would be a separate design. The spiking-versus-graded desk review stays open, and cannot be
done with local data only.

**In no case** does F2 show rhythm, balance, walking or a biological role, or justify an engine
change. The lesions are probes.

## Limits

- One DN (DNg100_L), one rate (100 Hz), the front-left network and 8 seeds.
- The groups are coarse superclass partitions. "Not needed" does not mean "no effect" (MINUS_DN
  changed brain activity).
- The combination of the three needed groups was not tested.
- The only lesion type is transmission removal.
- The 10 Hz bar is declared, not derived. Every condition was all-or-none, so the bar did not
  decide any label.
- Motor coordinates are unchanged (20/42 admitted, +4 conditional).

## Evidence

- `docs/evidence/core-support-map-v1/protocol.json` (sha 60359bb6…).
- `docs/evidence/core-support-map-v1/run/result.json` and `run/console.txt` (committed).
