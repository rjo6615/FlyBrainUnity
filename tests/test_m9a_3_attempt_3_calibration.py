"""Attempt-3 static/synthetic tests: no scientific simulation is executed."""
import inspect, json
import pytest
from malecns_backend.embodiment import m9a_3_attempt_3_calibration as m
from malecns_backend.embodiment import _windows_m9a_3_attempt_3_adapter as live


def row(mag, **changes):
    value={"magnitude_native":mag,"contact_pattern_diverged":False,"max_root_position_divergence_mm":.005,
      "max_orientation_divergence_deg":0.,"max_distal_tarsus_divergence_mm":0.,"max_continuous_divergence":.005,
      "finite_both":True,"catastrophic_through_750ms":False,"max_root_linear_velocity_divergence":5.,
      "max_absolute_root_displacement_mm":1.5,"max_absolute_tilt_deg":60.,"post_force_observation_ms":980.,
      "max_absolute_root_linear_speed_descriptive_only":100.}
    value.update(changes); return value


def rows(**changes): return [row(x,**changes) for x in m.CANDIDATE_FORCE_NATIVE]


def test_isolated_not_run_preregistration_and_frozen_protocol():
    p=m.protocol(); assert p==json.loads(m.PREREGISTRATION_PATH.read_text())
    assert (p["schema"].endswith(".3") and p["status"]=="NOT_RUN" and p["experiment_namespace"]=="M9A-3-Attempt-3")
    assert m.OUTPUT_DIR.name.endswith("attempt_3") and m.OUTPUT_DIR not in (m.ATTEMPT_1_DIR,m.ATTEMPT_2_DIR)
    assert m.CANDIDATE_FORCE_NATIVE==(.256,.512,1.024,2.048)
    assert (m.DT_MS,m.TRANSITIONS,m.STATES,m.START_MS,m.STOP_MS,m.OBSERVE_MS)==(.1,15000,15001,500.,520.,1500.)
    assert p["attempt_2_rationale"]["production_result"]=="NO_PREREGISTERED_CANDIDATE_QUALIFIES"


def test_index_force_schedule_and_control_zero():
    for condition in ("P","C"):
        active=[i for i in range(m.TRANSITIONS) if m.force_at(i*m.DT_MS,.256,condition)!=(0.,0.,0.)]
        assert active==(list(range(5000,5200)) if condition=="P" else [])


def test_baseline_speed_descriptive_only_and_safety_failures():
    assert m.choose_candidate(rows(max_absolute_root_linear_speed_descriptive_only=1000.))==.256
    for change in ({"max_root_linear_velocity_divergence":5.00001},{"catastrophic_through_750ms":True},
                   {"max_absolute_root_displacement_mm":1.50001},{"max_absolute_tilt_deg":60.00001}):
        assert m.choose_candidate(rows(**change)) == m.NO_SELECTION
    source=inspect.getsource(live._reduce_pair)
    assert 'linear_velocity\"])>10' not in source and 'baseline_characterization' in source


def test_meaningfulness_boundaries_and_lowest_selection():
    assert m.choose_candidate(rows(max_root_position_divergence_mm=.005))==.256
    assert m.choose_candidate(rows(max_root_position_divergence_mm=0.,max_orientation_divergence_deg=.25))==.256
    assert m.choose_candidate(rows(max_root_position_divergence_mm=0.,max_distal_tarsus_divergence_mm=.01))==.256
    assert m.choose_candidate(rows(max_root_position_divergence_mm=0.,contact_pattern_diverged=True))==.256
    candidates=rows(max_root_position_divergence_mm=.004,max_continuous_divergence=.004); candidates[2]=row(1.024)
    assert m.choose_candidate(candidates)==1.024
    assert m.choose_candidate(rows(max_root_position_divergence_mm=.004,max_continuous_divergence=.004)) == m.NO_SELECTION


def test_exact_pre_force_and_integrity_are_fail_closed_in_reducer():
    source=inspect.getsource(live._reduce_pair)
    assert "np.array_equal(p[k][pre], c[k][pre])" in source
    audit=inspect.getsource(live._audit_pair_schedule)
    for requirement in ("frozen state count","P/C timestamps differ","clock/cadence mismatch","recorded P/C force schedule mismatch"):
        assert requirement in audit


def test_historical_provenance_and_no_retrospective_scoring():
    m.verify_historical_evidence()
    assert sum(k.startswith("attempt2/candidate_") for k in m.HISTORICAL)==8
    assert "attempt2/m9a_3_attempt_2_preregistration.json" in m.HISTORICAL
    assert "attempt2_forensics/m9a_3_attempt_2_postrun_forensics.json" in m.HISTORICAL
    assert "ATTEMPT_2_DIR" not in inspect.getsource(m.choose_candidate)


def test_import_tests_and_preflight_contract_are_zero_transition_and_neural_free():
    module_source=inspect.getsource(live); preflight=inspect.getsource(live.windows_preflight)
    assert "MaleCNS" not in module_source and "sim.step(" not in preflight
    assert '"physics_transitions":0' in preflight and '"neural_transitions":0' in preflight
    assert "output_namespace_scientific_evidence_absent" in preflight
    assert "os.O_EXCL" in module_source
