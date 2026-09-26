from malecns_backend.embodiment.motor_population_inventory import ADMITTED, ATTEMPT4, generate, serialized


def test_inventory_is_deterministic_and_counts_authoritative_memberships():
    first, second = generate(), generate()
    assert serialized(first) == serialized(second)
    assert first["summary"]["motor_population_count"] == 102
    assert first["summary"]["neuron_membership_count"] == 328
    assert first["summary"]["unique_neuron_id_count"] == 328


def test_physical_order_candidates_and_ambiguity_are_preserved():
    data = generate()
    joints = data["physical_joint_inventory"]
    assert len(joints) == 42
    assert [x["action_index"] for x in joints] == list(range(42))
    assert all(x["joint_name"].startswith("joint_") for x in joints)
    assert data["summary"]["hinges_with_candidates"] == 38
    assert data["summary"]["unique_physical_mappings"] == 26
    assert data["summary"]["ambiguous_physical_mappings"] == 12


def test_admitted_and_attempt4_identities_are_exact():
    data = generate()
    assert [(x["joint"], x["action_index"], x["coordinate_sign"]) for x in data["admitted_11_inventory"]] == list(ADMITTED)
    assert [(x["joint"], x["action_index"], x["coordinate_sign"]) for x in data["attempt4_candidates"]] == list(ATTEMPT4)
    assert len(data["admitted_11_inventory"]) == 11
    assert not any(x["joint"] in {a[0] for a in ATTEMPT4} for x in data["admitted_11_inventory"])


def test_no_sign_is_guessed_and_coxa_yaw_is_complete():
    data = generate()
    established = {x[0] for x in ADMITTED + ATTEMPT4}
    assert all(x["mechanically_validated_coordinate_sign"] is None
               for x in data["physical_joint_inventory"] if x["joint_name"] not in established)
    assert len(data["coxa_yaw_audit"]) == 6
    assert all(x["coordinate_sign"] is None and len(x["annotation_names"]) == 2
               for x in data["coxa_yaw_audit"])


def test_surveyability_is_dense_index_backed_and_consistent():
    data = generate()
    assert sum(data["summary"]["surveyability_counts"].values()) == 102
    assert all(p["dense_neural_indices"] and len(p["dense_neural_indices"]) == p["neuron_count"]
               for p in data["population_inventory"])
    assert not any(p["surveyability"] == "NOT_CURRENTLY_SURVEYABLE" for p in data["population_inventory"])
