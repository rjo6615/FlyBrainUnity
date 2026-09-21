"""Windows-only M8 execution boundary; import performs no transitions."""
from __future__ import annotations
import hashlib, importlib, importlib.metadata, io, json, os, subprocess, time
from pathlib import Path
from typing import Any, Mapping, Sequence
from . import m8_extended_spontaneous as m8
from . import m7d_corrected_spontaneous as m7d
from . import _windows_m7d_corrected_spontaneous_adapter as m7da
from . import _windows_m7_spontaneous_locomotion_adapter as old
from . import integrated_whole_leg_readiness as m6c


def gate_contributions(values: Mapping[str, float], condition: str, admitted: Sequence[str]):
    return m7da.gate_contributions(values, condition, admitted)


def _runner(**kwargs: Any):
    from ._windows_m8_live_condition import run_condition
    return run_condition(**kwargs)


def _invoke(runner, protocol, records, table, condition, number, initialize_only):
    return runner(protocol=protocol, condition=condition, condition_number=number,
        progress=lambda n,c,f,s,cw,tw,eta: f"[{n}/2] {c} {f:.1%} step {s}/100000",
        cached_admission_assertion=m6c.assert_physical_admission, cached_records=records,
        cached_table=table, initialize_only=initialize_only, duration_ms=m8.DURATION_MS,
        condition_names=m8.CONDITIONS, contribution_gate=gate_contributions,
        compact_telemetry=True, runtime_factory=m7da._runtime, proprioception_only=True,
        fixed_initial_baseline=True, m8_extended_telemetry=True)


def windows_preflight(runner=_runner):
    m8.validate_protocol(m8.protocol())
    if not m8.output_available(): raise FileExistsError("M8 output namespace is not empty")
    provenance={"b4":m7d.verify_b4(), "m7":m7d.verify_m7()}
    environment=m7da._environment(); protocol, records, table=m7da._protocol()
    states=[_invoke(runner,protocol,records,table,c,i,True) for i,c in enumerate(m8.CONDITIONS,1)]
    if any(x["physics_steps"] or x["neural_steps"] for x in states): raise RuntimeError("preflight crossed transition boundary")
    if not m6c.pre_intervention_equivalent(*(x["pre_intervention_state"] for x in states)): raise RuntimeError("initial states differ")
    audits=[x["initial_physical_state_audit"] for x in states]
    if audits[0] != audits[1] or audits[0]["body_position"] != list(m8.SPAWN_POS): raise RuntimeError("physical initialization mismatch")
    contact=audits[0].get("m8_contact_identity", {"available":False,"method":"unavailable from runtime"})
    return {"schema":m8.SCHEMA,"status":"PREFLIGHT_PASS","scientific_run_executed":False,
        "physics_transitions":0,"neural_transitions":0,"fresh_runtime_count":2,
        "strict_initial_equivalence":True,"environment":environment,"provenance":provenance,
        "contact_identity":contact,"telemetry_schema":states[0]["telemetry_schema"]}


def _write_npz(path: Path, arrays):
    import numpy as np
    b=io.BytesIO(); np.savez_compressed(b, **arrays); payload=b.getvalue(); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("xb") as f: f.write(payload); f.flush(); os.fsync(f.fileno())
    return hashlib.sha256(payload).hexdigest()


def _publish(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("x",encoding="utf-8") as f: json.dump(value,f,indent=2,sort_keys=True,allow_nan=False); f.write("\n")


def run_windows(runner=_runner):
    pre=windows_preflight(runner); protocol,records,table=m7da._protocol(); results={}; started=time.perf_counter()
    for i,c in enumerate(m8.CONDITIONS,1):
        r=_invoke(runner,protocol,records,table,c,i,False)
        if (r["physics_steps"],r["neural_steps"]) != (m8.EXPECTED_PHYSICS_TRANSITIONS,m8.EXPECTED_NEURAL_UPDATES): raise RuntimeError("wrong transition count")
        if r["physics_instability"] or r["unauthorized_contribution_count"]: raise RuntimeError("instability or unauthorized motor contribution")
        results[c]=r
    if not m6c.pre_intervention_equivalent(*(results[c]["pre_intervention_state"] for c in m8.CONDITIONS)): raise RuntimeError("matched-state failure")
    arrays={f"{c}__{k}":v for c,r in results.items() for k,v in r["raw_arrays"].items()}
    digest=_write_npz(m8.RAW_PATH,arrays)
    manifest={"schema":m8.SCHEMA,"status":"COMPLETE","source_commit":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
        "protocol":m8.protocol(),"environment":pre["environment"],"provenance":pre["provenance"],"contact_identity":pre["contact_identity"],
        "runtime_seconds":time.perf_counter()-started,"raw":{"path":str(m8.RAW_PATH.resolve()),"sha256":digest,"byte_size":m8.RAW_PATH.stat().st_size},
        "arrays":{k:{"shape":list(v.shape),"dtype":str(v.dtype)} for k,v in arrays.items()}}
    _publish(m8.MANIFEST_PATH,manifest)
    from . import m8_postrun_analysis, m8_replay_export
    analysis=m8_postrun_analysis.analyze(m8.RAW_PATH,m8.MANIFEST_PATH,m8.ANALYSIS_PATH,m8.REPORT_PATH)
    m8_replay_export.export(m8.RAW_PATH,m8.MANIFEST_PATH,m8.REPLAY_MANIFEST_PATH)
    manifest["artifacts"]={p.name:{"byte_size":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for p in (m8.ANALYSIS_PATH,m8.REPORT_PATH,m8.REPLAY_MANIFEST_PATH,*[m8.OUTPUT_DIR/n for n in ("m8_enabled_replay.bin","m8_disabled_replay.bin")])}
    temporary=m8.MANIFEST_PATH.with_suffix(".json.tmp"); temporary.write_text(json.dumps(manifest,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8"); temporary.replace(m8.MANIFEST_PATH)
    return analysis
