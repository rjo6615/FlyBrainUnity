"""M9A-3 pure/static contract tests. These execute zero physics transitions."""
from __future__ import annotations

import hashlib
import inspect
import json

import pytest

from malecns_backend.embodiment import m7d_corrected_spontaneous as m7d
from malecns_backend.embodiment import m9a_3_matched_control_calibration as m9a
from malecns_backend.embodiment import _windows_m9a_3_matched_control_adapter as live


def test_preregistration_and_candidate_ladder_are_frozen():
    p=m9a.protocol(); frozen=json.loads(m9a.PREREGISTRATION_PATH.read_text())
    assert p == frozen and p["status"] == "NOT_RUN" and p["experiment_namespace"] == "M9A-3-Attempt-2"
    assert m9a.CANDIDATE_FORCE_NATIVE == (.256,.512,1.024,2.048)
    assert all(b/a == 2 for a,b in zip(m9a.CANDIDATE_FORCE_NATIVE,m9a.CANDIDATE_FORCE_NATIVE[1:]))
    assert m9a.OUTPUT_DIR.name == "m9a_3_matched_control_calibration_attempt_2"
    assert m9a.OUTPUT_DIR != m9a.ATTEMPT_1_DIR
    assert p["attempt_provenance"]["scientific_protocol_change_from_predecessor"] is False
    attempt_1 = json.loads((m9a.ATTEMPT_1_DIR / "m9a_3_preregistration.json").read_text())
    for identity_key in ("schema", "experiment_namespace"):
        attempt_1.pop(identity_key)
    attempt_2_science = dict(p)
    for identity_key in ("schema", "experiment_namespace", "attempt_provenance"):
        attempt_2_science.pop(identity_key)
    assert attempt_2_science == attempt_1


def test_historical_evidence_byte_size_and_sha256_are_frozen():
    m9a.verify_historical_evidence()
    assert len(m9a.HISTORICAL) == 14


@pytest.mark.parametrize(("key", "frozen_size"), (
    ("m9a/m9a_preregistration.json", 5386),
    ("m9a_2/m9a_2_preregistration.json", 4877),
    ("forensics/README.md", 1235),
    ("forensics/m9a_2_postrun_forensics.py", 12776),
))
def test_text_evidence_lf_and_crlf_have_one_canonical_identity(tmp_path, key, frozen_size):
    expected_size, expected_digest = m9a.HISTORICAL[key]
    lf = m9a._canonical_historical_bytes(key, m9a._historical_path(key).read_bytes())
    crlf = lf.replace(b"\n", b"\r\n")
    assert len(lf) == expected_size == frozen_size
    assert hashlib.sha256(lf).hexdigest() == expected_digest
    assert m9a._canonical_historical_bytes(key, lf) == lf
    assert m9a._canonical_historical_bytes(key, crlf) == lf
    for name, data in (("lf.txt", lf), ("crlf.txt", crlf)):
        path = tmp_path / name; path.write_bytes(data)
        m9a._verify_historical_file(key, path, expected_size, expected_digest)


def test_canonical_text_mutation_and_bare_carriage_return_fail(tmp_path):
    key = "m9a/m9a_preregistration.json"
    size, digest = m9a.HISTORICAL[key]
    original = m9a._canonical_historical_bytes(key, m9a._historical_path(key).read_bytes())
    mutated = tmp_path / "mutated.json"
    mutated.write_bytes(original.replace(b'"status": "NOT_RUN"', b'"status": "HAS_RUN"'))
    with pytest.raises(RuntimeError, match="immutable historical evidence mismatch"):
        m9a._verify_historical_file(key, mutated, size, digest)
    stray = tmp_path / "stray.json"; stray.write_bytes(original + b"\r")
    with pytest.raises(RuntimeError, match="invalid historical line endings"):
        m9a._verify_historical_file(key, stray, size, digest)


def test_binary_historical_evidence_remains_exact_bytes(tmp_path):
    key = "m9a/candidate_0.0001_raw.npz"
    path = m9a._historical_path(key)
    size, digest = m9a.HISTORICAL[key]
    m9a._verify_historical_file(key, path, size, digest)
    raw = path.read_bytes()
    assert m9a._canonical_historical_bytes(key, raw) is raw
    changed = tmp_path / "changed.npz"
    changed.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
    with pytest.raises(RuntimeError, match="immutable historical evidence mismatch"):
        m9a._verify_historical_file(key, changed, size, digest)


