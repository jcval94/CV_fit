from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


LETTER_WIDTH_PT = 612.0
LETTER_HEIGHT_PT = 792.0
PIXEL_TOLERANCE = 1.5
POINT_TOLERANCE = 2.0
EDITORIAL_SECTIONS = ("experience", "education", "projects", "skills", "certifications")


class OverflowElement(BaseModel):
    page_number: int
    label: str
    top: float
    left: float
    right: float
    bottom: float


class SectionMeasurement(BaseModel):
    page_number: int
    section: str
    height: float
    area: float
    item_count: int = 0
    text_chars: int = 0


class PhysicalPageMeasurement(BaseModel):
    page_number: int
    client_width: float
    client_height: float
    scroll_width: float
    scroll_height: float
    computed_overflow_x: str
    computed_overflow_y: str
    overflow_x: bool
    overflow_y: bool
    out_of_bounds: list[OverflowElement] = Field(default_factory=list)
    orphan_headings: list[str] = Field(default_factory=list)
    usable_height: float = 0.0
    used_height: float = 0.0
    utilization_ratio: float = 0.0
    sections: list[SectionMeasurement] = Field(default_factory=list)


class PhysicalLayoutReport(BaseModel):
    schema_version: int = 2
    status: Literal["PASS", "FAIL"]
    html_file: str
    pdf_file: str
    expected_pages: int
    dom_pages: int
    pdf_pages: int
    pdf_page_sizes_points: list[tuple[float, float]]
    pages: list[PhysicalPageMeasurement]
    reasons: list[str] = Field(default_factory=list)
    screenshot_file: str | None = None
    page_utilization: list[float] = Field(default_factory=list)
    section_area_ratios: dict[str, float] = Field(default_factory=dict)
    section_item_counts: dict[str, int] = Field(default_factory=dict)
    empty_rendered_sections: list[str] = Field(default_factory=list)


def _measure_dom(page) -> list[dict]:
    return page.eval_on_selector_all(
        ".page",
        """
        (pages) => pages.map((root, pageIndex) => {
          const rr = root.getBoundingClientRect();
          const rs = getComputedStyle(root);
          const paddingTop = parseFloat(rs.paddingTop || '0') || 0;
          const paddingBottom = parseFloat(rs.paddingBottom || '0') || 0;
          const contentTop = rr.top + paddingTop;
          const contentBottom = rr.bottom - paddingBottom;
          const usableHeight = Math.max(1, contentBottom - contentTop);
          const visible = (el) => {
            const s = getComputedStyle(el);
            const r = el.getBoundingClientRect();
            return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0;
          };
          const label = (el) => {
            const cls = typeof el.className === 'string' && el.className.trim()
              ? '.' + el.className.trim().split(/\\s+/).slice(0, 2).join('.')
              : '';
            const text = (el.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 80);
            return `${el.tagName.toLowerCase()}${cls}${text ? ': ' + text : ''}`;
          };
          const offenders = [];
          for (const el of root.querySelectorAll('*')) {
            if (!visible(el)) continue;
            const r = el.getBoundingClientRect();
            if (r.top < rr.top - 1.5 || r.left < rr.left - 1.5 || r.right > rr.right + 1.5 || r.bottom > rr.bottom + 1.5) {
              offenders.push({
                page_number: pageIndex + 1,
                label: label(el),
                top: r.top - rr.top,
                left: r.left - rr.left,
                right: r.right - rr.left,
                bottom: r.bottom - rr.top,
              });
            }
          }
          const orphanHeadings = [];
          for (const h of root.querySelectorAll('h1,h2,h3')) {
            if (!visible(h)) continue;
            let next = h.nextElementSibling;
            while (next && !visible(next)) next = next.nextElementSibling;
            if (!next) {
              orphanHeadings.push(label(h));
              continue;
            }
            const nr = next.getBoundingClientRect();
            if (nr.top >= rr.bottom - 2 || nr.bottom > rr.bottom + 1.5) orphanHeadings.push(label(h));
          }

          const topSections = Array.from(root.querySelectorAll(':scope > [data-section]')).filter(visible);
          let maxBottom = contentTop;
          const sections = topSections.map((section) => {
            const r = section.getBoundingClientRect();
            maxBottom = Math.max(maxBottom, r.bottom);
            const text = (section.textContent || '').replace(/\\s+/g, ' ').trim();
            return {
              page_number: pageIndex + 1,
              section: section.dataset.section || 'unknown',
              height: Math.max(0, r.height),
              area: Math.max(0, r.width * r.height),
              item_count: section.querySelectorAll('[data-item]').length,
              text_chars: text.length,
            };
          });
          const usedHeight = Math.max(0, Math.min(contentBottom, maxBottom) - contentTop);
          const utilizationRatio = Math.max(0, Math.min(1, usedHeight / usableHeight));

          return {
            page_number: pageIndex + 1,
            client_width: root.clientWidth,
            client_height: root.clientHeight,
            scroll_width: root.scrollWidth,
            scroll_height: root.scrollHeight,
            computed_overflow_x: rs.overflowX,
            computed_overflow_y: rs.overflowY,
            overflow_x: root.scrollWidth > root.clientWidth + 1.5,
            overflow_y: root.scrollHeight > root.clientHeight + 1.5,
            out_of_bounds: offenders.slice(0, 40),
            orphan_headings: orphanHeadings,
            usable_height: usableHeight,
            used_height: usedHeight,
            utilization_ratio: utilizationRatio,
            sections,
          };
        })
        """,
    )


