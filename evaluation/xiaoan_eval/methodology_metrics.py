"""Cross-run contracts required by the repository methodology.

The functions in this module are pure: provider failures remain unavailable
and are never converted into quality observations.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any, Callable, Mapping, Sequence


PAIRWISE_CONTRACT_VERSION = "pairwise/v1"
PAIRWISE_WINNERS = frozenset({"LEFT", "RIGHT", "TIE", "INVALID"})


@dataclass(frozen=True)
class PairwiseDecision:
    case_id: str
    turn: int
    left_answer_id: str
    right_answer_id: str
    judge_id: str
    display_order: str
    winner: str
    status: str
    rationale: str
    control_digest: str


def control_digest(contract: Mapping[str, Any]) -> str:
    """Hash all caller-supplied controls used to establish comparability."""
    encoded = json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def pairwise_decision(payload: Mapping[str, Any]) -> PairwiseDecision:
    """Validate one blinded A/B decision without turning ties into half wins."""
    if payload.get("contract_version") != PAIRWISE_CONTRACT_VERSION:
        raise ValueError(f"contract_version must be {PAIRWISE_CONTRACT_VERSION}")
    winner = payload.get("winner")
    if winner not in PAIRWISE_WINNERS:
        raise ValueError("winner must be LEFT, RIGHT, TIE, or INVALID")
    status = payload.get("status")
    if status not in {"AVAILABLE", "UNAVAILABLE"}:
        raise ValueError("status must be AVAILABLE or UNAVAILABLE")
    if status == "UNAVAILABLE" and winner != "INVALID":
        raise ValueError("UNAVAILABLE pairwise decisions must use winner=INVALID")
    display_order = _text(payload, "display_order")
    if display_order not in {"A_LEFT", "B_LEFT"}:
        raise ValueError("display_order must be A_LEFT or B_LEFT")
    return PairwiseDecision(
        case_id=_text(payload, "case_id"),
        turn=_positive_int(payload, "turn"),
        left_answer_id=_text(payload, "left_answer_id"),
        right_answer_id=_text(payload, "right_answer_id"),
        judge_id=_text(payload, "judge_id"),
        display_order=display_order,
        winner=str(winner),
        status=str(status),
        rationale=_text(payload, "rationale"),
        control_digest=_text(payload, "control_digest"),
    )


def run_pairwise_pass(
    answers: Sequence[Mapping[str, Any]],
    pairs: Sequence[tuple[str, str]],
    judges: Sequence[str],
    provider: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    *,
    controls: Mapping[str, Any],
    seed: str,
) -> list[PairwiseDecision]:
    """Judge immutable answer artifacts using deterministic blinded A/B order.

    Subject generation is deliberately outside this function. A judge retry can
    therefore never regenerate a subject answer.
    """
    index = {_text(answer, "answer_id"): dict(answer) for answer in answers}
    if len(index) != len(answers):
        raise ValueError("answer_id values must be unique")
    digest = control_digest(controls)
    decisions: list[PairwiseDecision] = []
    for first_id, second_id in pairs:
        if first_id not in index or second_id not in index or first_id == second_id:
            raise ValueError("pair references missing or identical answers")
        first, second = index[first_id], index[second_id]
        if (first.get("case_id"), first.get("turn")) != (second.get("case_id"), second.get("turn")):
            raise ValueError("pairwise answers must share case_id and turn")
        for judge_id in judges:
            reverse = int(hashlib.sha256(f"{seed}:{first_id}:{second_id}:{judge_id}".encode()).hexdigest(), 16) % 2 == 1
            left, right = (second, first) if reverse else (first, second)
            order = "B_LEFT" if reverse else "A_LEFT"
            request = {
                "contract_version": PAIRWISE_CONTRACT_VERSION,
                "case_id": first.get("case_id"), "turn": first.get("turn"),
                "judge_id": judge_id, "display_order": order,
                "control_digest": digest,
                "content_is_untrusted": True,
                "instructions": "Compare blinded candidates. Return winner LEFT, RIGHT, TIE, or INVALID and a rationale.",
                "left": {"answer": left.get("answer", left.get("text", ""))},
                "right": {"answer": right.get("answer", right.get("text", ""))},
            }
            if str(left.get("status", "PASS")) != "PASS" or str(right.get("status", "PASS")) != "PASS":
                raw: Mapping[str, Any] = {"winner": "INVALID", "rationale": "subject answer unavailable", "status": "UNAVAILABLE"}
            else:
                try:
                    candidate = provider(request)
                    if not isinstance(candidate, Mapping):
                        raise TypeError("pairwise provider must return a mapping")
                    raw = candidate
                except Exception as exc:  # operational state, never a quality loss
                    raw = {"winner": "INVALID", "rationale": f"{type(exc).__name__}: {exc}", "status": "UNAVAILABLE"}
            decisions.append(pairwise_decision({
                **raw, "contract_version": PAIRWISE_CONTRACT_VERSION,
                "case_id": str(first.get("case_id")), "turn": int(first.get("turn", 0)),
                "left_answer_id": str(left["answer_id"]), "right_answer_id": str(right["answer_id"]),
                "judge_id": str(judge_id), "display_order": order, "control_digest": digest,
                "status": raw.get("status", "AVAILABLE"),
            }))
    return decisions


def summarize_pairwise(decisions: Sequence[PairwiseDecision]) -> dict[str, Any]:
    """Report available denominators, ties, and position flips separately."""
    available = [item for item in decisions if item.status == "AVAILABLE" and item.winner != "INVALID"]
    directional = [item for item in available if item.winner in {"LEFT", "RIGHT"}]
    by_identity: dict[tuple[str, int, str, str, str], list[PairwiseDecision]] = defaultdict(list)
    for item in directional:
        pair = tuple(sorted((item.left_answer_id, item.right_answer_id)))
        by_identity[(item.case_id, item.turn, pair[0], pair[1], item.judge_id)].append(item)
    checked = flips = 0
    for items in by_identity.values():
        by_order = {item.display_order: item for item in items}
        if set(by_order) != {"A_LEFT", "B_LEFT"}:
            continue
        checked += 1
        a = by_order["A_LEFT"]
        b = by_order["B_LEFT"]
        winner_a = a.left_answer_id if a.winner == "LEFT" else a.right_answer_id
        winner_b = b.left_answer_id if b.winner == "LEFT" else b.right_answer_id
        # A position flip means the preferred answer identity changes when the
        # same two answers are shown in reversed positions.
        if winner_a != winner_b:
            flips += 1
    return {
        "status": "AVAILABLE" if available else "UNAVAILABLE",
        "attempted_n": len(decisions),
        "eligible_n": len(available),
        "missing_n": len(decisions) - len(available),
        "left_wins": sum(item.winner == "LEFT" for item in available),
        "right_wins": sum(item.winner == "RIGHT" for item in available),
        "ties": sum(item.winner == "TIE" for item in available),
        "position_retests_n": checked,
        "position_flip_rate": flips / checked if checked else None,
        "tie_policy": "SEPARATE",
    }


def self_judging(subject: Mapping[str, Any], judge: Mapping[str, Any]) -> bool:
    """Identify same provider/model judging itself for denominator isolation."""
    return (
        str(subject.get("provider", "")) == str(judge.get("provider", ""))
        and str(subject.get("model", "")) == str(judge.get("model", ""))
    )


def agreement_report(rows: Sequence[Mapping[str, Any]], dimension: str) -> dict[str, Any]:
    """Compute descriptive ordinal alpha, Kendall W, and pairwise Spearman.

    Only PASS, non-self observations with a numeric dimension score enter the
    denominator. Missing/provider-failed cells are counted, not scored zero.
    """
    eligible = [
        row for row in rows
        if row.get("status") == "PASS"
        and not row.get("self_judging", False)
        and _number(row.get("scores", {}).get(dimension)) is not None
    ]
    attempted = len(rows)
    values: dict[tuple[str, int, str], dict[str, float]] = defaultdict(dict)
    for row in eligible:
        unit = (str(row.get("case_id")), int(row.get("turn", 0)), str(row["subject"]["id"]))
        values[unit][str(row["judge"]["id"])] = float(row["scores"][dimension])
    alpha = _ordinal_alpha(list(values.values()))
    judges = sorted({judge for cell in values.values() for judge in cell})
    # Kendall W ranks subjects only within the same case/turn stratum. Scores
    # from unrelated cases are never treated as one ranking population.
    strata: dict[tuple[str, int], dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(dict))
    for row in eligible:
        stratum = (str(row.get("case_id")), int(row.get("turn", 0)))
        strata[stratum][str(row["subject"]["id"])][str(row["judge"]["id"])] = float(row["scores"][dimension])
    kendall_strata = []
    for (case_id, turn), subjects in sorted(strata.items()):
        complete_subjects = [scores for scores in subjects.values() if all(judge in scores for judge in judges)]
        kendall_strata.append({
            "case_id": case_id, "turn": turn,
            "subject_n": len(complete_subjects),
            "judge_n": len(judges),
            "kendall_w": _kendall_w(complete_subjects, judges),
        })
    available_w = [item["kendall_w"] for item in kendall_strata if item["kendall_w"] is not None]
    kendall = sum(available_w) / len(available_w) if available_w else None
    pairwise = []
    for index, left in enumerate(judges):
        for right in judges[index + 1:]:
            pairs = [(cell[left], cell[right]) for cell in values.values() if left in cell and right in cell]
            pairwise.append({"left_judge": left, "right_judge": right, "eligible_n": len(pairs), "spearman_rho": _spearman(pairs)})
    return {
        "interpretation": "DESCRIPTIVE_ONLY",
        "dimension": dimension,
        "attempted_n": attempted,
        "eligible_n": len(eligible),
        "missing_n": attempted - len(eligible),
        "krippendorff_alpha_ordinal": alpha,
        "kendall_w": kendall,
        "kendall_strata": kendall_strata,
        "pairwise_spearman": pairwise,
    }


def summarize_memory_metrics(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Aggregate memory lifecycle and fact retrieval without imputing missing data.

    Rows may include ``expected_facts`` and ``retrieved_facts`` plus booleans
    ``remembered``, ``retrieved``, ``used_when_required``,
    ``not_used_when_forbidden``, ``updated_correctly``, ``isolated`` and
    ``stale_or_unsafe``. Only PASS/FAIL rows enter checkpoint denominators.
    """
    available = [row for row in results if str(row.get("status", "")).lower() in {"pass", "fail"}]
    passed = sum(str(row.get("status", "")).lower() == "pass" for row in available)
    expected: set[str] = set()
    retrieved: set[str] = set()
    for index, row in enumerate(available):
        expected.update(f"{index}:{fact}" for fact in _strings(row.get("expected_facts")))
        retrieved.update(f"{index}:{fact}" for fact in _strings(row.get("retrieved_facts")))
    tp, fp, fn = len(expected & retrieved), len(retrieved - expected), len(expected - retrieved)
    lifecycle = {}
    for field in (
        "remembered", "retrieved", "used_when_required", "not_used_when_forbidden",
        "updated_correctly", "isolated",
    ):
        observed = [bool(row[field]) for row in available if isinstance(row.get(field), bool)]
        lifecycle[field] = {
            "eligible_n": len(observed),
            "missing_n": len(available) - len(observed),
            "rate": sum(observed) / len(observed) if observed else None,
        }
    stale = [bool(row["stale_or_unsafe"]) for row in available if isinstance(row.get("stale_or_unsafe"), bool)]
    return {
        "status": "AVAILABLE" if available else "UNAVAILABLE",
        "attempted_n": len(results),
        "eligible_n": len(available),
        "missing_n": len(results) - len(available),
        "passed_n": passed,
        "retention_and_use_rate": passed / len(available) if available else None,
        "fact_retrieval": {
            "tp": tp, "fp": fp, "fn": fn,
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None,
        },
        "lifecycle": lifecycle,
        "stale_or_unsafe": {
            "eligible_n": len(stale), "missing_n": len(available) - len(stale),
            "rate": sum(stale) / len(stale) if stale else None,
        },
    }


