# M4C-2 six-tibia sensory leave-one-out perturbation

## Scope and intervention

This experiment compares the canonical **500 ms, seed-1** all-six condition
with six independently initialized conditions (`-LF`, `-LM`, `-LH`, `-RF`,
`-RM`, and `-RH`). Each condition gets a fresh brain, body, RNG, encoder,
motor observer/decoder, and actuator state. The baseline must exactly reproduce
the checked M4B-2/M4C-1 sensory counts, mapped motor counts, first motor times,
and peak offsets. A mismatch stops execution before any intervention is run.

The intervention is engineered sensory delivery withholding, not biological
silence. All six unchanged encoders execute in canonical `LF LM LH RF RM RH`
order. MaleCNS generates stochastic external-spike candidates for every
population. It records those candidates in `counterfactual_sensory_increments`,
then removes candidates belonging to the selected population immediately before
CNS delivery. `delivered_sensory_increments` is consequently zero for that
external stream. A shadow external refractory state preserves the candidate
process and RNG draw count/order when withheld candidate events would normally
impose a refractory interval. Future rates are always encoded from the live
physical state; baseline sensory sequences are never replayed after physical
divergence.

Each runtime telemetry row also contains `sensory_provenance`, keyed by leg.
Every leg entry has `counterfactual_provenance: "MODELED_TRANSDUCTION"`.
`delivered_provenance` is `"ENGINEERED_SENSORY_WITHHOLDING"` for the selected
population and `"MODELED_TRANSDUCTION"` for every normally delivered
population. Thus the counterfactual and delivered count fields identify the
two event streams, while the provenance fields identify how each stream was
produced.

The physical leg, tibia joint, motor populations, connectome edges, body
physics, motor decoder, and actuator remain present and operational. No neural,
sensory, motor, or physical scientific constant is changed. No tonic or
descending drive, motor stimulation, noise, learning, gait logic, CPG,
controller, or engineered cross-leg coupling is introduced.

## Outputs and interpretation

The summarized JSON uses `counterfactual_encoded_spikes` and
`intervention_delivered_spikes` for the two sensory counts and carries the
same `counterfactual_provenance` and `delivered_provenance` labels. It also
contains CNS totals,
nonsensory totals, per-role and selected mapped motor outcomes, a signed 6-by-6
motor influence matrix, physical trajectory differences, and direct versus
returned-feedback timestamps. `P0` through `P7` are engineering trace stages,
not rankings or biological/behavior scores. Cross-leg entries describe only a
causal cross-population effect under this modeled condition. Leave-one-out
effects may be nonlinear and non-additive and must not be summed to explain the
isolated-versus-simultaneous difference.

Detailed output is ignored under `perturbation_output/`. Expected runtime is
approximately seven times one canonical closed-loop run, plus comparison and
serialization overhead; the JSON records measured per-run wall time,
real-time factor, and total wall time. Every body is closed in a `finally`
block after its run.

## Real run

From the repository root in the existing Windows project environment:

```powershell
.\fly-brain-interactive\.venv\Scripts\python.exe -m malecns_backend.embodiment.six_tibia_perturbation_audit --json malecns_backend/embodiment/perturbation_output/six_tibia_leave_one_out.json
```

Progress is written to standard error. After a successful experiment, the
first standard-output line is `BASELINE REPRODUCTION: PASS`, followed by the
motor influence matrix and concise intervention summaries. No scientific
result should be inferred unless that line reports `PASS`.
