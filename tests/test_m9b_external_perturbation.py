"""Zero-transition static/synthetic tests for the frozen M9B preregistration."""
import importlib
import json
import shutil
from pathlib import Path

import pytest

from malecns_backend.embodiment import m9b_external_perturbation as m9b


def test_import_and_protocol_are_inert_and_preregistered(monkeypatch):
    # A reload must not touch either execution clock.
    monkeypatch.setattr(m9b, "verify_m9a_provenance", lambda *a, **k: {})
    module = importlib.reload(m9b)
    p = module.protocol()
    assert p["status"] == "NOT_RUN" and p["scientific_run_executed"] is False
    assert (module.PHYSICS_TRANSITIONS, module.PHYSICS_STATES, module.NEURAL_UPDATES) == (15000, 15001, 3000)


def test_frozen_m9a_attempt_3_provenance_and_selection():
    evidence = m9b.verify_m9a_provenance()
    assert set(evidence) == set(m9b.CALIBRATION_FILES)
    p = m9b.protocol()
    assert p["calibration"] == {"schema": m9b.CALIBRATION_SCHEMA, "attempt": 3,
        "status": "COMPLETE", "selected_force_magnitude_native": 1.024,
        "selection": "preregistered lowest qualifying candidate"}


def _copy_calibration(tmp_path):
    for name in m9b.CALIBRATION_FILES:
        shutil.copy2(m9b.CALIBRATION_DIR / name, tmp_path / name)


def _verify_fixture(tmp_path):
    return m9b.verify_m9a_provenance(
        tmp_path, immutable_directory=m9b.CALIBRATION_DIR)


@pytest.mark.parametrize("name", sorted(m9b.CANONICAL_LF_TEXT_ARTIFACTS))
def test_canonical_lf_and_equivalent_crlf_text_pass(tmp_path, name):
    _copy_calibration(tmp_path)
    target = tmp_path / name
    canonical = target.read_bytes()
    assert b"\r" not in canonical
    _verify_fixture(tmp_path)
    target.write_bytes(canonical.replace(b"\n", b"\r\n"))
    _verify_fixture(tmp_path)


@pytest.mark.parametrize("name", sorted(m9b.CANONICAL_LF_TEXT_ARTIFACTS))
def test_equivalent_lone_cr_text_passes(tmp_path, name):
    _copy_calibration(tmp_path)
    target = tmp_path / name
    target.write_bytes(target.read_bytes().replace(b"\n", b"\r"))
    _verify_fixture(tmp_path)


def test_crlf_canonicalization_does_not_create_crcrlf():
    name = "m9a_3_attempt_3_report.json"
    assert m9b._canonical_provenance_bytes(name, b"a\r\nb\rc\n") == b"a\nb\nc\n"


@pytest.mark.parametrize("mutation", [
    lambda raw: raw.replace(b'"status": "NOT_RUN"', b'"status": "READY"', 1),
    lambda raw: raw.replace(b'  "attempt_provenance"', b'   "attempt_provenance"', 1),
])
def test_changed_text_or_non_newline_whitespace_fails(tmp_path, mutation):
    _copy_calibration(tmp_path)
    target = tmp_path / "m9a_3_attempt_3_preregistration.json"
    changed = mutation(target.read_bytes())
    assert json.loads(changed)
    target.write_bytes(changed)
    with pytest.raises(RuntimeError, match="provenance mismatch"):
        _verify_fixture(tmp_path)


def test_changed_binary_bytes_fail(tmp_path):
    target = tmp_path / "raw.npz"
    target.write_bytes(b"immutable binary")
    assert m9b._exact_file_identity(target, 16,
        "c45a85f54ff5f95113bf9708107595a28429ae00bff84cd6395b11878411273d")
    target.write_bytes(b"immutable binarz")
    assert not m9b._exact_file_identity(target, 16,
        "c45a85f54ff5f95113bf9708107595a28429ae00bff84cd6395b11878411273d")


def test_wrong_binary_size_fails(tmp_path):
    target = tmp_path / "raw.npz"
    target.write_bytes(b"immutable binary ")
    assert not m9b._exact_file_identity(target, 16,
        "c45a85f54ff5f95113bf9708107595a28429ae00bff84cd6395b11878411273d")


def test_unknown_provenance_artifact_fails_closed():
    with pytest.raises(RuntimeError, match="unclassified"):
        m9b._canonical_provenance_bytes("unknown.json", b"{}\n")


