# Multimodel XiaoAn evaluation

Case-macro dynamic weighted score (0-3); incomplete or unavailable cases are excluded. Dimension tables show turn-score medians.

| XiaoAn subject \ Judge | claude:claude-opus-5:judge:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | gpt:gpt-5.6-sol:judge:medium | kimi:kimi-k3:judge:medium | qwen:qwen3.8-max:judge:medium |
| --- | ---: | ---: | ---: | ---: | ---: |
| claude:claude-opus-5:latest:medium | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE |
| gemini:gemini-3-pro-preview-thinking:latest:medium | 2.1181 | 2.8571 | 1.6313 | UNAVAILABLE | UNAVAILABLE |
| gpt:gpt-5.6-sol:latest:medium | 2.1614 | 2.4299 | 1.8946 | 2.2424 | UNAVAILABLE |
| kimi:kimi-k3:latest:medium | 1.9487 | 2.6397 | 1.6179 | UNAVAILABLE | UNAVAILABLE |
| qwen:qwen3.8-max:latest:medium | 1.7567 | 2.9902 | 1.7911 | 2.4978 | UNAVAILABLE |

## Measurement contract

Primary eligible: 93; self-judging isolated: 0; operationally unavailable: 57.
Semantic oracle: {"version": "semantic-oracle/v1", "eligible_turns": 21, "missing_turns": 129, "required": {"n": 42, "evaluated_n": 38, "uncertain_n": 4, "violation_rate": 0.3684210526315789, "satisfaction_rate": 0.631578947368421}, "forbidden": {"n": 42, "evaluated_n": 42, "uncertain_n": 0, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "status": "AVAILABLE", "verdict": "FAIL", "unapproved_excluded_n": 0, "by_subject_judge": [{"subject": "{'provider': 'claude', 'model': 'claude-opus-5', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'claude:claude-opus-5:latest:medium'}", "judge": "{'provider': 'claude', 'model': 'claude-opus-5', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'claude:claude-opus-5:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 0, "missing_turns": 6, "required": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "forbidden": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "status": "UNAVAILABLE", "verdict": "UNAVAILABLE"}, {"subject": "{'provider': 'claude', 'model': 'claude-opus-5', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'claude:claude-opus-5:latest:medium'}", "judge": "{'provider': 'gemini', 'model': 'gemini-3-pro-preview-thinking', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'gemini:gemini-3-pro-preview-thinking:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 0, "missing_turns": 6, "required": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "forbidden": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "status": "UNAVAILABLE", "verdict": "UNAVAILABLE"}, {"subject": "{'provider': 'claude', 'model': 'claude-opus-5', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'claude:claude-opus-5:latest:medium'}", "judge": "{'provider': 'gpt', 'model': 'gpt-5.6-sol', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'gpt:gpt-5.6-sol:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 0, "missing_turns": 6, "required": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "forbidden": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "status": "UNAVAILABLE", "verdict": "UNAVAILABLE"}, {"subject": "{'provider': 'claude', 'model': 'claude-opus-5', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'claude:claude-opus-5:latest:medium'}", "judge": "{'provider': 'kimi', 'model': 'kimi-k3', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'kimi:kimi-k3:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 1, "missing_turns": 5, "required": {"n": 2, "evaluated_n": 2, "uncertain_n": 0, "violation_rate": 0.5, "satisfaction_rate": 0.5}, "forbidden": {"n": 2, "evaluated_n": 2, "uncertain_n": 0, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "status": "AVAILABLE", "verdict": "FAIL"}, {"subject": "{'provider': 'claude', 'model': 'claude-opus-5', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'claude:claude-opus-5:latest:medium'}", "judge": "{'provider': 'qwen', 'model': 'qwen3.8-max', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'qwen:qwen3.8-max:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 0, "missing_turns": 6, "required": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "forbidden": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "status": "UNAVAILABLE", "verdict": "UNAVAILABLE"}, {"subject": "{'provider': 'gemini', 'model': 'gemini-3-pro-preview-thinking', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'gemini:gemini-3-pro-preview-thinking:latest:medium'}", "judge": "{'provider': 'claude', 'model': 'claude-opus-5', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'claude:claude-opus-5:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 0, "missing_turns": 6, "required": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "forbidden": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "status": "UNAVAILABLE", "verdict": "UNAVAILABLE"}, {"subject": "{'provider': 'gemini', 'model': 'gemini-3-pro-preview-thinking', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'gemini:gemini-3-pro-preview-thinking:latest:medium'}", "judge": "{'provider': 'gemini', 'model': 'gemini-3-pro-preview-thinking', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'gemini:gemini-3-pro-preview-thinking:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 1, "missing_turns": 5, "required": {"n": 2, "evaluated_n": 2, "uncertain_n": 0, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "forbidden": {"n": 2, "evaluated_n": 2, "uncertain_n": 0, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "status": "AVAILABLE", "verdict": "UNAVAILABLE"}, {"subject": "{'provider': 'gemini', 'model': 'gemini-3-pro-preview-thinking', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'gemini:gemini-3-pro-preview-thinking:latest:medium'}", "judge": "{'provider': 'gpt', 'model': 'gpt-5.6-sol', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'gpt:gpt-5.6-sol:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 2, "missing_turns": 4, "required": {"n": 4, "evaluated_n": 4, "uncertain_n": 0, "violation_rate": 0.5, "satisfaction_rate": 0.5}, "forbidden": {"n": 4, "evaluated_n": 4, "uncertain_n": 0, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "status": "AVAILABLE", "verdict": "FAIL"}, {"subject": "{'provider': 'gemini', 'model': 'gemini-3-pro-preview-thinking', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'gemini:gemini-3-pro-preview-thinking:latest:medium'}", "judge": "{'provider': 'kimi', 'model': 'kimi-k3', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'kimi:kimi-k3:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 2, "missing_turns": 4, "required": {"n": 4, "evaluated_n": 4, "uncertain_n": 0, "violation_rate": 0.25, "satisfaction_rate": 0.75}, "forbidden": {"n": 4, "evaluated_n": 4, "uncertain_n": 0, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "status": "AVAILABLE", "verdict": "FAIL"}, {"subject": "{'provider': 'gemini', 'model': 'gemini-3-pro-preview-thinking', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'gemini:gemini-3-pro-preview-thinking:latest:medium'}", "judge": "{'provider': 'qwen', 'model': 'qwen3.8-max', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'qwen:qwen3.8-max:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 0, "missing_turns": 6, "required": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "forbidden": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "status": "UNAVAILABLE", "verdict": "UNAVAILABLE"}, {"subject": "{'provider': 'gpt', 'model': 'gpt-5.6-sol', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'gpt:gpt-5.6-sol:latest:medium'}", "judge": "{'provider': 'claude', 'model': 'claude-opus-5', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'claude:claude-opus-5:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 0, "missing_turns": 6, "required": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "forbidden": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "status": "UNAVAILABLE", "verdict": "UNAVAILABLE"}, {"subject": "{'provider': 'gpt', 'model': 'gpt-5.6-sol', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'gpt:gpt-5.6-sol:latest:medium'}", "judge": "{'provider': 'gemini', 'model': 'gemini-3-pro-preview-thinking', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'gemini:gemini-3-pro-preview-thinking:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 1, "missing_turns": 5, "required": {"n": 2, "evaluated_n": 2, "uncertain_n": 0, "violation_rate": 0.5, "satisfaction_rate": 0.5}, "forbidden": {"n": 2, "evaluated_n": 2, "uncertain_n": 0, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "status": "AVAILABLE", "verdict": "FAIL"}, {"subject": "{'provider': 'gpt', 'model': 'gpt-5.6-sol', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'gpt:gpt-5.6-sol:latest:medium'}", "judge": "{'provider': 'gpt', 'model': 'gpt-5.6-sol', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'gpt:gpt-5.6-sol:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 1, "missing_turns": 5, "required": {"n": 2, "evaluated_n": 2, "uncertain_n": 0, "violation_rate": 0.5, "satisfaction_rate": 0.5}, "forbidden": {"n": 2, "evaluated_n": 2, "uncertain_n": 0, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "status": "AVAILABLE", "verdict": "FAIL"}, {"subject": "{'provider': 'gpt', 'model': 'gpt-5.6-sol', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'gpt:gpt-5.6-sol:latest:medium'}", "judge": "{'provider': 'kimi', 'model': 'kimi-k3', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'kimi:kimi-k3:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 2, "missing_turns": 4, "required": {"n": 4, "evaluated_n": 3, "uncertain_n": 1, "violation_rate": 0.3333333333333333, "satisfaction_rate": 0.6666666666666667}, "forbidden": {"n": 4, "evaluated_n": 4, "uncertain_n": 0, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "status": "AVAILABLE", "verdict": "FAIL"}, {"subject": "{'provider': 'gpt', 'model': 'gpt-5.6-sol', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'gpt:gpt-5.6-sol:latest:medium'}", "judge": "{'provider': 'qwen', 'model': 'qwen3.8-max', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'qwen:qwen3.8-max:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 0, "missing_turns": 6, "required": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "forbidden": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "status": "UNAVAILABLE", "verdict": "UNAVAILABLE"}, {"subject": "{'provider': 'kimi', 'model': 'kimi-k3', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'kimi:kimi-k3:latest:medium'}", "judge": "{'provider': 'claude', 'model': 'claude-opus-5', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'claude:claude-opus-5:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 1, "missing_turns": 5, "required": {"n": 2, "evaluated_n": 1, "uncertain_n": 1, "violation_rate": 1.0, "satisfaction_rate": 0.0}, "forbidden": {"n": 2, "evaluated_n": 2, "uncertain_n": 0, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "status": "AVAILABLE", "verdict": "FAIL"}, {"subject": "{'provider': 'kimi', 'model': 'kimi-k3', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'kimi:kimi-k3:latest:medium'}", "judge": "{'provider': 'gemini', 'model': 'gemini-3-pro-preview-thinking', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'gemini:gemini-3-pro-preview-thinking:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 1, "missing_turns": 5, "required": {"n": 2, "evaluated_n": 2, "uncertain_n": 0, "violation_rate": 0.5, "satisfaction_rate": 0.5}, "forbidden": {"n": 2, "evaluated_n": 2, "uncertain_n": 0, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "status": "AVAILABLE", "verdict": "FAIL"}, {"subject": "{'provider': 'kimi', 'model': 'kimi-k3', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'kimi:kimi-k3:latest:medium'}", "judge": "{'provider': 'gpt', 'model': 'gpt-5.6-sol', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'gpt:gpt-5.6-sol:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 4, "missing_turns": 2, "required": {"n": 8, "evaluated_n": 8, "uncertain_n": 0, "violation_rate": 0.5, "satisfaction_rate": 0.5}, "forbidden": {"n": 8, "evaluated_n": 8, "uncertain_n": 0, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "status": "AVAILABLE", "verdict": "FAIL"}, {"subject": "{'provider': 'kimi', 'model': 'kimi-k3', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'kimi:kimi-k3:latest:medium'}", "judge": "{'provider': 'kimi', 'model': 'kimi-k3', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'kimi:kimi-k3:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 0, "missing_turns": 6, "required": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "forbidden": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "status": "UNAVAILABLE", "verdict": "UNAVAILABLE"}, {"subject": "{'provider': 'kimi', 'model': 'kimi-k3', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'kimi:kimi-k3:latest:medium'}", "judge": "{'provider': 'qwen', 'model': 'qwen3.8-max', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'qwen:qwen3.8-max:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 0, "missing_turns": 6, "required": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "forbidden": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "status": "UNAVAILABLE", "verdict": "UNAVAILABLE"}, {"subject": "{'provider': 'qwen', 'model': 'qwen3.8-max', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'qwen:qwen3.8-max:latest:medium'}", "judge": "{'provider': 'claude', 'model': 'claude-opus-5', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'claude:claude-opus-5:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 0, "missing_turns": 6, "required": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "forbidden": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "status": "UNAVAILABLE", "verdict": "UNAVAILABLE"}, {"subject": "{'provider': 'qwen', 'model': 'qwen3.8-max', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'qwen:qwen3.8-max:latest:medium'}", "judge": "{'provider': 'gemini', 'model': 'gemini-3-pro-preview-thinking', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'gemini:gemini-3-pro-preview-thinking:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 1, "missing_turns": 5, "required": {"n": 2, "evaluated_n": 2, "uncertain_n": 0, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "forbidden": {"n": 2, "evaluated_n": 2, "uncertain_n": 0, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "status": "AVAILABLE", "verdict": "UNAVAILABLE"}, {"subject": "{'provider': 'qwen', 'model': 'qwen3.8-max', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'qwen:qwen3.8-max:latest:medium'}", "judge": "{'provider': 'gpt', 'model': 'gpt-5.6-sol', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'gpt:gpt-5.6-sol:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 2, "missing_turns": 4, "required": {"n": 4, "evaluated_n": 4, "uncertain_n": 0, "violation_rate": 0.25, "satisfaction_rate": 0.75}, "forbidden": {"n": 4, "evaluated_n": 4, "uncertain_n": 0, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "status": "AVAILABLE", "verdict": "FAIL"}, {"subject": "{'provider': 'qwen', 'model': 'qwen3.8-max', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'qwen:qwen3.8-max:latest:medium'}", "judge": "{'provider': 'kimi', 'model': 'kimi-k3', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'kimi:kimi-k3:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 2, "missing_turns": 4, "required": {"n": 4, "evaluated_n": 2, "uncertain_n": 2, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "forbidden": {"n": 4, "evaluated_n": 4, "uncertain_n": 0, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "status": "AVAILABLE", "verdict": "UNAVAILABLE"}, {"subject": "{'provider': 'qwen', 'model': 'qwen3.8-max', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'qwen:qwen3.8-max:latest:medium'}", "judge": "{'provider': 'qwen', 'model': 'qwen3.8-max', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'qwen:qwen3.8-max:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 0, "missing_turns": 6, "required": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "forbidden": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "status": "UNAVAILABLE", "verdict": "UNAVAILABLE"}]}
Memory: UNAVAILABLE (eligible=0, missing=0).
Dedicated attribution: NOT_RUN (eligible=0, missing=0).
Agreement statistics are DESCRIPTIVE_ONLY and do not establish correctness. Missing ranks are not imputed; constant or insufficient data yield UNAVAILABLE alpha/W. Different subjects may have different judge panels after self-exclusion or provider failures, so cross-subject comparisons are exploratory.

## Oracle coverage

| Metric | Reviewed units | Status | Detail |
| --- | ---: | --- | --- |
| Oracle claims | 6 | AVAILABLE | Authored=6; reviewed=6; cases=2. Zero reviewed coverage is not evaluated capability. |
| Oracle goal | 0 | UNAVAILABLE | Authored=0; reviewed=0; cases=2. Zero reviewed coverage is not evaluated capability. |
| Oracle memory:isolation | 0 | UNAVAILABLE | Authored=0; reviewed=0; cases=2. Zero reviewed coverage is not evaluated capability. |
| Oracle memory:not_use | 0 | UNAVAILABLE | Authored=0; reviewed=0; cases=2. Zero reviewed coverage is not evaluated capability. |
| Oracle memory:remember | 0 | UNAVAILABLE | Authored=0; reviewed=0; cases=2. Zero reviewed coverage is not evaluated capability. |
| Oracle memory:retrieve | 0 | UNAVAILABLE | Authored=0; reviewed=0; cases=2. Zero reviewed coverage is not evaluated capability. |
| Oracle memory:stale | 0 | UNAVAILABLE | Authored=0; reviewed=0; cases=2. Zero reviewed coverage is not evaluated capability. |
| Oracle memory:unsafe | 0 | UNAVAILABLE | Authored=0; reviewed=0; cases=2. Zero reviewed coverage is not evaluated capability. |
| Oracle memory:update | 0 | UNAVAILABLE | Authored=0; reviewed=0; cases=2. Zero reviewed coverage is not evaluated capability. |
| Oracle memory:use | 0 | UNAVAILABLE | Authored=0; reviewed=0; cases=2. Zero reviewed coverage is not evaluated capability. |
| Oracle response | 6 | AVAILABLE | Authored=6; reviewed=6; cases=2. Zero reviewed coverage is not evaluated capability. |
| Oracle route | 0 | UNAVAILABLE | Authored=0; reviewed=0; cases=2. Zero reviewed coverage is not evaluated capability. |
| Oracle safety | 0 | UNAVAILABLE | Authored=0; reviewed=0; cases=2. Zero reviewed coverage is not evaluated capability. |
| Oracle tools | 0 | UNAVAILABLE | Authored=0; reviewed=0; cases=2. Zero reviewed coverage is not evaluated capability. |

## Self-judging cells

| Subject | Judge | Case | Turn | Weighted score | Status |
| --- | --- | --- | ---: | ---: | --- |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | TC-17 | 2 | 2.4934497816593897 | PASS |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium | TC-17 | 4 | None | UNAVAILABLE |
| qwen:qwen3.8-max:latest:medium | qwen:qwen3.8-max:judge:medium | TC-17 | 3 | None | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium | TC-17 | 1 | None | UNAVAILABLE |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | TC-17 | 4 | 2.0000000000000004 | PASS |
| qwen:qwen3.8-max:latest:medium | qwen:qwen3.8-max:judge:medium | TC-52 | 2 | None | UNAVAILABLE |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | TC-52 | 1 | 2.116883116883117 | PASS |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | TC-17 | 3 | None | UNAVAILABLE |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | TC-17 | 1 | 1.7292576419213976 | PASS |
| qwen:qwen3.8-max:latest:medium | qwen:qwen3.8-max:judge:medium | TC-52 | 1 | None | UNAVAILABLE |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | TC-17 | 2 | 2.270742358078603 | PASS |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | TC-52 | 2 | 1.58008658008658 | PASS |
| qwen:qwen3.8-max:latest:medium | qwen:qwen3.8-max:judge:medium | TC-17 | 2 | None | UNAVAILABLE |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | TC-17 | 3 | 3.0000000000000004 | PASS |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium | TC-52 | 1 | None | UNAVAILABLE |
| qwen:qwen3.8-max:latest:medium | qwen:qwen3.8-max:judge:medium | TC-17 | 1 | None | UNAVAILABLE |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | TC-52 | 2 | None | UNAVAILABLE |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | TC-17 | 2 | 3.0000000000000004 | PASS |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium | TC-17 | 2 | 2.192139737991267 | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | TC-52 | 1 | 2.541125541125541 | PASS |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | TC-17 | 3 | 1.8864628820960703 | PASS |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium | TC-17 | 3 | 2.3144104803493457 | PASS |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium | TC-52 | 2 | None | UNAVAILABLE |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | TC-17 | 1 | None | UNAVAILABLE |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | TC-17 | 4 | 3.0000000000000004 | PASS |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | TC-17 | 4 | None | UNAVAILABLE |
| qwen:qwen3.8-max:latest:medium | qwen:qwen3.8-max:judge:medium | TC-17 | 4 | None | UNAVAILABLE |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | TC-52 | 2 | 2.887445887445887 | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | TC-17 | 1 | 3.0000000000000004 | PASS |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | TC-52 | 1 | 1.9437229437229435 | PASS |

## Dimension medians by subject

| Subject | 丰富性 | 包容性与可及性 | 基础能力 | 求助转介 | 法律维权 | 行动赋权 | 表达能力 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| claude:claude-opus-5:latest:medium | 2.0000 | 2.0000 | 3.0000 | 2.0000 | 2.0000 | 2.0000 | 3.0000 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | 2.0000 | 3.0000 | 3.0000 | 1.0000 | 2.0000 | 2.0000 | 3.0000 |
| gpt:gpt-5.6-sol:latest:medium | 2.0000 | 2.5000 | 3.0000 | 1.0000 | 2.0000 | 2.5000 | 3.0000 |
| kimi:kimi-k3:latest:medium | 2.0000 | 2.0000 | 3.0000 | 1.5000 | 1.5000 | 2.0000 | 3.0000 |
| qwen:qwen3.8-max:latest:medium | 2.0000 | 3.0000 | 3.0000 | 1.0000 | 1.0000 | 2.0000 | 3.0000 |

## Dimension medians by subject and judge

| Subject | Judge | 丰富性 | 包容性与可及性 | 基础能力 | 求助转介 | 法律维权 | 行动赋权 | 表达能力 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium | 1.5000 | 2.0000 | 3.0000 | 1.5000 | 2.5000 | 2.0000 | 3.0000 |
| claude:claude-opus-5:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 3.0000 | 3.0000 | 3.0000 | 3.0000 | 3.0000 | 3.0000 | 3.0000 |
| claude:claude-opus-5:latest:medium | gpt:gpt-5.6-sol:judge:medium | 1.0000 | 1.0000 | 2.0000 | 0.5000 | 1.0000 | 1.0000 | 3.0000 |
| claude:claude-opus-5:latest:medium | kimi:kimi-k3:judge:medium | 2.0000 | 2.0000 | 3.0000 | 2.0000 | 2.0000 | 2.0000 | 3.0000 |
| claude:claude-opus-5:latest:medium | qwen:qwen3.8-max:judge:medium | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE |
| gemini:gemini-3-pro-preview-thinking:latest:medium | claude:claude-opus-5:judge:medium | 1.0000 | 3.0000 | 3.0000 | 0.0000 | 0.0000 | 2.5000 | 3.0000 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 3.0000 | 3.0000 | 3.0000 | 3.0000 | 3.0000 | 3.0000 | 3.0000 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gpt:gpt-5.6-sol:judge:medium | 1.0000 | 2.0000 | 2.0000 | 1.0000 | 1.0000 | 2.0000 | 3.0000 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | kimi:kimi-k3:judge:medium | 2.0000 | 2.0000 | 3.0000 | 2.0000 | 2.0000 | 2.0000 | 3.0000 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | qwen:qwen3.8-max:judge:medium | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE |
| gpt:gpt-5.6-sol:latest:medium | claude:claude-opus-5:judge:medium | 2.0000 | 3.0000 | 3.0000 | 0.0000 | 0.0000 | 3.0000 | 3.0000 |
| gpt:gpt-5.6-sol:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 3.0000 | 3.0000 | 3.0000 | 3.0000 | 3.0000 | 3.0000 | 3.0000 |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | 2.0000 | 2.0000 | 2.0000 | 1.0000 | 1.0000 | 2.0000 | 3.0000 |
| gpt:gpt-5.6-sol:latest:medium | kimi:kimi-k3:judge:medium | 2.0000 | 2.0000 | 3.0000 | 1.5000 | 2.0000 | 3.0000 | 3.0000 |
| gpt:gpt-5.6-sol:latest:medium | qwen:qwen3.8-max:judge:medium | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE |
| kimi:kimi-k3:latest:medium | claude:claude-opus-5:judge:medium | 1.5000 | 2.5000 | 3.0000 | 0.0000 | 0.0000 | 2.0000 | 3.0000 |
| kimi:kimi-k3:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 2.5000 | 3.0000 | 3.0000 | 2.5000 | 2.5000 | 2.5000 | 3.0000 |
| kimi:kimi-k3:latest:medium | gpt:gpt-5.6-sol:judge:medium | 1.0000 | 1.5000 | 2.0000 | 1.0000 | 1.0000 | 1.5000 | 3.0000 |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | 2.0000 | 2.0000 | 2.5000 | 2.0000 | 2.0000 | 2.0000 | 3.0000 |
| kimi:kimi-k3:latest:medium | qwen:qwen3.8-max:judge:medium | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE |
| qwen:qwen3.8-max:latest:medium | claude:claude-opus-5:judge:medium | 1.0000 | 2.0000 | 3.0000 | 0.0000 | 0.0000 | 2.0000 | 3.0000 |
| qwen:qwen3.8-max:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 3.0000 | 3.0000 | 3.0000 | 3.0000 | 3.0000 | 3.0000 | 3.0000 |
| qwen:qwen3.8-max:latest:medium | gpt:gpt-5.6-sol:judge:medium | 1.0000 | 2.0000 | 3.0000 | 1.0000 | 1.0000 | 2.0000 | 3.0000 |
| qwen:qwen3.8-max:latest:medium | kimi:kimi-k3:judge:medium | 2.0000 | 3.0000 | 3.0000 | 2.0000 | 2.0000 | 2.0000 | 3.0000 |
| qwen:qwen3.8-max:latest:medium | qwen:qwen3.8-max:judge:medium | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE |

## Dimension distribution by subject and judge

| Subject | Judge | Dimension | Median | MAD | IQR | Range | N |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium | 丰富性 | 1.5 | 0.5 | 1.0 | 1.0 | 2 |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium | 包容性与可及性 | 2.0 | 0.0 | 0.0 | 0.0 | 2 |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium | 基础能力 | 3.0 | 0.0 | 0.0 | 0.0 | 2 |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium | 求助转介 | 1.5 | 0.5 | 1.0 | 1.0 | 2 |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium | 法律维权 | 2.5 | 0.5 | 1.0 | 1.0 | 2 |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium | 行动赋权 | 2.0 | 0.0 | 0.0 | 0.0 | 2 |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 2 |
| claude:claude-opus-5:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 丰富性 | 3.0 | 0.0 | 0.0 | 0.0 | 2 |
| claude:claude-opus-5:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 包容性与可及性 | 3.0 | 0.0 | 0.0 | 0.0 | 2 |
| claude:claude-opus-5:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 基础能力 | 3.0 | 0.0 | 0.0 | 0.0 | 2 |
| claude:claude-opus-5:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 求助转介 | 3.0 | 0.0 | 0.0 | 0.0 | 2 |
| claude:claude-opus-5:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 法律维权 | 3.0 | 0.0 | 0.0 | 0.0 | 2 |
| claude:claude-opus-5:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 行动赋权 | 3.0 | 0.0 | 0.0 | 0.0 | 2 |
| claude:claude-opus-5:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 2 |
| claude:claude-opus-5:latest:medium | gpt:gpt-5.6-sol:judge:medium | 丰富性 | 1.0 | 0.0 | 0.0 | 0.0 | 2 |
| claude:claude-opus-5:latest:medium | gpt:gpt-5.6-sol:judge:medium | 包容性与可及性 | 1.0 | 0.0 | 0.0 | 0.0 | 2 |
| claude:claude-opus-5:latest:medium | gpt:gpt-5.6-sol:judge:medium | 基础能力 | 2.0 | 0.0 | 0.0 | 0.0 | 2 |
| claude:claude-opus-5:latest:medium | gpt:gpt-5.6-sol:judge:medium | 求助转介 | 0.5 | 0.5 | 1.0 | 1.0 | 2 |
| claude:claude-opus-5:latest:medium | gpt:gpt-5.6-sol:judge:medium | 法律维权 | 1.0 | 1.0 | 2.0 | 2.0 | 2 |
| claude:claude-opus-5:latest:medium | gpt:gpt-5.6-sol:judge:medium | 行动赋权 | 1.0 | 0.0 | 0.0 | 0.0 | 2 |
| claude:claude-opus-5:latest:medium | gpt:gpt-5.6-sol:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 2 |
| claude:claude-opus-5:latest:medium | kimi:kimi-k3:judge:medium | 丰富性 | 2.0 | 0.0 | 0.0 | 0.0 | 1 |
| claude:claude-opus-5:latest:medium | kimi:kimi-k3:judge:medium | 包容性与可及性 | 2.0 | 0.0 | 0.0 | 0.0 | 1 |
| claude:claude-opus-5:latest:medium | kimi:kimi-k3:judge:medium | 基础能力 | 3.0 | 0.0 | 0.0 | 0.0 | 1 |
| claude:claude-opus-5:latest:medium | kimi:kimi-k3:judge:medium | 求助转介 | 2.0 | 0.0 | 0.0 | 0.0 | 1 |
| claude:claude-opus-5:latest:medium | kimi:kimi-k3:judge:medium | 法律维权 | 2.0 | 0.0 | 0.0 | 0.0 | 1 |
| claude:claude-opus-5:latest:medium | kimi:kimi-k3:judge:medium | 行动赋权 | 2.0 | 0.0 | 0.0 | 0.0 | 1 |
| claude:claude-opus-5:latest:medium | kimi:kimi-k3:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 1 |
| claude:claude-opus-5:latest:medium | qwen:qwen3.8-max:judge:medium | 丰富性 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| claude:claude-opus-5:latest:medium | qwen:qwen3.8-max:judge:medium | 包容性与可及性 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| claude:claude-opus-5:latest:medium | qwen:qwen3.8-max:judge:medium | 基础能力 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| claude:claude-opus-5:latest:medium | qwen:qwen3.8-max:judge:medium | 求助转介 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| claude:claude-opus-5:latest:medium | qwen:qwen3.8-max:judge:medium | 法律维权 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| claude:claude-opus-5:latest:medium | qwen:qwen3.8-max:judge:medium | 行动赋权 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| claude:claude-opus-5:latest:medium | qwen:qwen3.8-max:judge:medium | 表达能力 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | claude:claude-opus-5:judge:medium | 丰富性 | 1.0 | 0.5 | 2.0 | 3.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | claude:claude-opus-5:judge:medium | 包容性与可及性 | 3.0 | 0.0 | 1.0 | 1.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | claude:claude-opus-5:judge:medium | 基础能力 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | claude:claude-opus-5:judge:medium | 求助转介 | 0.0 | 0.0 | 3.0 | 3.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | claude:claude-opus-5:judge:medium | 法律维权 | 0.0 | 0.0 | 3.0 | 3.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | claude:claude-opus-5:judge:medium | 行动赋权 | 2.5 | 0.5 | 1.0 | 1.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | claude:claude-opus-5:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 丰富性 | 3.0 | 0.0 | 0.0 | 1.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 包容性与可及性 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 基础能力 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 求助转介 | 3.0 | 0.0 | 1.0 | 2.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 法律维权 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 行动赋权 | 3.0 | 0.0 | 0.0 | 1.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gpt:gpt-5.6-sol:judge:medium | 丰富性 | 1.0 | 0.0 | 0.0 | 0.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gpt:gpt-5.6-sol:judge:medium | 包容性与可及性 | 2.0 | 0.0 | 0.0 | 1.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gpt:gpt-5.6-sol:judge:medium | 基础能力 | 2.0 | 0.0 | 0.0 | 0.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gpt:gpt-5.6-sol:judge:medium | 求助转介 | 1.0 | 0.0 | 1.0 | 1.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gpt:gpt-5.6-sol:judge:medium | 法律维权 | 1.0 | 1.0 | 2.0 | 2.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gpt:gpt-5.6-sol:judge:medium | 行动赋权 | 2.0 | 0.0 | 0.0 | 1.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gpt:gpt-5.6-sol:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | kimi:kimi-k3:judge:medium | 丰富性 | 2.0 | 0.0 | 0.0 | 0.0 | 3 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | kimi:kimi-k3:judge:medium | 包容性与可及性 | 2.0 | 0.0 | 0.5 | 1.0 | 3 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | kimi:kimi-k3:judge:medium | 基础能力 | 3.0 | 0.0 | 0.0 | 0.0 | 3 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | kimi:kimi-k3:judge:medium | 求助转介 | 2.0 | 1.0 | 1.0 | 2.0 | 3 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | kimi:kimi-k3:judge:medium | 法律维权 | 2.0 | 0.0 | 0.5 | 1.0 | 3 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | kimi:kimi-k3:judge:medium | 行动赋权 | 2.0 | 0.0 | 0.0 | 0.0 | 3 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | kimi:kimi-k3:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 3 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | qwen:qwen3.8-max:judge:medium | 丰富性 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | qwen:qwen3.8-max:judge:medium | 包容性与可及性 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | qwen:qwen3.8-max:judge:medium | 基础能力 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | qwen:qwen3.8-max:judge:medium | 求助转介 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | qwen:qwen3.8-max:judge:medium | 法律维权 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | qwen:qwen3.8-max:judge:medium | 行动赋权 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | qwen:qwen3.8-max:judge:medium | 表达能力 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| gpt:gpt-5.6-sol:latest:medium | claude:claude-opus-5:judge:medium | 丰富性 | 2.0 | 0.5 | 1.0 | 2.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | claude:claude-opus-5:judge:medium | 包容性与可及性 | 3.0 | 0.0 | 1.0 | 1.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | claude:claude-opus-5:judge:medium | 基础能力 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | claude:claude-opus-5:judge:medium | 求助转介 | 0.0 | 0.0 | 3.0 | 3.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | claude:claude-opus-5:judge:medium | 法律维权 | 0.0 | 0.0 | 3.0 | 3.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | claude:claude-opus-5:judge:medium | 行动赋权 | 3.0 | 0.0 | 1.0 | 1.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | claude:claude-opus-5:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 丰富性 | 3.0 | 0.0 | 1.0 | 1.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 包容性与可及性 | 3.0 | 0.0 | 1.0 | 1.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 基础能力 | 3.0 | 0.0 | 1.0 | 1.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 求助转介 | 3.0 | 0.0 | 1.0 | 3.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 法律维权 | 3.0 | 0.0 | 1.0 | 3.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 行动赋权 | 3.0 | 0.0 | 1.0 | 1.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 1.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | 丰富性 | 2.0 | 0.0 | 1.0 | 1.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | 包容性与可及性 | 2.0 | 0.0 | 1.0 | 1.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | 基础能力 | 2.0 | 0.0 | 0.0 | 1.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | 求助转介 | 1.0 | 0.0 | 0.0 | 3.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | 法律维权 | 1.0 | 0.5 | 1.0 | 3.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | 行动赋权 | 2.0 | 0.0 | 0.0 | 0.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | kimi:kimi-k3:judge:medium | 丰富性 | 2.0 | 0.0 | 0.5 | 1.0 | 4 |
| gpt:gpt-5.6-sol:latest:medium | kimi:kimi-k3:judge:medium | 包容性与可及性 | 2.0 | 0.0 | 0.5 | 1.0 | 4 |
| gpt:gpt-5.6-sol:latest:medium | kimi:kimi-k3:judge:medium | 基础能力 | 3.0 | 0.0 | 0.5 | 1.0 | 4 |
| gpt:gpt-5.6-sol:latest:medium | kimi:kimi-k3:judge:medium | 求助转介 | 1.5 | 0.5 | 1.0 | 1.0 | 4 |
| gpt:gpt-5.6-sol:latest:medium | kimi:kimi-k3:judge:medium | 法律维权 | 2.0 | 0.0 | 0.5 | 1.0 | 4 |
| gpt:gpt-5.6-sol:latest:medium | kimi:kimi-k3:judge:medium | 行动赋权 | 3.0 | 0.0 | 0.5 | 1.0 | 4 |
| gpt:gpt-5.6-sol:latest:medium | kimi:kimi-k3:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 4 |
| gpt:gpt-5.6-sol:latest:medium | qwen:qwen3.8-max:judge:medium | 丰富性 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| gpt:gpt-5.6-sol:latest:medium | qwen:qwen3.8-max:judge:medium | 包容性与可及性 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| gpt:gpt-5.6-sol:latest:medium | qwen:qwen3.8-max:judge:medium | 基础能力 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| gpt:gpt-5.6-sol:latest:medium | qwen:qwen3.8-max:judge:medium | 求助转介 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| gpt:gpt-5.6-sol:latest:medium | qwen:qwen3.8-max:judge:medium | 法律维权 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| gpt:gpt-5.6-sol:latest:medium | qwen:qwen3.8-max:judge:medium | 行动赋权 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| gpt:gpt-5.6-sol:latest:medium | qwen:qwen3.8-max:judge:medium | 表达能力 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| kimi:kimi-k3:latest:medium | claude:claude-opus-5:judge:medium | 丰富性 | 1.5 | 0.5 | 1.0 | 1.0 | 6 |
| kimi:kimi-k3:latest:medium | claude:claude-opus-5:judge:medium | 包容性与可及性 | 2.5 | 0.5 | 1.0 | 1.0 | 6 |
| kimi:kimi-k3:latest:medium | claude:claude-opus-5:judge:medium | 基础能力 | 3.0 | 0.0 | 0.0 | 1.0 | 6 |
| kimi:kimi-k3:latest:medium | claude:claude-opus-5:judge:medium | 求助转介 | 0.0 | 0.0 | 2.0 | 3.0 | 6 |
| kimi:kimi-k3:latest:medium | claude:claude-opus-5:judge:medium | 法律维权 | 0.0 | 0.0 | 3.0 | 3.0 | 6 |
| kimi:kimi-k3:latest:medium | claude:claude-opus-5:judge:medium | 行动赋权 | 2.0 | 0.5 | 1.0 | 3.0 | 6 |
| kimi:kimi-k3:latest:medium | claude:claude-opus-5:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| kimi:kimi-k3:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 丰富性 | 2.5 | 0.5 | 1.0 | 1.0 | 6 |
| kimi:kimi-k3:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 包容性与可及性 | 3.0 | 0.0 | 1.0 | 1.0 | 6 |
| kimi:kimi-k3:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 基础能力 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| kimi:kimi-k3:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 求助转介 | 2.5 | 0.5 | 1.0 | 1.0 | 6 |
| kimi:kimi-k3:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 法律维权 | 2.5 | 0.5 | 1.0 | 1.0 | 6 |
| kimi:kimi-k3:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 行动赋权 | 2.5 | 0.5 | 1.0 | 1.0 | 6 |
| kimi:kimi-k3:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| kimi:kimi-k3:latest:medium | gpt:gpt-5.6-sol:judge:medium | 丰富性 | 1.0 | 0.0 | 0.0 | 1.0 | 6 |
| kimi:kimi-k3:latest:medium | gpt:gpt-5.6-sol:judge:medium | 包容性与可及性 | 1.5 | 0.5 | 1.0 | 1.0 | 6 |
| kimi:kimi-k3:latest:medium | gpt:gpt-5.6-sol:judge:medium | 基础能力 | 2.0 | 0.0 | 0.0 | 1.0 | 6 |
| kimi:kimi-k3:latest:medium | gpt:gpt-5.6-sol:judge:medium | 求助转介 | 1.0 | 0.0 | 0.0 | 1.0 | 6 |
| kimi:kimi-k3:latest:medium | gpt:gpt-5.6-sol:judge:medium | 法律维权 | 1.0 | 0.0 | 0.0 | 0.0 | 6 |
| kimi:kimi-k3:latest:medium | gpt:gpt-5.6-sol:judge:medium | 行动赋权 | 1.5 | 0.5 | 1.0 | 2.0 | 6 |
| kimi:kimi-k3:latest:medium | gpt:gpt-5.6-sol:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | 丰富性 | 2.0 | 0.0 | 0.0 | 0.0 | 2 |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | 包容性与可及性 | 2.0 | 0.0 | 0.0 | 0.0 | 2 |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | 基础能力 | 2.5 | 0.5 | 1.0 | 1.0 | 2 |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | 求助转介 | 2.0 | 0.0 | 0.0 | 0.0 | 2 |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | 法律维权 | 2.0 | 0.0 | 0.0 | 0.0 | 2 |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | 行动赋权 | 2.0 | 0.0 | 0.0 | 0.0 | 2 |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 2 |
| kimi:kimi-k3:latest:medium | qwen:qwen3.8-max:judge:medium | 丰富性 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| kimi:kimi-k3:latest:medium | qwen:qwen3.8-max:judge:medium | 包容性与可及性 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| kimi:kimi-k3:latest:medium | qwen:qwen3.8-max:judge:medium | 基础能力 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| kimi:kimi-k3:latest:medium | qwen:qwen3.8-max:judge:medium | 求助转介 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| kimi:kimi-k3:latest:medium | qwen:qwen3.8-max:judge:medium | 法律维权 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| kimi:kimi-k3:latest:medium | qwen:qwen3.8-max:judge:medium | 行动赋权 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| kimi:kimi-k3:latest:medium | qwen:qwen3.8-max:judge:medium | 表达能力 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| qwen:qwen3.8-max:latest:medium | claude:claude-opus-5:judge:medium | 丰富性 | 1.0 | 0.0 | 0.0 | 1.0 | 6 |
| qwen:qwen3.8-max:latest:medium | claude:claude-opus-5:judge:medium | 包容性与可及性 | 2.0 | 0.0 | 1.0 | 1.0 | 6 |
| qwen:qwen3.8-max:latest:medium | claude:claude-opus-5:judge:medium | 基础能力 | 3.0 | 0.0 | 0.0 | 1.0 | 6 |
| qwen:qwen3.8-max:latest:medium | claude:claude-opus-5:judge:medium | 求助转介 | 0.0 | 0.0 | 0.0 | 0.0 | 6 |
| qwen:qwen3.8-max:latest:medium | claude:claude-opus-5:judge:medium | 法律维权 | 0.0 | 0.0 | 0.0 | 0.0 | 6 |
| qwen:qwen3.8-max:latest:medium | claude:claude-opus-5:judge:medium | 行动赋权 | 2.0 | 0.0 | 0.0 | 1.0 | 6 |
| qwen:qwen3.8-max:latest:medium | claude:claude-opus-5:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| qwen:qwen3.8-max:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 丰富性 | 3.0 | 0.0 | 0.0 | 1.0 | 6 |
| qwen:qwen3.8-max:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 包容性与可及性 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| qwen:qwen3.8-max:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 基础能力 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| qwen:qwen3.8-max:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 求助转介 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| qwen:qwen3.8-max:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 法律维权 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| qwen:qwen3.8-max:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 行动赋权 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| qwen:qwen3.8-max:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| qwen:qwen3.8-max:latest:medium | gpt:gpt-5.6-sol:judge:medium | 丰富性 | 1.0 | 0.0 | 1.0 | 1.0 | 6 |
| qwen:qwen3.8-max:latest:medium | gpt:gpt-5.6-sol:judge:medium | 包容性与可及性 | 2.0 | 0.0 | 0.0 | 2.0 | 6 |
| qwen:qwen3.8-max:latest:medium | gpt:gpt-5.6-sol:judge:medium | 基础能力 | 3.0 | 0.0 | 1.0 | 1.0 | 6 |
| qwen:qwen3.8-max:latest:medium | gpt:gpt-5.6-sol:judge:medium | 求助转介 | 1.0 | 0.0 | 1.0 | 1.0 | 6 |
| qwen:qwen3.8-max:latest:medium | gpt:gpt-5.6-sol:judge:medium | 法律维权 | 1.0 | 0.0 | 1.0 | 1.0 | 6 |
| qwen:qwen3.8-max:latest:medium | gpt:gpt-5.6-sol:judge:medium | 行动赋权 | 2.0 | 0.0 | 1.0 | 1.0 | 6 |
| qwen:qwen3.8-max:latest:medium | gpt:gpt-5.6-sol:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| qwen:qwen3.8-max:latest:medium | kimi:kimi-k3:judge:medium | 丰富性 | 2.0 | 0.0 | 0.0 | 0.0 | 5 |
| qwen:qwen3.8-max:latest:medium | kimi:kimi-k3:judge:medium | 包容性与可及性 | 3.0 | 0.0 | 0.0 | 1.0 | 5 |
| qwen:qwen3.8-max:latest:medium | kimi:kimi-k3:judge:medium | 基础能力 | 3.0 | 0.0 | 0.0 | 1.0 | 5 |
| qwen:qwen3.8-max:latest:medium | kimi:kimi-k3:judge:medium | 求助转介 | 2.0 | 0.0 | 0.0 | 0.0 | 5 |
| qwen:qwen3.8-max:latest:medium | kimi:kimi-k3:judge:medium | 法律维权 | 2.0 | 0.0 | 0.0 | 1.0 | 5 |
| qwen:qwen3.8-max:latest:medium | kimi:kimi-k3:judge:medium | 行动赋权 | 2.0 | 0.0 | 0.0 | 1.0 | 5 |
| qwen:qwen3.8-max:latest:medium | kimi:kimi-k3:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 5 |
| qwen:qwen3.8-max:latest:medium | qwen:qwen3.8-max:judge:medium | 丰富性 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| qwen:qwen3.8-max:latest:medium | qwen:qwen3.8-max:judge:medium | 包容性与可及性 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| qwen:qwen3.8-max:latest:medium | qwen:qwen3.8-max:judge:medium | 基础能力 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| qwen:qwen3.8-max:latest:medium | qwen:qwen3.8-max:judge:medium | 求助转介 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| qwen:qwen3.8-max:latest:medium | qwen:qwen3.8-max:judge:medium | 法律维权 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| qwen:qwen3.8-max:latest:medium | qwen:qwen3.8-max:judge:medium | 行动赋权 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| qwen:qwen3.8-max:latest:medium | qwen:qwen3.8-max:judge:medium | 表达能力 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |

Self-judging cells are displayed separately and excluded by default. Explicit inclusion is exploratory; agreement uses non-self observations. Scores are descriptive and do not establish quality acceptance or Judge validity.

## Operational telemetry

| Subject | Judge | First character | First-character ms | Answer queue ms | Answer ms | Answer tokens | Answer attempts | Answer cached/write | Answer error | Judge queue ms | Judge ms | Judge tokens | Judge attempts | Judge cached/write | Cache hit ratio | Judge error | Status |
| --- | --- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| gpt:gpt-5.6-sol:latest:medium | claude:claude-opus-5:judge:medium | 他 | None | 33234.57495891489 | 26666.411750018597 | 17247 | 1 | None/None | None | 698.0128330178559 | 14240.672833053395 | 688 | 1 | 2482/5037 | 1241.0 | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 他 | None | 33234.57495891489 | 26666.411750018597 | 17247 | 1 | None/None | None | 50667.04050009139 | 28970.036707934923 | 5813 | 1 | None/None | None | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | 他 | None | 33234.57495891489 | 26666.411750018597 | 17247 | 1 | None/None | None | 27102.009416092187 | 41915.107458946295 | 6828 | 1 | 4480/None | 0.964270340077486 | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | kimi:kimi-k3:judge:medium | 他 | None | 33234.57495891489 | 26666.411750018597 | 17247 | 1 | None/None | None | 89819.82237496413 | 43304.13879198022 | 6761 | 1 | 1280/None | 0.29836829836829837 | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | qwen:qwen3.8-max:judge:medium | 他 | None | 33234.57495891489 | 26666.411750018597 | 17247 | 1 | None/None | None | 0.0025420449674129486 | 61082.26183289662 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium |  | None | 0.012791948392987251 | 62961.06816700194 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium |  | None | 0.012791948392987251 | 62961.06816700194 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | gpt:gpt-5.6-sol:judge:medium |  | None | 0.012791948392987251 | 62961.06816700194 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | kimi:kimi-k3:judge:medium |  | None | 0.012791948392987251 | 62961.06816700194 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | qwen:qwen3.8-max:judge:medium |  | None | 0.012791948392987251 | 62961.06816700194 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| qwen:qwen3.8-max:latest:medium | claude:claude-opus-5:judge:medium | 这 | None | 34009.66741703451 | 61163.69841701817 | 10547 | 1 | None/None | None | 26249.766124994494 | 16766.307499958202 | 843 | 1 | 2475/7688 | 1237.5 | None | PASS |
| qwen:qwen3.8-max:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 这 | None | 34009.66741703451 | 61163.69841701817 | 10547 | 1 | None/None | None | 32363.53199998848 | 15767.704125028104 | 7477 | 1 | None/None | None | None | PASS |
| qwen:qwen3.8-max:latest:medium | gpt:gpt-5.6-sol:judge:medium | 这 | None | 34009.66741703451 | 61163.69841701817 | 10547 | 1 | None/None | None | 48131.59483298659 | 29111.205500084907 | 8009 | 1 | 6400/None | 0.9768009768009768 | None | PASS |
| qwen:qwen3.8-max:latest:medium | kimi:kimi-k3:judge:medium | 这 | None | 34009.66741703451 | 61163.69841701817 | 10547 | 1 | None/None | None | 43016.9771250803 | 49538.64837507717 | 9096 | 1 | 1280/None | 0.21610670268445045 | None | PASS |
| qwen:qwen3.8-max:latest:medium | qwen:qwen3.8-max:judge:medium | 这 | None | 34009.66741703451 | 61163.69841701817 | 10547 | 1 | None/None | None | 28003.378959023394 | 62123.593209078535 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium |  | None | 0.002958928234875202 | 42396.95541700348 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium |  | None | 0.002958928234875202 | 42396.95541700348 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | gpt:gpt-5.6-sol:judge:medium |  | None | 0.002958928234875202 | 42396.95541700348 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | kimi:kimi-k3:judge:medium |  | None | 0.002958928234875202 | 42396.95541700348 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | qwen:qwen3.8-max:judge:medium |  | None | 0.002958928234875202 | 42396.95541700348 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| gpt:gpt-5.6-sol:latest:medium | claude:claude-opus-5:judge:medium | 如 | None | 0.005375011824071407 | 16899.529250105843 | 19837 | 1 | None/None | None | 37477.95891598798 | 20289.302417077124 | 981 | 1 | 2475/7981 | 1237.5 | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 如 | None | 0.005375011824071407 | 16899.529250105843 | 19837 | 1 | None/None | None | 36511.75029203296 | 16639.64037504047 | 7707 | 1 | None/None | None | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | 如 | None | 0.005375011824071407 | 16899.529250105843 | 19837 | 1 | None/None | None | 33916.14387498703 | 36417.97129204497 | 8553 | 1 | 6528/None | 0.9663952627683198 | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | kimi:kimi-k3:judge:medium | 如 | None | 0.005375011824071407 | 16899.529250105843 | 19837 | 1 | None/None | None | 0.0030830269679427147 | 61437.77879199479 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| gpt:gpt-5.6-sol:latest:medium | qwen:qwen3.8-max:judge:medium | 如 | None | 0.005375011824071407 | 16899.529250105843 | 19837 | 1 | None/None | None | 28421.106749912724 | 61103.48049993627 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| qwen:qwen3.8-max:latest:medium | claude:claude-opus-5:judge:medium | 你 | None | 70982.88416711148 | 34000.858582905494 | 7050 | 1 | None/None | None | 6395.19637497142 | 15841.949832974933 | 14928 | 1 | 173706/0 | 12.393407534246576 | None | PASS |
| qwen:qwen3.8-max:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 你 | None | 70982.88416711148 | 34000.858582905494 | 7050 | 1 | None/None | None | 55093.88408402447 | 22619.806749979034 | 6316 | 1 | None/None | None | None | PASS |
| qwen:qwen3.8-max:latest:medium | gpt:gpt-5.6-sol:judge:medium | 你 | None | 70982.88416711148 | 34000.858582905494 | 7050 | 1 | None/None | None | 77714.04912509024 | 37404.231333057396 | 6061 | 1 | None/None | None | None | PASS |
| qwen:qwen3.8-max:latest:medium | kimi:kimi-k3:judge:medium | 你 | None | 70982.88416711148 | 34000.858582905494 | 7050 | 1 | None/None | None | 32309.25145803485 | 42185.55179203395 | 5968 | 1 | 1280/None | 0.32803690415171705 | None | PASS |
| qwen:qwen3.8-max:latest:medium | qwen:qwen3.8-max:judge:medium | 你 | None | 70982.88416711148 | 34000.858582905494 | 7050 | 1 | None/None | None | 28069.93620796129 | 61074.42408299539 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| kimi:kimi-k3:latest:medium | claude:claude-opus-5:judge:medium | 不 | None | 0.0020829029381275177 | 33912.83812490292 | 7356 | 1 | None/None | None | 54450.12812502682 | 17683.126208023168 | 1120 | 1 | 2475/5627 | 1237.5 | None | PASS |
| kimi:kimi-k3:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 不 | None | 0.0020829029381275177 | 33912.83812490292 | 7356 | 1 | None/None | None | 72136.84854202438 | 29833.20749993436 | 6337 | 1 | None/None | None | None | PASS |
| kimi:kimi-k3:latest:medium | gpt:gpt-5.6-sol:judge:medium | 不 | None | 0.0020829029381275177 | 33912.83812490292 | 7356 | 1 | None/None | None | 0.029667047783732414 | 31072.016208898276 | 6616 | 1 | 4864/None | 0.9654624851131401 | None | PASS |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | 不 | None | 0.0020829029381275177 | 33912.83812490292 | 7356 | 1 | None/None | None | 33133.90333310235 | 56171.8234999571 | 6790 | 1 | None/None | None | None | PASS |
| kimi:kimi-k3:latest:medium | qwen:qwen3.8-max:judge:medium | 不 | None | 0.0020829029381275177 | 33912.83812490292 | 7356 | 1 | None/None | None | 36874.92512492463 | 62156.50704095606 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| kimi:kimi-k3:latest:medium | claude:claude-opus-5:judge:medium | 你 | None | 33933.159958105534 | 38646.63562504575 | 7489 | 1 | None/None | None | 14652.811624924652 | 13218.176416005008 | 768 | 1 | 2475/5356 | 1237.5 | None | PASS |
| kimi:kimi-k3:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 你 | None | 33933.159958105534 | 38646.63562504575 | 7489 | 1 | None/None | None | 19987.630292074755 | 11343.559041968547 | 5201 | 1 | None/None | None | None | PASS |
| kimi:kimi-k3:latest:medium | gpt:gpt-5.6-sol:judge:medium | 你 | None | 33933.159958105534 | 38646.63562504575 | 7489 | 1 | None/None | None | 16222.556790919043 | 50879.93995798752 | 6864 | 1 | None/None | None | None | PASS |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | 你 | None | 33933.159958105534 | 38646.63562504575 | 7489 | 1 | None/None | None | 0.0020830193534493446 | 62055.55054207798 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| kimi:kimi-k3:latest:medium | qwen:qwen3.8-max:judge:medium | 你 | None | 33933.159958105534 | 38646.63562504575 | 7489 | 1 | None/None | None | 0.013375072740018368 | 62061.46400002763 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| gpt:gpt-5.6-sol:latest:medium | claude:claude-opus-5:judge:medium | 发 | None | 0.0021670712158083916 | 30059.226542012766 | 17425 | 1 | None/None | None | 0.006416928954422474 | 17051.762707997113 | 822 | 1 | 0/7337 | 0.0 | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 发 | None | 0.0021670712158083916 | 30059.226542012766 | 17425 | 1 | None/None | None | 0.0028329668566584587 | 20940.606457996182 | 5673 | 1 | None/None | None | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | 发 | None | 0.0021670712158083916 | 30059.226542012766 | 17425 | 1 | None/None | None | 0.0037499703466892242 | 52313.854124979116 | 6483 | 1 | 4352/None | 0.958590308370044 | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | kimi:kimi-k3:judge:medium | 发 | None | 0.0021670712158083916 | 30059.226542012766 | 17425 | 1 | None/None | None | 0.002583954483270645 | 35771.3687090436 | 5758 | 1 | 1280/None | 0.30396580384706723 | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | qwen:qwen3.8-max:judge:medium | 发 | None | 0.0021670712158083916 | 30059.226542012766 | 17425 | 1 | None/None | None | 0.002125045284628868 | 61159.60766701028 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| qwen:qwen3.8-max:latest:medium | claude:claude-opus-5:judge:medium | 你 | None | 0.002166023477911949 | 40428.876749938354 | 7174 | 1 | None/None | None | 89961.72370901331 | 15238.079292001203 | 6351 | 1 | 0/30720 | 0.0 | None | PASS |
| qwen:qwen3.8-max:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 你 | None | 0.002166023477911949 | 40428.876749938354 | 7174 | 1 | None/None | None | 84305.3959159879 | 18338.610582984984 | 5210 | 1 | None/None | None | None | PASS |
| qwen:qwen3.8-max:latest:medium | gpt:gpt-5.6-sol:judge:medium | 你 | None | 0.002166023477911949 | 40428.876749938354 | 7174 | 1 | None/None | None | 65895.69854200818 | 29093.339917017147 | 5454 | 1 | 3840/None | 0.953090096798213 | None | PASS |
| qwen:qwen3.8-max:latest:medium | kimi:kimi-k3:judge:medium | 你 | None | 0.002166023477911949 | 40428.876749938354 | 7174 | 1 | None/None | None | 49283.80216599908 | 35021.15433302242 | 5395 | 1 | 1280/None | 0.3397929386779931 | None | PASS |
| qwen:qwen3.8-max:latest:medium | qwen:qwen3.8-max:judge:medium | 你 | None | 0.002166023477911949 | 40428.876749938354 | 7174 | 1 | None/None | None | 57152.489457977936 | 61449.58729192149 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| kimi:kimi-k3:latest:medium | claude:claude-opus-5:judge:medium | 锁 | None | 0.005209003575146198 | 28195.811458979733 | 6471 | 1 | None/None | None | 41325.328917009756 | 13650.501040974632 | 738 | 1 | 2475/5210 | 1237.5 | None | PASS |
| kimi:kimi-k3:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 锁 | None | 0.005209003575146198 | 28195.811458979733 | 6471 | 1 | None/None | None | 47490.62358296942 | 34057.59024992585 | 7708 | 1 | None/None | None | None | PASS |
| kimi:kimi-k3:latest:medium | gpt:gpt-5.6-sol:judge:medium | 锁 | None | 0.005209003575146198 | 28195.811458979733 | 6471 | 1 | None/None | None | 0.0029579969123005867 | 42121.906040934846 | 6856 | 1 | None/None | None | None | PASS |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | 锁 | None | 0.005209003575146198 | 28195.811458979733 | 6471 | 1 | None/None | None | 0.0027080532163381577 | 57846.58324997872 | 5922 | 1 | 4373/None | 1.0 | None | PASS |
| kimi:kimi-k3:latest:medium | qwen:qwen3.8-max:judge:medium | 锁 | None | 0.005209003575146198 | 28195.811458979733 | 6471 | 1 | None/None | None | 57100.92454205733 | 60989.790500025265 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| gpt:gpt-5.6-sol:latest:medium | claude:claude-opus-5:judge:medium | 不 | None | 26675.104875001125 | 13562.272084061988 | 17160 | 1 | None/None | None | 0.006417045369744301 | 17255.919208051637 | 1505 | 1 | 2448/4386 | 1224.0 | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 不 | None | 26675.104875001125 | 13562.272084061988 | 17160 | 1 | None/None | None | 79204.47641599458 | 19682.747542043217 | 5381 | 1 | None/None | None | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | 不 | None | 26675.104875001125 | 13562.272084061988 | 17160 | 1 | None/None | None | 29626.80524995085 | 32008.200583979487 | 5810 | 1 | 4096/None | 0.9717674970344009 | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | kimi:kimi-k3:judge:medium | 不 | None | 26675.104875001125 | 13562.272084061988 | 17160 | 1 | None/None | None | 2908.834083005786 | 56080.73758298997 | 5833 | 1 | 1280/None | 0.3262809074687739 | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | qwen:qwen3.8-max:judge:medium | 不 | None | 26675.104875001125 | 13562.272084061988 | 17160 | 1 | None/None | None | 61083.6157919839 | 60971.11341601703 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| qwen:qwen3.8-max:latest:medium | claude:claude-opus-5:judge:medium | 锁 | None | 40442.40629195701 | 70973.44437497668 | 8241 | 1 | None/None | None | 0.004624947905540466 | 17012.480999925174 | 1224 | 1 | 2448/5048 | 1224.0 | None | PASS |
| qwen:qwen3.8-max:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 锁 | None | 40442.40629195701 | 70973.44437497668 | 8241 | 1 | None/None | None | 71558.98958398029 | 28201.212833053432 | 7216 | 1 | None/None | None | None | PASS |
| qwen:qwen3.8-max:latest:medium | gpt:gpt-5.6-sol:judge:medium | 锁 | None | 40442.40629195701 | 70973.44437497668 | 8241 | 1 | None/None | None | 17015.619582962245 | 34910.46712489333 | 6387 | 1 | None/None | None | None | PASS |
| qwen:qwen3.8-max:latest:medium | kimi:kimi-k3:judge:medium | 锁 | None | 40442.40629195701 | 70973.44437497668 | 8241 | 1 | None/None | None | 34974.558540969156 | 50339.655334013514 | 6614 | 1 | 1280/None | 0.29857709353860507 | None | PASS |
| qwen:qwen3.8-max:latest:medium | qwen:qwen3.8-max:judge:medium | 锁 | None | 40442.40629195701 | 70973.44437497668 | 8241 | 1 | None/None | None | 57233.854333055206 | 61137.551666935906 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| gemini:gemini-3-pro-preview-thinking:latest:medium | claude:claude-opus-5:judge:medium | 担 | None | 0.005082925781607628 | 28932.857499923557 | 11134 | 1 | None/None | None | 45668.59083296731 | 16634.95804206468 | 1082 | 1 | 0/7773 | 0.0 | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 担 | None | 0.005082925781607628 | 28932.857499923557 | 11134 | 1 | None/None | None | 53323.44591699075 | 21260.789250023663 | 6054 | 1 | None/None | None | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gpt:gpt-5.6-sol:judge:medium | 担 | None | 0.005082925781607628 | 28932.857499923557 | 11134 | 1 | None/None | None | 0.03462505992501974 | 56485.85279204417 | 6324 | 1 | 4608/None | 0.955421936554012 | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | kimi:kimi-k3:judge:medium | 担 | None | 0.005082925781607628 | 28932.857499923557 | 11134 | 1 | None/None | None | 0.00291608739644289 | 61214.24870798364 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| gemini:gemini-3-pro-preview-thinking:latest:medium | qwen:qwen3.8-max:judge:medium | 担 | None | 0.005082925781607628 | 28932.857499923557 | 11134 | 1 | None/None | None | 28510.35887503531 | 61167.175458977 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium |  | None | 0.002459040842950344 | 20622.030499973334 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium |  | None | 0.002459040842950344 | 20622.030499973334 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | gpt:gpt-5.6-sol:judge:medium |  | None | 0.002459040842950344 | 20622.030499973334 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | kimi:kimi-k3:judge:medium |  | None | 0.002459040842950344 | 20622.030499973334 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | qwen:qwen3.8-max:judge:medium |  | None | 0.002459040842950344 | 20622.030499973334 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| qwen:qwen3.8-max:latest:medium | claude:claude-opus-5:judge:medium | 发 | None | 0.0019170111045241356 | 79491.88508291263 | 9103 | 1 | None/None | None | 45645.16650000587 | 14301.956415991299 | 820 | 1 | 2482/4827 | 1241.0 | None | PASS |
| qwen:qwen3.8-max:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 发 | None | 0.0019170111045241356 | 79491.88508291263 | 9103 | 1 | None/None | None | 0.01016608439385891 | 20607.288458035327 | 5795 | 1 | None/None | None | None | PASS |
| qwen:qwen3.8-max:latest:medium | gpt:gpt-5.6-sol:judge:medium | 发 | None | 0.0019170111045241356 | 79491.88508291263 | 9103 | 1 | None/None | None | 62641.76887506619 | 37199.619041988626 | 5985 | 1 | None/None | None | None | PASS |
| qwen:qwen3.8-max:latest:medium | kimi:kimi-k3:judge:medium | 发 | None | 0.0019170111045241356 | 79491.88508291263 | 9103 | 1 | None/None | None | 59947.36054202076 | 51524.21629196033 | 7303 | 1 | 1280/None | 0.30497974743864664 | None | PASS |
| qwen:qwen3.8-max:latest:medium | qwen:qwen3.8-max:judge:medium | 发 | None | 0.0019170111045241356 | 79491.88508291263 | 9103 | 1 | None/None | None | 36529.91566702258 | 61366.142333019525 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| kimi:kimi-k3:latest:medium | claude:claude-opus-5:judge:medium | 你 | None | 38656.992624979466 | 31497.3951659631 | 6902 | 1 | None/None | None | 45872.6732499199 | 18061.95112504065 | 1196 | 1 | 2475/4492 | 1237.5 | None | PASS |
| kimi:kimi-k3:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 你 | None | 38656.992624979466 | 31497.3951659631 | 6902 | 1 | None/None | None | 48881.608374998905 | 20388.348417007364 | 5969 | 1 | None/None | None | None | PASS |
| kimi:kimi-k3:latest:medium | gpt:gpt-5.6-sol:judge:medium | 你 | None | 38656.992624979466 | 31497.3951659631 | 6902 | 1 | None/None | None | 49252.55283305887 | 42316.07933295891 | 6506 | 1 | None/None | None | None | PASS |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | 你 | None | 38656.992624979466 | 31497.3951659631 | 6902 | 1 | None/None | None | 0.002708984538912773 | 61010.8715420356 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| kimi:kimi-k3:latest:medium | qwen:qwen3.8-max:judge:medium | 你 | None | 38656.992624979466 | 31497.3951659631 | 6902 | 1 | None/None | None | 0.003125052899122238 | 61050.158708007075 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| gemini:gemini-3-pro-preview-thinking:latest:medium | claude:claude-opus-5:judge:medium | 连 | None | 0.004625064320862293 | 24824.02583397925 | 9931 | 1 | None/None | None | 7007.970542064868 | 13930.284333066083 | 796 | 1 | 2482/5106 | 1241.0 | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 连 | None | 0.004625064320862293 | 24824.02583397925 | 9931 | 1 | None/None | None | 20938.3500830736 | 14147.412915946916 | 5475 | 1 | None/None | None | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gpt:gpt-5.6-sol:judge:medium | 连 | None | 0.004625064320862293 | 24824.02583397925 | 9931 | 1 | None/None | None | 50014.90075001493 | 16850.297417026013 | 5348 | 1 | None/None | None | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | kimi:kimi-k3:judge:medium | 连 | None | 0.004625064320862293 | 24824.02583397925 | 9931 | 1 | None/None | None | 58721.03200003039 | 57723.90124993399 | 6279 | 1 | 4096/None | 0.9516728624535316 | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | qwen:qwen3.8-max:judge:medium | 连 | None | 0.004625064320862293 | 24824.02583397925 | 9931 | 1 | None/None | None | 93465.59433301445 | 60962.28995907586 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium | 他 | None | 0.03591692075133324 | 42515.91324992478 | None | 1 | None/None | None | 0.003208988346159458 | 50441.63362495601 | 3660 | 1 | 2482/4972 | 1241.0 | None | PASS |
| claude:claude-opus-5:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 他 | None | 0.03591692075133324 | 42515.91324992478 | None | 1 | None/None | None | 20939.313584007323 | 15732.814415940084 | 5406 | 1 | None/None | None | None | PASS |
| claude:claude-opus-5:latest:medium | gpt:gpt-5.6-sol:judge:medium | 他 | None | 0.03591692075133324 | 42515.91324992478 | None | 1 | None/None | None | 17035.21495894529 | 34931.31262506358 | 6335 | 1 | 4352/None | 0.9577464788732394 | None | PASS |
| claude:claude-opus-5:latest:medium | kimi:kimi-k3:judge:medium | 他 | None | 0.03591692075133324 | 42515.91324992478 | None | 1 | None/None | None | 35771.671665948816 | 43811.76900002174 | 6177 | 1 | 1280/None | 0.301389215917118 | None | PASS |
| claude:claude-opus-5:latest:medium | qwen:qwen3.8-max:judge:medium | 他 | None | 0.03591692075133324 | 42515.91324992478 | None | 1 | None/None | None | 61048.01079200115 | 61114.71704207361 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| gemini:gemini-3-pro-preview-thinking:latest:medium | claude:claude-opus-5:judge:medium | 你 | None | 0.0018330756574869156 | 29266.023208969273 | 11331 | 1 | None/None | None | 36672.17429110315 | 16341.540541965514 | 1532 | 1 | 2482/5259 | 1241.0 | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 你 | None | 0.0018330756574869156 | 29266.023208969273 | 11331 | 1 | None/None | None | 51966.27099998295 | 21784.728207974695 | 6047 | 1 | None/None | None | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gpt:gpt-5.6-sol:judge:medium | 你 | None | 0.0018330756574869156 | 29266.023208969273 | 11331 | 1 | None/None | None | 50441.32520793937 | 28976.49004193954 | 6231 | 1 | 4608/None | 0.9634120844658164 | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | kimi:kimi-k3:judge:medium | 你 | None | 0.0018330756574869156 | 29266.023208969273 | 11331 | 1 | None/None | None | 0.006208079867064953 | 66181.0757080093 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| gemini:gemini-3-pro-preview-thinking:latest:medium | qwen:qwen3.8-max:judge:medium | 你 | None | 0.0018330756574869156 | 29266.023208969273 | 11331 | 1 | None/None | None | 74816.04245794006 | 61212.208749959245 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| gpt:gpt-5.6-sol:latest:medium | claude:claude-opus-5:judge:medium | 我 | None | 13573.31254100427 | 17871.788250049576 | 19751 | 1 | None/None | None | 56058.77879192121 | 17486.103667062707 | 10232 | 1 | 0/28129 | 0.0 | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 我 | None | 13573.31254100427 | 17871.788250049576 | 19751 | 1 | None/None | None | 56908.12766703311 | 15464.365707943216 | 7438 | 1 | None/None | None | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | 我 | None | 13573.31254100427 | 17871.788250049576 | 19751 | 1 | None/None | None | 30037.925499957055 | 46234.54275005497 | 8982 | 1 | 6400/None | 0.9763539282990084 | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | kimi:kimi-k3:judge:medium | 我 | None | 13573.31254100427 | 17871.788250049576 | 19751 | 1 | None/None | None | 66058.54654102586 | 61511.19445904624 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| gpt:gpt-5.6-sol:latest:medium | qwen:qwen3.8-max:judge:medium | 我 | None | 13573.31254100427 | 17871.788250049576 | 19751 | 1 | None/None | None | 48342.044792021625 | 61254.8199580051 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium | 你 | None | 0.010291929356753826 | 46014.37620795332 | None | 1 | None/None | None | 44350.82358401269 | 17232.402833062224 | 7390 | 1 | 0/29195 | 0.0 | None | PASS |
| claude:claude-opus-5:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 你 | None | 0.010291929356753826 | 46014.37620795332 | None | 1 | None/None | None | 7790.412332979031 | 15590.575166977942 | 5625 | 1 | None/None | None | None | PASS |
| claude:claude-opus-5:latest:medium | gpt:gpt-5.6-sol:judge:medium | 你 | None | 0.010291929356753826 | 46014.37620795332 | None | 1 | None/None | None | 61590.26908304077 | 24314.2997919349 | 5961 | 1 | 4608/None | 0.9694929518199032 | None | PASS |
| claude:claude-opus-5:latest:medium | kimi:kimi-k3:judge:medium | 你 | None | 0.010291929356753826 | 46014.37620795332 | None | 1 | None/None | None | 0.005292007699608803 | 66121.49970897008 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | qwen:qwen3.8-max:judge:medium | 你 | None | 0.010291929356753826 | 46014.37620795332 | None | 1 | None/None | None | 36525.094332988374 | 60999.53174998518 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium |  | None | 0.017208978533744812 | 34160.99354100879 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium |  | None | 0.017208978533744812 | 34160.99354100879 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | gpt:gpt-5.6-sol:judge:medium |  | None | 0.017208978533744812 | 34160.99354100879 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | kimi:kimi-k3:judge:medium |  | None | 0.017208978533744812 | 34160.99354100879 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | qwen:qwen3.8-max:judge:medium |  | None | 0.017208978533744812 | 34160.99354100879 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| kimi:kimi-k3:latest:medium | claude:claude-opus-5:judge:medium | 能 | None | 0.0024579931050539017 | 33561.18058296852 | 6802 | 1 | None/None | None | 39284.23529106658 | 16054.852916975506 | 7628 | 1 | 0/30165 | 0.0 | None | PASS |
| kimi:kimi-k3:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 能 | None | 0.0024579931050539017 | 33561.18058296852 | 6802 | 1 | None/None | None | 42222.28645894211 | 18360.860125045292 | 5893 | 1 | None/None | None | None | PASS |
| kimi:kimi-k3:latest:medium | gpt:gpt-5.6-sol:judge:medium | 能 | None | 0.0024579931050539017 | 33561.18058296852 | 6802 | 1 | None/None | None | 92771.86899993103 | 56107.85475000739 | 7603 | 1 | 4480/None | 0.9580838323353293 | None | PASS |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | 能 | None | 0.0024579931050539017 | 33561.18058296852 | 6802 | 1 | None/None | None | 0.012291944585740566 | 61466.90454205964 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| kimi:kimi-k3:latest:medium | qwen:qwen3.8-max:judge:medium | 能 | None | 0.0024579931050539017 | 33561.18058296852 | 6802 | 1 | None/None | None | 36845.34474997781 | 61267.70645810757 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| gemini:gemini-3-pro-preview-thinking:latest:medium | claude:claude-opus-5:judge:medium | 你 | None | 0.004541012458503246 | 32341.303708031774 | 11507 | 1 | None/None | None | 82524.09687498584 | 14911.935582989827 | 865 | 1 | 2475/5433 | 1237.5 | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 你 | None | 0.004541012458503246 | 32341.303708031774 | 11507 | 1 | None/None | None | 49214.02133395895 | 33309.47495799046 | 7997 | 1 | None/None | None | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gpt:gpt-5.6-sol:judge:medium | 你 | None | 0.004541012458503246 | 32341.303708031774 | 11507 | 1 | None/None | None | 90940.04220794886 | 52835.91412496753 | 10324 | 1 | None/None | None | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | kimi:kimi-k3:judge:medium | 你 | None | 0.004541012458503246 | 32341.303708031774 | 11507 | 1 | None/None | None | 123121.25729105901 | 45902.036208077334 | 6362 | 1 | 1280/None | 0.28412874583795783 | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | qwen:qwen3.8-max:judge:medium | 你 | None | 0.004541012458503246 | 32341.303708031774 | 11507 | 1 | None/None | None | 36942.29999999516 | 61038.00725005567 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| kimi:kimi-k3:latest:medium | claude:claude-opus-5:judge:medium | 你 | None | 31507.74024997372 | 35438.966542016715 | 9013 | 1 | None/None | None | 0.005832989700138569 | 18590.723333065398 | 983 | 1 | 0/10614 | 0.0 | None | PASS |
| kimi:kimi-k3:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 你 | None | 31507.74024997372 | 35438.966542016715 | 9013 | 1 | None/None | None | 0.00300002284348011 | 22486.586624989286 | 8371 | 1 | None/None | None | None | PASS |
| kimi:kimi-k3:latest:medium | gpt:gpt-5.6-sol:judge:medium | 你 | None | 31507.74024997372 | 35438.966542016715 | 9013 | 1 | None/None | None | 0.0037909485399723053 | 50463.13450008165 | 9418 | 1 | 6656/None | 0.970686889310194 | None | PASS |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | 你 | None | 31507.74024997372 | 35438.966542016715 | 9013 | 1 | None/None | None | 0.0026669586077332497 | 61298.11850003898 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| kimi:kimi-k3:latest:medium | qwen:qwen3.8-max:judge:medium | 你 | None | 31507.74024997372 | 35438.966542016715 | 9013 | 1 | None/None | None | 0.005209003575146198 | 61546.76175001077 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| qwen:qwen3.8-max:latest:medium | claude:claude-opus-5:judge:medium | 你 | None | 0.005832989700138569 | 53429.699875065126 | 10320 | 1 | None/None | None | 0.003500026650726795 | 17258.497875067405 | 930 | 1 | 2475/7879 | 1237.5 | None | PASS |
| qwen:qwen3.8-max:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 你 | None | 0.005832989700138569 | 53429.699875065126 | 10320 | 1 | None/None | None | 0.002583954483270645 | 19548.553374945186 | 7972 | 1 | None/None | None | None | PASS |
| qwen:qwen3.8-max:latest:medium | gpt:gpt-5.6-sol:judge:medium | 你 | None | 0.005832989700138569 | 53429.699875065126 | 10320 | 1 | None/None | None | 0.002874992787837982 | 31128.29058407806 | 8231 | 1 | None/None | None | None | PASS |
| qwen:qwen3.8-max:latest:medium | kimi:kimi-k3:judge:medium | 你 | None | 0.005832989700138569 | 53429.699875065126 | 10320 | 1 | None/None | None | 0.007582944817841053 | 61611.00399994757 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| qwen:qwen3.8-max:latest:medium | qwen:qwen3.8-max:judge:medium | 你 | None | 0.005832989700138569 | 53429.699875065126 | 10320 | 1 | None/None | None | 0.043791020289063454 | 61390.302833984606 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| gemini:gemini-3-pro-preview-thinking:latest:medium | claude:claude-opus-5:judge:medium | 你 | None | 0.004083034582436085 | 43176.18483409751 | 10995 | 1 | None/None | None | 14364.353417069651 | 14923.978292034008 | 889 | 1 | 2482/5541 | 1241.0 | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 你 | None | 0.004083034582436085 | 43176.18483409751 | 10995 | 1 | None/None | None | 29288.463749922812 | 23402.080707950518 | 6712 | 1 | None/None | None | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gpt:gpt-5.6-sol:judge:medium | 你 | None | 0.004083034582436085 | 43176.18483409751 | 10995 | 1 | None/None | None | 24338.7571250787 | 40017.99470803235 | 6467 | 1 | None/None | None | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | kimi:kimi-k3:judge:medium | 你 | None | 0.004083034582436085 | 43176.18483409751 | 10995 | 1 | None/None | None | 31161.98808304034 | 60973.66575000342 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| gemini:gemini-3-pro-preview-thinking:latest:medium | qwen:qwen3.8-max:judge:medium | 你 | None | 0.004083034582436085 | 43176.18483409751 | 10995 | 1 | None/None | None | 47048.3947499888 | 61049.74545806181 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| gemini:gemini-3-pro-preview-thinking:latest:medium | claude:claude-opus-5:judge:medium | 发 | None | 0.002084067091345787 | 25112.634374992922 | 10563 | 1 | None/None | None | 94994.76575001609 | 15088.468458969146 | 1040 | 1 | 2482/4911 | 1241.0 | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 发 | None | 0.002084067091345787 | 25112.634374992922 | 10563 | 1 | None/None | None | 67254.82587504666 | 20134.069583029486 | 5886 | 1 | None/None | None | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gpt:gpt-5.6-sol:judge:medium | 发 | None | 0.002084067091345787 | 25112.634374992922 | 10563 | 1 | None/None | None | 131954.72054195125 | 43527.47600001749 | 6606 | 1 | None/None | None | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | kimi:kimi-k3:judge:medium | 发 | None | 0.002084067091345787 | 25112.634374992922 | 10563 | 1 | None/None | None | 73750.9545419598 | 50201.271041994914 | 6353 | 1 | 1280/None | 0.30303030303030304 | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | qwen:qwen3.8-max:judge:medium | 发 | None | 0.002084067091345787 | 25112.634374992922 | 10563 | 1 | None/None | None | 0.005209003575146198 | 61217.491541057825 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| gpt:gpt-5.6-sol:latest:medium | claude:claude-opus-5:judge:medium | 你 | None | 0.0020419247448444366 | 33220.660499995574 | 16997 | 1 | None/None | None | 79583.02795898635 | 15410.697582992725 | 6558 | 1 | 0/30914 | 0.0 | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 你 | None | 0.0020419247448444366 | 33220.660499995574 | 16997 | 1 | None/None | None | 110083.89095810708 | 32051.433959044516 | 5135 | 1 | None/None | None | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | 你 | None | 0.0020419247448444366 | 33220.660499995574 | 16997 | 1 | None/None | None | 52295.97674997058 | 37069.562791031785 | 5886 | 1 | None/None | None | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | kimi:kimi-k3:judge:medium | 你 | None | 0.0020419247448444366 | 33220.660499995574 | 16997 | 1 | None/None | None | 0.005624955520033836 | 58968.890791991726 | 5508 | 1 | None/None | None | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | qwen:qwen3.8-max:judge:medium | 你 | None | 0.0020419247448444366 | 33220.660499995574 | 16997 | 1 | None/None | None | 0.00400003045797348 | 61067.25454097614 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
