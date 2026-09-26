"""Paired capsule-exposure experiment over immutable composer inputs.

This measures a fixed-route composer intervention, not end-to-end route changes.
The subject adapter must return actual context and control receipts; without
them no experiment effect is eligible. Unsafe pairs stay visible as failures.
"""
from __future__ import annotations

from copy import deepcopy

from .contracts import canonical_context, canonical_history, digest, text
from .runtime import ResponseStore, evaluate, prepare_rows


def run(spec, provider=None, *, checkpoint_dir=None, subject_provider=None):
    controls = spec.get("controls")
    if not isinstance(controls, dict):
        raise ValueError("explicit fixed experiment controls required")
    if set(controls) != {"model", "provider", "prompt_version", "knowledge_version", "route_id",
                         "system_prompt", "mode", "max_output_tokens", "seed", "temperature"}:
        raise ValueError("controls must use only the declared experiment fields")
    for key in ("model", "provider", "prompt_version", "knowledge_version", "route_id", "system_prompt"):
        text(controls.get(key), key)
    if controls.get("mode") != "COMPOSER_FIXED_CONTEXT":
        raise ValueError("ablation must declare COMPOSER_FIXED_CONTEXT")
    if type(controls.get("max_output_tokens")) is not int or controls["max_output_tokens"] < 1:
        raise ValueError("max_output_tokens required")
    if type(controls.get("seed")) is not int or not isinstance(controls.get("temperature"), (int, float)):
        raise ValueError("explicit seed and temperature required")
    control_hash = digest(controls)
    rows = prepare_rows(spec)
    store = ResponseStore(checkpoint_dir)
    generated, receipts = [], []
    for row in rows:
        row["context"] = canonical_context(row.get("context", []))
        row["history"] = canonical_history(row.get("history", []))
        if row["subject_model"] != controls["model"] or row["subject_provider"] != controls["provider"]:
            raise ValueError("subject identity differs from experiment controls")
        capsules = [u for u in row.get("context", []) if u["layer"] == "CAPSULE"]
        if not capsules:
            raise ValueError("capsule ablation requires an exposed capsule in each input")
        for enabled in (True, False):
            arm = "WITH_CAPSULE" if enabled else "WITHOUT_CAPSULE"
            context = [u for u in row["context"] if enabled or u["layer"] != "CAPSULE"]
            payload = {"task": "generate_ablation", "contract": spec["contract"],
                       "question": row["question"], "history": row.get("history", []),
                       "context": context, "controls": controls, "control_hash": control_hash}
            payload["binding"] = digest(payload)
            candidate = deepcopy(row)
            candidate.update(subject_id=f'{row["subject_id"]}:{arm}',
                             answer_id=f'{row["answer_id"]}:{arm}', context=context,
                             context_version=digest(context), status="UNAVAILABLE", answer=None)
            # Never reuse assessments or extraction from the input answer.
            for key in ("inventory", "assessments", "inventory_audit", "human_inventory"):
                candidate.pop(key, None)

            def validate(response, request):
                if not isinstance(response, dict) or response.get("binding") != request["binding"]:
                    raise ValueError("generation binding mismatch")
                if response.get("control_hash") != control_hash or response.get("actual_context") != context:
                    raise ValueError("generation receipt differs from fixed controls/context")
                text(response.get("answer"), "generated answer")
                return response

            try:
                response = store.call(payload, subject_provider, validate,
                                      row.get("generation_responses", {}).get(arm))
                candidate.update(answer=response["answer"], status="AVAILABLE",
                                 observations=response.get("observations", {}))
                receipts.append({"answer_id": candidate["answer_id"], "arm": arm,
                                 "control_hash": control_hash, "request_hash": digest(payload),
                                 "response": response, "status": "AVAILABLE"})
            except Exception as exc:
                receipts.append({"answer_id": candidate["answer_id"], "arm": arm,
                                 "status": "UNAVAILABLE", "reason": type(exc).__name__})
            generated.append(candidate)
    result = evaluate({**spec, "rows": generated, "conversation_constraints": [],
                       "planned_subjects": sorted({r["subject_id"] for r in generated})},
                      provider, checkpoint_dir=checkpoint_dir)
    pairs = []
    by_key = {(c["answer_id"], c["judge_id"]): c for c in result["cells"]}
    for row in rows:
        for judge in spec["judges"]:
            with_capsule = by_key[(f'{row["answer_id"]}:WITH_CAPSULE', judge["id"])]
            without = by_key[(f'{row["answer_id"]}:WITHOUT_CAPSULE', judge["id"])]
            pair = {"case_id": row["case_id"], "turn": row["turn"], "judge_id": judge["id"],
                    "subject_id": row["subject_id"], "status": "UNAVAILABLE",
                    "with_answer_id": with_capsule["answer_id"], "without_answer_id": without["answer_id"]}
            gates = [c.get("requirements", {}).get("release_gate", "UNAVAILABLE")
                     for c in (with_capsule, without)]
            pair.update(with_gate=gates[0], without_gate=gates[1])
            pair["status"] = "FAIL" if "FAIL" in gates else "ELIGIBLE" if gates == ["PASS", "PASS"] else "UNAVAILABLE"
            if with_capsule["status"] == without["status"] == "AVAILABLE":
                pair["diagnostic_deltas"] = {}
                for dimension in ("faithfulness", "correctness"):
                    a = with_capsule["metrics"][dimension]["strict_rate"]
                    b = without["metrics"][dimension]["strict_rate"]
                    pair["diagnostic_deltas"][dimension] = a - b if a is not None and b is not None else None
                for kind in ("task", "constraint", "interaction", "safety"):
                    a = with_capsule["requirements"]["by_kind"].get(kind, {}).get("satisfied_rate")
                    b = without["requirements"]["by_kind"].get(kind, {}).get("satisfied_rate")
                    pair["diagnostic_deltas"][kind] = a - b if a is not None and b is not None else None
            pairs.append(pair)
    return {"contract": spec["contract"], "mode": "COMPOSER_FIXED_CONTEXT", "control_hash": control_hash,
            "receipts": receipts, "generation_requests": store.requests, "evaluation": result, "pairs": pairs,
            "interpretation": "With minus without capsule. Fixed-route composer intervention only; "
                              "provider receipts are not independent execution verification. "
                              "Gate failures are retained; diagnostic deltas never override gates. "
                              "Generated answers have different claim inventories; their support delta "
                              "is descriptive, not a matched-claim causal effect. No population inference."}