def _aggregate_section_metrics(measurements: list[PhysicalPageMeasurement]) -> tuple[dict[str, float], dict[str, int], list[str]]:
    areas = {section: 0.0 for section in EDITORIAL_SECTIONS}
    counts = {section: 0 for section in EDITORIAL_SECTIONS}
    empty: list[str] = []
    seen_occurrences: dict[str, int] = {}
    for page in measurements:
        for section in page.sections:
            if section.section not in areas:
                continue
            areas[section.section] += section.area
            counts[section.section] += section.item_count
            seen_occurrences[section.section] = seen_occurrences.get(section.section, 0) + 1
            if section.text_chars == 0 or section.height <= 0:
                empty.append(f"page_{page.page_number}:{section.section}")
    total_area = sum(areas.values())
    ratios = {
        section: round(area / total_area, 4) if total_area > 0 else 0.0
        for section, area in areas.items()
    }
    return ratios, counts, empty


def validate_html_and_export_pdf(
    html_path: Path,
    pdf_path: Path,
    *,
    expected_pages: int,
    screenshot_path: Path | None = None,
) -> PhysicalLayoutReport:
    """Measure rendered Letter pages in Chromium, export PDF, and fail closed on clipping/overflow.

    In addition to mechanical layout safety, the report records objective visual
    metrics used by a separate senior-CV presentation gate: vertical page use,
    section area ratios and rendered item counts. Those metrics do not change the
    physical PASS/FAIL result by themselves.
    """
    if expected_pages not in {1, 2}:
        raise ValueError("expected_pages must be 1 or 2")
    if not html_path.exists():
        raise FileNotFoundError(html_path)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - dependency preflight
        raise RuntimeError("Playwright is required for physical layout validation") from exc

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    if screenshot_path is not None:
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1800}, device_scale_factor=1)
        page.emulate_media(media="print")
        page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
        page.evaluate("document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve()")
        raw_pages = _measure_dom(page)
        if screenshot_path is not None:
            page.screenshot(path=str(screenshot_path), full_page=True)
        page.pdf(
            path=str(pdf_path),
            format="Letter",
            print_background=True,
            prefer_css_page_size=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        browser.close()

    measurements = [PhysicalPageMeasurement.model_validate(item) for item in raw_pages]

    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency preflight
        raise RuntimeError("pypdf is required for PDF page verification") from exc

    reader = PdfReader(str(pdf_path))
    page_sizes: list[tuple[float, float]] = []
    for pdf_page in reader.pages:
        page_sizes.append((round(float(pdf_page.mediabox.width), 2), round(float(pdf_page.mediabox.height), 2)))

    reasons: list[str] = []
    dom_pages = len(measurements)
    pdf_pages = len(reader.pages)
    if dom_pages != expected_pages:
        reasons.append(f"dom_page_count_mismatch:{dom_pages}!={expected_pages}")
    if pdf_pages != expected_pages:
        reasons.append(f"pdf_page_count_mismatch:{pdf_pages}!={expected_pages}")

    for item in measurements:
        if item.overflow_x:
            reasons.append(f"page_{item.page_number}_horizontal_overflow:{item.scroll_width}>{item.client_width}")
        if item.overflow_y:
            reasons.append(f"page_{item.page_number}_vertical_overflow:{item.scroll_height}>{item.client_height}")
        if item.out_of_bounds:
            reasons.append(f"page_{item.page_number}_out_of_bounds_elements:{len(item.out_of_bounds)}")
        if item.orphan_headings:
            reasons.append(f"page_{item.page_number}_orphan_headings:{len(item.orphan_headings)}")
        if item.computed_overflow_x == "hidden" or item.computed_overflow_y == "hidden":
            reasons.append(f"page_{item.page_number}_uses_hidden_overflow")

    for index, (width, height) in enumerate(page_sizes, start=1):
        if abs(width - LETTER_WIDTH_PT) > POINT_TOLERANCE or abs(height - LETTER_HEIGHT_PT) > POINT_TOLERANCE:
            reasons.append(f"pdf_page_{index}_not_letter:{width}x{height}")

    section_area_ratios, section_item_counts, empty_sections = _aggregate_section_metrics(measurements)
    return PhysicalLayoutReport(
        status="PASS" if not reasons else "FAIL",
        html_file=str(html_path),
        pdf_file=str(pdf_path),
        expected_pages=expected_pages,
        dom_pages=dom_pages,
        pdf_pages=pdf_pages,
        pdf_page_sizes_points=page_sizes,
        pages=measurements,
        reasons=reasons,
        screenshot_file=str(screenshot_path) if screenshot_path is not None else None,
        page_utilization=[round(page.utilization_ratio, 4) for page in measurements],
        section_area_ratios=section_area_ratios,
        section_item_counts=section_item_counts,
        empty_rendered_sections=empty_sections,
    )
