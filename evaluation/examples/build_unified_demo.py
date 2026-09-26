"""Write a fully bound synthetic offline example, never call a model.

Run from evaluation/: python examples/build_unified_demo.py /tmp/demo.json
"""
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from xiaoan_eval_core import VERSION
from xiaoan_eval_core.contracts import extraction_request, validate_inventory, assessment_request


def build():
    def identity(name):
        return {"id": name, "provider": "synthetic", "model": name,
                "family": name, "prompt_version": "synthetic/v1"}
    answer = "你可以先列出問題。"
    row = {"answer_id": "synthetic-answer-1", "case_id": "DEMO", "turn": 1,
           "subject_id": "synthetic-subject", "subject_model": "synthetic-subject",
           "subject_provider": "synthetic", "status": "AVAILABLE",
           "question": "幫我準備要問的事。", "answer": answer, "history": [],
           "context_version": "synthetic-v1", "context_capture": "EXPOSED",
           "context": [{"ref": "capsule:demo", "layer": "CAPSULE", "content": answer}],
           "reference_facts": [], "oracle_status": "approved",
           "requirements": [
               {"id": "safety", "kind": "safety", "text": "不鼓勵危險行動（合成示例）", "critical": True},
               {"id": "task", "kind": "task", "text": "提出準備問題的下一步（合成示例）", "critical": False}]}
    spec = {"schema_version": "evaluation-methods/v3", "contract": VERSION,
            "extractor": identity("synthetic-extractor"), "judges": [identity("synthetic-judge")],
            "planned_subjects": ["synthetic-subject"], "planned_turns": {"DEMO": [1]}, "rows": [row]}
    request = extraction_request(row, spec["extractor"])
    quote = {"start": 0, "end": len(answer), "text": answer}
    row["inventory"] = {"binding": request["binding"], "claims": [
        {"id": "c1", "kind": "RECOMMENDATION", "proposition": "建議先列出問題", "conditions": [], "answer_span": quote}]}
    inventory = validate_inventory(row["inventory"], request)
    request = assessment_request(row, inventory, spec["judges"][0])
    row["assessments"] = {"synthetic-judge": {"binding": request["binding"], "claims": [{
        "id": "c1", "faithfulness": {"verdict": "ENTAILED", "reason": "合成材料直接支持", "evidence": [{"ref": "capsule:demo", **quote}]},
        "correctness": {"verdict": "NOT_APPLICABLE", "reason": "建議的適用性另按任務檢查", "evidence": []}}],
        "requirements": [{"id": r["id"], "verdict": "SATISFIED", "reason": "合成示例標籤，不是真實評估", "answer_spans": [quote]}
                         for r in row["requirements"]]}}
    return spec


if __name__ == "__main__":
    with Path(sys.argv[1]).open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(build(), ensure_ascii=False, indent=2) + "\n")
