from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Iterable


SUBSTANTIVE_ITEM_MIN_CHARS = 24
FULL_SCORE_THRESHOLD = 70.0
PARTIAL_SCORE_THRESHOLD = 30.0


@dataclass(frozen=True)
class JDFidelityAssessment:
    classification: str
    score: float
    generation_eligible: bool
    description_chars: int
    requirements_count: int
    responsibilities_count: int
    substantive_detail_count: int
    reasons: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _compact(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def _substantive(items: Iterable[str]) -> list[str]:
    return [item for item in (_compact(value) for value in items) if len(item) >= SUBSTANTIVE_ITEM_MIN_CHARS]


def assess_jd_fidelity(
    *,
    description: str | None,
    requirements: list[str],
    responsibilities: list[str],
) -> JDFidelityAssessment:
    """Assess whether a vacancy preserves enough of the original JD for CV generation.

    Source fit commentary and inferred tech-stack terms are deliberately excluded.
    They can help discovery, but they are not substitutes for the employer's actual
    job description, requirements, or responsibilities.
    """

    description_chars = len(_compact(description))
    substantive_requirements = _substantive(requirements)
    substantive_responsibilities = _substantive(responsibilities)
    detail_count = len(substantive_requirements) + len(substantive_responsibilities)

    description_score = min(description_chars / 1200.0, 1.0) * 60.0
    detail_score = min(detail_count / 8.0, 1.0) * 40.0
    score = round(description_score + detail_score, 1)

    full = (
        description_chars >= 1200
        or detail_count >= 10
        or (description_chars >= 600 and detail_count >= 3 and score >= FULL_SCORE_THRESHOLD)
    )
    partial = description_chars >= 300 or detail_count >= 3 or score >= PARTIAL_SCORE_THRESHOLD

    if full:
        classification = "full"
    elif partial:
        classification = "partial"
    else:
        classification = "sparse"

    reasons: list[str] = [
        f"description_chars={description_chars}",
        f"substantive_requirements={len(substantive_requirements)}",
        f"substantive_responsibilities={len(substantive_responsibilities)}",
    ]
    if classification == "sparse":
        reasons.append(
            "insufficient original JD detail; source-fit commentary and inferred tech stack do not count toward fidelity"
        )
    elif classification == "partial":
        reasons.append("usable employer-authored detail exists, but the JD is not fully preserved")
    else:
        reasons.append("substantive employer-authored JD detail is preserved")

    return JDFidelityAssessment(
        classification=classification,
        score=score,
        generation_eligible=classification in {"partial", "full"},
        description_chars=description_chars,
        requirements_count=len(substantive_requirements),
        responsibilities_count=len(substantive_responsibilities),
        substantive_detail_count=detail_count,
        reasons=reasons,
    )
