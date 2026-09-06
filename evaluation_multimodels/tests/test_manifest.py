from xiaoan_eval.manifest import RunManifest, SuiteCaseBinding, SuiteManifest


def test_manifest_fingerprint_is_stable_and_sensitive_to_configuration() -> None:
    base = RunManifest(
        run_started_at="2026-08-17T03:00:00+08:00",
        product_version="build-1",
        safety_policy_version="safety-1",
        output_guard_version="guard-1",
        prompt_hashes={"router": "abc", "composer": "def"},
        knowledge_versions={"lawwiki": "2026-08-17"},
        model_ids={"router": "router-1", "response": "response-1", "judge": "judge-1"},
        provider_versions={"router": "provider-build-1"},
        hyperparameters={"router.context_turns": 6},
        run_config={"case_concurrency": 1},
        evaluator_version="0.1.0",
        rating_rule_hash="rules-1",
        rating_rule_schema_version="legacy-v1",
        judge_prompt_version="judge-prompt-1",
        seed=101,
        retry_policy={"max_attempts": 2},
    )

    same = RunManifest(**base.to_dict())
    changed = RunManifest(**{**base.to_dict(), "seed": 202})

    assert base.fingerprint == same.fingerprint
    assert base.fingerprint != changed.fingerprint


def test_suite_fingerprint_binds_order_taxonomy_maturity_and_retry_policy():
    binding = SuiteCaseBinding(
        case_id="TC-01", case_digest="abc", expected_turns=(1, 2),
        scenario_id="crisis", coverage_axes={"risk": ("critical",)},
        comparability_group="v1", maturity="REVIEWED",
    )
    suite = SuiteManifest(
        suite_id="canonical", suite_version="1", taxonomy_version="1",
        scoring_contract_version="response-effectiveness/v1", cases=(binding,),
        retry_policy={"max_attempts": 2},
    )
    changed = SuiteManifest(
        **{**suite.to_dict(), "cases": (SuiteCaseBinding(**{**binding.to_dict(), "maturity": "APPROVED_AGGREGATE"}),)}
    )

    assert suite.fingerprint != changed.fingerprint
