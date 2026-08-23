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


def cost_optimized_policy_for_iteration(
    iteration: int,
    *,
    previous_score: int | None = None,
    previous_blocking_issues: int | None = None,
    previous_validators_pass: bool = False,
) -> IterationModelPolicy:
    """Conservative cost policy used only by the A/B cost experiment.

    Iterations 1-4 are identical to the production baseline. Iteration 5 keeps
    the premium model only when the previous candidate is genuinely close to
    passing and all deterministic validators already pass. Otherwise the fifth
    review stays on the balanced tier; a premium model cannot repair missing
    evidence or deterministic safety failures.
    """

    baseline = policy_for_iteration(iteration)
    if iteration < MAX_REVIEW_ITERATIONS:
        return baseline

    close_to_pass = (
        previous_score is not None
        and previous_score >= 90
        and (previous_blocking_issues or 0) <= 1
        and previous_validators_pass
    )
    if close_to_pass:
        return baseline

    balanced = model_ids()["balanced"]
    return IterationModelPolicy(
        iteration=iteration,
        tier="balanced_guarded",
        reviewer_model=balanced,
        reviser_model=balanced,
        max_output_tokens=5500,
        premium=False,
    )


def escalation_plan() -> list[IterationModelPolicy]:
    return [policy_for_iteration(iteration) for iteration in range(1, MAX_REVIEW_ITERATIONS + 1)]
