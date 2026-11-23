# Published physiology Step P1 (front-leg motor network review): results

Reviewed 2026-11-23, once, from the preregistered commit b820615 (protocol
`docs/evidence/physiology-review-v1/protocol.json`, sha c28c524a…, no amendments). 21 declared queries,
one-level snowball, 26 extracted entries. Every entry got a second, separate read; the label was
computed once by `malecns_backend/evidence_review.py`. Outputs: `evidence.json`, `search_log.json` and
`result.json` in the same folder. Design: `PHYSIOLOGY_REVIEW_V1.md`.

This is a literature review. No simulation was run, and the live engine is unchanged.

## Verdict: `EVIDENCE_PARTIAL`

- **Model changes are supported:**
  - two graded-unit candidates (D1);
  - measured leg motor neuron parameters (D2).
- **No held-out validation target qualifies (D5 = 0).**

| Expectation | Outcome |
|---|---|
| X1 (no grade A physiology for E1, E2 or I1) | **held**: none found |
| X2 (grade A/B evidence that some nerve-cord interneuron class is graded) | **held**: 13Bα and 10Bα |
| X3 (leg motor neuron intrinsic or recruitment data exist) | **held**: Azevedo et al. 2020 |
| X4 (`EVIDENCE_PARTIAL`) | **held** |

**Integrity.** All entries valid, ids unique, every entry second-read, search log complete. 14 of 26
entries count toward decisions: primary, *D. melanogaster*, grade A or B, and confirmed by the second
read. 7 entries disagree under the strict rule (below). None of them would count anyway.

## What the evidence says

### Q1: spiking or graded (D1)

| Group in our network | Result | Evidence (in vivo whole-cell, adult) |
|---|---|---|
| Hemilineage **13B** (39 neurons in the network) | **CANDIDATE** for a graded unit | Agrawal et al. 2020: all recorded 13Bα cells lacked detectable action potentials |
| Hemilineage **10B** (11 neurons) | **CANDIDATE** (weaker) | Agrawal et al. 2020: no identifiable action potentials in 10Bα; occasional spike-like events in a subset |
| Hemilineage **9A** (31 neurons) | SPIKING | Agrawal et al. 2020: 9Aα and 9Aα2 spike |
| Leg motor neurons (class) | SPIKING | Azevedo et al. 2020: tibia flexor MNs spike |
| DNa02, DNg13 (types) | SPIKING | Yang et al. 2024: whole-cell in walking flies |

**Limit of D1.** The evidence is about one identified cell type in each hemilineage (13Bα, 10Bα), and
neither is linked to a connectome type. "Candidate" means at least one type in the hemilineage is
non-spiking. It does not mean all 39 or 11 of our neurons are. Which of our 13B and 10B neurons
correspond to 13Bα and 10Bα is not established.

**Context.** Published nerve-cord modelling already treats premotor neurons as non-spiking. Pugliese et
al. chose a rate model because many insect nerve-cord premotor neurons are nonspiking. Its citations for
that are cockroach, locust and stick-insect work, plus Agrawal 2020. So Agrawal 2020 is the only adult
*Drosophila* recording behind it.

### Q2: leg motor neurons (D2)

Azevedo et al. 2020, tibia flexor MNs, in vivo whole-cell; n = 15 fast, 11 intermediate, 14 slow:

| Measure | Fast | Intermediate | Slow | Engine (v1, inherited) |
|---|---|---|---|---|
| Resting potential | −68 mV | −60 mV | −48 mV | −52 mV for every neuron |
| Input resistance | 150 MΩ | 300 MΩ | 700 MΩ | not represented (weights scale with size instead) |
| Firing at rest | silent | silent | about 30 Hz | silent without drive |
| Recruitment | last | middle | first | — |

- **Point-neuron caveat.** In fast and intermediate MNs, somatic current injection did not reliably
  evoke spikes. The authors attribute this to the soma being electrically distant from the spike
  initiation zone. A point-neuron model cannot represent that.
- **D2 supports a class-level change for leg MNs**, but the data cover one motor pool (tibia flexor)
  of one leg. Extending them to all 68 front-left MNs would be an assumption and must be tagged as one.

### Q3: synaptic sign, kinetics, gap junctions (D3, D4)

- **No grade A or B evidence.** The engine's rule (glutamate inhibitory) stays `inherited`.
- **What exists is grade C, and it agrees with that rule:**
  - glutamate inhibits through GluClα in the brain (Liu & Wilson 2013);
  - in larval motor neurons (MacNamee et al. 2016);
  - in two pairs of adult nerve-cord sleep neurons, whose class is not stated, by calcium imaging
    (Fan et al. 2025).
- **No evoked synaptic kinetics from nerve-cord synapses were found.**
- **Gap junctions (D4).** Larval evidence only (Matsunaga et al. 2017), and no connectivity map. Out of
  reach.

### Q4: held-out validation targets (D5 = 0)

