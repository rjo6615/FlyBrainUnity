"""Read-only contract tests for M9A-2 post-run forensics."""
import ast
import hashlib
import inspect
from pathlib import Path
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
