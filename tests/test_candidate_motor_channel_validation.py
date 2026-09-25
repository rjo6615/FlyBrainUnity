from malecns_backend.embodiment import candidate_motor_channel_validation as audit


def test_identity_decoder_and_fail_closed_preregistration():
    result = audit.build()
    assert result["identity_validation_passed"] is True
    assert result["decoder_validation_passed"] is True
    assert result["mechanical_validation_passed"] is False
    assert result["preregistration_created"] is False
    assert set(result["candidate_channels"]) == set(audit.CANDIDATES)


def test_engineered_vectors_are_isolated_and_means_not_sums():
    for name, index in audit.CANDIDATES.items():
        check = audit.engineered_checks(name, index)
        assert check["passed"] is True
        assert check["population_mean_invariance_hz"] == [34.0, 34.0]
        for case in check["cases"].values():
            assert case["nonzero_action_indices"] in ([], [index])
