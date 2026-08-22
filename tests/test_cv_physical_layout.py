from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

from cv_presentation.physical_layout import validate_html_and_export_pdf


@unittest.skipUnless(
    importlib.util.find_spec("playwright") is not None and importlib.util.find_spec("pypdf") is not None,
    "physical layout dependencies are installed only in the presentation/agent CI environment",
)
class PhysicalLayoutTests(unittest.TestCase):
    def _render(self, body: str, *, expected_pages: int):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        html = root / "cv.html"
        pdf = root / "cv.pdf"
        screenshot = root / "cv.png"
        html.write_text(
            f"""<!doctype html><html><head><style>
            *{{box-sizing:border-box}} html,body{{margin:0;padding:0}}
            .page{{width:8.5in;height:11in;page-break-after:always;background:white;padding:.5in;position:relative}}
            .page:last-child{{page-break-after:auto}}
            [data-section]{{margin-bottom:12px}}
            @page{{size:letter;margin:0}}
            @media print{{body{{margin:0}}}}
            </style></head><body>{body}</body></html>""",
            encoding="utf-8",
        )
        report = validate_html_and_export_pdf(html, pdf, expected_pages=expected_pages, screenshot_path=screenshot)
        return tmp, report, pdf, screenshot

    def test_one_letter_page_passes_and_exports_pdf(self):
        tmp, report, pdf, screenshot = self._render(
            '<section class="page"><h1>Candidate</h1><p>Grounded CV content.</p></section>',
            expected_pages=1,
        )
        try:
            self.assertEqual(report.status, "PASS", report.reasons)
            self.assertEqual(report.dom_pages, 1)
            self.assertEqual(report.pdf_pages, 1)
            self.assertEqual(report.pdf_page_sizes_points, [(612.0, 792.0)])
            self.assertTrue(pdf.exists())
            self.assertTrue(screenshot.exists())
        finally:
            tmp.cleanup()

    def test_two_letter_pages_pass(self):
        tmp, report, _, _ = self._render(
            '<section class="page"><h1>Page one</h1><p>Content</p></section>'
            '<section class="page"><h1>Page two</h1><p>Content</p></section>',
            expected_pages=2,
        )
        try:
            self.assertEqual(report.status, "PASS", report.reasons)
            self.assertEqual(report.pdf_pages, 2)
        finally:
            tmp.cleanup()

    def test_section_metrics_are_measured_from_rendered_dom(self):
        body = (
            '<section class="page" data-page="1">'
            '<header data-section="header"><h1>Candidate</h1></header>'
            '<section data-section="experience"><h2>Experience</h2>'
            '<article data-item="experience"><p>Role one</p><p>Impact detail.</p></article>'
            '<article data-item="experience"><p>Role two</p><p>Impact detail.</p></article></section>'
            '<section data-section="education"><h2>Education</h2><div data-item="education">Degree</div></section>'
            '<section data-section="skills"><h2>Skills</h2><span data-item="skill">Python</span><span data-item="skill">GenAI</span></section>'
            '<section data-section="certifications"><h2>Certifications</h2>'
            '<div data-item="certification">A</div><div data-item="certification">B</div><div data-item="certification">C</div></section>'
            '</section>'
        )
        tmp, report, _, _ = self._render(body, expected_pages=1)
        try:
            self.assertEqual(report.status, "PASS", report.reasons)
            self.assertEqual(report.schema_version, 2)
            self.assertEqual(report.section_item_counts["experience"], 2)
            self.assertEqual(report.section_item_counts["skills"], 2)
            self.assertEqual(report.section_item_counts["certifications"], 3)
            self.assertGreater(report.page_utilization[0], 0)
            self.assertGreater(report.section_area_ratios["experience"], 0)
        finally:
            tmp.cleanup()

    def test_out_of_bounds_content_fails_closed(self):
        tmp, report, _, _ = self._render(
            '<section class="page"><h1>Candidate</h1><div style="position:absolute;top:10.8in;height:.5in">Overflow</div></section>',
            expected_pages=1,
        )
        try:
            self.assertEqual(report.status, "FAIL")
            self.assertTrue(any("out_of_bounds" in reason or "vertical_overflow" in reason for reason in report.reasons), report.reasons)
        finally:
            tmp.cleanup()

    def test_page_count_mismatch_fails(self):
        tmp, report, _, _ = self._render(
            '<section class="page"><h1>Only one page</h1><p>Content</p></section>',
            expected_pages=2,
        )
        try:
            self.assertEqual(report.status, "FAIL")
            self.assertIn("dom_page_count_mismatch:1!=2", report.reasons)
            self.assertIn("pdf_page_count_mismatch:1!=2", report.reasons)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
