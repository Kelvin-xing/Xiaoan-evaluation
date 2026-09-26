import math

from xiaoan_eval_core.relevancy import (
    DEFAULT_REVERSE_QUESTION_COUNT,
    answer_relevancy,
    build_request,
    evaluate_relevancy,
)


def fixture():
    task = build_request("answer-1", "original", "answer",
                         generator={"provider": "fixture", "model": "m",
                                    "prompt_version": "p1"})
    questions = ["same", "orthogonal", "opposite"]
    generation = {"binding": task["binding"], "questions": questions}
    embeddings = {
        "model_id": "fixture",
        "revision": "v1",
        "vectors": {
            "original": [1.0, 0.0], "same": [1.0, 0.0],
            "orthogonal": [0.0, 1.0], "opposite": [-1.0, 0.0],
        },
    }
    return task, generation, embeddings


def test_build_request_hides_original_question_from_generator_input():
    task = build_request("a", "original", "answer")
    assert task["n"] == DEFAULT_REVERSE_QUESTION_COUNT
    assert task["original_question"] not in str(task["generation_input"])


def test_score_uses_raw_cosine_mean_and_keeps_negative_values():
    task, generation, embeddings = fixture()
    result = answer_relevancy(task, generation, embeddings)
    assert result["similarities"] == [1.0, 0.0, -1.0]
    assert result["score"] == 0.0
    assert result["status"] == "AVAILABLE"


def test_incomplete_or_stale_observations_are_unavailable():
    task, generation, embeddings = fixture()
    generation["questions"].pop()
    assert answer_relevancy(task, generation, embeddings)["status"] == "UNAVAILABLE"
    assert answer_relevancy(task, None, embeddings)["reason"] == "GENERATION_MISSING_OR_STALE"
    task, generation, embeddings = fixture()
    task["original_question"] = "changed"
    assert answer_relevancy(task, generation, embeddings)["reason"] == "GENERATION_MISSING_OR_STALE"


def test_invalid_embedding_is_unavailable_and_never_zero():
    task, generation, embeddings = fixture()
    embeddings["vectors"]["same"] = [0.0, 0.0]
    result = answer_relevancy(task, generation, embeddings)
    assert result["status"] == "UNAVAILABLE"
    assert result["score"] is None
    embeddings["vectors"]["same"] = [math.nan, 0.0]
    assert answer_relevancy(task, generation, embeddings)["status"] == "UNAVAILABLE"


def test_provider_failures_are_terminal_for_this_attempt_and_retryable():
    task, _, _ = fixture()
    first = evaluate_relevancy(task, generation_provider=lambda _: (_ for _ in ()).throw(RuntimeError()))
    assert first["status"] == "UNAVAILABLE"
    assert first["reason"] == "GENERATION_PROVIDER_RuntimeError"
    task, generation, embeddings = fixture()
    result = evaluate_relevancy(task, supplied_generation=generation,
                                supplied_embeddings=embeddings)
    assert result["status"] == "AVAILABLE"


def test_embedding_provider_receives_exact_texts_after_generation():
    task, generation, _ = fixture()
    seen = []
    result = evaluate_relevancy(
        task,
        supplied_generation=generation,
        embedding_provider=lambda texts, _: seen.append(texts) or fixture()[2],
    )
    assert seen == [["original", "same", "orthogonal", "opposite"]]
    assert result["status"] == "AVAILABLE"

