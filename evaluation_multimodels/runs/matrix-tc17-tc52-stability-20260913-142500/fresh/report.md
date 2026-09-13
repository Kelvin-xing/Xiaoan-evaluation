# Multimodel XiaoAn evaluation

Case-macro dynamic weighted score (0-3); incomplete or unavailable cases are excluded. Dimension tables show turn-score medians.

| XiaoAn subject \ Judge | claude:claude-opus-5:judge:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | gpt:gpt-5.6-sol:judge:medium | kimi:kimi-k3:judge:medium | qwen:qwen3.8-max:judge:medium |
| --- | ---: | ---: | ---: | ---: | ---: |
| claude:claude-opus-5:latest:medium | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE |
| gemini:gemini-3-pro-preview-thinking:latest:medium | 1.9789 | 2.8280 | 1.6582 | UNAVAILABLE | UNAVAILABLE |
| gpt:gpt-5.6-sol:latest:medium | 1.8672 | 2.5828 | 1.9195 | 1.9827 | UNAVAILABLE |
| kimi:kimi-k3:latest:medium | 1.9050 | 2.4323 | 1.5068 | UNAVAILABLE | UNAVAILABLE |
| qwen:qwen3.8-max:latest:medium | 1.5439 | 2.9134 | 1.6631 | 2.3722 | UNAVAILABLE |

## Measurement contract

