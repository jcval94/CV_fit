from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TemplatePolicy:
    template_id: str
    filename: str
    adaptive_branding: bool
    locked_visual_system: bool
    supports_two_pages: bool = True
    source_name: str = ""


TEMPLATES: dict[str, TemplatePolicy] = {
    "professional_sidebar_v1": TemplatePolicy(
        template_id="professional_sidebar_v1",
        filename="professional_sidebar_v1.html.j2",
        adaptive_branding=True,
        locked_visual_system=False,
        source_name="cv_.html",
    ),
    "ai_engineer_sidebar_v1": TemplatePolicy(
        template_id="ai_engineer_sidebar_v1",
        filename="ai_engineer_sidebar_v1.html.j2",
        adaptive_branding=True,
        locked_visual_system=False,
        source_name="cv_data_scientist_ai_engineer.html",
    ),
    "executive_letter_v1": TemplatePolicy(
        template_id="executive_letter_v1",
        filename="executive_letter_v1.html.j2",
        adaptive_branding=True,
        locked_visual_system=False,
        source_name="cv_data_scientist.html",
    ),
    "technical_modern_v1": TemplatePolicy(
        template_id="technical_modern_v1",
        filename="technical_modern_v1.html.j2",
        adaptive_branding=True,
        locked_visual_system=False,
        source_name="CV_fit Technical Modern ATS-first redesign",
    ),
    "ats_classic_v1": TemplatePolicy(
        template_id="ats_classic_v1",
        filename="executive_letter_v1.html.j2",
        adaptive_branding=True,
        locked_visual_system=False,
        source_name="compatibility alias -> cv_data_scientist.html",
    ),
    "harvard_v1": TemplatePolicy(
        template_id="harvard_v1",
        filename="harvard_v1.html.j2",
        adaptive_branding=False,
        locked_visual_system=True,
        source_name="cv_formato_harvard_ai_engineer.html",
    ),
}


def get_template_policy(template_id: str) -> TemplatePolicy:
    try:
        return TEMPLATES[template_id]
    except KeyError as exc:
        raise ValueError(f"unknown CV template_id {template_id!r}; allowed={sorted(TEMPLATES)}") from exc