def _strings(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(str(item) for item in value)


def _ordinal_alpha(cells: Sequence[Mapping[str, float]]) -> float | None:
    categories = sorted({value for cell in cells for value in cell.values()})
    coincidence: dict[tuple[float, float], float] = defaultdict(float)
    for cell in cells:
        values = list(cell.values())
        if len(values) < 2:
            continue
        counts = {category: values.count(category) for category in categories}
        for left in categories:
            for right in categories:
                count = counts[left] * (counts[right] - (1 if left == right else 0))
                coincidence[(left, right)] += count / (len(values) - 1)
    marginals = {
        category: sum(coincidence[(category, other)] for other in categories)
        for category in categories
    }
    total = sum(marginals.values())
    if total < 2 or not categories:
        return None

    def distance(left: float, right: float) -> float:
        low, high = sorted((categories.index(left), categories.index(right)))
        mass = sum(marginals[categories[index]] for index in range(low, high + 1))
        return (mass - (marginals[left] + marginals[right]) / 2) ** 2

    observed = sum(
        coincidence[(left, right)] * distance(left, right)
        for left in categories for right in categories
    ) / total
    expected = sum(
        marginals[left] * marginals[right] * distance(left, right)
        for left in categories for right in categories
    ) / (total * (total - 1))
    return 1.0 if expected == 0 and observed == 0 else (None if expected == 0 else 1 - observed / expected)


def _kendall_w(cells: Sequence[Mapping[str, float]], judges: Sequence[str]) -> float | None:
    if len(cells) < 2 or len(judges) < 2:
        return None
    rank_sums = {key: 0.0 for key in range(len(cells))}
    tie_correction = 0.0
    for judge in judges:
        raw = [cell[judge] for cell in cells]
        ranks = _ranks(raw)
        for index, rank in enumerate(ranks):
            rank_sums[index] += rank
        groups = defaultdict(int)
        for value in raw:
            groups[value] += 1
        tie_correction += sum(size ** 3 - size for size in groups.values())
    n, m = len(cells), len(judges)
    mean = m * (n + 1) / 2
    numerator = 12 * sum((value - mean) ** 2 for value in rank_sums.values())
    denominator = m * m * (n ** 3 - n) - m * tie_correction
    return numerator / denominator if denominator else None


def _spearman(pairs: Sequence[tuple[float, float]]) -> float | None:
    if len(pairs) < 2:
        return None
    left, right = zip(*pairs)
    x, y = _ranks(left), _ranks(right)
    xm, ym = sum(x) / len(x), sum(y) / len(y)
    numerator = sum((a - xm) * (b - ym) for a, b in zip(x, y))
    denominator = math.sqrt(sum((a - xm) ** 2 for a in x) * sum((b - ym) ** 2 for b in y))
    return numerator / denominator if denominator else None


def _ranks(values: Sequence[float]) -> list[float]:
    ranks = [0.0] * len(values)
    ordered = sorted(range(len(values)), key=lambda index: values[index])
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and values[ordered[end]] == values[ordered[start]]:
            end += 1
        rank = (start + 1 + end) / 2
        for index in ordered[start:end]:
            ranks[index] = rank
        start = end
    return ranks


def _number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _text(payload: Mapping[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be non-empty text")
    return value.strip()


def _positive_int(payload: Mapping[str, Any], field: str) -> int:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field} must be a positive integer")
    return value
