"""Answer-relevancy stage with a frozen reverse-question contract.

The stage deliberately contains no provider or network dependency. Callers can
retry it by invoking :func:`evaluate_relevancy` again with a provider or with
new supplied observations. Missing observations remain ``UNAVAILABLE``; they
are never converted into a zero score.
"""
from __future__ import annotations

import math
from copy import deepcopy

from .contracts import digest, text
from .configuration import prompt, schema


DEFAULT_REVERSE_QUESTION_COUNT = 3
METRIC_VERSION = "answer-relevancy-reverse-q/v1"
UNAVAILABLE = "UNAVAILABLE"


def build_request(answer_id, question, answer, *, generator=None,
                  question_count=DEFAULT_REVERSE_QUESTION_COUNT,
                  query_mode="raw_current_user"):
    """Build the immutable task sent to a reverse-question generator.

    The original question is retained in the task for the later embedding
    comparison but is intentionally absent from ``generation_input``.
    """
    text(answer_id, "answer_id")
    text(question, "original_question")
    text(answer, "answer")
    if type(question_count) is not int or question_count < 1:
        raise ValueError("question_count must be a positive integer")
    if not isinstance(query_mode, str) or not query_mode.strip():
        raise ValueError("query_mode must be non-empty text")
    generator = generator or {
        "provider": "unspecified",
        "model": "unspecified",
        "prompt_version": "reverse-question-zh/v1",
    }
    if not isinstance(generator, dict):
        raise ValueError("generator must be an object")
    # Only descriptive identity fields belong in the request binding. This
    # prevents accidental transmission of provider configuration or secrets.
    identity = {
        key: text(generator.get(key), key)
        for key in ("provider", "model", "prompt_version")
    }
    task = {
        "metric_version": METRIC_VERSION,
        "answer_id": answer_id,
        "original_question": question,
        "answer": answer,
        "n": question_count,
        "query_mode": query_mode,
        "generator": identity,
        "generation_input": {
            "answer": answer,
            "n": question_count,
            "task": "relevancy_generation",
            "response_schema": schema("relevancy"),
            "instructions": prompt("relevancy.md"),
        },
    }
    task["binding"] = digest(task)
    return task


def _unavailable(reason, binding, **extra):
    return {"status": UNAVAILABLE, "reason": reason, "score": None,
            "binding": binding, **extra}


def _is_current_task(task):
    payload = {key: value for key, value in task.items() if key != "binding"}
    return digest(payload) == task.get("binding")


def _cosine(left, right):
    if (not isinstance(left, list) or not isinstance(right, list) or
            not left or len(left) != len(right)):
        raise ValueError("INVALID_EMBEDDING_DIMENSIONS")
    values = left + right
    if any(type(value) not in (int, float) or not math.isfinite(value)
           for value in values):
        raise ValueError("NON_FINITE_EMBEDDING")
    # Scale before norm calculation so valid large vectors do not overflow.
    left_scale = max(abs(value) for value in left)
    right_scale = max(abs(value) for value in right)
    if not left_scale or not right_scale:
        raise ValueError("ZERO_EMBEDDING")
    a = [value / left_scale for value in left]
    b = [value / right_scale for value in right]
    denominator = math.sqrt(math.fsum(value * value for value in a)) * math.sqrt(
        math.fsum(value * value for value in b))
    return min(1.0, max(-1.0, math.fsum(x * y for x, y in zip(a, b)) / denominator))


def score_relevancy(task, generation, embeddings):
    """Score validated supplied observations using the frozen metric formula."""
    binding = task.get("binding") if isinstance(task, dict) else None
    if not isinstance(binding, str):
        raise ValueError("task binding is required")
    if not _is_current_task(task):
        return _unavailable("GENERATION_MISSING_OR_STALE", binding)
    if not isinstance(generation, dict) or generation.get("binding") != binding:
        return _unavailable("GENERATION_MISSING_OR_STALE", binding)
    n = task.get("n")
    questions = generation.get("questions")
    if (type(n) is not int or n < 1 or not isinstance(questions, list) or
            len(questions) != n or any(not isinstance(q, str) or not q.strip()
                                       for q in questions)):
        return _unavailable("INVALID_QUESTION_COUNT_OR_TEXT", binding)
    if (not isinstance(embeddings, dict) or not embeddings.get("model_id") or
            not embeddings.get("revision")):
        return _unavailable("EMBEDDING_CONFIG_MISSING", binding)
    vectors = embeddings.get("vectors")
    if not isinstance(vectors, dict):
        return _unavailable("EMBEDDING_MISSING", binding)
    texts = [task.get("original_question"), *questions]
    if any(not isinstance(value, str) or value not in vectors for value in texts):
        return _unavailable("EMBEDDING_MISSING", binding)
    try:
        similarities = [_cosine(vectors[texts[0]], vectors[question])
                        for question in questions]
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
        reason = str(error) or "INVALID_EMBEDDING"
        return _unavailable(reason, binding)
    return {
        "status": "AVAILABLE",
        "score": math.fsum(similarities) / n,
        "n": n,
        "similarities": similarities,
        "questions": questions,
        "generator": task["generator"],
        "duplicate_questions": n - len(set(questions)),
        "binding": binding,
        "embedding_model": embeddings["model_id"],
        "embedding_revision": embeddings["revision"],
        "interpretation": (
            "Semantic alignment proxy, not completeness, concision or truth."
        ),
    }


def evaluate_relevancy(task, *, generation_provider=None,
                       embedding_provider=None, supplied_generation=None,
                       supplied_embeddings=None):
    """Run the stage without allowing one provider failure to escape.

    Providers are optional callables. A generation provider receives a copy of
    ``task['generation_input']``. An embedding provider receives the exact text
    list ``[original_question, *reverse_questions]`` and a copy of the task.
    The returned observations can be supplied on a later invocation to retry a
    failed stage without regenerating successful earlier work.
    """
    if not isinstance(task, dict) or not isinstance(task.get("binding"), str):
        raise ValueError("task binding is required")
    binding = task["binding"]
    generation = supplied_generation
    if generation is None:
        if generation_provider is None:
            return _unavailable("GENERATION_NOT_ATTEMPTED", binding)
        try:
            generation = generation_provider(deepcopy(task["generation_input"]))
        except Exception as error:  # provider details must not enter artifacts
            return _unavailable(f"GENERATION_PROVIDER_{type(error).__name__}", binding)
    preliminary = score_relevancy(task, generation, None)
    if preliminary["reason"] not in {"EMBEDDING_CONFIG_MISSING", "EMBEDDING_MISSING"}:
        return preliminary
    embeddings = supplied_embeddings
    if embeddings is None:
        if embedding_provider is None:
            return preliminary
        try:
            questions = generation.get("questions", []) if isinstance(generation, dict) else []
            embeddings = embedding_provider(
                [task.get("original_question"), *questions], deepcopy(task)
            )
        except Exception as error:
            return _unavailable(f"EMBEDDING_PROVIDER_{type(error).__name__}", binding)
    return score_relevancy(task, generation, embeddings)


# Compatibility name for callers migrating from examples/answer_metric_contracts.py.
answer_relevancy = score_relevancy