Primary eligible: 99; self-judging isolated: 0; operationally unavailable: 51.
Semantic oracle: {"version": "semantic-oracle/v1", "eligible_turns": 36, "missing_turns": 114, "required": {"n": 72, "evaluated_n": 66, "uncertain_n": 6, "violation_rate": 0.3787878787878788, "satisfaction_rate": 0.6212121212121212}, "forbidden": {"n": 72, "evaluated_n": 72, "uncertain_n": 0, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "status": "AVAILABLE", "verdict": "FAIL", "unapproved_excluded_n": 0, "by_subject_judge": [{"subject": "{'provider': 'claude', 'model': 'claude-opus-5', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'claude:claude-opus-5:latest:medium'}", "judge": "{'provider': 'claude', 'model': 'claude-opus-5', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'claude:claude-opus-5:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 0, "missing_turns": 6, "required": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "forbidden": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "status": "UNAVAILABLE", "verdict": "UNAVAILABLE"}, {"subject": "{'provider': 'claude', 'model': 'claude-opus-5', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'claude:claude-opus-5:latest:medium'}", "judge": "{'provider': 'gemini', 'model': 'gemini-3-pro-preview-thinking', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'gemini:gemini-3-pro-preview-thinking:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 0, "missing_turns": 6, "required": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "forbidden": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "status": "UNAVAILABLE", "verdict": "UNAVAILABLE"}, {"subject": "{'provider': 'claude', 'model': 'claude-opus-5', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'claude:claude-opus-5:latest:medium'}", "judge": "{'provider': 'gpt', 'model': 'gpt-5.6-sol', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'gpt:gpt-5.6-sol:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 2, "missing_turns": 4, "required": {"n": 4, "evaluated_n": 4, "uncertain_n": 0, "violation_rate": 0.5, "satisfaction_rate": 0.5}, "forbidden": {"n": 4, "evaluated_n": 4, "uncertain_n": 0, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "status": "AVAILABLE", "verdict": "FAIL"}, {"subject": "{'provider': 'claude', 'model': 'claude-opus-5', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'claude:claude-opus-5:latest:medium'}", "judge": "{'provider': 'kimi', 'model': 'kimi-k3', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'kimi:kimi-k3:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 1, "missing_turns": 5, "required": {"n": 2, "evaluated_n": 2, "uncertain_n": 0, "violation_rate": 0.5, "satisfaction_rate": 0.5}, "forbidden": {"n": 2, "evaluated_n": 2, "uncertain_n": 0, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "status": "AVAILABLE", "verdict": "FAIL"}, {"subject": "{'provider': 'claude', 'model': 'claude-opus-5', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'claude:claude-opus-5:latest:medium'}", "judge": "{'provider': 'qwen', 'model': 'qwen3.8-max', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'qwen:qwen3.8-max:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 0, "missing_turns": 6, "required": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "forbidden": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "status": "UNAVAILABLE", "verdict": "UNAVAILABLE"}, {"subject": "{'provider': 'gemini', 'model': 'gemini-3-pro-preview-thinking', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'gemini:gemini-3-pro-preview-thinking:latest:medium'}", "judge": "{'provider': 'claude', 'model': 'claude-opus-5', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'claude:claude-opus-5:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 0, "missing_turns": 6, "required": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "forbidden": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "status": "UNAVAILABLE", "verdict": "UNAVAILABLE"}, {"subject": "{'provider': 'gemini', 'model': 'gemini-3-pro-preview-thinking', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'gemini:gemini-3-pro-preview-thinking:latest:medium'}", "judge": "{'provider': 'gemini', 'model': 'gemini-3-pro-preview-thinking', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'gemini:gemini-3-pro-preview-thinking:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 1, "missing_turns": 5, "required": {"n": 2, "evaluated_n": 2, "uncertain_n": 0, "violation_rate": 0.5, "satisfaction_rate": 0.5}, "forbidden": {"n": 2, "evaluated_n": 2, "uncertain_n": 0, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "status": "AVAILABLE", "verdict": "FAIL"}, {"subject": "{'provider': 'gemini', 'model': 'gemini-3-pro-preview-thinking', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'gemini:gemini-3-pro-preview-thinking:latest:medium'}", "judge": "{'provider': 'gpt', 'model': 'gpt-5.6-sol', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'gpt:gpt-5.6-sol:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 5, "missing_turns": 1, "required": {"n": 10, "evaluated_n": 10, "uncertain_n": 0, "violation_rate": 0.4, "satisfaction_rate": 0.6}, "forbidden": {"n": 10, "evaluated_n": 10, "uncertain_n": 0, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "status": "AVAILABLE", "verdict": "FAIL"}, {"subject": "{'provider': 'gemini', 'model': 'gemini-3-pro-preview-thinking', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'gemini:gemini-3-pro-preview-thinking:latest:medium'}", "judge": "{'provider': 'kimi', 'model': 'kimi-k3', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'kimi:kimi-k3:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 2, "missing_turns": 4, "required": {"n": 4, "evaluated_n": 3, "uncertain_n": 1, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "forbidden": {"n": 4, "evaluated_n": 4, "uncertain_n": 0, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "status": "AVAILABLE", "verdict": "UNAVAILABLE"}, {"subject": "{'provider': 'gemini', 'model': 'gemini-3-pro-preview-thinking', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'gemini:gemini-3-pro-preview-thinking:latest:medium'}", "judge": "{'provider': 'qwen', 'model': 'qwen3.8-max', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'qwen:qwen3.8-max:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 0, "missing_turns": 6, "required": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "forbidden": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "status": "UNAVAILABLE", "verdict": "UNAVAILABLE"}, {"subject": "{'provider': 'gpt', 'model': 'gpt-5.6-sol', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'gpt:gpt-5.6-sol:latest:medium'}", "judge": "{'provider': 'claude', 'model': 'claude-opus-5', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'claude:claude-opus-5:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 0, "missing_turns": 6, "required": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "forbidden": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "status": "UNAVAILABLE", "verdict": "UNAVAILABLE"}, {"subject": "{'provider': 'gpt', 'model': 'gpt-5.6-sol', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'gpt:gpt-5.6-sol:latest:medium'}", "judge": "{'provider': 'gemini', 'model': 'gemini-3-pro-preview-thinking', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'gemini:gemini-3-pro-preview-thinking:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 1, "missing_turns": 5, "required": {"n": 2, "evaluated_n": 2, "uncertain_n": 0, "violation_rate": 0.5, "satisfaction_rate": 0.5}, "forbidden": {"n": 2, "evaluated_n": 2, "uncertain_n": 0, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "status": "AVAILABLE", "verdict": "FAIL"}, {"subject": "{'provider': 'gpt', 'model': 'gpt-5.6-sol', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'gpt:gpt-5.6-sol:latest:medium'}", "judge": "{'provider': 'gpt', 'model': 'gpt-5.6-sol', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'gpt:gpt-5.6-sol:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 5, "missing_turns": 1, "required": {"n": 10, "evaluated_n": 9, "uncertain_n": 1, "violation_rate": 0.4444444444444444, "satisfaction_rate": 0.5555555555555556}, "forbidden": {"n": 10, "evaluated_n": 10, "uncertain_n": 0, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "status": "AVAILABLE", "verdict": "FAIL"}, {"subject": "{'provider': 'gpt', 'model': 'gpt-5.6-sol', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'gpt:gpt-5.6-sol:latest:medium'}", "judge": "{'provider': 'kimi', 'model': 'kimi-k3', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'kimi:kimi-k3:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 1, "missing_turns": 5, "required": {"n": 2, "evaluated_n": 1, "uncertain_n": 1, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "forbidden": {"n": 2, "evaluated_n": 2, "uncertain_n": 0, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "status": "AVAILABLE", "verdict": "UNAVAILABLE"}, {"subject": "{'provider': 'gpt', 'model': 'gpt-5.6-sol', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'gpt:gpt-5.6-sol:latest:medium'}", "judge": "{'provider': 'qwen', 'model': 'qwen3.8-max', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'qwen:qwen3.8-max:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 0, "missing_turns": 6, "required": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "forbidden": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "status": "UNAVAILABLE", "verdict": "UNAVAILABLE"}, {"subject": "{'provider': 'kimi', 'model': 'kimi-k3', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'kimi:kimi-k3:latest:medium'}", "judge": "{'provider': 'claude', 'model': 'claude-opus-5', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'claude:claude-opus-5:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 1, "missing_turns": 5, "required": {"n": 2, "evaluated_n": 2, "uncertain_n": 0, "violation_rate": 1.0, "satisfaction_rate": 0.0}, "forbidden": {"n": 2, "evaluated_n": 2, "uncertain_n": 0, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "status": "AVAILABLE", "verdict": "FAIL"}, {"subject": "{'provider': 'kimi', 'model': 'kimi-k3', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'kimi:kimi-k3:latest:medium'}", "judge": "{'provider': 'gemini', 'model': 'gemini-3-pro-preview-thinking', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'gemini:gemini-3-pro-preview-thinking:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 0, "missing_turns": 6, "required": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "forbidden": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "status": "UNAVAILABLE", "verdict": "UNAVAILABLE"}, {"subject": "{'provider': 'kimi', 'model': 'kimi-k3', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'kimi:kimi-k3:latest:medium'}", "judge": "{'provider': 'gpt', 'model': 'gpt-5.6-sol', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'gpt:gpt-5.6-sol:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 6, "missing_turns": 0, "required": {"n": 12, "evaluated_n": 12, "uncertain_n": 0, "violation_rate": 0.4166666666666667, "satisfaction_rate": 0.5833333333333333}, "forbidden": {"n": 12, "evaluated_n": 12, "uncertain_n": 0, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "status": "AVAILABLE", "verdict": "FAIL"}, {"subject": "{'provider': 'kimi', 'model': 'kimi-k3', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'kimi:kimi-k3:latest:medium'}", "judge": "{'provider': 'kimi', 'model': 'kimi-k3', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'kimi:kimi-k3:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 2, "missing_turns": 4, "required": {"n": 4, "evaluated_n": 3, "uncertain_n": 1, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "forbidden": {"n": 4, "evaluated_n": 4, "uncertain_n": 0, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "status": "AVAILABLE", "verdict": "UNAVAILABLE"}, {"subject": "{'provider': 'kimi', 'model': 'kimi-k3', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'kimi:kimi-k3:latest:medium'}", "judge": "{'provider': 'qwen', 'model': 'qwen3.8-max', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'qwen:qwen3.8-max:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 0, "missing_turns": 6, "required": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "forbidden": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "status": "UNAVAILABLE", "verdict": "UNAVAILABLE"}, {"subject": "{'provider': 'qwen', 'model': 'qwen3.8-max', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'qwen:qwen3.8-max:latest:medium'}", "judge": "{'provider': 'claude', 'model': 'claude-opus-5', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'claude:claude-opus-5:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 0, "missing_turns": 6, "required": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "forbidden": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "status": "UNAVAILABLE", "verdict": "UNAVAILABLE"}, {"subject": "{'provider': 'qwen', 'model': 'qwen3.8-max', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'qwen:qwen3.8-max:latest:medium'}", "judge": "{'provider': 'gemini', 'model': 'gemini-3-pro-preview-thinking', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'gemini:gemini-3-pro-preview-thinking:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 1, "missing_turns": 5, "required": {"n": 2, "evaluated_n": 1, "uncertain_n": 1, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "forbidden": {"n": 2, "evaluated_n": 2, "uncertain_n": 0, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "status": "AVAILABLE", "verdict": "UNAVAILABLE"}, {"subject": "{'provider': 'qwen', 'model': 'qwen3.8-max', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'qwen:qwen3.8-max:latest:medium'}", "judge": "{'provider': 'gpt', 'model': 'gpt-5.6-sol', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'gpt:gpt-5.6-sol:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 5, "missing_turns": 1, "required": {"n": 10, "evaluated_n": 10, "uncertain_n": 0, "violation_rate": 0.4, "satisfaction_rate": 0.6}, "forbidden": {"n": 10, "evaluated_n": 10, "uncertain_n": 0, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "status": "AVAILABLE", "verdict": "FAIL"}, {"subject": "{'provider': 'qwen', 'model': 'qwen3.8-max', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'qwen:qwen3.8-max:latest:medium'}", "judge": "{'provider': 'kimi', 'model': 'kimi-k3', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'kimi:kimi-k3:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 3, "missing_turns": 3, "required": {"n": 6, "evaluated_n": 5, "uncertain_n": 1, "violation_rate": 0.2, "satisfaction_rate": 0.8}, "forbidden": {"n": 6, "evaluated_n": 6, "uncertain_n": 0, "violation_rate": 0.0, "satisfaction_rate": 1.0}, "status": "AVAILABLE", "verdict": "FAIL"}, {"subject": "{'provider': 'qwen', 'model': 'qwen3.8-max', 'tier': 'latest', 'reasoning_effort': 'medium', 'id': 'qwen:qwen3.8-max:latest:medium'}", "judge": "{'provider': 'qwen', 'model': 'qwen3.8-max', 'tier': 'judge', 'reasoning_effort': 'medium', 'id': 'qwen:qwen3.8-max:judge:medium'}", "version": "semantic-oracle/v1", "eligible_turns": 0, "missing_turns": 6, "required": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "forbidden": {"n": 0, "evaluated_n": 0, "uncertain_n": 0, "violation_rate": null, "satisfaction_rate": null}, "status": "UNAVAILABLE", "verdict": "UNAVAILABLE"}]}
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
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | TC-17 | 2 | 2.0000000000000004 | PASS |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium | TC-17 | 4 | None | UNAVAILABLE |
| qwen:qwen3.8-max:latest:medium | qwen:qwen3.8-max:judge:medium | TC-17 | 3 | None | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium | TC-17 | 1 | None | UNAVAILABLE |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | TC-17 | 4 | 1.7292576419213976 | PASS |
| qwen:qwen3.8-max:latest:medium | qwen:qwen3.8-max:judge:medium | TC-52 | 2 | None | UNAVAILABLE |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | TC-52 | 1 | 2.116883116883117 | PASS |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | TC-17 | 3 | None | UNAVAILABLE |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | TC-17 | 1 | 1.921397379912664 | PASS |
| qwen:qwen3.8-max:latest:medium | qwen:qwen3.8-max:judge:medium | TC-52 | 1 | None | UNAVAILABLE |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | TC-17 | 2 | 2.270742358078603 | PASS |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | TC-52 | 2 | 1.8484848484848484 | PASS |
| qwen:qwen3.8-max:latest:medium | qwen:qwen3.8-max:judge:medium | TC-17 | 2 | None | UNAVAILABLE |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | TC-17 | 3 | 3.0000000000000004 | PASS |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium | TC-52 | 1 | None | UNAVAILABLE |
| qwen:qwen3.8-max:latest:medium | qwen:qwen3.8-max:judge:medium | TC-17 | 1 | None | UNAVAILABLE |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | TC-52 | 2 | None | UNAVAILABLE |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | TC-17 | 2 | 3.0000000000000004 | PASS |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium | TC-17 | 2 | 2.414847161572053 | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | TC-52 | 1 | 2.6536796536796534 | PASS |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | TC-17 | 3 | 2.0000000000000004 | PASS |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium | TC-17 | 3 | 2.1091703056768565 | PASS |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium | TC-52 | 2 | None | UNAVAILABLE |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | TC-17 | 1 | 2.5065502183406116 | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | TC-17 | 4 | 3.0000000000000004 | PASS |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | TC-17 | 4 | 2.270742358078603 | PASS |
| qwen:qwen3.8-max:latest:medium | qwen:qwen3.8-max:judge:medium | TC-17 | 4 | None | UNAVAILABLE |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | TC-52 | 2 | 2.887445887445887 | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | TC-17 | 1 | 2.5414847161572056 | PASS |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | TC-52 | 1 | 2.004329004329004 | PASS |

## Dimension medians by subject

| Subject | 丰富性 | 包容性与可及性 | 基础能力 | 求助转介 | 法律维权 | 行动赋权 | 表达能力 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| claude:claude-opus-5:latest:medium | 2.0000 | 2.5000 | 3.0000 | 1.5000 | 2.0000 | 2.0000 | 3.0000 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | 1.0000 | 3.0000 | 3.0000 | 1.5000 | 1.5000 | 2.0000 | 3.0000 |
| gpt:gpt-5.6-sol:latest:medium | 2.0000 | 2.0000 | 3.0000 | 1.0000 | 1.0000 | 2.0000 | 3.0000 |
| kimi:kimi-k3:latest:medium | 2.0000 | 2.0000 | 3.0000 | 1.0000 | 1.0000 | 2.0000 | 3.0000 |
| qwen:qwen3.8-max:latest:medium | 2.0000 | 2.0000 | 3.0000 | 1.5000 | 1.5000 | 2.0000 | 3.0000 |

## Dimension medians by subject and judge

| Subject | Judge | 丰富性 | 包容性与可及性 | 基础能力 | 求助转介 | 法律维权 | 行动赋权 | 表达能力 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium | 2.0000 | 3.0000 | 3.0000 | 1.0000 | 1.0000 | 2.5000 | 3.0000 |
| claude:claude-opus-5:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 3.0000 | 3.0000 | 3.0000 | 2.5000 | 3.0000 | 3.0000 | 3.0000 |
| claude:claude-opus-5:latest:medium | gpt:gpt-5.6-sol:judge:medium | 1.0000 | 1.5000 | 2.5000 | 0.5000 | 0.5000 | 1.5000 | 2.5000 |
| claude:claude-opus-5:latest:medium | kimi:kimi-k3:judge:medium | 2.0000 | 2.0000 | 3.0000 | 1.5000 | 2.0000 | 2.0000 | 3.0000 |
| claude:claude-opus-5:latest:medium | qwen:qwen3.8-max:judge:medium | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE |
| gemini:gemini-3-pro-preview-thinking:latest:medium | claude:claude-opus-5:judge:medium | 1.0000 | 2.5000 | 3.0000 | 0.0000 | 0.0000 | 2.5000 | 3.0000 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 3.0000 | 3.0000 | 3.0000 | 3.0000 | 3.0000 | 3.0000 | 3.0000 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gpt:gpt-5.6-sol:judge:medium | 1.0000 | 2.0000 | 2.5000 | 1.0000 | 1.0000 | 2.0000 | 3.0000 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | kimi:kimi-k3:judge:medium | 2.0000 | 3.0000 | 3.0000 | 2.0000 | 2.0000 | 2.5000 | 3.0000 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | qwen:qwen3.8-max:judge:medium | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE |
| gpt:gpt-5.6-sol:latest:medium | claude:claude-opus-5:judge:medium | 1.5000 | 2.5000 | 3.0000 | 0.0000 | 0.0000 | 2.5000 | 3.0000 |
| gpt:gpt-5.6-sol:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 3.0000 | 3.0000 | 3.0000 | 2.0000 | 2.5000 | 3.0000 | 3.0000 |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | 2.0000 | 2.0000 | 2.5000 | 1.0000 | 1.0000 | 2.0000 | 3.0000 |
| gpt:gpt-5.6-sol:latest:medium | kimi:kimi-k3:judge:medium | 2.0000 | 2.0000 | 2.0000 | 2.0000 | 2.0000 | 2.0000 | 3.0000 |
| gpt:gpt-5.6-sol:latest:medium | qwen:qwen3.8-max:judge:medium | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE |
| kimi:kimi-k3:latest:medium | claude:claude-opus-5:judge:medium | 1.5000 | 3.0000 | 3.0000 | 0.0000 | 0.0000 | 2.5000 | 3.0000 |
| kimi:kimi-k3:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 2.0000 | 3.0000 | 3.0000 | 3.0000 | 3.0000 | 2.5000 | 3.0000 |
| kimi:kimi-k3:latest:medium | gpt:gpt-5.6-sol:judge:medium | 1.0000 | 1.5000 | 2.0000 | 1.0000 | 1.0000 | 1.5000 | 3.0000 |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | 2.0000 | 2.0000 | 3.0000 | 2.0000 | 2.0000 | 2.0000 | 3.0000 |
| kimi:kimi-k3:latest:medium | qwen:qwen3.8-max:judge:medium | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE |
| qwen:qwen3.8-max:latest:medium | claude:claude-opus-5:judge:medium | 1.0000 | 2.0000 | 3.0000 | 0.0000 | 0.0000 | 2.0000 | 3.0000 |
| qwen:qwen3.8-max:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 3.0000 | 3.0000 | 3.0000 | 3.0000 | 3.0000 | 3.0000 | 3.0000 |
| qwen:qwen3.8-max:latest:medium | gpt:gpt-5.6-sol:judge:medium | 1.0000 | 2.0000 | 2.0000 | 0.5000 | 0.5000 | 2.0000 | 3.0000 |
| qwen:qwen3.8-max:latest:medium | kimi:kimi-k3:judge:medium | 2.0000 | 2.5000 | 3.0000 | 2.0000 | 2.0000 | 2.0000 | 3.0000 |
| qwen:qwen3.8-max:latest:medium | qwen:qwen3.8-max:judge:medium | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE |

## Dimension distribution by subject and judge

| Subject | Judge | Dimension | Median | MAD | IQR | Range | N |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium | 丰富性 | 2.0 | 0.0 | 0.0 | 0.0 | 2 |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium | 包容性与可及性 | 3.0 | 0.0 | 0.0 | 0.0 | 2 |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium | 基础能力 | 3.0 | 0.0 | 0.0 | 0.0 | 2 |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium | 求助转介 | 1.0 | 1.0 | 2.0 | 2.0 | 2 |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium | 法律维权 | 1.0 | 1.0 | 2.0 | 2.0 | 2 |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium | 行动赋权 | 2.5 | 0.5 | 1.0 | 1.0 | 2 |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 2 |
| claude:claude-opus-5:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 丰富性 | 3.0 | 0.0 | 0.0 | 0.0 | 2 |
| claude:claude-opus-5:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 包容性与可及性 | 3.0 | 0.0 | 0.0 | 0.0 | 2 |
| claude:claude-opus-5:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 基础能力 | 3.0 | 0.0 | 0.0 | 0.0 | 2 |
| claude:claude-opus-5:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 求助转介 | 2.5 | 0.5 | 1.0 | 1.0 | 2 |
| claude:claude-opus-5:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 法律维权 | 3.0 | 0.0 | 0.0 | 0.0 | 2 |
| claude:claude-opus-5:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 行动赋权 | 3.0 | 0.0 | 0.0 | 0.0 | 2 |
| claude:claude-opus-5:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 2 |
| claude:claude-opus-5:latest:medium | gpt:gpt-5.6-sol:judge:medium | 丰富性 | 1.0 | 0.0 | 0.0 | 0.0 | 2 |
| claude:claude-opus-5:latest:medium | gpt:gpt-5.6-sol:judge:medium | 包容性与可及性 | 1.5 | 0.5 | 1.0 | 1.0 | 2 |
| claude:claude-opus-5:latest:medium | gpt:gpt-5.6-sol:judge:medium | 基础能力 | 2.5 | 0.5 | 1.0 | 1.0 | 2 |
| claude:claude-opus-5:latest:medium | gpt:gpt-5.6-sol:judge:medium | 求助转介 | 0.5 | 0.5 | 1.0 | 1.0 | 2 |
| claude:claude-opus-5:latest:medium | gpt:gpt-5.6-sol:judge:medium | 法律维权 | 0.5 | 0.5 | 1.0 | 1.0 | 2 |
| claude:claude-opus-5:latest:medium | gpt:gpt-5.6-sol:judge:medium | 行动赋权 | 1.5 | 0.5 | 1.0 | 1.0 | 2 |
| claude:claude-opus-5:latest:medium | gpt:gpt-5.6-sol:judge:medium | 表达能力 | 2.5 | 0.5 | 1.0 | 1.0 | 2 |
| claude:claude-opus-5:latest:medium | kimi:kimi-k3:judge:medium | 丰富性 | 2.0 | 0.0 | 0.0 | 0.0 | 2 |
| claude:claude-opus-5:latest:medium | kimi:kimi-k3:judge:medium | 包容性与可及性 | 2.0 | 0.0 | 0.0 | 0.0 | 2 |
| claude:claude-opus-5:latest:medium | kimi:kimi-k3:judge:medium | 基础能力 | 3.0 | 0.0 | 0.0 | 0.0 | 2 |
| claude:claude-opus-5:latest:medium | kimi:kimi-k3:judge:medium | 求助转介 | 1.5 | 0.5 | 1.0 | 1.0 | 2 |
| claude:claude-opus-5:latest:medium | kimi:kimi-k3:judge:medium | 法律维权 | 2.0 | 0.0 | 0.0 | 0.0 | 2 |
| claude:claude-opus-5:latest:medium | kimi:kimi-k3:judge:medium | 行动赋权 | 2.0 | 0.0 | 0.0 | 0.0 | 2 |
| claude:claude-opus-5:latest:medium | kimi:kimi-k3:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 2 |
| claude:claude-opus-5:latest:medium | qwen:qwen3.8-max:judge:medium | 丰富性 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| claude:claude-opus-5:latest:medium | qwen:qwen3.8-max:judge:medium | 包容性与可及性 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| claude:claude-opus-5:latest:medium | qwen:qwen3.8-max:judge:medium | 基础能力 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| claude:claude-opus-5:latest:medium | qwen:qwen3.8-max:judge:medium | 求助转介 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| claude:claude-opus-5:latest:medium | qwen:qwen3.8-max:judge:medium | 法律维权 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| claude:claude-opus-5:latest:medium | qwen:qwen3.8-max:judge:medium | 行动赋权 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| claude:claude-opus-5:latest:medium | qwen:qwen3.8-max:judge:medium | 表达能力 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | claude:claude-opus-5:judge:medium | 丰富性 | 1.0 | 0.0 | 0.0 | 3.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | claude:claude-opus-5:judge:medium | 包容性与可及性 | 2.5 | 0.5 | 1.0 | 1.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | claude:claude-opus-5:judge:medium | 基础能力 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | claude:claude-opus-5:judge:medium | 求助转介 | 0.0 | 0.0 | 0.0 | 3.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | claude:claude-opus-5:judge:medium | 法律维权 | 0.0 | 0.0 | 0.0 | 3.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | claude:claude-opus-5:judge:medium | 行动赋权 | 2.5 | 0.5 | 1.0 | 1.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | claude:claude-opus-5:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 丰富性 | 3.0 | 0.0 | 1.0 | 1.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 包容性与可及性 | 3.0 | 0.0 | 0.0 | 1.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 基础能力 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 求助转介 | 3.0 | 0.0 | 1.0 | 1.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 法律维权 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 行动赋权 | 3.0 | 0.0 | 1.0 | 1.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gpt:gpt-5.6-sol:judge:medium | 丰富性 | 1.0 | 0.0 | 0.0 | 0.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gpt:gpt-5.6-sol:judge:medium | 包容性与可及性 | 2.0 | 0.0 | 0.0 | 1.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gpt:gpt-5.6-sol:judge:medium | 基础能力 | 2.5 | 0.5 | 1.0 | 1.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gpt:gpt-5.6-sol:judge:medium | 求助转介 | 1.0 | 0.0 | 1.0 | 1.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gpt:gpt-5.6-sol:judge:medium | 法律维权 | 1.0 | 0.0 | 1.0 | 1.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gpt:gpt-5.6-sol:judge:medium | 行动赋权 | 2.0 | 0.0 | 0.0 | 1.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gpt:gpt-5.6-sol:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | kimi:kimi-k3:judge:medium | 丰富性 | 2.0 | 0.0 | 0.5 | 1.0 | 4 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | kimi:kimi-k3:judge:medium | 包容性与可及性 | 3.0 | 0.0 | 0.0 | 0.0 | 4 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | kimi:kimi-k3:judge:medium | 基础能力 | 3.0 | 0.0 | 0.0 | 0.0 | 4 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | kimi:kimi-k3:judge:medium | 求助转介 | 2.0 | 0.0 | 0.0 | 0.0 | 4 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | kimi:kimi-k3:judge:medium | 法律维权 | 2.0 | 0.0 | 0.0 | 0.0 | 4 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | kimi:kimi-k3:judge:medium | 行动赋权 | 2.5 | 0.5 | 1.0 | 1.0 | 4 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | kimi:kimi-k3:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 4 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | qwen:qwen3.8-max:judge:medium | 丰富性 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | qwen:qwen3.8-max:judge:medium | 包容性与可及性 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | qwen:qwen3.8-max:judge:medium | 基础能力 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | qwen:qwen3.8-max:judge:medium | 求助转介 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | qwen:qwen3.8-max:judge:medium | 法律维权 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | qwen:qwen3.8-max:judge:medium | 行动赋权 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| gemini:gemini-3-pro-preview-thinking:latest:medium | qwen:qwen3.8-max:judge:medium | 表达能力 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| gpt:gpt-5.6-sol:latest:medium | claude:claude-opus-5:judge:medium | 丰富性 | 1.5 | 0.5 | 1.0 | 1.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | claude:claude-opus-5:judge:medium | 包容性与可及性 | 2.5 | 0.5 | 1.0 | 1.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | claude:claude-opus-5:judge:medium | 基础能力 | 3.0 | 0.0 | 0.0 | 1.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | claude:claude-opus-5:judge:medium | 求助转介 | 0.0 | 0.0 | 0.0 | 0.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | claude:claude-opus-5:judge:medium | 法律维权 | 0.0 | 0.0 | 0.0 | 0.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | claude:claude-opus-5:judge:medium | 行动赋权 | 2.5 | 0.5 | 1.0 | 1.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | claude:claude-opus-5:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 丰富性 | 3.0 | 0.0 | 1.0 | 1.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 包容性与可及性 | 3.0 | 0.0 | 0.0 | 1.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 基础能力 | 3.0 | 0.0 | 1.0 | 1.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 求助转介 | 2.0 | 0.0 | 1.0 | 1.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 法律维权 | 2.5 | 0.5 | 1.0 | 1.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 行动赋权 | 3.0 | 0.0 | 0.0 | 1.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | 丰富性 | 2.0 | 0.0 | 1.0 | 1.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | 包容性与可及性 | 2.0 | 0.0 | 0.0 | 0.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | 基础能力 | 2.5 | 0.5 | 1.0 | 1.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | 求助转介 | 1.0 | 0.0 | 0.0 | 0.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | 法律维权 | 1.0 | 0.0 | 0.0 | 1.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | 行动赋权 | 2.0 | 0.0 | 0.0 | 0.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| gpt:gpt-5.6-sol:latest:medium | kimi:kimi-k3:judge:medium | 丰富性 | 2.0 | 0.0 | 0.0 | 0.0 | 5 |
| gpt:gpt-5.6-sol:latest:medium | kimi:kimi-k3:judge:medium | 包容性与可及性 | 2.0 | 0.0 | 0.0 | 0.0 | 5 |
| gpt:gpt-5.6-sol:latest:medium | kimi:kimi-k3:judge:medium | 基础能力 | 2.0 | 0.0 | 1.0 | 1.0 | 5 |
| gpt:gpt-5.6-sol:latest:medium | kimi:kimi-k3:judge:medium | 求助转介 | 2.0 | 0.0 | 1.0 | 1.0 | 5 |
| gpt:gpt-5.6-sol:latest:medium | kimi:kimi-k3:judge:medium | 法律维权 | 2.0 | 0.0 | 0.0 | 1.0 | 5 |
| gpt:gpt-5.6-sol:latest:medium | kimi:kimi-k3:judge:medium | 行动赋权 | 2.0 | 0.0 | 1.0 | 1.0 | 5 |
| gpt:gpt-5.6-sol:latest:medium | kimi:kimi-k3:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 5 |
| gpt:gpt-5.6-sol:latest:medium | qwen:qwen3.8-max:judge:medium | 丰富性 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| gpt:gpt-5.6-sol:latest:medium | qwen:qwen3.8-max:judge:medium | 包容性与可及性 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| gpt:gpt-5.6-sol:latest:medium | qwen:qwen3.8-max:judge:medium | 基础能力 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| gpt:gpt-5.6-sol:latest:medium | qwen:qwen3.8-max:judge:medium | 求助转介 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| gpt:gpt-5.6-sol:latest:medium | qwen:qwen3.8-max:judge:medium | 法律维权 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| gpt:gpt-5.6-sol:latest:medium | qwen:qwen3.8-max:judge:medium | 行动赋权 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| gpt:gpt-5.6-sol:latest:medium | qwen:qwen3.8-max:judge:medium | 表达能力 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| kimi:kimi-k3:latest:medium | claude:claude-opus-5:judge:medium | 丰富性 | 1.5 | 0.5 | 1.0 | 2.0 | 6 |
| kimi:kimi-k3:latest:medium | claude:claude-opus-5:judge:medium | 包容性与可及性 | 3.0 | 0.0 | 1.0 | 1.0 | 6 |
| kimi:kimi-k3:latest:medium | claude:claude-opus-5:judge:medium | 基础能力 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| kimi:kimi-k3:latest:medium | claude:claude-opus-5:judge:medium | 求助转介 | 0.0 | 0.0 | 0.0 | 2.0 | 6 |
| kimi:kimi-k3:latest:medium | claude:claude-opus-5:judge:medium | 法律维权 | 0.0 | 0.0 | 0.0 | 3.0 | 6 |
| kimi:kimi-k3:latest:medium | claude:claude-opus-5:judge:medium | 行动赋权 | 2.5 | 0.5 | 1.0 | 3.0 | 6 |
| kimi:kimi-k3:latest:medium | claude:claude-opus-5:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| kimi:kimi-k3:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 丰富性 | 2.0 | 0.5 | 1.0 | 2.0 | 6 |
| kimi:kimi-k3:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 包容性与可及性 | 3.0 | 0.0 | 1.0 | 1.0 | 6 |
| kimi:kimi-k3:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 基础能力 | 3.0 | 0.0 | 1.0 | 1.0 | 6 |
| kimi:kimi-k3:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 求助转介 | 3.0 | 0.0 | 1.0 | 2.0 | 6 |
| kimi:kimi-k3:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 法律维权 | 3.0 | 0.0 | 1.0 | 2.0 | 6 |
| kimi:kimi-k3:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 行动赋权 | 2.5 | 0.5 | 1.0 | 2.0 | 6 |
| kimi:kimi-k3:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| kimi:kimi-k3:latest:medium | gpt:gpt-5.6-sol:judge:medium | 丰富性 | 1.0 | 0.0 | 0.0 | 1.0 | 6 |
| kimi:kimi-k3:latest:medium | gpt:gpt-5.6-sol:judge:medium | 包容性与可及性 | 1.5 | 0.5 | 1.0 | 1.0 | 6 |
| kimi:kimi-k3:latest:medium | gpt:gpt-5.6-sol:judge:medium | 基础能力 | 2.0 | 0.0 | 0.0 | 0.0 | 6 |
| kimi:kimi-k3:latest:medium | gpt:gpt-5.6-sol:judge:medium | 求助转介 | 1.0 | 0.0 | 1.0 | 1.0 | 6 |
| kimi:kimi-k3:latest:medium | gpt:gpt-5.6-sol:judge:medium | 法律维权 | 1.0 | 0.0 | 1.0 | 1.0 | 6 |
| kimi:kimi-k3:latest:medium | gpt:gpt-5.6-sol:judge:medium | 行动赋权 | 1.5 | 0.5 | 1.0 | 1.0 | 6 |
| kimi:kimi-k3:latest:medium | gpt:gpt-5.6-sol:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | 丰富性 | 2.0 | 0.0 | 0.0 | 0.0 | 4 |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | 包容性与可及性 | 2.0 | 0.0 | 0.0 | 0.0 | 4 |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | 基础能力 | 3.0 | 0.0 | 0.5 | 1.0 | 4 |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | 求助转介 | 2.0 | 0.0 | 0.0 | 0.0 | 4 |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | 法律维权 | 2.0 | 0.0 | 0.0 | 0.0 | 4 |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | 行动赋权 | 2.0 | 0.0 | 0.5 | 1.0 | 4 |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 4 |
| kimi:kimi-k3:latest:medium | qwen:qwen3.8-max:judge:medium | 丰富性 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| kimi:kimi-k3:latest:medium | qwen:qwen3.8-max:judge:medium | 包容性与可及性 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| kimi:kimi-k3:latest:medium | qwen:qwen3.8-max:judge:medium | 基础能力 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| kimi:kimi-k3:latest:medium | qwen:qwen3.8-max:judge:medium | 求助转介 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| kimi:kimi-k3:latest:medium | qwen:qwen3.8-max:judge:medium | 法律维权 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| kimi:kimi-k3:latest:medium | qwen:qwen3.8-max:judge:medium | 行动赋权 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| kimi:kimi-k3:latest:medium | qwen:qwen3.8-max:judge:medium | 表达能力 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | 0 |
| qwen:qwen3.8-max:latest:medium | claude:claude-opus-5:judge:medium | 丰富性 | 1.0 | 1.0 | 2.0 | 2.0 | 6 |
| qwen:qwen3.8-max:latest:medium | claude:claude-opus-5:judge:medium | 包容性与可及性 | 2.0 | 1.0 | 3.0 | 3.0 | 6 |
| qwen:qwen3.8-max:latest:medium | claude:claude-opus-5:judge:medium | 基础能力 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| qwen:qwen3.8-max:latest:medium | claude:claude-opus-5:judge:medium | 求助转介 | 0.0 | 0.0 | 0.0 | 0.0 | 6 |
| qwen:qwen3.8-max:latest:medium | claude:claude-opus-5:judge:medium | 法律维权 | 0.0 | 0.0 | 0.0 | 0.0 | 6 |
| qwen:qwen3.8-max:latest:medium | claude:claude-opus-5:judge:medium | 行动赋权 | 2.0 | 1.0 | 3.0 | 3.0 | 6 |
| qwen:qwen3.8-max:latest:medium | claude:claude-opus-5:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| qwen:qwen3.8-max:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 丰富性 | 3.0 | 0.0 | 0.0 | 1.0 | 6 |
| qwen:qwen3.8-max:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 包容性与可及性 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| qwen:qwen3.8-max:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 基础能力 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| qwen:qwen3.8-max:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 求助转介 | 3.0 | 0.0 | 0.0 | 1.0 | 6 |
| qwen:qwen3.8-max:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 法律维权 | 3.0 | 0.0 | 0.0 | 1.0 | 6 |
| qwen:qwen3.8-max:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 行动赋权 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| qwen:qwen3.8-max:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| qwen:qwen3.8-max:latest:medium | gpt:gpt-5.6-sol:judge:medium | 丰富性 | 1.0 | 0.0 | 0.0 | 0.0 | 6 |
| qwen:qwen3.8-max:latest:medium | gpt:gpt-5.6-sol:judge:medium | 包容性与可及性 | 2.0 | 0.0 | 0.0 | 1.0 | 6 |
| qwen:qwen3.8-max:latest:medium | gpt:gpt-5.6-sol:judge:medium | 基础能力 | 2.0 | 0.0 | 1.0 | 1.0 | 6 |
| qwen:qwen3.8-max:latest:medium | gpt:gpt-5.6-sol:judge:medium | 求助转介 | 0.5 | 0.5 | 1.0 | 1.0 | 6 |
| qwen:qwen3.8-max:latest:medium | gpt:gpt-5.6-sol:judge:medium | 法律维权 | 0.5 | 0.5 | 1.0 | 1.0 | 6 |
| qwen:qwen3.8-max:latest:medium | gpt:gpt-5.6-sol:judge:medium | 行动赋权 | 2.0 | 0.0 | 0.0 | 1.0 | 6 |
| qwen:qwen3.8-max:latest:medium | gpt:gpt-5.6-sol:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
| qwen:qwen3.8-max:latest:medium | kimi:kimi-k3:judge:medium | 丰富性 | 2.0 | 0.0 | 0.0 | 0.0 | 6 |
| qwen:qwen3.8-max:latest:medium | kimi:kimi-k3:judge:medium | 包容性与可及性 | 2.5 | 0.5 | 1.0 | 1.0 | 6 |
| qwen:qwen3.8-max:latest:medium | kimi:kimi-k3:judge:medium | 基础能力 | 3.0 | 0.0 | 1.0 | 1.0 | 6 |
| qwen:qwen3.8-max:latest:medium | kimi:kimi-k3:judge:medium | 求助转介 | 2.0 | 0.0 | 0.0 | 0.0 | 6 |
| qwen:qwen3.8-max:latest:medium | kimi:kimi-k3:judge:medium | 法律维权 | 2.0 | 0.0 | 0.0 | 0.0 | 6 |
| qwen:qwen3.8-max:latest:medium | kimi:kimi-k3:judge:medium | 行动赋权 | 2.0 | 0.0 | 0.0 | 1.0 | 6 |
| qwen:qwen3.8-max:latest:medium | kimi:kimi-k3:judge:medium | 表达能力 | 3.0 | 0.0 | 0.0 | 0.0 | 6 |
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
| gpt:gpt-5.6-sol:latest:medium | claude:claude-opus-5:judge:medium | 他 | None | 33234.57495891489 | 26666.411750018597 | 17247 | 1 | None/None | None | 0.0035419361665844917 | 15095.015083090402 | 1056 | 1 | 0/7519 | 0.0 | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 他 | None | 33234.57495891489 | 26666.411750018597 | 17247 | 1 | None/None | None | 0.002834014594554901 | 52707.17316691298 | 6712 | 1 | None/None | None | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | 他 | None | 33234.57495891489 | 26666.411750018597 | 17247 | 1 | None/None | None | 89064.49141702615 | 43076.80275000166 | 6884 | 1 | None/None | None | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | kimi:kimi-k3:judge:medium | 他 | None | 33234.57495891489 | 26666.411750018597 | 17247 | 1 | None/None | None | 55843.62754097674 | 50233.59512502793 | 6564 | 1 | 1280/None | 0.29836829836829837 | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | qwen:qwen3.8-max:judge:medium | 他 | None | 33234.57495891489 | 26666.411750018597 | 17247 | 1 | None/None | None | 0.0025420449674129486 | 61082.26183289662 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium |  | None | 0.012791948392987251 | 62961.06816700194 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium |  | None | 0.012791948392987251 | 62961.06816700194 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | gpt:gpt-5.6-sol:judge:medium |  | None | 0.012791948392987251 | 62961.06816700194 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | kimi:kimi-k3:judge:medium |  | None | 0.012791948392987251 | 62961.06816700194 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | qwen:qwen3.8-max:judge:medium |  | None | 0.012791948392987251 | 62961.06816700194 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| qwen:qwen3.8-max:latest:medium | claude:claude-opus-5:judge:medium | 这 | None | 34009.66741703451 | 61163.69841701817 | 10547 | 1 | None/None | None | 0.0031249364838004112 | 13082.447500084527 | 651 | 1 | 2448/7715 | 1224.0 | None | PASS |
| qwen:qwen3.8-max:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 这 | None | 34009.66741703451 | 61163.69841701817 | 10547 | 1 | None/None | None | 0.002500019036233425 | 16281.60145797301 | 7483 | 1 | None/None | None | None | PASS |
| qwen:qwen3.8-max:latest:medium | gpt:gpt-5.6-sol:judge:medium | 这 | None | 34009.66741703451 | 61163.69841701817 | 10547 | 1 | None/None | None | 0.002040993422269821 | 29185.827041976154 | 8008 | 1 | None/None | None | None | PASS |
| qwen:qwen3.8-max:latest:medium | kimi:kimi-k3:judge:medium | 这 | None | 34009.66741703451 | 61163.69841701817 | 10547 | 1 | None/None | None | 0.011124997399747372 | 52925.14395795297 | 8880 | 1 | 1280/None | 0.21610670268445045 | None | PASS |
| qwen:qwen3.8-max:latest:medium | qwen:qwen3.8-max:judge:medium | 这 | None | 34009.66741703451 | 61163.69841701817 | 10547 | 1 | None/None | None | 28003.378959023394 | 62123.593209078535 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium |  | None | 0.002958928234875202 | 42396.95541700348 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium |  | None | 0.002958928234875202 | 42396.95541700348 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | gpt:gpt-5.6-sol:judge:medium |  | None | 0.002958928234875202 | 42396.95541700348 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | kimi:kimi-k3:judge:medium |  | None | 0.002958928234875202 | 42396.95541700348 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | qwen:qwen3.8-max:judge:medium |  | None | 0.002958928234875202 | 42396.95541700348 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| gpt:gpt-5.6-sol:latest:medium | claude:claude-opus-5:judge:medium | 如 | None | 0.005375011824071407 | 16899.529250105843 | 19837 | 1 | None/None | None | 0.0032079406082630157 | 17646.293416968547 | 964 | 1 | 0/10456 | 0.0 | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 如 | None | 0.005375011824071407 | 16899.529250105843 | 19837 | 1 | None/None | None | 0.0024579931050539017 | 17078.026333008893 | 7904 | 1 | None/None | None | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | 如 | None | 0.005375011824071407 | 16899.529250105843 | 19837 | 1 | None/None | None | 0.003166031092405319 | 39532.76766696945 | 8789 | 1 | None/None | None | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | kimi:kimi-k3:judge:medium | 如 | None | 0.005375011824071407 | 16899.529250105843 | 19837 | 1 | None/None | None | 0.0030830269679427147 | 61437.77879199479 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| gpt:gpt-5.6-sol:latest:medium | qwen:qwen3.8-max:judge:medium | 如 | None | 0.005375011824071407 | 16899.529250105843 | 19837 | 1 | None/None | None | 28421.106749912724 | 61103.48049993627 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| qwen:qwen3.8-max:latest:medium | claude:claude-opus-5:judge:medium | 你 | None | 70982.88416711148 | 34000.858582905494 | 7050 | 1 | None/None | None | 0.004749977961182594 | 14935.182875022292 | 973 | 1 | 2448/4374 | 1224.0 | None | PASS |
| qwen:qwen3.8-max:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 你 | None | 70982.88416711148 | 34000.858582905494 | 7050 | 1 | None/None | None | 0.0027919886633753777 | 23219.91666709073 | 6015 | 1 | None/None | None | None | PASS |
| qwen:qwen3.8-max:latest:medium | gpt:gpt-5.6-sol:judge:medium | 你 | None | 70982.88416711148 | 34000.858582905494 | 7050 | 1 | None/None | None | 0.0026669586077332497 | 32230.979166924953 | 5545 | 1 | None/None | None | None | PASS |
| qwen:qwen3.8-max:latest:medium | kimi:kimi-k3:judge:medium | 你 | None | 70982.88416711148 | 34000.858582905494 | 7050 | 1 | None/None | None | 0.002624932676553726 | 27772.873832960613 | 5577 | 1 | 1280/None | 0.32803690415171705 | None | PASS |
| qwen:qwen3.8-max:latest:medium | qwen:qwen3.8-max:judge:medium | 你 | None | 70982.88416711148 | 34000.858582905494 | 7050 | 1 | None/None | None | 28069.93620796129 | 61074.42408299539 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| kimi:kimi-k3:latest:medium | claude:claude-opus-5:judge:medium | 不 | None | 0.0020829029381275177 | 33912.83812490292 | 7356 | 1 | None/None | None | 0.0033329706639051437 | 16229.296874953434 | 1092 | 1 | 0/8102 | 0.0 | None | PASS |
| kimi:kimi-k3:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 不 | None | 0.0020829029381275177 | 33912.83812490292 | 7356 | 1 | None/None | None | 0.002374988980591297 | 17667.478541028686 | 5920 | 1 | None/None | None | None | PASS |
| kimi:kimi-k3:latest:medium | gpt:gpt-5.6-sol:judge:medium | 不 | None | 0.0020829029381275177 | 33912.83812490292 | 7356 | 1 | None/None | None | 0.0030419323593378067 | 37292.538375011645 | 6930 | 1 | None/None | None | None | PASS |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | 不 | None | 0.0020829029381275177 | 33912.83812490292 | 7356 | 1 | None/None | None | 0.0022080494090914726 | 53578.095708973706 | 6675 | 1 | None/None | None | None | PASS |
| kimi:kimi-k3:latest:medium | qwen:qwen3.8-max:judge:medium | 不 | None | 0.0020829029381275177 | 33912.83812490292 | 7356 | 1 | None/None | None | 36874.92512492463 | 62156.50704095606 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| kimi:kimi-k3:latest:medium | claude:claude-opus-5:judge:medium | 你 | None | 33933.159958105534 | 38646.63562504575 | 7489 | 1 | None/None | None | 0.0029999064281582832 | 13741.664916044101 | 810 | 1 | 2471/5360 | 1235.5 | None | PASS |
| kimi:kimi-k3:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 你 | None | 33933.159958105534 | 38646.63562504575 | 7489 | 1 | None/None | None | 0.0017910497263073921 | 15092.361207935028 | 5665 | 1 | None/None | None | None | PASS |
| kimi:kimi-k3:latest:medium | gpt:gpt-5.6-sol:judge:medium | 你 | None | 33933.159958105534 | 38646.63562504575 | 7489 | 1 | None/None | None | 0.0024170149117708206 | 40784.634415991604 | 6905 | 1 | None/None | None | None | PASS |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | 你 | None | 33933.159958105534 | 38646.63562504575 | 7489 | 1 | None/None | None | 0.0020830193534493446 | 62055.55054207798 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| kimi:kimi-k3:latest:medium | qwen:qwen3.8-max:judge:medium | 你 | None | 33933.159958105534 | 38646.63562504575 | 7489 | 1 | None/None | None | 0.013375072740018368 | 62061.46400002763 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| gpt:gpt-5.6-sol:latest:medium | claude:claude-opus-5:judge:medium | 发 | None | 0.0021670712158083916 | 30059.226542012766 | 17425 | 1 | None/None | None | 44647.9883750435 | 18713.52874999866 | 1142 | 1 | 2466/4871 | 1233.0 | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 发 | None | 0.0021670712158083916 | 30059.226542012766 | 17425 | 1 | None/None | None | 55604.129416984506 | 27133.125000051223 | 6657 | 1 | None/None | None | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | 发 | None | 0.0021670712158083916 | 30059.226542012766 | 17425 | 1 | None/None | None | 0.0027919886633753777 | 32579.682165989652 | 6190 | 1 | None/None | None | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | kimi:kimi-k3:judge:medium | 发 | None | 0.0021670712158083916 | 30059.226542012766 | 17425 | 1 | None/None | None | 48331.754124956205 | 34399.32879200205 | 6308 | 1 | 1280/None | 0.30396580384706723 | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | qwen:qwen3.8-max:judge:medium | 发 | None | 0.0021670712158083916 | 30059.226542012766 | 17425 | 1 | None/None | None | 0.002125045284628868 | 61159.60766701028 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| qwen:qwen3.8-max:latest:medium | claude:claude-opus-5:judge:medium | 你 | None | 0.002166023477911949 | 40428.876749938354 | 7174 | 1 | None/None | None | 0.0024581095203757286 | 15485.786958946846 | 967 | 1 | 2451/4126 | 1225.5 | None | PASS |
| qwen:qwen3.8-max:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 你 | None | 0.002166023477911949 | 40428.876749938354 | 7174 | 1 | None/None | None | 0.001708976924419403 | 19956.239333027042 | 5447 | 1 | None/None | None | None | PASS |
| qwen:qwen3.8-max:latest:medium | gpt:gpt-5.6-sol:judge:medium | 你 | None | 0.002166023477911949 | 40428.876749938354 | 7174 | 1 | None/None | None | 0.0024170149117708206 | 27474.752874928527 | 5324 | 1 | None/None | None | None | PASS |
| qwen:qwen3.8-max:latest:medium | kimi:kimi-k3:judge:medium | 你 | None | 0.002166023477911949 | 40428.876749938354 | 7174 | 1 | None/None | None | 8475.876749958843 | 38694.65133396443 | 5669 | 1 | 1280/None | 0.3397929386779931 | None | PASS |
| qwen:qwen3.8-max:latest:medium | qwen:qwen3.8-max:judge:medium | 你 | None | 0.002166023477911949 | 40428.876749938354 | 7174 | 1 | None/None | None | 57152.489457977936 | 61449.58729192149 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| kimi:kimi-k3:latest:medium | claude:claude-opus-5:judge:medium | 锁 | None | 0.005209003575146198 | 28195.811458979733 | 6471 | 1 | None/None | None | 0.0030420487746596336 | 13645.243209088221 | 720 | 1 | 2448/5237 | 1224.0 | None | PASS |
| kimi:kimi-k3:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 锁 | None | 0.005209003575146198 | 28195.811458979733 | 6471 | 1 | None/None | None | 0.001959037035703659 | 22106.173084001057 | 6359 | 1 | None/None | None | None | PASS |
| kimi:kimi-k3:latest:medium | gpt:gpt-5.6-sol:judge:medium | 锁 | None | 0.005209003575146198 | 28195.811458979733 | 6471 | 1 | None/None | None | 0.0024170149117708206 | 48861.56474996824 | 7065 | 1 | None/None | None | None | PASS |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | 锁 | None | 0.005209003575146198 | 28195.811458979733 | 6471 | 1 | None/None | None | 0.07162499241530895 | 44400.97254200373 | 6345 | 1 | 1280/None | 0.29270523667962495 | None | PASS |
| kimi:kimi-k3:latest:medium | qwen:qwen3.8-max:judge:medium | 锁 | None | 0.005209003575146198 | 28195.811458979733 | 6471 | 1 | None/None | None | 57100.92454205733 | 60989.790500025265 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| gpt:gpt-5.6-sol:latest:medium | claude:claude-opus-5:judge:medium | 不 | None | 26675.104875001125 | 13562.272084061988 | 17160 | 1 | None/None | None | 0.0029170187190175056 | 17527.47579093557 | 1596 | 1 | 0/6834 | 0.0 | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 不 | None | 26675.104875001125 | 13562.272084061988 | 17160 | 1 | None/None | None | 0.0027909409254789352 | 21810.894957976416 | 5396 | 1 | None/None | None | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | 不 | None | 26675.104875001125 | 13562.272084061988 | 17160 | 1 | None/None | None | 33341.1707499763 | 34571.93004200235 | 6003 | 1 | None/None | None | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | kimi:kimi-k3:judge:medium | 不 | None | 26675.104875001125 | 13562.272084061988 | 17160 | 1 | None/None | None | 78465.58445796836 | 50714.06320889946 | 6813 | 1 | 1280/None | 0.3262809074687739 | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | qwen:qwen3.8-max:judge:medium | 不 | None | 26675.104875001125 | 13562.272084061988 | 17160 | 1 | None/None | None | 61083.6157919839 | 60971.11341601703 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| qwen:qwen3.8-max:latest:medium | claude:claude-opus-5:judge:medium | 锁 | None | 40442.40629195701 | 70973.44437497668 | 8241 | 1 | None/None | None | 0.0026670750230550766 | 14485.943541047163 | 1179 | 1 | 2451/5045 | 1225.5 | None | PASS |
| qwen:qwen3.8-max:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 锁 | None | 40442.40629195701 | 70973.44437497668 | 8241 | 1 | None/None | None | 0.002375105395913124 | 15378.799417056143 | 5660 | 1 | None/None | None | None | PASS |
| qwen:qwen3.8-max:latest:medium | gpt:gpt-5.6-sol:judge:medium | 锁 | None | 40442.40629195701 | 70973.44437497668 | 8241 | 1 | None/None | None | 0.002834014594554901 | 28901.496957987547 | 6078 | 1 | None/None | None | None | PASS |
| qwen:qwen3.8-max:latest:medium | kimi:kimi-k3:judge:medium | 锁 | None | 40442.40629195701 | 70973.44437497668 | 8241 | 1 | None/None | None | 0.002874992787837982 | 35781.240583979525 | 6065 | 1 | 1280/None | 0.29857709353860507 | None | PASS |
| qwen:qwen3.8-max:latest:medium | qwen:qwen3.8-max:judge:medium | 锁 | None | 40442.40629195701 | 70973.44437497668 | 8241 | 1 | None/None | None | 57233.854333055206 | 61137.551666935906 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| gemini:gemini-3-pro-preview-thinking:latest:medium | claude:claude-opus-5:judge:medium | 担 | None | 0.005082925781607628 | 28932.857499923557 | 11134 | 1 | None/None | None | 0.00458303838968277 | 13591.645292006433 | 867 | 1 | 2451/5322 | 1225.5 | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 担 | None | 0.005082925781607628 | 28932.857499923557 | 11134 | 1 | None/None | None | 0.003959052264690399 | 27043.33533300087 | 6852 | 1 | None/None | None | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gpt:gpt-5.6-sol:judge:medium | 担 | None | 0.005082925781607628 | 28932.857499923557 | 11134 | 1 | None/None | None | 0.002625049091875553 | 36930.57508394122 | 6702 | 1 | None/None | None | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | kimi:kimi-k3:judge:medium | 担 | None | 0.005082925781607628 | 28932.857499923557 | 11134 | 1 | None/None | None | 0.00291608739644289 | 61214.24870798364 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| gemini:gemini-3-pro-preview-thinking:latest:medium | qwen:qwen3.8-max:judge:medium | 担 | None | 0.005082925781607628 | 28932.857499923557 | 11134 | 1 | None/None | None | 28510.35887503531 | 61167.175458977 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium |  | None | 0.002459040842950344 | 20622.030499973334 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium |  | None | 0.002459040842950344 | 20622.030499973334 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | gpt:gpt-5.6-sol:judge:medium |  | None | 0.002459040842950344 | 20622.030499973334 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | kimi:kimi-k3:judge:medium |  | None | 0.002459040842950344 | 20622.030499973334 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | qwen:qwen3.8-max:judge:medium |  | None | 0.002459040842950344 | 20622.030499973334 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| qwen:qwen3.8-max:latest:medium | claude:claude-opus-5:judge:medium | 发 | None | 0.0019170111045241356 | 79491.88508291263 | 9103 | 1 | None/None | None | 0.006292015314102173 | 14944.667333969846 | 960 | 1 | 2479/4830 | 1239.5 | None | PASS |
| qwen:qwen3.8-max:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 发 | None | 0.0019170111045241356 | 79491.88508291263 | 9103 | 1 | None/None | None | 0.0033329706639051437 | 26237.816583015956 | 6646 | 1 | None/None | None | None | PASS |
| qwen:qwen3.8-max:latest:medium | gpt:gpt-5.6-sol:judge:medium | 发 | None | 0.0019170111045241356 | 79491.88508291263 | 9103 | 1 | None/None | None | 28868.88408300001 | 28151.333958958276 | 5942 | 1 | None/None | None | None | PASS |
| qwen:qwen3.8-max:latest:medium | kimi:kimi-k3:judge:medium | 发 | None | 0.0019170111045241356 | 79491.88508291263 | 9103 | 1 | None/None | None | 237.96916601713747 | 59567.04624998383 | 7406 | 1 | 1280/None | 0.30497974743864664 | None | PASS |
| qwen:qwen3.8-max:latest:medium | qwen:qwen3.8-max:judge:medium | 发 | None | 0.0019170111045241356 | 79491.88508291263 | 9103 | 1 | None/None | None | 36529.91566702258 | 61366.142333019525 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| kimi:kimi-k3:latest:medium | claude:claude-opus-5:judge:medium | 你 | None | 38656.992624979466 | 31497.3951659631 | 6902 | 1 | None/None | None | 0.004665926098823547 | 18438.443083083257 | 1054 | 1 | 0/6967 | 0.0 | None | PASS |
| kimi:kimi-k3:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 你 | None | 38656.992624979466 | 31497.3951659631 | 6902 | 1 | None/None | None | 0.00300002284348011 | 29179.733083001338 | 6494 | 1 | None/None | None | None | PASS |
| kimi:kimi-k3:latest:medium | gpt:gpt-5.6-sol:judge:medium | 你 | None | 38656.992624979466 | 31497.3951659631 | 6902 | 1 | None/None | None | 0.0029579969123005867 | 37239.75920805242 | 6168 | 1 | None/None | None | None | PASS |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | 你 | None | 38656.992624979466 | 31497.3951659631 | 6902 | 1 | None/None | None | 0.002708984538912773 | 61010.8715420356 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| kimi:kimi-k3:latest:medium | qwen:qwen3.8-max:judge:medium | 你 | None | 38656.992624979466 | 31497.3951659631 | 6902 | 1 | None/None | None | 0.003125052899122238 | 61050.158708007075 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| gemini:gemini-3-pro-preview-thinking:latest:medium | claude:claude-opus-5:judge:medium | 连 | None | 0.004625064320862293 | 24824.02583397925 | 9931 | 1 | None/None | None | 0.0032919924706220627 | 13374.411207973026 | 882 | 1 | 2479/5109 | 1239.5 | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 连 | None | 0.004625064320862293 | 24824.02583397925 | 9931 | 1 | None/None | None | 0.002874992787837982 | 16241.056666942313 | 5659 | 1 | None/None | None | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gpt:gpt-5.6-sol:judge:medium | 连 | None | 0.004625064320862293 | 24824.02583397925 | 9931 | 1 | None/None | None | 70811.1326249782 | 40814.27249999251 | 6193 | 1 | None/None | None | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | kimi:kimi-k3:judge:medium | 连 | None | 0.004625064320862293 | 24824.02583397925 | 9931 | 1 | None/None | None | 0.0029999064281582832 | 55326.36112498585 | 6153 | 1 | None/None | None | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | qwen:qwen3.8-max:judge:medium | 连 | None | 0.004625064320862293 | 24824.02583397925 | 9931 | 1 | None/None | None | 93465.59433301445 | 60962.28995907586 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium | 他 | None | 0.03591692075133324 | 42515.91324992478 | None | 1 | None/None | None | 0.045874970965087414 | 58068.047582986765 | 4123 | 1 | 0/7454 | 0.0 | None | PASS |
| claude:claude-opus-5:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 他 | None | 0.03591692075133324 | 42515.91324992478 | None | 1 | None/None | None | 58062.18595802784 | 16783.459500060417 | 5563 | 1 | None/None | None | None | PASS |
| claude:claude-opus-5:latest:medium | gpt:gpt-5.6-sol:judge:medium | 他 | None | 0.03591692075133324 | 42515.91324992478 | None | 1 | None/None | None | 32567.261832999066 | 25494.52254199423 | 5773 | 1 | None/None | None | None | PASS |
| claude:claude-opus-5:latest:medium | kimi:kimi-k3:judge:medium | 他 | None | 0.03591692075133324 | 42515.91324992478 | None | 1 | None/None | None | 58067.13358289562 | 58955.176915973425 | 6062 | 1 | 1280/None | 0.301389215917118 | None | PASS |
| claude:claude-opus-5:latest:medium | qwen:qwen3.8-max:judge:medium | 他 | None | 0.03591692075133324 | 42515.91324992478 | None | 1 | None/None | None | 61048.01079200115 | 61114.71704207361 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| gemini:gemini-3-pro-preview-thinking:latest:medium | claude:claude-opus-5:judge:medium | 你 | None | 0.0018330756574869156 | 29266.023208969273 | 11331 | 1 | None/None | None | 63350.377541966736 | 17332.642500055954 | 1306 | 1 | 2466/5275 | 1233.0 | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 你 | None | 0.0018330756574869156 | 29266.023208969273 | 11331 | 1 | None/None | None | 100524.7700830223 | 20964.763082913123 | 5681 | 1 | None/None | None | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gpt:gpt-5.6-sol:judge:medium | 你 | None | 0.0018330756574869156 | 29266.023208969273 | 11331 | 1 | None/None | None | 61117.83912498504 | 33272.46883395128 | 6447 | 1 | None/None | None | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | kimi:kimi-k3:judge:medium | 你 | None | 0.0018330756574869156 | 29266.023208969273 | 11331 | 1 | None/None | None | 182730.36512499675 | 248743.77208400983 | 6221 | 4 | 4352/None | 0.99179580674567 | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | qwen:qwen3.8-max:judge:medium | 你 | None | 0.0018330756574869156 | 29266.023208969273 | 11331 | 1 | None/None | None | 74816.04245794006 | 61212.208749959245 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| gpt:gpt-5.6-sol:latest:medium | claude:claude-opus-5:judge:medium | 我 | None | 13573.31254100427 | 17871.788250049576 | 19751 | 1 | None/None | None | 0.004375004209578037 | 15468.592207995243 | 838 | 1 | 0/10188 | 0.0 | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 我 | None | 13573.31254100427 | 17871.788250049576 | 19751 | 1 | None/None | None | 0.0026669586077332497 | 21266.831167042255 | 7863 | 1 | None/None | None | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | 我 | None | 13573.31254100427 | 17871.788250049576 | 19751 | 1 | None/None | None | 0.002499902620911598 | 41439.48249996174 | 8582 | 1 | None/None | None | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | kimi:kimi-k3:judge:medium | 我 | None | 13573.31254100427 | 17871.788250049576 | 19751 | 1 | None/None | None | 113.13104094006121 | 35698.57124995906 | 7743 | 1 | 1280/None | 0.21639898562975485 | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | qwen:qwen3.8-max:judge:medium | 我 | None | 13573.31254100427 | 17871.788250049576 | 19751 | 1 | None/None | None | 48342.044792021625 | 61254.8199580051 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium | 你 | None | 0.010291929356753826 | 46014.37620795332 | None | 1 | None/None | None | 70.746292010881 | 12288.158916984685 | 681 | 1 | 2480/5183 | 1240.0 | None | PASS |
| claude:claude-opus-5:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 你 | None | 0.010291929356753826 | 46014.37620795332 | None | 1 | None/None | None | 12358.701874967664 | 20127.820459078066 | 6127 | 1 | None/None | None | None | PASS |
| claude:claude-opus-5:latest:medium | gpt:gpt-5.6-sol:judge:medium | 你 | None | 0.010291929356753826 | 46014.37620795332 | None | 1 | None/None | None | 6805.11520896107 | 29720.018124906346 | 6224 | 1 | None/None | None | None | PASS |
| claude:claude-opus-5:latest:medium | kimi:kimi-k3:judge:medium | 你 | None | 0.010291929356753826 | 46014.37620795332 | None | 1 | None/None | None | 13868.808957980946 | 42584.73416697234 | 7233 | 1 | 1280/None | 0.2931073963819556 | None | PASS |
| claude:claude-opus-5:latest:medium | qwen:qwen3.8-max:judge:medium | 你 | None | 0.010291929356753826 | 46014.37620795332 | None | 1 | None/None | None | 36525.094332988374 | 60999.53174998518 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | claude:claude-opus-5:judge:medium |  | None | 0.017208978533744812 | 34160.99354100879 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium |  | None | 0.017208978533744812 | 34160.99354100879 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | gpt:gpt-5.6-sol:judge:medium |  | None | 0.017208978533744812 | 34160.99354100879 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | kimi:kimi-k3:judge:medium |  | None | 0.017208978533744812 | 34160.99354100879 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| claude:claude-opus-5:latest:medium | qwen:qwen3.8-max:judge:medium |  | None | 0.017208978533744812 | 34160.99354100879 | None | 1 | None/None | PROVIDER_5XX | 0.0 | None | None | 1 | None/None | None | SUBJECT_UNAVAILABLE | UNAVAILABLE |
| kimi:kimi-k3:latest:medium | claude:claude-opus-5:judge:medium | 能 | None | 0.0024579931050539017 | 33561.18058296852 | 6802 | 1 | None/None | None | 0.003166031092405319 | 16719.05304095708 | 1176 | 1 | 2451/5084 | 1225.5 | None | PASS |
| kimi:kimi-k3:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 能 | None | 0.0024579931050539017 | 33561.18058296852 | 6802 | 1 | None/None | None | 0.002959044650197029 | 20446.20383309666 | 6164 | 1 | None/None | None | None | PASS |
| kimi:kimi-k3:latest:medium | gpt:gpt-5.6-sol:judge:medium | 能 | None | 0.0024579931050539017 | 33561.18058296852 | 6802 | 1 | None/None | None | 0.0027919886633753777 | 47773.139083059505 | 7133 | 1 | None/None | None | None | PASS |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | 能 | None | 0.0024579931050539017 | 33561.18058296852 | 6802 | 1 | None/None | None | 0.0037919962778687477 | 27596.903249970637 | 6248 | 1 | 1280/None | 0.29684601113172543 | None | PASS |
| kimi:kimi-k3:latest:medium | qwen:qwen3.8-max:judge:medium | 能 | None | 0.0024579931050539017 | 33561.18058296852 | 6802 | 1 | None/None | None | 36845.34474997781 | 61267.70645810757 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| gemini:gemini-3-pro-preview-thinking:latest:medium | claude:claude-opus-5:judge:medium | 你 | None | 0.004541012458503246 | 32341.303708031774 | 11507 | 1 | None/None | None | 0.0035410048440098763 | 14024.97700008098 | 790 | 1 | 2448/5460 | 1224.0 | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 你 | None | 0.004541012458503246 | 32341.303708031774 | 11507 | 1 | None/None | None | 0.00300002284348011 | 19492.592833936214 | 6298 | 1 | None/None | None | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gpt:gpt-5.6-sol:judge:medium | 你 | None | 0.004541012458503246 | 32341.303708031774 | 11507 | 1 | None/None | None | 0.0029579969123005867 | 37959.5486249309 | 6645 | 1 | None/None | None | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | kimi:kimi-k3:judge:medium | 你 | None | 0.004541012458503246 | 32341.303708031774 | 11507 | 1 | None/None | None | 0.07383304182440042 | 50295.99591693841 | 6692 | 1 | 1280/None | 0.28412874583795783 | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | qwen:qwen3.8-max:judge:medium | 你 | None | 0.004541012458503246 | 32341.303708031774 | 11507 | 1 | None/None | None | 36942.29999999516 | 61038.00725005567 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| kimi:kimi-k3:latest:medium | claude:claude-opus-5:judge:medium | 你 | None | 31507.74024997372 | 35438.966542016715 | 9013 | 1 | None/None | None | 0.0030420487746596336 | 22341.255916981027 | 1072 | 1 | 2488/8126 | 1244.0 | None | PASS |
| kimi:kimi-k3:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 你 | None | 31507.74024997372 | 35438.966542016715 | 9013 | 1 | None/None | None | 0.0027080532163381577 | 20650.620250031352 | 7842 | 1 | None/None | None | None | PASS |
| kimi:kimi-k3:latest:medium | gpt:gpt-5.6-sol:judge:medium | 你 | None | 31507.74024997372 | 35438.966542016715 | 9013 | 1 | None/None | None | 0.0019159633666276932 | 46563.980042003095 | 8978 | 1 | None/None | None | None | PASS |
| kimi:kimi-k3:latest:medium | kimi:kimi-k3:judge:medium | 你 | None | 31507.74024997372 | 35438.966542016715 | 9013 | 1 | None/None | None | 0.024416949599981308 | 51705.79562499188 | 7968 | 1 | None/None | None | None | PASS |
| kimi:kimi-k3:latest:medium | qwen:qwen3.8-max:judge:medium | 你 | None | 31507.74024997372 | 35438.966542016715 | 9013 | 1 | None/None | None | 0.005209003575146198 | 61546.76175001077 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| qwen:qwen3.8-max:latest:medium | claude:claude-opus-5:judge:medium | 你 | None | 0.005832989700138569 | 53429.699875065126 | 10320 | 1 | None/None | None | 0.0032079406082630157 | 16189.367834012955 | 911 | 1 | 2471/7883 | 1235.5 | None | PASS |
| qwen:qwen3.8-max:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 你 | None | 0.005832989700138569 | 53429.699875065126 | 10320 | 1 | None/None | None | 0.002749962732195854 | 19541.080832947046 | 7860 | 1 | None/None | None | None | PASS |
| qwen:qwen3.8-max:latest:medium | gpt:gpt-5.6-sol:judge:medium | 你 | None | 0.005832989700138569 | 53429.699875065126 | 10320 | 1 | None/None | None | 0.002250075340270996 | 41119.31024992373 | 8749 | 1 | None/None | None | None | PASS |
| qwen:qwen3.8-max:latest:medium | kimi:kimi-k3:judge:medium | 你 | None | 0.005832989700138569 | 53429.699875065126 | 10320 | 1 | None/None | None | 32876.5417910181 | 53922.86245897412 | 7964 | 1 | 1280/None | 0.2107342772472835 | None | PASS |
| qwen:qwen3.8-max:latest:medium | qwen:qwen3.8-max:judge:medium | 你 | None | 0.005832989700138569 | 53429.699875065126 | 10320 | 1 | None/None | None | 0.043791020289063454 | 61390.302833984606 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| gemini:gemini-3-pro-preview-thinking:latest:medium | claude:claude-opus-5:judge:medium | 你 | None | 0.004083034582436085 | 43176.18483409751 | 10995 | 1 | None/None | None | 0.007542083039879799 | 16902.671708958223 | 1539 | 1 | 2479/5544 | 1239.5 | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 你 | None | 0.004083034582436085 | 43176.18483409751 | 10995 | 1 | None/None | None | 0.005542067810893059 | 15145.758832921274 | 5738 | 1 | None/None | None | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gpt:gpt-5.6-sol:judge:medium | 你 | None | 0.004083034582436085 | 43176.18483409751 | 10995 | 1 | None/None | None | 50585.46266600024 | 39288.63558394369 | 6982 | 1 | None/None | None | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | kimi:kimi-k3:judge:medium | 你 | None | 0.004083034582436085 | 43176.18483409751 | 10995 | 1 | None/None | None | 31161.98808304034 | 60973.66575000342 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| gemini:gemini-3-pro-preview-thinking:latest:medium | qwen:qwen3.8-max:judge:medium | 你 | None | 0.004083034582436085 | 43176.18483409751 | 10995 | 1 | None/None | None | 47048.3947499888 | 61049.74545806181 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| gemini:gemini-3-pro-preview-thinking:latest:medium | claude:claude-opus-5:judge:medium | 发 | None | 0.002084067091345787 | 25112.634374992922 | 10563 | 1 | None/None | None | 13367.372417007573 | 15894.54112504609 | 1078 | 1 | 2466/4927 | 1233.0 | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 发 | None | 0.002084067091345787 | 25112.634374992922 | 10563 | 1 | None/None | None | 82730.74008303229 | 17798.286291072145 | 5784 | 1 | None/None | None | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | gpt:gpt-5.6-sol:judge:medium | 发 | None | 0.002084067091345787 | 25112.634374992922 | 10563 | 1 | None/None | None | 57343.61795790028 | 250580.40987502318 | 9849 | 4 | 7936/None | 0.887199552822806 | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | kimi:kimi-k3:judge:medium | 发 | None | 0.002084067091345787 | 25112.634374992922 | 10563 | 1 | None/None | None | 82720.80820798874 | 61313.136540935375 | 8518 | 1 | 1280/None | 0.30303030303030304 | None | PASS |
| gemini:gemini-3-pro-preview-thinking:latest:medium | qwen:qwen3.8-max:judge:medium | 发 | None | 0.002084067091345787 | 25112.634374992922 | 10563 | 1 | None/None | None | 0.005209003575146198 | 61217.491541057825 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
| gpt:gpt-5.6-sol:latest:medium | claude:claude-opus-5:judge:medium | 你 | None | 0.0020419247448444366 | 33220.660499995574 | 16997 | 1 | None/None | None | 29262.123708962463 | 15385.586791904643 | 987 | 1 | 2466/4163 | 1233.0 | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | gemini:gemini-3-pro-preview-thinking:judge:medium | 你 | None | 0.0020419247448444366 | 33220.660499995574 | 16997 | 1 | None/None | None | 15950.28358406853 | 39655.40066699032 | 5084 | 2 | None/None | None | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | gpt:gpt-5.6-sol:judge:medium | 你 | None | 0.0020419247448444366 | 33220.660499995574 | 16997 | 1 | None/None | None | 307925.34591595177 | 45072.41441705264 | 9521 | 1 | None/None | None | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | kimi:kimi-k3:judge:medium | 你 | None | 0.0020419247448444366 | 33220.660499995574 | 16997 | 1 | None/None | None | 0.002374988980591297 | 48332.36499992199 | 5283 | 1 | None/None | None | None | PASS |
| gpt:gpt-5.6-sol:latest:medium | qwen:qwen3.8-max:judge:medium | 你 | None | 0.0020419247448444366 | 33220.660499995574 | 16997 | 1 | None/None | None | 0.00400003045797348 | 61067.25454097614 | None | 1 | None/None | None | CONNECTION | UNAVAILABLE |
