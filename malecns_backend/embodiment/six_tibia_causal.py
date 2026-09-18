"""Milestone 4B-2 matched simultaneous six-tibia causal experiment.

This module composes the validated 4B-1 interfaces.  It does not contain an
anatomical mapping, locomotion policy, or cross-leg coupling.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import subprocess

import numpy as np

from .body import SixTibiaFlyGymBody
from .motor import MotorActivityObserver, MotorSafety
from .sensory import LegSensoryFrame, SensoryEncoder
from .six_tibia import LEG_ORDER, SIX_LEG_MAP, IsolatedMotorDecoder, load_six_tibia_interfaces

CONTROL_DT_S = .001
PHYSICS_DT_S = .0001
TOLERANCE = 1e-12
# The checked-in 4B-2 result and the production CLI were generated with the
# historical default seed.  Keep this in one place so follow-on diagnostics
# cannot silently select a different trajectory.
CANONICAL_SEED = 1
ISOLATED_BASELINE = {
    "LF": (0, None, 0.), "LM": (9, 34.5, .207284),
    "LH": (0, None, 0.), "RF": (0, None, 0.),
    "RM": (4, 48.5, .140410), "RH": (6, 24.5, .156191),
}
PROVENANCE = {
    "angles": "PHYSICS_MEASURED", "sensory_rates": "MODELED_TRANSDUCTION",
    "cns": "CONNECTOME_DERIVED", "motor_populations": "ANNOTATION_DERIVED",
    "offsets": "MODELED_MOTOR_DECODING", "actuator_limits": "ENGINEERING_CONSTRAINT",
}


def rng_state_digest(rng):
    """Return a stable, non-advancing SHA-256 digest of a NumPy RNG state."""
    state=json.dumps(rng.bit_generator.state,sort_keys=True,separators=(",", ":"))
    return hashlib.sha256(state.encode("ascii")).hexdigest()


class EventObserver:
    def __init__(self, interfaces):
        self.sensors = {l: set(p.sensor.dense_indices) for l, p in interfaces.items()}
        self.motors = {l: set(i for q in p.motor_populations for i in q.dense_indices)
                       for l, p in interfaces.items()}
        self.first_sensory = {l: None for l in LEG_ORDER}
        self.first_motor = {l: None for l in LEG_ORDER}
        self.first_downstream = None

    def before_delivery(self, brain, arriving): pass

    def after_step(self, brain, fired):
        fired = set(map(int, fired)); all_sensors = set().union(*self.sensors.values())
        for leg in LEG_ORDER:
            if self.first_sensory[leg] is None and fired & self.sensors[leg]:
                self.first_sensory[leg] = brain.time_ms
            if self.first_motor[leg] is None and fired & self.motors[leg]:
                self.first_motor[leg] = brain.time_ms
        if self.first_downstream is None and fired - all_sensors:
            self.first_downstream = brain.time_ms


class _ObserverFanout:
    """Forward read-only diagnostic callbacks without changing their order."""
    def __init__(self, *observers):
        self.observers = observers

    def before_delivery(self, brain, arriving):
        for observer in self.observers:
            observer.before_delivery(brain, arriving)

    def after_step(self, brain, fired):
        # Preserve the canonical observer call first.  Diagnostics get their
        # own event array: even a buggy callback cannot rewrite the array
        # returned by Brain.step or seen by another observer.
        self.observers[0].after_step(brain, fired)
        for observer in self.observers[1:]:
            observer.after_step(brain, fired.copy())


class SixTibiaRuntime:
    """One brain, six encoders, and six strictly independent observer/decoders."""
    def __init__(self, brain, body, interfaces, seed, apply_neural_motor,
                 diagnostic_observer=None, withheld_sensory=None):
        self.brain, self.body = brain, body
        self.interfaces = dict(interfaces)
        if tuple(self.interfaces) != LEG_ORDER: raise ValueError("exactly six ordered interfaces required")
        self.encoders = {l: SensoryEncoder(p) for l, p in self.interfaces.items()}
        self.observers = {l: MotorActivityObserver({q.name: q.dense_indices
                          for q in p.motor_populations}) for l, p in self.interfaces.items()}
        self.decoders = {l: IsolatedMotorDecoder(p, MotorSafety(*p.joint_range_rad, .25, 4.))
                         for l, p in self.interfaces.items()}
        self.apply_neural_motor = bool(apply_neural_motor)
        if withheld_sensory is not None and withheld_sensory not in LEG_ORDER:
            raise ValueError(f"unknown sensory population: {withheld_sensory}")
        self.withheld_sensory = withheld_sensory
        self.events = EventObserver(self.interfaces)
        brain.reset(seed)
        self.rng_after_reset = rng_state_digest(brain.rng) if hasattr(brain,"rng") else None
        # The optional observer is passive and receives the same callbacks as
        # the compact canonical event observer.  The default path is unchanged.
        brain.diagnostic_observer = (_ObserverFanout(self.events, diagnostic_observer)
                                     if diagnostic_observer is not None else self.events)
        for observer in self.observers.values(): observer.reset(brain.spike_counts)

    def step(self, time_ms):
        before = self.body.observe()
        rng_before = rng_state_digest(self.brain.rng) if hasattr(self.brain,"rng") else None
        encoded = {l: self.encoders[l].encode(LegSensoryFrame(before.time_s, before.angles_rad[l]))
                   for l in LEG_ORDER}
        self.brain.clear_external_drive()
        for drive in encoded.values(): self.brain.set_external_drive(drive.indices, drive.rates_hz)
        withheld_indices = (encoded[self.withheld_sensory].indices
                            if self.withheld_sensory is not None else np.empty(0, np.intp))
        # MaleCNS draws candidate external events for all six populations in
        # canonical dense-index order, then removes only these events before
        # CNS delivery.  Encoding and RNG consumption are therefore never
        # skipped merely because a population is withheld.
        self.brain.external_drive_withheld_indices = np.asarray(withheld_indices, dtype=np.intp)
        counts0 = self.brain.spike_counts.copy()
        distinct = set(); counterfactual = {l: 0 for l in LEG_ORDER}; delivered_external = {l: 0 for l in LEG_ORDER}
        neural_steps = int(round(CONTROL_DT_S * 1000 / self.brain.config.dt))
        sensor_sets = {l: set(map(int, encoded[l].indices)) for l in LEG_ORDER}
        for _ in range(neural_steps):
            distinct.update(map(int, self.brain.step()))
            candidates = set(map(int, getattr(self.brain, "_last_external_candidates", ())))
            delivered_candidates = set(map(int, getattr(self.brain, "_last_external_delivered", candidates)))
            for leg in LEG_ORDER:
                counterfactual[leg] += len(candidates & sensor_sets[leg])
                delivered_external[leg] += len(delivered_candidates & sensor_sets[leg])
        rng_after = rng_state_digest(self.brain.rng) if hasattr(self.brain,"rng") else None
        counts = self.brain.spike_counts
        motor, commands, actuation = {}, {}, {}
        for leg in LEG_ORDER:
            p = self.interfaces[leg]
            observed = self.observers[leg].update(counts, 1.)
            directional = self.decoders[leg].directional_rates(observed["filtered_hz"])
            command = self.decoders[leg].decode(observed["filtered_hz"], before.angles_rad[leg],
                                                CONTROL_DT_S, self.apply_neural_motor)
            observed["directional_filtered_hz"] = directional
            motor[leg], commands[leg] = observed, command
            applied = command.magnitude_clamped_output_rad if self.apply_neural_motor else 0.
            actuation[leg] = {"base_target_rad": before.angles_rad[leg],
                "candidate_rad": command.unclamped_position_rad,
                "final_target_rad": command.target_position_rad,
                "decoded_offset_rad": command.magnitude_clamped_output_rad,
                "applied_neural_contribution_rad": applied,
                "range_clamped": command.range_clamped_position_rad != command.unclamped_position_rad,
                "slew_clamped": command.target_position_rad != command.range_clamped_position_rad}
        # Passive failure diagnostics: retain the inputs to the physics call so
        # a PhysicsError can be reported without manufacturing a successful
        # control row or modifying the state passed to MuJoCo.
        self.last_step_attempt = {"time_ms": time_ms, "before": before,
                                  "actuation": actuation}
        physics_diagnostic = getattr(self.body, "physics_diagnostic", None)
        if physics_diagnostic is not None:
            physics_diagnostic.set_control_context(time_ms, actuation)
        after = self.body.step(commands, int(round(CONTROL_DT_S / self.body.timestep_s)))
        sensory_increments = {l: int((counts-counts0)[encoded[l].indices].sum()) for l in LEG_ORDER}
        # Fakes predating candidate telemetry still get useful all-six data.
        if not hasattr(self.brain, "_last_external_candidates"):
            counterfactual = dict(sensory_increments); delivered_external = dict(sensory_increments)
        return {"time_ms": time_ms, "before": before, "after": after, "encoded": encoded,
                "sensory_provenance": {l: {"counterfactual_provenance": "MODELED_TRANSDUCTION",
                    "delivered_provenance": "ENGINEERED_SENSORY_WITHHOLDING" if l == self.withheld_sensory else "MODELED_TRANSDUCTION"}
                    for l in LEG_ORDER},
                "counterfactual_sensory_increments": counterfactual,
                "delivered_sensory_increments": delivered_external,
                "sensory_increments": sensory_increments,
                "cns_spike_increment": int((counts-counts0).sum()),
                "spiking_neuron_indices": tuple(sorted(distinct)),
                "distinct_spiking_neurons": len(distinct), "motor": motor, "actuation": actuation,
                "rng_before_sensory": rng_before, "rng_after_stochastic_drive": rng_after}


def _first(rows, predicate):
    return next((r["time_ms"] for r in rows if predicate(r)), None)


def analyze_matched(closed, control, events_closed=None, tolerance=TOLERANCE):
    """Analyze compact telemetry with strict temporal prerequisite semantics."""
    if len(closed) != len(control) or [r["time_ms"] for r in closed] != [r["time_ms"] for r in control]:
        raise ValueError("matched telemetry schedule differs")
    applied = _first(closed, lambda r: any(abs(r["actuation"][l]["applied_neural_contribution_rad"]) > tolerance for l in LEG_ORDER))
    decoded = _first(closed, lambda r: any(abs(r["actuation"][l]["decoded_offset_rad"]) > tolerance for l in LEG_ORDER))
    motor_spike = _first(closed, lambda r: any(sum(r["motor"][l]["increments"].values()) for l in LEG_ORDER))
    angle_d = np.asarray([[a["after"].angles_rad[l]-b["after"].angles_rad[l] for l in LEG_ORDER]
                          for a,b in zip(closed,control)], dtype=float)
    rate_equal = [[np.array_equal(a["encoded"][l].rates_hz,b["encoded"][l].rates_hz) for l in LEG_ORDER]
                  for a,b in zip(closed,control)]
    physical = next((r["time_ms"] for r,d in zip(closed,angle_d) if np.linalg.norm(d)>tolerance),None)
    sensory = next((r["time_ms"] for r,e in zip(closed,rate_equal) if not all(e)),None)
    cns = next((a["time_ms"] for a,b in zip(closed,control)
                if a["cns_spike_increment"] != b["cns_spike_increment"] or
                a.get("spiking_neuron_indices") != b.get("spiking_neuron_indices")),None)
    # A mapped-motor difference can be the cause of actuation, so it is not
    # evidence that the feedback loop has returned to the motor population.
    # Feedback motor divergence is specifically the first difference at or
    # after downstream CNS divergence.  These values are telemetry-row times
    # (control-step milliseconds), just like the other global stages; the
    # observer's sub-step neural timestamps are only reported per leg.
    motor_div = next((a["time_ms"] for a,b in zip(closed,control) if
        cns is not None and a["time_ms"] >= cns and any(
        a["motor"][l]["increments"] != b["motor"][l]["increments"] for l in LEG_ORDER)),None)
    pre = [i for i,r in enumerate(closed) if applied is None or r["time_ms"] < applied]
    pre_ok = all(np.linalg.norm(angle_d[i]) <= tolerance and
                 all(abs(closed[i]["after"].velocities_rad_s[l]-control[i]["after"].velocities_rad_s[l]) <= tolerance for l in LEG_ORDER) and
                 all(rate_equal[i]) and
                 closed[i]["sensory_increments"] == control[i]["sensory_increments"] and
                 closed[i]["cns_spike_increment"] == control[i]["cns_spike_increment"] and
                 closed[i].get("spiking_neuron_indices") == control[i].get("spiking_neuron_indices") and
                 all(closed[i]["motor"][l]["increments"] == control[i]["motor"][l]["increments"] and
                     closed[i]["actuation"][l]["decoded_offset_rad"] == control[i]["actuation"][l]["decoded_offset_rad"]
                     for l in LEG_ORDER) for i in pre)
    order = [motor_spike, decoded, applied, physical, sensory, cns, motor_div]
    observed = [x for x in order if x is not None]
    valid_order = observed == sorted(observed) and (physical is None or applied is not None)
    if not pre_ok or not valid_order: classification = "INVALID"
    else:
        downstream = any(r["cns_spike_increment"] > sum(r["sensory_increments"].values()) for r in closed)
        sensory_activity = any(sum(r["sensory_increments"].values()) for r in closed)
        stage = 0 if not sensory_activity else 1 if not downstream else 2
        if motor_spike is not None and decoded is not None: stage = 3
        reached_s4 = physical is not None and applied is not None and physical >= applied
        reached_s5 = reached_s4 and sensory is not None and sensory >= physical
        reached_s6 = reached_s5 and cns is not None and cns >= sensory
        reached_s7 = reached_s6 and motor_div is not None and motor_div >= cns
        if reached_s4: stage = 4
        if reached_s5: stage = 5
        if reached_s6: stage = 6
        if reached_s7: stage = 7
        classification = f"S{stage}"
    per_leg = {}
    sample_times = (50,100,250,500)
    for j,leg in enumerate(LEG_ORDER):
        diffs=angle_d[:,j]; first_phys=next((r["time_ms"] for r,d in zip(closed,diffs) if abs(d)>tolerance),None)
        first_sens=next((r["time_ms"] for r,e in zip(closed,rate_equal) if not e[j]),None)
        first_mdiv=next((a["time_ms"] for a,b in zip(closed,control) if cns is not None and
            a["time_ms"] >= cns and a["motor"][leg]["increments"] != b["motor"][leg]["increments"]),None)
        first_apply=_first(closed,lambda r,l=leg: abs(r["actuation"][l]["applied_neural_contribution_rad"])>tolerance)
        post=[d for r,d in zip(closed,diffs) if first_apply is not None and r["time_ms"]>=first_apply]
        bytime={r["time_ms"]:float(d) for r,d in zip(closed,diffs)}
        per_leg[leg]={"first_sensory_spike_ms": getattr(events_closed,"first_sensory",{}).get(leg) if events_closed else None,
          "first_mapped_motor_spike_ms": getattr(events_closed,"first_motor",{}).get(leg) if events_closed else _first(closed,lambda r,l=leg:sum(r["motor"][l]["increments"].values())>0),
          "first_decoded_offset_ms":_first(closed,lambda r,l=leg:abs(r["actuation"][l]["decoded_offset_rad"])>tolerance),
          "first_applied_ms":first_apply,"first_physical_divergence_ms":first_phys,
          "first_sensory_encoding_divergence_ms":first_sens,
          "first_sensory_spike_divergence_ms":next((a["time_ms"] for a,b in zip(closed,control) if a["sensory_increments"][leg]!=b["sensory_increments"][leg]),None),
          "first_cns_spike_divergence_ms":cns,"first_motor_population_divergence_ms":first_mdiv,
          "angle_differences_rad":{str(t):bytime.get(t) for t in sample_times},
          "maximum_absolute_angle_difference_rad":float(np.max(np.abs(diffs))),
          "rms_post_motor_angle_difference_rad":float(math.sqrt(np.mean(np.square(post)))) if post else 0.,
          "final_angle_difference_rad":float(diffs[-1]),"final_difference_sign":"positive" if diffs[-1]>0 else "negative" if diffs[-1]<0 else "zero"}
    norms=np.linalg.norm(angle_d,axis=1); postnorm=[n for r,n in zip(closed,norms) if applied is not None and r["time_ms"]>=applied]
    ca, cb = closed[-1]["after"], control[-1]["after"]
    def vector_difference(name):
        a=np.asarray(getattr(ca,name,()),dtype=float); b=np.asarray(getattr(cb,name,()),dtype=float)
        return (a-b).tolist() if a.shape == b.shape else None
    return {"classification":classification,"pre_motor_equivalence":pre_ok,"global_causal_order_ms":dict(zip(
        ("motor_spike","decoded_output","applied_output","physical_divergence","sensory_encoding_divergence","cns_divergence","mapped_motor_divergence"),order)),
        "per_leg":per_leg,"trajectory":{"first_divergence_ms":physical,"maximum_norm_rad":float(max(norms,default=0)),
        "rms_post_motor_norm_rad":float(math.sqrt(np.mean(np.square(postnorm)))) if postnorm else 0.,"final_norm_rad":float(norms[-1]) if len(norms) else 0.},
        "body_level_final_differences":{"position_m":vector_difference("body_position_m"),
          "orientation":vector_difference("body_orientation"),
          "linear_velocity_m_s":vector_difference("body_linear_velocity_m_s"),
          "angular_velocity_rad_s":vector_difference("body_angular_velocity_rad_s"),
          "contact_force_n":float(getattr(ca,"contact_force_n",0)-getattr(cb,"contact_force_n",0))}}


def run_matched_closed_control(duration_ms, seed, interfaces, data, make_brain,
                               make_body, closed_observer=None):
    """Authoritative 4B-2 execution path, optionally observed on CLOSED.

    Object construction and CLOSED-then-CONTROL ordering are intentionally
    centralized here.  Callers must not duplicate this experimental loop.
    """
    runs=[]; runtimes=[]
    for apply in (True, False):
        brain=make_brain(data)
        body=make_body(interfaces)
        observer=closed_observer if apply else None
        runtime=SixTibiaRuntime(brain,body,interfaces,seed,apply,observer); runtimes.append(runtime)
        try: rows=[runtime.step(t) for t in range(1,duration_ms+1)]
        finally: body.close()
        runs.append(rows)
    return runs, runtimes


def run_experiment(duration_ms=500, seed=CANONICAL_SEED, *, interfaces=None, data=None, brain_factory=None, body_factory=None):
    if duration_ms != 500: raise ValueError("primary experiment duration is fixed at 500 ms")
    from malecns_backend import MaleCNSBrain, load_malecns
    interfaces=interfaces or load_six_tibia_interfaces(); data=data if data is not None else load_malecns()
    make_brain=brain_factory or MaleCNSBrain
    make_body=body_factory or SixTibiaFlyGymBody
    runs,runtimes=run_matched_closed_control(duration_ms,seed,interfaces,data,make_brain,make_body)
    result=analyze_matched(*runs,runtimes[0].events)
    for leg in LEG_ORDER:
        row=result["per_leg"][leg]; total=sum(sum(r["motor"][leg]["increments"].values()) for r in runs[0])
        peak=max(abs(r["actuation"][leg]["decoded_offset_rad"]) for r in runs[0])
        iso=ISOLATED_BASELINE[leg]
        row.update({"sensory_spikes":sum(r["sensory_increments"][leg] for r in runs[0]),"motor_spikes":total,"peak_decoded_offset_rad":peak})
        row["simultaneous_vs_isolated"]={"isolated_motor_spikes":iso[0],"simultaneous_motor_spikes":total,
          "isolated_first_motor_ms":iso[1],"simultaneous_first_motor_ms":row["first_mapped_motor_spike_ms"],
          "isolated_peak_offset_rad":iso[2],"simultaneous_peak_offset_rad":peak,
          "previously_silent_became_active":iso[0]==0 and total>0,"previously_active_became_silent":iso[0]>0 and total==0}
    result.update({"seed":seed,"duration_ms":duration_ms,"neural_timestep_ms":runtimes[0].brain.config.dt,
      "physics_timestep_s":runtimes[0].body.timestep_s,"control_timestep_s":CONTROL_DT_S,"provenance":PROVENANCE,
      "mapping_sha256":hashlib.sha256(SIX_LEG_MAP.read_bytes()).hexdigest(),"git_commit":_git_commit(),
      "shared_runtime_per_run":True,"scientific_safeguards":["no gait","no CPG","no behavior controller","no engineered cross-leg coupling","no artificial/tonic descending drive","no tuning","model constants unchanged"]})
    return result


def _git_commit():
    try:return subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    except Exception:return "unavailable"


def print_report(r):
    print(f"GLOBAL CLASSIFICATION: {r['classification']}")
    print("PRE-MOTOR EQUIVALENCE: "+("PASS" if r["pre_motor_equivalence"] else "FAIL"))
    print("GLOBAL CAUSAL ORDER: "+" -> ".join(f"{k}={v}" for k,v in r["global_causal_order_ms"].items()))
    print("LEG SENSORY MOTOR FIRST_MOTOR PEAK_OFFSET 50ms 100ms 250ms 500ms SENSORY_FB CNS_FB MOTOR_FB")
    for l in LEG_ORDER:
        x=r["per_leg"][l]; d=x["angle_differences_rad"]
        print(l,x["sensory_spikes"],x["motor_spikes"],x["first_mapped_motor_spike_ms"],f"{x['peak_decoded_offset_rad']:.6g}",*(d[str(t)] for t in (50,100,250,500)),x["first_sensory_encoding_divergence_ms"],x["first_cns_spike_divergence_ms"],x["first_motor_population_divergence_ms"])
    print("SIX-LEG TRAJECTORY DIFFERENCE:",json.dumps(r["trajectory"],sort_keys=True))
    print("SIMULTANEOUS VS ISOLATED:",json.dumps({l:r["per_leg"][l]["simultaneous_vs_isolated"] for l in LEG_ORDER},sort_keys=True))
    print("BODY-LEVEL DIFFERENCES: "+json.dumps(r["body_level_final_differences"],sort_keys=True)+" (descriptive only)")
    print("SCIENTIFIC SAFEGUARDS: "+"; ".join(r["scientific_safeguards"]))


def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--json",type=Path); p.add_argument("--seed",type=int,default=CANONICAL_SEED)
    args=p.parse_args(argv); result=run_experiment(seed=args.seed); print_report(result)
    if args.json: args.json.parent.mkdir(parents=True,exist_ok=True); args.json.write_text(json.dumps(result,indent=2)+"\n")

if __name__ == "__main__": main()
