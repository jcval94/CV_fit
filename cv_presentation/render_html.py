from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from cv_presentation.branding import DesignTokens
from cv_presentation.design_agent import DesignReview
from cv_presentation.pagination import build_page_plan
from cv_presentation.schemas import CVPresentationModel
from cv_presentation.templates import get_template_policy


LABELS = {
    "en": {
        "summary": "Professional Summary",
        "experience": "Experience",
        "projects": "Selected Projects",
        "skills": "Skills",
        "education": "Education",
        "certifications": "Certifications",
        "page": "Page",
    },
    "es": {
        "summary": "Resumen Profesional",
        "experience": "Experiencia Profesional",
        "projects": "Proyectos Seleccionados",
        "skills": "Habilidades",
        "education": "Formación",
        "certifications": "Certificaciones",
        "page": "Página",
    },
    "fr": {
        "summary": "Résumé Professionnel",
        "experience": "Expérience",
        "projects": "Projets Sélectionnés",
        "skills": "Compétences",
        "education": "Formation",
        "certifications": "Certifications",
        "page": "Page",
    },
}


def _environment() -> Environment:
    template_dir = Path(__file__).resolve().parent / "templates"
    return Environment(
        loader=FileSystemLoader(str(template_dir)),
        # Every template in this environment is HTML, even though files end in
        # .html.j2. Extension-based select_autoescape would therefore miss them.
        autoescape=True,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _adaptive_style_tokens(tokens: DesignTokens, review: DesignReview | None) -> dict[str, Any]:
    style = tokens.model_dump()
    if review is None:
        return style
    if review.decision != "PASS" or not review.ats_safe or not review.print_safe:
        raise ValueError("adaptive template cannot render until the design review passes ATS and print safety")
    if review.preserve_template:
        raise ValueError("preserve_template is reserved for Harvard")

    # The reviewer can restrict a supplied brand color to accent-only use without
    # inventing any replacement color. Existing contrast-safe tokens are reused.
    if review.primary_usage == "accents_only":
        style["accent"] = tokens.primary
        style["primary"] = tokens.text
    elif review.primary_usage == "sidebar_background":
        style["primary"] = tokens.primary

    if review.secondary_usage == "accents_only":
        style["secondary"] = tokens.muted
    elif review.secondary_usage == "sidebar_background":
        style["primary"] = tokens.secondary
    else:
        style["secondary"] = tokens.secondary
    return style


def render_html(
    model: CVPresentationModel,
    *,
    tokens: DesignTokens,
    design_review: DesignReview | None = None,
) -> str:
    policy = get_template_policy(model.document.template_id)
    pages = build_page_plan(model)
    labels = LABELS.get(model.language, LABELS["en"])

    if policy.locked_visual_system:
        if design_review is not None and not design_review.preserve_template:
            raise ValueError("Harvard template requires preserve_template=true")
        style_tokens: dict[str, Any] = {
            "primary": "#000000",
            "secondary": "#000000",
            "accent": "#000000",
            "surface": "#FFFFFF",
            "text": "#000000",
            "muted": "#000000",
            "heading_font_stack": '"Times New Roman", Times, serif',
            "body_font_stack": '"Times New Roman", Times, serif',
        }
    else:
        style_tokens = _adaptive_style_tokens(tokens, design_review)

    template = _environment().get_template(policy.filename)
    return template.render(
        cv=model,
        pages=pages,
        labels=labels,
        style=style_tokens,
        design=design_review.model_dump() if design_review else None,
        policy=policy,
    )


def write_html(
    model: CVPresentationModel,
    output_path: Path,
    *,
    tokens: DesignTokens,
    design_review: DesignReview | None = None,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_html(model, tokens=tokens, design_review=design_review), encoding="utf-8")
    return output_path