def test_historical_evidence_policy_is_exhaustive_and_disjoint():
    assert m9a.CANONICAL_LF_TEXT_EVIDENCE | m9a.EXACT_BYTE_BINARY_EVIDENCE == set(m9a.HISTORICAL)
    assert m9a.CANONICAL_LF_TEXT_EVIDENCE & m9a.EXACT_BYTE_BINARY_EVIDENCE == set()
    with pytest.raises(RuntimeError, match="unclassified historical evidence"):
        m9a._canonical_historical_bytes("future/unclassified.txt", b"evidence\n")


def test_protocol_validation_accepts_crlf_historical_checkout(tmp_path, monkeypatch):
    original_path = m9a._historical_path
    windows_paths = {}
    for key in m9a.CANONICAL_LF_TEXT_EVIDENCE:
        lf = m9a._canonical_historical_bytes(key, original_path(key).read_bytes())
        crlf_path = tmp_path / key.replace("/", "_")
        crlf_path.write_bytes(lf.replace(b"\n", b"\r\n"))
        windows_paths[key] = crlf_path
    monkeypatch.setattr(m9a, "_historical_path",
                        lambda candidate: (windows_paths[candidate] if candidate in windows_paths
                                           else original_path(candidate)))
    m9a.validate_protocol(m9a.protocol())


def test_exact_m7d_b4_initialization_is_inherited_and_pair_equivalence_required():
    p=m9a.protocol()
    assert p["physical_initialization"] == m7d.protocol()["physical_initialization"]
    assert p["matched_pair"]["exact_pre_force_equivalence_required"] is True
    assert "np.array_equal" in inspect.getsource(live._reduce_pair)
    m9a.validate_protocol(p)


def test_force_body_direction_window_and_control_zero_are_exact():
    assert m9a.APPLICATION_BODY_SOURCE == "Thorax" and m9a.DIRECTION == (0.,1.,0.)
    for condition in ("P","C"):
        values=[m9a.force_at(i*m9a.DT_MS,.512,condition) for i in range(m9a.TRANSITIONS)]
        active=[i for i,x in enumerate(values) if x != (0.,0.,0.)]
        assert active == (list(range(5000,5200)) if condition == "P" else [])
    assert m9a.force_at(500,.512,"P") == (0.,.512,0.)
    assert m9a.force_at(520,.512,"P") == (0.,0.,0.)


class Model:
    nbody=3
    _bodies=("world","0/Thorax","0/FakeThorax")
    def id2name(self, object_id, kind): return self._bodies[object_id]


def test_authoritative_terminal_component_thorax_resolution():
    assert live._body_identity(Model())["body_id"] == 1
    Model._bodies=("world","0/Thorax","1/Thorax")
    with pytest.raises(RuntimeError,match="uniquely"): live._body_identity(Model())
    Model._bodies=("world","0/FakeThorax","ThoraxExtra")
    with pytest.raises(RuntimeError,match="uniquely"): live._body_identity(Model())


def test_authoritative_contact_resolution_is_required_before_transition():
    source=inspect.getsource(live._run_condition)
    assert 'contact.resolve(physics.model)' in source
    assert 'if not identity["available"]' in source
    assert source.index('if not identity["available"]') < source.index("sim.step(")


def test_no_malecns_neural_or_prohibited_assistance():
    source=inspect.getsource(live)
    assert "MaleCNS" not in source and "malecns_backend import" not in source
    assert m9a.protocol()["male_cns"] == {"constructed":False,"neural_transitions":0}
    assert not any(m9a.protocol()["explicit_absences"].values())
    assert '"adhesion": np.zeros(6)' in source and "commands.copy()" in source


def row(magnitude, **changes):
    x={"magnitude_native":magnitude,"contact_pattern_diverged":False,"max_root_position_divergence_mm":.006,
       "max_orientation_divergence_deg":.1,"max_distal_tarsus_divergence_mm":.001,"max_continuous_divergence":.006,
       "finite_both":True,"catastrophic_through_750ms":False,"max_root_linear_velocity_divergence":1.,
       "max_absolute_root_displacement_mm":1.,"max_absolute_tilt_deg":20.,"max_absolute_root_linear_speed":2.,
       "post_force_observation_ms":980.}
    x.update(changes); return x


