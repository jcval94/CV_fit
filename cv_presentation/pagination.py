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
    education: list[PresentationLine] = field(default_factory=list)
    projects: list[PresentationProjectItem] = field(default_factory=list)
    skills: list[PresentationLine] = field(default_factory=list)
    certifications: list[PresentationLine] = field(default_factory=list)


def _text_lines(text: str, chars_per_line: int) -> int:
    return max(1, math.ceil(max(len(text.strip()), 1) / chars_per_line))


def _experience_lines(item: PresentationExperienceItem, chars: int) -> int:
    return 2 + sum(1 + _text_lines(bullet.text, chars) for bullet in item.bullets)


def _project_lines(item: PresentationProjectItem, chars: int) -> int:
    return 1 + sum(1 + _text_lines(bullet.text, chars) for bullet in item.bullets)


def _new_page(pages: list[PageContent], used: list[int], *, continuation_lines: int) -> None:
    if len(pages) >= 2:
        return
    pages.append(PageContent(page_number=2, total_pages=2, show_header=False, show_summary=False))
    used.append(continuation_lines)


def _should_break(current_used: int, cost: int, per_page: int, pages: list[PageContent]) -> bool:
    return current_used + cost > per_page and len(pages) < 2


def _pack_experience(
    items: list[PresentationExperienceItem],
    *,
    pages: list[PageContent],
    used: list[int],
    per_page: int,
    chars: int,
    continuation_lines: int,
) -> None:
    for item in items:
        current = pages[-1]
        heading_cost = 1 if not current.experience else 0
        cost = heading_cost + _experience_lines(item, chars)
        if _should_break(used[-1], cost, per_page, pages) and current.experience:
            _new_page(pages, used, continuation_lines=continuation_lines)
            current = pages[-1]
            heading_cost = 1
            cost = heading_cost + _experience_lines(item, chars)
        current.experience.append(item)
        used[-1] += cost


def _pack_lines(
    items: list[PresentationLine],
    *,
    attribute: str,
    pages: list[PageContent],
    used: list[int],
    per_page: int,
    chars: int,
    continuation_lines: int,
) -> None:
    for item in items:
        current = pages[-1]
        values = getattr(current, attribute)
        heading_cost = 1 if not values else 0
        cost = heading_cost + _text_lines(item.text, chars)
        if _should_break(used[-1], cost, per_page, pages):
            _new_page(pages, used, continuation_lines=continuation_lines)
            current = pages[-1]
            values = getattr(current, attribute)
            heading_cost = 1
            cost = heading_cost + _text_lines(item.text, chars)
        values.append(item)
        used[-1] += cost


def _pack_projects(
    items: list[PresentationProjectItem],
    *,
    pages: list[PageContent],
    used: list[int],
    per_page: int,
    chars: int,
    continuation_lines: int,
) -> None:
    for item in items:
        current = pages[-1]
        heading_cost = 1 if not current.projects else 0
        cost = heading_cost + _project_lines(item, chars)
        if _should_break(used[-1], cost, per_page, pages):
            _new_page(pages, used, continuation_lines=continuation_lines)
            current = pages[-1]
            heading_cost = 1
            cost = heading_cost + _project_lines(item, chars)
        current.projects.append(item)
        used[-1] += cost


def build_page_plan(model: CVPresentationModel) -> list[PageContent]:
    """Pack approved content into one or two Letter pages in editorial order.

    The planner does not pre-assign all tail sections to page two. It fills
    available space on page one after the complete professional chronology,
    then continues on page two only when needed. This prevents the large blank
    areas observed in the first production renders while preserving the global
    order Experience -> Education -> Projects -> Skills -> Certifications.

    Experience entries and projects are never split. Education, skills and
    certifications can continue item-by-item. Chromium remains authoritative
    for physical fit; this planner only provides deterministic placement.
    """
    if model.document.page_size != "letter":
        raise ValueError("HTML templates currently support US Letter only")
    if model.document.target_pages not in {1, 2}:
        raise ValueError("HTML templates support target_pages of 1 or 2 only")

    chars = model.density.estimated_chars_per_line
    per_page = model.density.estimated_lines_per_page
    is_harvard = model.document.template_id == "harvard_v1"

    header_lines = 4
    summary_lines = 0 if is_harvard else 1 + _text_lines(model.summary.text, chars)
    continuation_lines = 0 if is_harvard else 2

    pages = [PageContent(
        page_number=1,
        total_pages=1,
        show_header=True,
        show_summary=not is_harvard,
    )]
    used = [header_lines + summary_lines]

    _pack_experience(
        list(model.experience),
        pages=pages,
        used=used,
        per_page=per_page,
        chars=chars,
        continuation_lines=continuation_lines,
    )

    # Only after every experience entry has been placed may lower-priority
    # sections consume the remaining page capacity.
    _pack_lines(
        list(model.education),
        attribute="education",
        pages=pages,
        used=used,
        per_page=per_page,
        chars=chars,
        continuation_lines=continuation_lines,
    )
    _pack_projects(
        list(model.projects),
        pages=pages,
        used=used,
        per_page=per_page,
        chars=chars,
        continuation_lines=continuation_lines,
    )
    _pack_lines(
        list(model.skills),
        attribute="skills",
        pages=pages,
        used=used,
        per_page=per_page,
        chars=chars,
        continuation_lines=continuation_lines,
    )
    _pack_lines(
        list(model.certifications),
        attribute="certifications",
        pages=pages,
        used=used,
        per_page=per_page,
        chars=chars,
        continuation_lines=continuation_lines,
    )

    total = len(pages)
    for index, page in enumerate(pages, start=1):
        page.page_number = index
        page.total_pages = total
    return pages
