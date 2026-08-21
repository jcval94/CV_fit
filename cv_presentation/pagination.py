from __future__ import annotations

import math
from dataclasses import dataclass, field

from cv_presentation.schemas import CVPresentationModel, PresentationExperienceItem, PresentationProjectItem, PresentationLine


@dataclass
class PageContent:
    page_number: int
    total_pages: int
    show_header: bool = False
    show_summary: bool = False
    experience: list[PresentationExperienceItem] = field(default_factory=list)
    projects: list[PresentationProjectItem] = field(default_factory=list)
    skills: list[PresentationLine] = field(default_factory=list)
    education: list[PresentationLine] = field(default_factory=list)
    certifications: list[PresentationLine] = field(default_factory=list)


def _text_lines(text: str, chars_per_line: int) -> int:
    return max(1, math.ceil(max(len(text.strip()), 1) / chars_per_line))


def _experience_lines(item: PresentationExperienceItem, chars: int) -> int:
    return 2 + sum(1 + _text_lines(bullet.text, chars) for bullet in item.bullets)


def _project_lines(item: PresentationProjectItem, chars: int) -> int:
    return 1 + sum(1 + _text_lines(bullet.text, chars) for bullet in item.bullets)


def _line_section_lines(items: list[PresentationLine], chars: int) -> int:
    return 0 if not items else 1 + sum(_text_lines(item.text, chars) for item in items)


def _tail_sections_lines(model: CVPresentationModel) -> int:
    chars = model.density.estimated_chars_per_line
    lines = 0
    if model.projects:
        lines += 1 + sum(_project_lines(item, chars) for item in model.projects)
    lines += _line_section_lines(model.skills, chars)
    lines += _line_section_lines(model.education, chars)
    lines += _line_section_lines(model.certifications, chars)
    return lines


def _harvard_page_plan(model: CVPresentationModel) -> list[PageContent]:
    """Preserve the source Harvard flow: header -> education -> experience -> projects -> skills.

    Certifications, when present, are carried as technical-skill tail content by the
    Harvard renderer rather than creating a new branded/visual section.
    """
    chars = model.density.estimated_chars_per_line
    per_page = model.density.estimated_lines_per_page
    header_lines = 4
    education_lines = _line_section_lines(model.education, chars)
    experience_heading = 1 if model.experience else 0
    exp_lines = [_experience_lines(item, chars) for item in model.experience]
    projects_lines = 0 if not model.projects else 1 + sum(_project_lines(item, chars) for item in model.projects)
    skills_lines = _line_section_lines(model.skills + model.certifications, chars)
    total_estimated = header_lines + education_lines + experience_heading + sum(exp_lines) + projects_lines + skills_lines

    if model.document.target_pages == 1 or total_estimated <= per_page:
        return [PageContent(
            page_number=1,
            total_pages=1,
            show_header=True,
            show_summary=False,
            education=list(model.education),
            experience=list(model.experience),
            projects=list(model.projects),
            skills=list(model.skills),
            certifications=list(model.certifications),
        )]

    used = header_lines + education_lines + experience_heading
    page1_exp: list[PresentationExperienceItem] = []
    page2_exp: list[PresentationExperienceItem] = []
    for item, item_lines in zip(model.experience, exp_lines):
        if not page1_exp or used + item_lines <= per_page:
            page1_exp.append(item)
            used += item_lines
        else:
            page2_exp.append(item)

    return [
        PageContent(
            page_number=1,
            total_pages=2,
            show_header=True,
            show_summary=False,
            education=list(model.education),
            experience=page1_exp,
        ),
        PageContent(
            page_number=2,
            total_pages=2,
            show_header=False,
            show_summary=False,
            experience=page2_exp,
            projects=list(model.projects),
            skills=list(model.skills),
            certifications=list(model.certifications),
        ),
    ]


def build_page_plan(model: CVPresentationModel) -> list[PageContent]:
    """Create a deterministic 1-2 page US-Letter-oriented content plan.

    The upstream fitter is expected to have already reduced content to the configured
    target. This planner never rewrites or truncates text and never splits a single
    experience item across pages. Physical browser measurement remains a later
    layout-validation concern.
    """
    if model.document.page_size != "letter":
        raise ValueError("HTML template v1 currently supports US Letter only")
    if model.document.target_pages not in {1, 2}:
        raise ValueError("HTML template v1 supports target_pages of 1 or 2 only")
    if model.document.template_id == "harvard_v1":
        return _harvard_page_plan(model)

    chars = model.density.estimated_chars_per_line
    per_page = model.density.estimated_lines_per_page
    header_lines = 4
    summary_lines = 1 + _text_lines(model.summary.text, chars)
    experience_heading = 1 if model.experience else 0
    exp_lines = [_experience_lines(item, chars) for item in model.experience]
    tail_lines = _tail_sections_lines(model)
    total_estimated = header_lines + summary_lines + experience_heading + sum(exp_lines) + tail_lines

    if model.document.target_pages == 1 or total_estimated <= per_page:
        return [PageContent(
            page_number=1,
            total_pages=1,
            show_header=True,
            show_summary=True,
            experience=list(model.experience),
            projects=list(model.projects),
            skills=list(model.skills),
            education=list(model.education),
            certifications=list(model.certifications),
        )]

    page1_base = header_lines + summary_lines + experience_heading
    page1_exp: list[PresentationExperienceItem] = []
    page2_exp: list[PresentationExperienceItem] = []
    used = page1_base

    for item, item_lines in zip(model.experience, exp_lines):
        if not page1_exp or used + item_lines <= per_page:
            page1_exp.append(item)
            used += item_lines
        else:
            page2_exp.append(item)

    if not page2_exp and tail_lines > max(8, per_page // 3) and len(page1_exp) > 1:
        page2_exp.insert(0, page1_exp.pop())

    return [
        PageContent(
            page_number=1,
            total_pages=2,
            show_header=True,
            show_summary=True,
            experience=page1_exp,
        ),
        PageContent(
            page_number=2,
            total_pages=2,
            show_header=False,
            show_summary=False,
            experience=page2_exp,
            projects=list(model.projects),
            skills=list(model.skills),
            education=list(model.education),
            certifications=list(model.certifications),
        ),
    ]