def test_all_expected_provenance_artifacts_are_exhaustively_classified():
    text = m9b.CANONICAL_LF_TEXT_ARTIFACTS
    binary = m9b.EXACT_BYTE_BINARY_ARTIFACTS
    assert text | binary == set(m9b.CALIBRATION_FILES)
    assert not text & binary


def test_integer_force_schedule_and_factorial_equality():
    expected = set(range(5000, 5200))
    for condition in m9b.CONDITIONS:
        active = {i for i in range(m9b.PHYSICS_TRANSITIONS)
                  if any(m9b.force_at_transition(condition, i))}
        assert active == (expected if condition in m9b.PERTURBED else set())
    assert [m9b.force_at_transition("A_P", i) for i in range(15000)] == [
        m9b.force_at_transition("B_P", i) for i in range(15000)]
    assert all(m9b.force_at_transition("A_P", i) == (0.0, 1.024, 0.0) for i in expected)
    assert all(m9b.force_at_transition(c, i) == (0.0, 0.0, 0.0)
               for c in ("A_C", "B_C") for i in range(15000))
    with pytest.raises(ValueError): m9b.force_at_transition("A_P", 5000.0)


def test_exact_frozen_interfaces_and_no_contact_mapping():
    p = m9b.protocol()
    assert tuple((x["name"], x["action_index"], x["coordinate_sign"])
                 for x in p["admitted_motor_interfaces"]) == m9b.MOTOR_INTERFACES
    assert len(m9b.MOTOR_INTERFACES) == 11
    assert tuple(p["admitted_sensory_interfaces"]) == m9b.SENSORY_INTERFACES
    assert len(m9b.SENSORY_INTERFACES) == 6 and p["contact_is_neural_input"] is False


def test_disabled_gate_only_zeros_physical_contribution():
    values = {name: i + .25 for i, name in enumerate(m9b.m7d.ADMITTED_MOTOR)}
    assert m9b.gate_contributions(values, "A_P", tuple(values)) == values
    assert set(m9b.gate_contributions(values, "B_P", tuple(values)).values()) == {0.0}
    d = m9b.protocol()["disabled_control"]
    assert all(d[k] for k in ("pre_zero_decoder_computed", "brain_active", "sensory_active",
                              "neural_updates_active", "observer_active", "decoder_active"))


def test_initialization_assistance_decoder_and_telemetry_are_frozen():
    p = m9b.protocol(); init = p["physical_initialization"]
    assert init == m9b.m7d.protocol()["physical_initialization"]
    assert init["spawn_pos"] == [0.0, 0.0, 0.6045752232266313]
    assert init["spawn_orientation"] == [0.0, 0.0, 0.0]
    assert init["settling_transitions"] == 0 and init["adhesion_enabled"] is False
    assert not any(p["hidden_assistance"].values())
    assert p["decoder_semantics"].startswith("exact frozen M7D/M8")
    physical, neural = p["telemetry"]["physics"], p["telemetry"]["neural"]
    assert len(physical) == 13 and len(neural) == 9
    assert "external_force_vector" in physical and "disabled_pre_zero_motor_vector" in neural


def test_exclusive_output_protection_and_conservative_classifications(tmp_path, monkeypatch):
    monkeypatch.setattr(m9b, "RAW_PATH", tmp_path / "raw")
    monkeypatch.setattr(m9b, "REPORT_PATH", tmp_path / "report")
    monkeypatch.setattr(m9b, "MANIFEST_PATH", tmp_path / "manifest")
    assert m9b.output_available()
    m9b.RAW_PATH.touch(); assert not m9b.output_available()
    assert m9b.CLASSIFICATIONS == (
        "M9B_COMPLETE_NO_DETECTABLE_NEURAL_MOTOR_EFFECT_UNDER_PERTURBATION",
        "M9B_NEURAL_MOTOR_CAUSALLY_ALTERS_TRAJECTORY_UNDER_PERTURBATION",
        "M9B_PERTURBATION_RESPONSE_DEPENDS_ON_NEURAL_MOTOR_ENABLEMENT")
    assert not any(any(word in x for word in ("BALANCE", "STABILIZATION", "RIGHTING", "NATURAL_RECOVERY"))
                   for x in m9b.CLASSIFICATIONS)


def test_checked_in_preregistration_matches_code():
    recorded = json.loads(m9b.PREREGISTRATION_PATH.read_text(encoding="utf-8"))
    assert recorded == m9b.protocol()
    m9b.validate_protocol(recorded)
