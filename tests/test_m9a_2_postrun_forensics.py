"""Read-only contract tests for M9A-2 post-run forensics."""
import ast
import hashlib
import inspect
from pathlib import Path
import numpy as np
import pytest
from malecns_backend.embodiment import m9a_2_postrun_forensics as f


def test_namespace_has_no_transition_or_malecns_route():
    source=inspect.getsource(f)
    tree=ast.parse(source)
    assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=="step" for n in ast.walk(tree))
    assert not any(isinstance(n,(ast.Import,ast.ImportFrom)) and "malecns_backend.neural" in ast.unparse(n) for n in ast.walk(tree))
    assert "physics_transitions\":0" in source and "neural_transitions\":0" in source


def test_only_existing_canonical_evidence_is_declared():
    assert len(f.CANDIDATES)==8
    assert {m for m,_ in f.CANDIDATES}=={.0001,.0002,.0004,.0008,.002,.008,.032,.128}
    assert all(p.name.startswith("candidate_") and p.name.endswith("_raw.npz") for _,p in f.CANDIDATES)


def test_missing_evidence_fails_closed_before_analysis():
    # The checkout intentionally does not fabricate/copy absent Windows output.
    if all(p.exists() for _,p in f.CANDIDATES): pytest.skip("all Windows evidence is present")
    with pytest.raises(FileNotFoundError,match="missing canonical raw evidence"): f.inventory()


def test_hash_inventory_is_read_only_for_present_inputs():
    present=[p for _,p in f.CANDIDATES if p.exists()]
    before={p:(p.stat().st_size,hashlib.sha256(p.read_bytes()).hexdigest()) for p in present}
    try: f.inventory()
    except FileNotFoundError: pass
    after={p:(p.stat().st_size,hashlib.sha256(p.read_bytes()).hexdigest()) for p in present}
    assert before==after


def test_report_writer_is_exclusive_and_separate(tmp_path):
    target=tmp_path/"forensics"/"report.json"
    f.write_report({"physics_transitions":0,"neural_transitions":0},target)
    with pytest.raises(FileExistsError): f.write_report({},target)
    assert all(target.resolve()!=p.resolve() for _,p in f.CANDIDATES)


def _trajectory_fixture():
    time=np.array([499.9,500.0,500.1,520.0])
    return {"time_ms":time,
        "root_position":np.zeros((4,3)), "linear_velocity":np.zeros((4,3)),
        "orientation_wxyz":np.zeros((4,4)), "body_up_z":np.zeros(4),
        "angular_velocity":np.zeros((4,3)), "ground_contact":np.zeros((4,6),dtype=bool),
        "distal_tarsus_positions":np.zeros((4,6,3))}


def test_identical_boolean_contacts_have_no_difference():
    base=_trajectory_fixture(); result=f._trajectory(np,base,{k:v.copy() for k,v in base.items()})
    contact=result["boolean_difference"]["ground_contact"]
    assert contact["any_difference"] is False
    assert contact["differing_value_count"]==0
    assert contact["differing_value_fraction"]==0.0
    assert contact["first_divergence_ms"] is None


def test_changed_boolean_contact_reports_exact_sample_and_time():
    base=_trajectory_fixture(); changed={k:v.copy() for k,v in base.items()}
    changed["ground_contact"][2,4]=True
    result=f._trajectory(np,base,changed)
    contact=result["boolean_difference"]["ground_contact"]
    assert result["first_exact_divergence_ms"]==500.1
    assert contact["first_divergence_ms"]==500.1
    assert contact["differing_value_count"]==1
    assert contact["differing_sample_count"]==1
    assert contact["differing_value_fraction"]==pytest.approx(1/24)


def test_numeric_trajectory_retains_max_absolute_difference():
    base=_trajectory_fixture(); changed={k:v.copy() for k,v in base.items()}
    changed["root_position"][1,2]=-3.25
    result=f._trajectory(np,base,changed)
    assert result["max_absolute_component_difference"]["root_position"]==3.25
    assert result["window_max_absolute_component_difference"]["root_position"]["during_500_to_519.9_ms"]==3.25


def test_mixed_trajectory_comparison_does_not_subtract_booleans():
    base=_trajectory_fixture(); changed={k:v.copy() for k,v in base.items()}
    changed["ground_contact"][0,0]=True
    changed["angular_velocity"][3,1]=2.0
    result=f._trajectory(np,base,changed)
    assert result["boolean_difference"]["ground_contact"]["any_difference"] is True
    assert result["max_absolute_component_difference"]["angular_velocity"]==2.0


def test_trajectory_rejects_non_boolean_contact_data():
    base=_trajectory_fixture(); changed={k:v.copy() for k,v in base.items()}
    changed["ground_contact"]=changed["ground_contact"].astype(np.int8)
    with pytest.raises(TypeError,match="ground_contact must contain Boolean"): f._trajectory(np,base,changed)