def test_selection_is_deterministic_lowest_qualifying_and_has_no_return_gate():
    rows=[row(x) for x in m9a.CANDIDATE_FORCE_NATIVE]
    rows[0]["max_root_position_divergence_mm"]=.004
    assert m9a.choose_candidate(rows) == .512
    assert m9a.protocol()["selection_rule_preregistered"]["passive_return_required"] is False
    rows[1]["catastrophic_through_750ms"]=True
    assert m9a.choose_candidate(rows) == 1.024
    with pytest.raises(RuntimeError): m9a.choose_candidate([row(x,finite_both=False) for x in m9a.CANDIDATE_FORCE_NATIVE])


def test_preflight_is_zero_transition_and_m9b_has_no_route():
    preflight=inspect.getsource(live.windows_preflight)
    assert "sim.step(" not in preflight
    main=inspect.getsource(m9a.main)
    assert main.count("modes.add_argument") == 2 and "m9b" not in main.lower()
    with pytest.raises(SystemExit): m9a.main(["--run-m9b"])


def test_exclusive_creation_and_separate_pc_raw_files():
    source=inspect.getsource(live)
    assert "os.O_EXCL" in source and 'for condition in ("P","C")' in source
    assert 'candidate_{magnitude:.6f}_{condition}_raw.npz' in source


def test_attempt_1_provenance_and_raw_schedule_regression_are_read_only():
    """Audit only: this deliberately does not call the scientific reducer."""
    np = pytest.importorskip("numpy")
    provenance = json.loads((m9a.ATTEMPT_1_DIR / "m9a_3_attempt_1_provenance.json").read_text())
    assert provenance["disposition"] == "INCOMPLETE_EXECUTION"
    assert provenance["execution"] == {
        "candidate_selected": False, "candidates_started": [0.256],
        "condition_order": ["P", "C"], "failure_location": "_reduce_pair()",
        "later_candidates_executed": False, "reduction_completed": False,
    }
    loaded = {}
    for record in provenance["raw_files"]:
        path = m9a.ATTEMPT_1_DIR / record["path"]
        raw = path.read_bytes()
        assert len(raw) == record["byte_size"]
        assert hashlib.sha256(raw).hexdigest() == record["sha256"]
        with np.load(path) as archive:
            loaded[record["path"].split("_")[-2]] = {key: archive[key] for key in archive.files}
    p, c = loaded["P"], loaded["C"]
    assert live._audit_pair_schedule(np, p, c, .256) == (5000, 5200)
    assert np.flatnonzero(np.any(p["applied_force"] != 0, axis=1)).tolist() == list(range(5000, 5200))
    assert not np.any(c["applied_force"])
    different = np.zeros(m9a.STATES, dtype=bool)
    for key in ("root_position", "orientation_wxyz", "body_up_z", "linear_velocity",
                "angular_velocity", "ground_contact", "distal_tarsus_positions"):
        delta = p[key] != c[key]
        different |= delta if delta.ndim == 1 else np.any(delta.reshape((m9a.STATES, -1)), axis=1)
    assert np.flatnonzero(different)[0] == 5001
    assert p["time_ms"][5000] < 500.0 and p["time_ms"][5200] < 520.0


def test_index_schedule_ignores_synthetic_accumulated_boundary_drift():
    np = pytest.importorskip("numpy")
    times = np.arange(m9a.STATES, dtype=float) * m9a.DT_MS
    times[5000] = np.nextafter(500.0, -np.inf)
    times[5200] = np.nextafter(520.0, -np.inf)
    expected_p = np.asarray([m9a.force_at(i * m9a.DT_MS, .512, "P") for i in range(m9a.STATES)])
    expected_c = np.asarray([m9a.force_at(i * m9a.DT_MS, .512, "C") for i in range(m9a.STATES)])
    p = {"time_ms": times, "applied_force": expected_p}
    c = {"time_ms": times.copy(), "applied_force": expected_c}
    assert live._audit_pair_schedule(np, p, c, .512) == (5000, 5200)
    assert np.flatnonzero(np.any(expected_p != 0, axis=1)).tolist() == list(range(5000, 5200))
