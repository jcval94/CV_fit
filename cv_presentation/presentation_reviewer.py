from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, Field

from cv_agent.model_policy import model_ids
from cv_presentation.physical_layout import PhysicalLayoutReport
from cv_presentation.visual_evals import VisualEvalReport


PRESENTATION_REVIEW_INSTRUCTION = """
You are a conservative Senior CV Presentation Reviewer for Data Science, AI/ML and technical leadership resumes.
You do not see an image. You receive only deterministic Chromium measurements, section counts, section-area ratios and factual template topology.

Judge only what those supplied measurements support:
- whether the professional experience remains the dominant visual/persuasive section;
- whether skills, projects and certifications are subordinate rather than visually overwhelming;
- whether page utilization is credible for a senior professional CV;
- whether the section counts support a concise, senior-level document;
- whether a two-page layout appears justified by measured use of both pages.

Hard rules:
- Never describe colors, typography, alignment, whitespace patterns or visual defects that are not explicitly supplied.
- Never invent candidate facts or vacancy fit.
- deterministic_visual_status=FAIL is authoritative. You must return REVIEW_REQUIRED and may not override it.
- physical_status=FAIL is authoritative. You must return REVIEW_REQUIRED and may not override it.
- Do not recommend adding unsupported content merely to fill space.
- Do not recommend more than 15 skills or more than 2 projects.
- Experience should remain more important than Skills or Projects.
- PASS only when the supplied metrics support a compact, senior, submission-ready composition.
""".strip()


class PresentationReview(BaseModel):
    decision: Literal["PASS", "REVIEW_REQUIRED"]
    senior_hierarchy: Literal["PASS", "CONCERN"]
    page_balance: Literal["PASS", "CONCERN"]
    section_balance: Literal["PASS", "CONCERN"]
    reasons: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class StructuredPresentationClient(Protocol):
    async def call(
        self,
        *,
        name: str,
        model: str,
        instruction: str,
        payload: dict,
        output_schema: type[BaseModel],
        max_output_tokens: int = 1600,
    ) -> BaseModel: ...


def blocked_presentation_review(*, visual: VisualEvalReport, physical: PhysicalLayoutReport) -> PresentationReview:
    reasons: list[str] = []
    if physical.status != "PASS":
        reasons.append("Physical layout gate failed; reviewer cannot override mechanical layout safety.")
    if visual.status != "PASS":
        reasons.extend(f"Deterministic visual gate: {reason}" for reason in visual.reasons[:8])
    return PresentationReview(
        decision="REVIEW_REQUIRED",
        senior_hierarchy="CONCERN",
        page_balance="CONCERN" if any("utilized" in reason for reason in visual.reasons) else "PASS",
        section_balance="CONCERN",
        reasons=reasons or ["Deterministic presentation gate did not pass."],
        recommendations=["Revise upstream content selection or fitting; do not fabricate content to improve page fill."],
    )


async def review_presentation(
    *,
    client: StructuredPresentationClient,
    template_id: str,
    role: str,
    visual: VisualEvalReport,
    physical: PhysicalLayoutReport,
) -> PresentationReview:
    """Review metric-grounded presentation without permitting LLM gate override."""
    if physical.status != "PASS" or visual.status != "PASS":
        return blocked_presentation_review(visual=visual, physical=physical)

    models = model_ids()
    result = await client.call(
        name=f"cv_presentation_reviewer_{role}",
        model=models["economy"],
        instruction=PRESENTATION_REVIEW_INSTRUCTION,
        payload={
            "template_id": template_id,
            "role": role,
            "physical_status": physical.status,
            "deterministic_visual_status": visual.status,
            "page_count": visual.page_count,
            "page_utilization": visual.page_utilization,
            "section_area_ratios": visual.section_area_ratios,
            "section_item_counts": visual.section_item_counts,
            "visual_thresholds": visual.thresholds.model_dump(mode="json"),
            "deterministic_notes": visual.notes,
        },
        output_schema=PresentationReview,
        max_output_tokens=1400,
    )
    assert isinstance(result, PresentationReview)
    return result