| Candidate | Why it does not qualify |
|---|---|
| MN firing at rest (Azevedo) | the in vivo resting state includes ongoing input the neural-only model does not reproduce |
| MN PSPs during passive tibia extension (Azevedo) | needs femoral chordotonal organ (FeCO) transduction, which the project has no validated encoder for |
| 13Bα / 9Aα / 10Bα responses to tibia movement (Agrawal) | needs FeCO transduction (and the second read found the 13Bα vibration data are imaging only) |
| Second-order responses to optogenetic FeCO activation (Chen et al. 2021) | reproducible only once the club/claw/hook afferents are mapped to our connectome's types (not done); class names also differed from the extraction |
| DNa02 activation (Yang et al. 2024) | behavioural readout (stride length), not physiological |

**The gap.** No published recording was found of an identified leg MN or premotor neuron, responding to
activation of an identified central or sensory neuron, that our model can reproduce now.

### Q5: model precedent

- **Shiu et al. 2024 (whole-brain LIF, the family our engine descends from).**
  - W_syn is its only fitted parameter. The others come from earlier models, not nerve-cord
    measurements.
  - It was validated on behaviour and calcium imaging: 91 % of 164 testable predictions.
  - Its stated limits include no non-spiking neurons and no gap junctions.
- **Pugliese et al. 2025/2026 (nerve-cord rate model).**
  - Its parameters are drawn from distributions, not fitted.
  - It uses size-scaled gain and threshold.
  - It was validated on behaviour only. No neural recordings of its core cells were found in the text
    read.
- **FlyGM 2026:** the connectome is the architecture of a controller trained by reinforcement learning.
- **Zarin et al. 2019:** a larval network model with behavioural validation.

No published nerve-cord model found here has been validated against recordings of its own core cells.

## Disagreements (strict second-read rule)

The rule, declared before the checks: an entry agrees only if its measure, numbers and identity are
confirmed in text the checker read verbatim.

| Entry | Reason |
|---|---|
| ZW16-larvalMN-spiking, ZW16-larvalMN-intrinsic | claim confirmed, sample sizes not found verbatim |
| MA17-gap-junction | full text returned HTTP 500 twice; the abstract confirms only part |
| AG20-target-FeCO | 13Bα vibration data are calcium imaging, not whole-cell |
| CH21-target-optoFeCO | class names wrong in the extraction (the paper uses 9Ba, 10Ba, 13Ba, 13Bb) |
| SH24-model, PU25-model | most parameter values lie in spans the checker did not read verbatim |

## Process notes and deviations

- **Access.**
  - PMC and eLife served bot-check pages to the reading agents, Springer redirected to a login, and a
    Bielefeld record was access-denied. bioRxiv rate-limited the first attempt.
  - No check was bypassed. Open-access full texts were read through Europe PMC's public REST service
    instead, and abstracts through its search service.
  - PDF-only sources were not downloaded and are logged as excluded.
- **Reading windows.** The agents read long papers in windows. Text outside the verbatim windows
  arrived only as tool summaries, which were not used for any counted value.
- **Snowball.**
  - References were followed one level.
  - Citing papers were listed for the two central primary sources (57 and 73 citing records) and
    screened by abstract. No further adult nerve-cord electrophysiology was found.
  - Grade C locust and stick-insect primary papers were not read (access, or grade C only).
- **Grading calls made during extraction (recorded):**
  - larval sources are grade C (different stage);
  - Fan 2025's neurons are grade C because their class is not stated;
  - Azevedo's MNs are graded B at the class level, not A, because the individual neurons are not
    matched to connectome types.
- **Protocol note for later reviews.** D3 as written would count an entry that confirms the engine's
  existing rule as a "supported change". This did not arise here (D3 is empty), but a later protocol
  should count only changes.

## What this means (per the declared outcomes)

**`EVIDENCE_PARTIAL`.** The design gives the user two options:
- a variant validated only on whatever targets exist, with that limit stated;
- a second, narrower review aimed at the gap.

With D5 = 0 there is nothing to validate a variant against. Under the charter, a variant cannot be
tested before physiology validation, so the first option is not available yet.

**Recommended (a judgment, not a declared rule): an identity-mapping review (P2).**
- It would search published connectome annotations, such as MANC/FANC typing papers and the FeCO
  connectome work, for the connectome types of 13Bα, 10Bα, 9Aα and the FeCO club/claw/hook afferents.
- That would raise the D1 candidates from hemilineage to type level.
- It could also make the Chen 2021 and Agrawal 2020 stimuli reproducible. Activating identified
  afferent types is something the neural-only engine can do. That would yield D5 targets.

**In no case** does P1 change the engine, or claim function or behaviour from anatomy.

## Limits

- Public literature only. Some full texts were readable only in part, and several sources only at
  abstract level.
- An AI reviewer worked through web tools. Its prior knowledge may have shaped what it noticed. The
  declared queries, the search log and the separate second read are the guard against that.
- Grade C evidence never decides. Identity mapping depends on published names.
- Motor coordinates are unchanged (20/42 admitted, +4 conditional).

## Evidence

`docs/evidence/physiology-review-v1/`:
- `protocol.json` (c28c524a…);
- `network_table.json`;
- `evidence.json` (26 entries with second-read notes);
- `search_log.json` (21 queries, screened hits, snowball, access log);
- `result.json`.
