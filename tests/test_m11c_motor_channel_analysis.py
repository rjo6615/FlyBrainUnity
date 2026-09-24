"""Dedicated tests for inert, fail-closed, deterministic M11C analysis."""
import hashlib
import importlib
import json
from pathlib import Path

import pytest

from malecns_backend.embodiment import m11c_motor_channel_analysis as m11c


def _bytes(value):
    return (json.dumps(value, sort_keys=True) + "\n").encode()


def _sources(directory: Path):
    deviations = {}
    estimands = {}
    conditions = ["full_11_enabled", "all_11_disabled"] + [
        f"leave_one_out__{name}" for name, _, _ in m11c.CHANNELS]
    full = {m11c.METRICS[0]: 1.0, m11c.METRICS[1]: 10.0}
    effects = {
        name: ((index - 5) * .005, (index % 3 - 1) * .25)
        for index, (name, _, _) in enumerate(m11c.CHANNELS)
    }
    for condition in conditions:
        deviations[condition] = {}
        channel = condition.removeprefix("leave_one_out__")
        for metric_index, metric in enumerate(m11c.METRICS):
            effect = effects[channel][metric_index] if condition.startswith("leave_one_out__") else 0.0
            deviations[condition][metric] = {"later_post_force": full[metric] + effect}
    for name, _, _ in m11c.CHANNELS:
        estimands[name] = {}
        for index, metric in enumerate(m11c.METRICS):
            # Use the exact same operation as the implementation and frozen M11B.
            effect = deviations[f"leave_one_out__{name}"][metric]["later_post_force"] - full[metric]
            estimands[name][metric] = {"effect": effect,
                "classification": m11c.classify(effect, m11c.THRESHOLDS[metric])}
    report = {
        "schema": m11c.SOURCE_SCHEMA, "status": "COMPLETE", "condition_order": conditions,
        "transition_counts": {"aggregate": {"neural_transitions": 39000,
                                              "physics_transitions": 195000}},
        "perturbation": {"magnitude": 1.024},
        "windows": {"later_post_force": m11c.LATER_WINDOW}, "thresholds": m11c.THRESHOLDS,
        "motor_inventory": [{"name": n, "action_index": i, "coordinate_sign": s}
                            for n, i, s in m11c.CHANNELS],
        "per_condition_deviations": deviations, "later_post_force_estimands": estimands,
    }
    prereg = {"analysis": {"primary_window": "later_post_force",
                            "thresholds": m11c.THRESHOLDS, "estimand": m11c.ESTIMAND}}
    values = {"m11_raw.npz": b"authenticated-but-analysis-does-not-load-this",
              "m11_report.json": _bytes(report), "m11_manifest.json": _bytes({"condition_count": 13}),
              m11c.PREREGISTRATION: _bytes(prereg)}
    for name, content in values.items():
        (directory / name).write_bytes(content)
    identities = {name: {"byte_size": len(content), "sha256": hashlib.sha256(content).hexdigest()}
                  for name, content in values.items()}
    return identities


def _validated(directory: Path):
    identities = _sources(directory)
    return m11c.validate_provenance(directory,
        {name: identities[name] for name in m11c.EXPECTED_IDENTITIES},
        identities[m11c.PREREGISTRATION])


def test_import_is_structurally_analysis_only():
    module = importlib.reload(m11c)
    assert module.NEURAL_TRANSITIONS == module.PHYSICS_TRANSITIONS == 0
    source = Path(module.__file__).read_text()
    assert "m11_motor_channel_dissection" not in source.replace('"interface_output" / "m11_motor_channel_dissection"', "")
    assert "mujoco" not in module.__dict__ and "flygym" not in module.__dict__


def test_frozen_identity_constants_are_exact():
    assert m11c.EXPECTED_IDENTITIES == {
        "m11_raw.npz": {"byte_size": 81305728, "sha256": "0f5c8ca4777c79640a8cf032e21366cd6819335a7b22ff9457ed07aec1e183c1"},
        "m11_report.json": {"byte_size": 17257, "sha256": "2678b2fcb74144632134c397d96132f8232992606d34a40e2d056e061a49606f"},
        "m11_manifest.json": {"byte_size": 4828, "sha256": "7a2f6c23a5b7e3f42929c94c88847a24d50bb7b87139e04cba35112fe5ea0180"},
    }
    assert m11c.EXPECTED_PREREGISTRATION == {"byte_size": 10003,
        "sha256": "aa8f0b57c1126d6f4bb5b477849e81be2dbd9c86ba6d180698810c7aedfe6fd5"}


