from __future__ import annotations

import unittest
from pathlib import Path

from cv_presentation.branding import fallback_brand, tokens_from_brand
from cv_presentation.design_agent import DesignReview
from cv_presentation.render_html import render_html
from cv_presentation.templates import get_template_policy
from tests.test_cv_templates import presentation


class TemplateGateTests(unittest.TestCase):
    def test_adaptive_render_refuses_design_revise(self):
        model = presentation("technical_modern_v1")
        tokens = tokens_from_brand(fallback_brand("Example Company"))
        review = DesignReview(
            decision="REVISE",
            ats_safe=False,
            print_safe=False,
            notes=["Hierarchy must be revised."],
        )
        with self.assertRaises(ValueError):
            render_html(model, tokens=tokens, design_review=review)

    def test_harvard_preserves_locked_visual_system_but_uses_senior_flow(self):
        model = presentation("harvard_v1")
        tokens = tokens_from_brand(fallback_brand("Example Company"))
        review = DesignReview(
            decision="PASS",
            preserve_template=True,
            ats_safe=True,
            print_safe=True,
        )
        html = render_html(model, tokens=tokens, design_review=review)
        self.assertNotIn("Professional Summary", html)
        self.assertNotIn(model.summary.text, html)
        self.assertLess(html.index("Experience"), html.index("Education"))
        self.assertIn('font-family:"Times New Roman"', html)

    def test_templates_do_not_silently_hide_page_overflow(self):
        template_dir = Path("cv_presentation/templates")
        for template_id in (
            "professional_sidebar_v1",
            "ai_engineer_sidebar_v1",
            "executive_letter_v1",
            "technical_modern_v1",
            "harvard_v1",
        ):
            text = (template_dir / get_template_policy(template_id).filename).read_text(encoding="utf-8")
            self.assertNotIn("overflow:hidden", text, template_id)


if __name__ == "__main__":
    unittest.main()
