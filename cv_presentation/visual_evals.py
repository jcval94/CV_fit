from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from cv_presentation.physical_layout import PhysicalLayoutReport


class VisualThresholds(BaseModel):
    one_page_min_utilization: float = 0.45
    two_page_page1_min_utilization: float = 0.62
    two_page_page2_min_utilization: float = 0.42
    min_experience_area_ratio: float = 0.30
    max_skills_area_ratio: float = 0.20
    max_projects_area_ratio: float = 0.28
    max_certifications_area_ratio: float = 0.18
    max_skills: int = 15
    max_projects: int = 2
    min_experience_items: int = 2
    min_education_items: int = 1
    min_certifications: int = 3


class VisualEvalReport(BaseModel):
    schema_version: int = 1
    status: Literal["PASS", "FAIL"]
    template_id: str
    page_count: int
    page_utilization: list[float]
    section_area_ratios: dict[str, float]
    section_item_counts: dict[str, int]
    thresholds: VisualThresholds
    reasons: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


def evaluate_visual_balance(
    physical: PhysicalLayoutReport,
    *,
    template_id: str,
    thresholds: VisualThresholds | None = None,
) -> VisualEvalReport:
    """Evaluate objective CV composition after Chromium has rendered the document.

    Mechanical clipping/overflow remains the physical validator's responsibility.
    This layer addresses the failures visible in the first production screenshots:
    under-filled pages, Skills visually outweighing Experience, project-heavy
    composition and rendered loss of mandatory senior-career sections.
    """
    t = thresholds or VisualThresholds()
    reasons: list[str] = []
    notes = [
        "Section area ratios exclude header/summary and compare Experience, Education, Projects, Skills and Certifications only.",
        "This gate never rewrites CV claims; upstream Writer/Fitter must resolve a failed composition.",
    ]

    if physical.status != "PASS":
        reasons.append("physical_layout_not_passed")

    page_count = physical.pdf_pages
    util = list(physical.page_utilization)
    if page_count == 1 and util:
        if util[0] < t.one_page_min_utilization:
            reasons.append(f"one_page_underutilized:{util[0]:.3f}<{t.one_page_min_utilization:.3f}")
    elif page_count == 2 and len(util) >= 2:
        if util[0] < t.two_page_page1_min_utilization:
            reasons.append(f"page_1_underutilized:{util[0]:.3f}<{t.two_page_page1_min_utilization:.3f}")
        if util[1] < t.two_page_page2_min_utilization:
            reasons.append(f"page_2_underutilized:{util[1]:.3f}<{t.two_page_page2_min_utilization:.3f}")

    ratios = physical.section_area_ratios
    counts = physical.section_item_counts
    experience = float(ratios.get("experience", 0.0))
    skills = float(ratios.get("skills", 0.0))
    projects = float(ratios.get("projects", 0.0))
    certifications = float(ratios.get("certifications", 0.0))

    if experience < t.min_experience_area_ratio:
        reasons.append(f"experience_area_too_small:{experience:.3f}<{t.min_experience_area_ratio:.3f}")
    if skills > t.max_skills_area_ratio:
        reasons.append(f"skills_area_too_large:{skills:.3f}>{t.max_skills_area_ratio:.3f}")
    if experience <= skills:
        reasons.append(f"skills_not_subordinate_to_experience:{skills:.3f}>={experience:.3f}")
    if projects > t.max_projects_area_ratio:
        reasons.append(f"projects_area_too_large:{projects:.3f}>{t.max_projects_area_ratio:.3f}")
    if certifications > t.max_certifications_area_ratio:
        reasons.append(f"certifications_area_too_large:{certifications:.3f}>{t.max_certifications_area_ratio:.3f}")

    if int(counts.get("experience", 0)) < t.min_experience_items:
        reasons.append(f"rendered_experience_items_too_few:{counts.get('experience', 0)}<{t.min_experience_items}")
    if int(counts.get("education", 0)) < t.min_education_items:
        reasons.append(f"rendered_education_missing:{counts.get('education', 0)}<{t.min_education_items}")
    if int(counts.get("skills", 0)) > t.max_skills:
        reasons.append(f"rendered_skill_count_exceeded:{counts.get('skills', 0)}>{t.max_skills}")
    if int(counts.get("projects", 0)) > t.max_projects:
        reasons.append(f"rendered_project_count_exceeded:{counts.get('projects', 0)}>{t.max_projects}")
    if int(counts.get("certifications", 0)) < t.min_certifications:
        reasons.append(f"rendered_mandatory_certifications_missing:{counts.get('certifications', 0)}<{t.min_certifications}")

    for value in physical.empty_rendered_sections:
        reasons.append(f"empty_rendered_section:{value}")

    return VisualEvalReport(
        status="PASS" if not reasons else "FAIL",
        template_id=template_id,
        page_count=page_count,
        page_utilization=util,
        section_area_ratios=dict(ratios),
        section_item_counts=dict(counts),
        thresholds=t,
        reasons=reasons,
        notes=notes,
    )