def test_provenance_content_and_complete_status_required(tmp_path):
    identities = _sources(tmp_path)
    validated = m11c.validate_provenance(tmp_path,
        {n: identities[n] for n in m11c.EXPECTED_IDENTITIES}, identities[m11c.PREREGISTRATION])
    assert len(validated["report"]["condition_order"]) == 13
    assert m11c.THRESHOLDS == {"thorax_com_deviation_mm": .005,
                               "root_orientation_shortest_arc_deg": .25}
    assert m11c.LATER_WINDOW == {"start_ms_inclusive": 557., "stop_ms_inclusive": 1500.}
    report_path = tmp_path / "m11_report.json"
    report = json.loads(report_path.read_text()); report["status"] = "NOT_COMPLETE"
    report_path.write_bytes(_bytes(report))
    identities["m11_report.json"] = {"byte_size": report_path.stat().st_size,
        "sha256": hashlib.sha256(report_path.read_bytes()).hexdigest()}
    with pytest.raises(RuntimeError, match="not COMPLETE"):
        m11c.validate_provenance(tmp_path,
            {n: identities[n] for n in m11c.EXPECTED_IDENTITIES}, identities[m11c.PREREGISTRATION])


def test_fail_closed_identity_mismatch_publishes_nothing(tmp_path):
    source, output = tmp_path / "source", tmp_path / "output"
    source.mkdir(); identities = _sources(source)
    identities["m11_raw.npz"]["sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="identity mismatch"):
        validated = m11c.validate_provenance(source,
            {n: identities[n] for n in m11c.EXPECTED_IDENTITIES}, identities[m11c.PREREGISTRATION])
        m11c.publish(output, m11c.build_analysis(validated), validated)
    assert not output.exists()


def test_estimand_table_classifications_cross_metric_and_order(tmp_path):
    analysis = m11c.build_analysis(_validated(tmp_path))
    rows = analysis["per_channel_table"]
    assert [row["channel_name"] for row in rows] == [x[0] for x in m11c.CHANNELS]
    assert len({row["channel_name"] for row in rows}) == 11
    first = rows[0][m11c.METRICS[0]]
    assert first["signed_leave_one_out_effect"] == first["leave_one_out_later_deviation"] - first["full_11_enabled_later_deviation"]
    assert all(row[metric]["inherited_classification"] ==
               m11c.classify(row[metric]["signed_leave_one_out_effect"], m11c.THRESHOLDS[metric])
               for row in rows for metric in m11c.METRICS)
    assert all(row["cross_metric_classification"] in {"BOTH_UNRESOLVED", "COM_RESOLVED_ONLY",
        "ORIENTATION_RESOLVED_ONLY", "BOTH_RESOLVED_SAME_DIRECTION",
        "BOTH_RESOLVED_OPPOSITE_DIRECTION"} for row in rows)
    summary = analysis["per_metric_deterministic_summaries"][m11c.METRICS[1]]
    assert any(len(group["channels"]) > 1 for group in summary["absolute_effect_order_largest_to_smallest_with_ties"])


def test_no_additive_composite_or_new_threshold_analysis(tmp_path):
    analysis = m11c.build_analysis(_validated(tmp_path))
    assert analysis["non_additivity_limitation"] == m11c.NON_ADDITIVITY
    assert analysis["prohibited_analyses_confirmation"] == {"performed": [],
        "new_thresholds": False, "composite_score": False, "additive_decomposition": False}
    assert analysis["inherited_thresholds"] == m11c.THRESHOLDS
    assert analysis["analysis_only"] is True
    assert analysis["transition_counts"] == {"neural_transitions": 0, "physics_transitions": 0}


def test_deterministic_bytes_sources_unchanged_and_manifest_no_self_hash(tmp_path):
    validated = _validated(tmp_path)
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    first = m11c._json_bytes(m11c.build_analysis(validated))
    second = m11c._json_bytes(m11c.build_analysis(validated))
    assert first == second
    output = tmp_path / "out"
    m11c.publish(output, m11c.build_analysis(validated), validated)
    manifest = json.loads((output / m11c.MANIFEST_NAME).read_text())
    assert set(manifest["outputs"]) == {m11c.ANALYSIS_NAME}
    assert before == {path.name: path.read_bytes() for path in tmp_path.iterdir() if path.is_file()}


def test_cli_requires_explicit_canonical_flag():
    with pytest.raises(SystemExit):
        m11c.main([])
