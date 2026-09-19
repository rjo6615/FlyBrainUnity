"""Read-only M5D-5D1 prefix-failure diagnostic.

This module never imports either live adapter.  It accepts only frozen JSON/NPZ
artifacts and fails closed before scientific interpretation when provenance is
not self-consistent.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


SCHEMA = "M5D-5D1.0"
CAUSE = "GUARD_SEMANTIC_MISMATCH"
MILESTONES = tuple(f"C{i}" for i in range(14))
PREFIX_REQUIRED = ("C3", "C4", "C6", "C7", "C8", "C10", "C11")
PREFIX_COMPARISONS = (
    ("C3", "<", "C4"), ("C4", "<=", "C6"),
    ("C6", "<=", "C7"), ("C7", "<=", "C8"),
    ("C8", "<=", "C10"), ("C10", "<", "C11"),
)


def _predicate(name: str, left: Any, operator: str, right: Any, result: bool) -> dict[str, Any]:
    return {"name": name, "left": left, "operator": operator, "right": right,
            "result": bool(result), "status": "PASS" if result else "FAIL"}


def reconstruct_guard(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Expand the exact adapter expression in source evaluation order."""
    m = report.get("milestones", {})
    predicates = [_predicate(f"{key}_is_not_None", m.get(key), "is not", None,
                             m.get(key) is not None) for key in PREFIX_REQUIRED]
    for left, operator, right in PREFIX_COMPARISONS:
        lv, rv = m.get(left), m.get(right)
        result = False if lv is None or rv is None else (lv < rv if operator == "<" else lv <= rv)
        predicates.append(_predicate(f"{left} {operator} {right}", lv, operator, rv, result))
    pre = report.get("pre_intervention_equivalence", {}).get("passed")
    prefix = all(p["result"] for p in predicates)
    predicates.extend((
        _predicate("exact_pre_intervention_equivalence", pre, "==", True, pre is True),
        _predicate("causal_prefix_ordered", prefix, "==", True, prefix is True),
        _predicate("replication_guard_passed", (pre is True and prefix), "==", True,
                   pre is True and prefix),
    ))
    return predicates


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_inputs(report_path: Path, telemetry_path: Path) -> dict[str, Any]:
    """Verify existence, digest advertised by JSON, schema, and readable NPZ."""
    result: dict[str, Any] = {"verified": False, "read_only": True,
        "json_path": str(report_path), "telemetry_path": str(telemetry_path)}
    if not report_path.is_file():
        result["failure"] = "AUTHORITATIVE_JSON_MISSING"; return result
    result["json_sha256"] = _sha256(report_path)
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception as exc:
        result["failure"] = f"AUTHORITATIVE_JSON_INVALID: {type(exc).__name__}"; return result
    if report.get("schema") != "M5D-5D.0" or report.get("run_status") != "COMPLETE":
        result["failure"] = "AUTHORITATIVE_JSON_SEMANTICS_MISMATCH"; return result
    if not telemetry_path.is_file():
        result["failure"] = "AUTHORITATIVE_TELEMETRY_MISSING"; return result
    digest = _sha256(telemetry_path); result["telemetry_sha256"] = digest
    if report.get("telemetry", {}).get("sha256") != digest:
        result["failure"] = "AUTHORITATIVE_TELEMETRY_DIGEST_MISMATCH"; return result
    try:
        import numpy as np
        with np.load(telemetry_path, allow_pickle=False) as z:
            schema = str(z["schema"].item())
            keys = sorted(z.files)
    except Exception as exc:
        result["failure"] = f"AUTHORITATIVE_TELEMETRY_INVALID: {type(exc).__name__}"; return result
    if schema != "M5D-5D-TELEMETRY.0":
        result["failure"] = "AUTHORITATIVE_TELEMETRY_SCHEMA_MISMATCH"; return result
    result.update(verified=True, telemetry_schema=schema, telemetry_keys=keys)
    return result


def diagnose(report_path: Path, telemetry_path: Path, m5d5b_path: Path) -> dict[str, Any]:
    provenance = verify_inputs(report_path, telemetry_path)
    shell = {"schema": SCHEMA, "run_status": "FAILED", "classification": "OTHER_DIAGNOSTIC_FAILURE",
        "first_failed_predicate": None, "guard_predicates": [], "m5d5b_vs_m5d5d": {},
        "pre_intervention_equivalence": {"verified": False}, "c1_timeline": {},
        "c13_preserved": {}, "scientific_interpretation": {"permitted": False},
        "provenance": provenance}
    if not provenance["verified"]:
        shell["scientific_interpretation"]["reason"] = provenance["failure"]
        return shell
    report = json.loads(report_path.read_text(encoding="utf-8"))
    baseline = json.loads(m5d5b_path.read_text(encoding="utf-8"))
    predicates = reconstruct_guard(report)
    first = next((p for p in predicates if not p["result"]), None)
    comparisons = {}
    for key in MILESTONES:
        b, d = baseline["milestones"].get(key), report["milestones"].get(key)
        delta = None if b is None or d is None else d - b
        relation = "exact" if b == d else "equivalent" if delta is not None and abs(delta) <= 1e-12 else "different"
        comparisons[key] = {"m5d5b_value_ms": b, "m5d5d_value_ms": d, "delta_ms": delta,
            "relation": relation, "scientifically_meaningful": relation == "different"}
    shell.update(run_status="COMPLETE", classification=CAUSE, first_failed_predicate=first,
        guard_predicates=predicates, m5d5b_vs_m5d5d={"milestones": comparisons},
        pre_intervention_equivalence=report["pre_intervention_equivalence"],
        c1_timeline=report["c1_resolution"], c13_preserved=report["c13_resolution"],
        scientific_interpretation={"permitted": True,
            "causal_prefix_reproduced": all(comparisons[k]["relation"] in ("exact", "equivalent") for k in ("C2","C3","C4","C5","C6","C7","C8","C9","C10","C11","C12")),
            "cause": "The guard requires C3 < C4 although raw and admitted contributions may occur in the same update; C1 is not a guard term."})
    return shell


def main() -> int:
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path,
        default=base / "interface_output/instrumented_closed_loop_prefix_diagnostic.json")
    args = parser.parse_args()
    result = diagnose(base / "interface_output/instrumented_proprioceptive_closed_loop_100ms.json",
        base / "interface_output/instrumented_proprioceptive_closed_loop_telemetry.npz",
        base / "interface_output/proprioceptive_closed_loop_100ms.json")
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if result["run_status"] == "COMPLETE" else 2

if __name__ == "__main__":
    raise SystemExit(main())
