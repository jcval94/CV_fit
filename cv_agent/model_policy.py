from __future__ import annotations

import os
from dataclasses import asdict, dataclass

from cv_agent.openai_provider import validate_openai_model_id


MAX_REVIEW_ITERATIONS = 5


@dataclass(frozen=True)
class IterationModelPolicy:
    iteration: int
    tier: str
    reviewer_model: str
    reviser_model: str
    max_output_tokens: int
    premium: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def model_ids() -> dict[str, str]:
    """Resolve OpenAI model IDs at runtime while preserving one-provider policy."""

    models = {
        "economy": os.getenv("CV_FIT_MODEL_ECONOMY", "gpt-5.6-luna"),
        "balanced": os.getenv("CV_FIT_MODEL_BALANCED", "gpt-5.6-terra"),
        "premium": os.getenv("CV_FIT_MODEL_PREMIUM", "gpt-5.6-sol"),
    }
    return {tier: validate_openai_model_id(model) for tier, model in models.items()}


def policy_for_iteration(iteration: int) -> IterationModelPolicy:
    if not 1 <= iteration <= MAX_REVIEW_ITERATIONS:
        raise ValueError(f"iteration must be between 1 and {MAX_REVIEW_ITERATIONS}")
    models = model_ids()
    if iteration <= 2:
        tier = "economy"
        model = models[tier]
        tokens = 4500
    elif iteration <= 4:
        tier = "balanced"
        model = models[tier]
        tokens = 6000
    else:
        tier = "premium"
        model = models[tier]
        tokens = 7000
    return IterationModelPolicy(
        iteration=iteration,
        tier=tier,
        reviewer_model=model,
        reviser_model=model,
        max_output_tokens=tokens,
        premium=tier == "premium",
    )


def escalation_plan() -> list[IterationModelPolicy]:
    return [policy_for_iteration(iteration) for iteration in range(1, MAX_REVIEW_ITERATIONS + 1)]
