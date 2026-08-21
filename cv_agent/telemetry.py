from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


PRICING_SNAPSHOT_DATE = "2026-08-21"
PRICING_BASIS = "OpenAI standard short-context text pricing, USD per 1M tokens"
PRICING_SOURCE = "https://platform.openai.com/pricing"
MODEL_PRICING_USD_PER_MILLION: dict[str, dict[str, float]] = {
    "gpt-5.6-luna": {"input": 1.00, "cached_input": 0.10, "output": 6.00},
    "gpt-5.6-terra": {"input": 2.50, "cached_input": 0.25, "output": 15.00},
    "gpt-5.6-sol": {"input": 5.00, "cached_input": 0.50, "output": 30.00},
}


@dataclass(frozen=True)
class LLMCallUsage:
    name: str
    model: str
    prompt_tokens: int
    cached_input_tokens: int
    candidate_tokens: int
    reasoning_tokens: int
    total_tokens: int
    duration_ms: int
    estimated_cost_usd: float | None
    pricing_snapshot_date: str
    pricing_basis: str
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def estimate_cost_usd(
    model: str,
    *,
    prompt_tokens: int,
    cached_input_tokens: int,
    candidate_tokens: int,
    reasoning_tokens: int = 0,
) -> float | None:
    """Estimate direct model cost from the pinned public pricing snapshot.

    ADK exposes cached prompt tokens separately. Reasoning/thought tokens are
    treated as output tokens for the estimate. Unknown configured gpt-* models
    remain usable but are reported as unpriced rather than silently assigned a
    guessed price.
    """

    rates = MODEL_PRICING_USD_PER_MILLION.get(model)
    if not rates:
        return None
    cached = max(int(cached_input_tokens or 0), 0)
    prompt = max(int(prompt_tokens or 0), 0)
    uncached = max(prompt - cached, 0)
    output = max(int(candidate_tokens or 0), 0) + max(int(reasoning_tokens or 0), 0)
    cost = (
        uncached * rates["input"]
        + cached * rates["cached_input"]
        + output * rates["output"]
    ) / 1_000_000.0
    return round(cost, 8)


def summarize_usage(calls: list[LLMCallUsage]) -> dict[str, Any]:
    known_costs = [call.estimated_cost_usd for call in calls if call.estimated_cost_usd is not None]
    unpriced_models = sorted({call.model for call in calls if call.estimated_cost_usd is None})
    return {
        "schema_version": 1,
        "pricing_snapshot_date": PRICING_SNAPSHOT_DATE,
        "pricing_basis": PRICING_BASIS,
        "pricing_source": PRICING_SOURCE,
        "call_count": len(calls),
        "prompt_tokens": sum(call.prompt_tokens for call in calls),
        "cached_input_tokens": sum(call.cached_input_tokens for call in calls),
        "candidate_tokens": sum(call.candidate_tokens for call in calls),
        "reasoning_tokens": sum(call.reasoning_tokens for call in calls),
        "total_tokens": sum(call.total_tokens for call in calls),
        "estimated_cost_usd": round(sum(known_costs), 8) if len(known_costs) == len(calls) else None,
        "known_estimated_cost_usd": round(sum(known_costs), 8),
        "unpriced_models": unpriced_models,
        "calls": [call.to_dict() for call in calls],
        "note": "Cost is an estimate from a pinned public pricing snapshot, not an OpenAI invoice.",
    }
