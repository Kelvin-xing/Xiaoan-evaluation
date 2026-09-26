from xiaoan_eval_core.results import build_complete_results

def fixture_result():
    rows = [{"answer_id": "a", "subject_id": "s", "case_id": "TC-01", "turn": 1, "question": "問題", "answer": "完整回答", "status": "AVAILABLE", "requirements": [], "context": []}]
    inv = {"answer_id": "a", "inventory_id": "i", "claims": [{"id": "c", "proposition": "完整主張", "kind": "FACTUAL", "conditions": [], "answer_span": {"start": 0, "end": 4, "text": "完整回答"}}]}
    cells = [{"answer_id": "a", "judge_id": j, "status": "AVAILABLE", "inventory_id": "i", "assessment": {"claims": [{"id": "c", "faithfulness": {"verdict": "UNKNOWN", "evidence": [], "reason": "缺少證據"}, "correctness": {"verdict": "UNKNOWN", "evidence": [], "reason": "缺少真值"}}], "requirements": []}} for j in ("j1", "j2")]
    rubrics = [{"answer_id": "a", "judge_id": j, "status": "AVAILABLE", "rubric": {"status": "AVAILABLE", "scores": {"同理": n}, "weighted_total": n, "final_weights": {"同理": 1}, "gate": "PASS", "red_lines": [], "dimension_details": [{"module": "同理", "score": n, "reason": "明確回應感受"}]}} for j, n in (("j1", 1), ("j2", 3))]
    return build_complete_results({"judges": [{"id": "j1"}, {"id": "j2"}]}, rows, {"inventories": [inv], "cells": cells}, rubrics, [], [], [])
