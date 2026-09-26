"""Offline cost and quality analysis for matrix rows.

This module deliberately knows nothing about transports, environment files, or
the matrix CLI.  A catalog entry is valid only for its exact provider, model,
currency, and billing route; a provider name alone is never a billing route.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class Rate:
    provider: str
    model: str
    billing_route: str
    currency: str
    input_per_million: float
    output_per_million: float
    cached_input_per_million: float | None = None
    cache_write_per_million: float | None = None
    source_url: str = ""
    catalog_version: str = ""
    checked_date: str = ""
    input_token_semantics: str = "uncached input_tokens; add cache read/write fields when present"


@dataclass(frozen=True)
class CostLine:
    lane: str
    identity: str
    provider: str
    model: str
    billing_route: str | None
    currency: str | None
    status: str
    cost: float | None
    input_tokens: int | None
    output_tokens: int | None
    cached_input_tokens: int | None
    cache_write_tokens: int | None
    attempts: int | None
    reason: str | None = None


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _response(row: Mapping[str, Any], lane: str) -> Mapping[str, Any]:
    value = row.get("answer" if lane == "subject" else "judgement")
    if isinstance(value, Mapping):
        return value
    value = row.get("subject_response" if lane == "subject" else "judge_response")
    return _mapping(value)


def _identity(row: Mapping[str, Any], lane: str) -> str:
    if lane == "subject":
        return str(row.get("answer_id") or row.get("subject_answer_id") or "")
    return ":".join(str(row.get(key) or "") for key in ("answer_id", "judge_id"))


def _spec(row: Mapping[str, Any], response: Mapping[str, Any], lane: str) -> tuple[str, str, str | None]:
    source = _mapping(row.get("subject" if lane == "subject" else "judge"))
    provider = str(response.get("provider") or source.get("provider") or row.get(f"{lane}_provider") or "")
    model = str(response.get("model") or source.get("model") or row.get(f"{lane}_model") or "")
    route = response.get("billing_route") or source.get("billing_route") or row.get(f"{lane}_billing_route")
    return provider, model, str(route) if route is not None else None


def _int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _catalog(catalog: Mapping[str, Any] | str | Path) -> list[Rate]:
    if isinstance(catalog, (str, Path)):
        catalog = json.loads(Path(catalog).read_text(encoding="utf-8"))
    entries = catalog.get("rates", catalog) if isinstance(catalog, Mapping) else []
    result = []
    for item in entries if isinstance(entries, list) else []:
        if not isinstance(item, Mapping):
            continue
        result.append(Rate(
            provider=str(item.get("provider", "")), model=str(item.get("model", "")),
            billing_route=str(item.get("billing_route", "")), currency=str(item.get("currency", "")),
            input_per_million=float(item["input_per_million"]),
            output_per_million=float(item["output_per_million"]),
            cached_input_per_million=float(item["cached_input_per_million"]) if item.get("cached_input_per_million") is not None else None,
            cache_write_per_million=float(item["cache_write_per_million"]) if item.get("cache_write_per_million") is not None else None,
            source_url=str(item.get("source_url", "")), catalog_version=str(item.get("catalog_version", "")),
            checked_date=str(item.get("checked_date", "")), input_token_semantics=str(item.get("input_token_semantics", "")),
        ))
    return result


def _rate(rates: Iterable[Rate], provider: str, model: str, route: str | None) -> Rate | None:
    if not route:
        return None
    matches = [r for r in rates if (r.provider, r.model, r.billing_route) == (provider, model, route)]
    return matches[0] if len(matches) == 1 else None


def _line(row: Mapping[str, Any], lane: str, rates: list[Rate]) -> CostLine:
    response = _response(row, lane)
    provider, model, route = _spec(row, response, lane)
    identity = _identity(row, lane)
    status = str(response.get("status") or row.get("status") or "")
    attempts = _int(response.get("attempt_count"))
    inp, out = _int(response.get("input_tokens")), _int(response.get("output_tokens"))
    cached = _int(response.get("cached_input_tokens"))
    written = _int(response.get("cache_write_tokens"))
    if not identity:
        return CostLine(lane, identity, provider, model, route, None, UNAVAILABLE, None, inp, out, cached, written, attempts, "missing identity")
    if status and status != "PASS":
        return CostLine(lane, identity, provider, model, route, None, UNAVAILABLE, None, inp, out, cached, written, attempts, f"response status {status}")
    if attempts is not None and attempts > 1 and (not isinstance(response.get("attempts"), list) or not response.get("attempts")):
        return CostLine(lane, identity, provider, model, route, None, UNAVAILABLE, None, inp, out, cached, written, attempts, "retry usage is not itemized")
    price = _rate(rates, provider, model, route)
    if price is None:
        return CostLine(lane, identity, provider, model, route, None, UNAVAILABLE, None, inp, out, cached, written, attempts, "no exact provider/model/billing_route price")
    if inp is None or out is None:
        return CostLine(lane, identity, provider, model, route, price.currency, UNAVAILABLE, None, inp, out, cached, written, attempts, "missing token usage")
    if (cached or written) and price.cached_input_per_million is None:
        return CostLine(lane, identity, provider, model, route, price.currency, UNAVAILABLE, None, inp, out, cached, written, attempts, "cache usage has no catalog rate")
    regular = inp * price.input_per_million / 1_000_000
    cached_cost = (cached or 0) * (price.cached_input_per_million if price.cached_input_per_million is not None else price.input_per_million) / 1_000_000
    write_cost = (written or 0) * (price.cache_write_per_million if price.cache_write_per_million is not None else price.input_per_million) / 1_000_000
    cost = regular + cached_cost + write_cost + out * price.output_per_million / 1_000_000
    return CostLine(lane, identity, provider, model, route, price.currency, "PASS", cost, inp, out, cached, written, attempts)


def build_cost_analysis(rows: Iterable[Mapping[str, Any]], catalog: Mapping[str, Any] | str | Path) -> dict[str, Any]:
    """Return serialisable cost lines and quality summaries for matrix rows."""
    rates = _catalog(catalog)
    materialized = list(rows)
    subject_rows: dict[str, Mapping[str, Any]] = {}
    for row in materialized:
        identity = _identity(row, "subject")
        if identity and identity not in subject_rows:
            subject_rows[identity] = row
    lines = [_line(row, "subject", rates) for row in subject_rows.values()]
    lines.extend(_line(row, "judge", rates) for row in materialized)
    totals: dict[str, dict[str, Any]] = {}
    for line in lines:
        bucket = totals.setdefault(line.currency or UNAVAILABLE, {"currency": line.currency, "cost": 0.0, "known_lines": 0, "unavailable_lines": 0})
        if line.cost is None:
            bucket["unavailable_lines"] += 1
        else:
            bucket["cost"] += line.cost
            bucket["known_lines"] += 1
    quality: dict[str, dict[str, Any]] = {}
    for row in materialized:
        score = row.get("weighted_score")
        if not isinstance(score, (int, float)) or isinstance(score, bool):
            continue
        subject = _mapping(row.get("subject")); judge = _mapping(row.get("judge"))
        key = ":".join((str(subject.get("provider", "")), str(subject.get("model", "")), str(judge.get("provider", "")), str(judge.get("model", ""))))
        item = quality.setdefault(key, {"pair": key, "quality_score_sum": 0.0, "quality_observations": 0})
        item["quality_score_sum"] += float(score); item["quality_observations"] += 1
    for item in quality.values():
        item["quality_score_mean"] = item["quality_score_sum"] / item["quality_observations"]
    return {"schema_version": "cost-quality/v1", "lines": [asdict(line) for line in lines], "totals_by_currency": totals, "quality_by_pair": quality, "subject_unique_count": len(subject_rows), "matrix_row_count": len(materialized)}


def render_cost_analysis(result: Mapping[str, Any]) -> str:
    """Render the result as stable Markdown for reports or workbook metadata."""
    totals = result.get("totals_by_currency", {})
    lines = ["# Cost quality", "", f"- Matrix rows: {result.get('matrix_row_count', 0)}", f"- Unique subject answers: {result.get('subject_unique_count', 0)}", "", "## Cost by currency", "", "| Currency | Known cost | Known lines | Unavailable lines |", "|---|---:|---:|---:|"]
    for currency, item in sorted(totals.items()):
        cost = item.get("cost") if item.get("known_lines") else UNAVAILABLE
        lines.append(f"| {currency} | {cost} | {item.get('known_lines', 0)} | {item.get('unavailable_lines', 0)} |")
    lines += ["", "## Quality by subject/Judge pair", "", "| Pair | Mean score | Observations |", "|---|---:|---:|"]
    for key, item in sorted((result.get("quality_by_pair") or {}).items()):
        lines.append(f"| {key} | {item.get('quality_score_mean', UNAVAILABLE)} | {item.get('quality_observations', 0)} |")
    return "\n".join(lines) + "\n"
