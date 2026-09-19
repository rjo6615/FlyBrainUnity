from malecns_backend.embodiment.instrumented_closed_loop_prefix_diagnostic import reconstruct_guard


def test_exact_guard_first_failure_is_strict_c3_c4_order():
    report = {"milestones": {"C3": 13.5, "C4": 13.5, "C6": 13.6, "C7": 13.6,
        "C8": 14.0, "C10": 22.0, "C11": 24.0},
        "pre_intervention_equivalence": {"passed": True}}
    predicates = reconstruct_guard(report)
    failed = [p for p in predicates if not p["result"]]
    assert failed[0] == {"name": "C3 < C4", "left": 13.5, "operator": "<",
                         "right": 13.5, "result": False, "status": "FAIL"}
    assert [p["name"] for p in failed] == ["C3 < C4", "causal_prefix_ordered", "replication_guard_passed"]


def test_missing_milestone_fails_closed_without_comparing_none():
    predicates = reconstruct_guard({"milestones": {}, "pre_intervention_equivalence": {"passed": True}})
    assert predicates[0]["result"] is False
    assert predicates[-1]["result"] is False
