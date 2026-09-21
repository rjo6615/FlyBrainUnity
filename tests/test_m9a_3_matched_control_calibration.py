"""M9A-3 pure/static contract tests. These execute zero physics transitions."""
from __future__ import annotations

import inspect
import json

import pytest

from malecns_backend.embodiment import m7d_corrected_spontaneous as m7d
from malecns_backend.embodiment import m9a_3_matched_control_calibration as m9a
from malecns_backend.embodiment import _windows_m9a_3_matched_control_adapter as live


def test_preregistration_and_candidate_ladder_are_frozen():
    p=m9a.protocol(); frozen=json.loads(m9a.PREREGISTRATION_PATH.read_text())
    assert p == frozen and p["status"] == "NOT_RUN" and p["experiment_namespace"] == "M9A-3"
    assert m9a.CANDIDATE_FORCE_NATIVE == (.256,.512,1.024,2.048)
    assert all(b/a == 2 for a,b in zip(m9a.CANDIDATE_FORCE_NATIVE,m9a.CANDIDATE_FORCE_NATIVE[1:]))
    assert m9a.OUTPUT_DIR.name == "m9a_3_matched_control_calibration"


def test_historical_evidence_byte_size_and_sha256_are_frozen():
    m9a.verify_historical_evidence()
    assert len(m9a.HISTORICAL) == 12


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
