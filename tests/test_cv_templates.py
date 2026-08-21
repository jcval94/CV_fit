from __future__ import annotations

import asyncio
import unittest
from pathlib import Path

from cv_presentation.branding import BrandProfile, DesignTokens, fallback_brand, tokens_from_brand, validate_design_tokens
from cv_presentation.design_agent import DesignReview, review_design
from cv_presentation.pagination import build_page_plan
from cv_presentation.render_html import render_html
from cv_presentation.schemas import (
    CVPresentationModel,
    CandidateIdentity,
    DensitySpec,
    DocumentSpec,
    LayoutSpec,
    PresentationExperienceItem,
    PresentationLine,
    PresentationProjectItem,
)
from cv_presentation.templates import TEMPLATES, get_template_policy


class FakeDesignClient:
    def __init__(self, output: DesignReview) -> None:
        self.output = output
        self.calls = 0

    async def call(self, **kwargs):
        self.calls += 1
        return self.output


def line(text: str, ref: str = "evidence-1") -> PresentationLine:
    return PresentationLine(text=text, evidence_refs=[ref])


def presentation(template_id: str = "executive_letter_v1", *, large: bool = False) -> CVPresentationModel:
    bullet_text = (
        "Built and operated a production analytics workflow with measurable business impact, reproducible controls, "
        "technical review, and documented deployment practices across distributed data workloads."
        if large else "Built a production analytics workflow with measurable impact."
    )
    roles = []
    role_count = 3 if large else 2
    for index in range(role_count):
        roles.append(PresentationExperienceItem(
            organization=f"Organization {index + 1}",
            title=f"Role {index + 1}",
            period=f"202{index} – 202{index + 1}",
            evidence_refs=[f"role-{index}"],
            bullets=[line(bullet_text, f"role-{index}-b{bullet}") for bullet in range(4 if large else 2)],
        ))
    density = DensitySpec(
        estimated_chars_per_line=60 if large else 92,
        estimated_lines_per_page=35 if large else 50,
        max_role_bullets=4,
        min_role_bullets=1,
    )
    return CVPresentationModel(
        source_cv_hash="source",
        config_hash="config",
        candidate=CandidateIdentity(
            name="Candidate Name",
            location="Mexico",
            linkedin="linkedin.example/candidate",
            github="github.example/candidate",
        ),
        language="en",
        target_role="Senior Data Scientist",
        headline=line("Senior Data Scientist | AI/ML"),
        summary=line("Evidence-grounded data scientist focused on production machine learning and responsible AI."),
        experience=roles,
        projects=[PresentationProjectItem(name="Project A", evidence_refs=["project-a"], bullets=[line("Grounded AI evaluation project.", "project-a-b1")])],
        skills=[line("Python, SQL, Machine Learning", "skills-1")],
        education=[line("Graduate degree in Data Science", "education-1")],
        certifications=[line("Technical certification", "cert-1")],
        document=DocumentSpec(page_size="letter", target_pages=2, template_id=template_id),
        layout=LayoutSpec(),
        density=density,
    )


class TemplateIntakeTests(unittest.TestCase):
    def test_four_source_templates_are_registered(self):
        expected = {
            "professional_sidebar_v1",
            "ai_engineer_sidebar_v1",
            "executive_letter_v1",
            "harvard_v1",
        }
        self.assertTrue(expected.issubset(TEMPLATES))
        self.assertTrue(get_template_policy("harvard_v1").locked_visual_system)
        self.assertFalse(get_template_policy("harvard_v1").adaptive_branding)

    def test_templates_are_self_contained_and_have_no_demo_placeholders(self):
        template_dir = Path("cv_presentation/templates")
        forbidden = [
            "cdn.tailwindcss.com",
            "fonts.googleapis.com",
            "font-awesome",
            "fontawesome",
            "JUAN PÉREZ",
            "Alejandro Vázquez",
            "Lorem ipsum",
            "$XX",
            "[Nombre",
            "[Python]",
        ]
        for template_id in ("professional_sidebar_v1", "ai_engineer_sidebar_v1", "executive_letter_v1", "harvard_v1"):
            text = (template_dir / get_template_policy(template_id).filename).read_text(encoding="utf-8")
            for value in forbidden:
                self.assertNotIn(value, text, f"{template_id} still contains {value!r}")
            self.assertIn("size:letter", text.replace(" ", ""))
            self.assertIn("8.5in", text)
            self.assertIn("11in", text)

    def test_large_content_builds_two_letter_pages_without_splitting_roles(self):
        model = presentation("executive_letter_v1", large=True)
        pages = build_page_plan(model)
        self.assertEqual(len(pages), 2)
        self.assertEqual([page.page_number for page in pages], [1, 2])
        original_roles = [item.title for item in model.experience]
        planned_roles = [item.title for page in pages for item in page.experience]
        self.assertEqual(planned_roles, original_roles)

    def test_non_harvard_template_receives_brand_tokens(self):
        model = presentation("executive_letter_v1")
        tokens = DesignTokens(
            company="Example",
            brand_verified=True,
            brand_source_kind="verified_manual",
            brand_source_url="https://example.com/brand",
            primary="#123456",
            secondary="#334455",
            accent="#006699",
            surface="#FFFFFF",
            text="#111111",
            muted="#444444",
            heading_font_stack="Georgia, serif",
            body_font_stack="Arial, sans-serif",
        )
        html = render_html(model, tokens=tokens)
        self.assertIn("#123456", html)
        self.assertIn("Georgia, serif", html)
        self.assertIn("Candidate Name", html)

    def test_harvard_ignores_brand_tokens(self):
        model = presentation("harvard_v1")
        tokens = DesignTokens(
            company="Example",
            brand_verified=True,
            brand_source_kind="verified_manual",
            brand_source_url="https://example.com/brand",
            primary="#FF00FF",
            secondary="#00FF00",
            accent="#0000FF",
            surface="#FFFF00",
            text="#660066",
            muted="#006666",
            heading_font_stack="Arial, sans-serif",
            body_font_stack="Arial, sans-serif",
        )
        html = render_html(model, tokens=tokens)
        self.assertNotIn("#FF00FF", html)
        self.assertIn('Times New Roman', html)
        self.assertIn("Candidate Name", html)

    def test_jinja_autoescapes_candidate_text(self):
        model = presentation("executive_letter_v1")
        model.summary = line("Safe text <script>alert('x')</script>")
        html = render_html(model, tokens=tokens_from_brand(fallback_brand("Example")))
        self.assertNotIn("<script>alert", html)
        self.assertIn("&lt;script&gt;", html)


class BrandingAndDesignReviewTests(unittest.TestCase):
    def test_fallback_brand_is_explicitly_unverified_but_contrast_safe(self):
        tokens = tokens_from_brand(fallback_brand("Unknown Company"))
        validation = validate_design_tokens(tokens)
        self.assertFalse(tokens.brand_verified)
        self.assertTrue(validation.passed)
        self.assertTrue(any("brand_unverified" in reason for reason in validation.reasons))

    def test_unsafe_palette_fails_deterministic_contrast(self):
        profile = BrandProfile(
            company="Example",
            source_kind="verified_manual",
            source_url="https://example.com/brand",
            verified=True,
            primary="#FFFFFF",
            secondary="#FFFFFF",
            accent="#FFFFFF",
            surface="#FFFFFF",
            text="#EEEEEE",
            muted="#EEEEEE",
        )
        self.assertFalse(validate_design_tokens(tokens_from_brand(profile)).passed)

    def test_harvard_design_review_uses_no_model_call(self):
        client = FakeDesignClient(DesignReview(decision="REVISE", ats_safe=False, print_safe=False))
        review, _ = asyncio.run(review_design(
            client=client,
            template_id="harvard_v1",
            tokens=tokens_from_brand(fallback_brand("Example")),
            target_pages=2,
        ))
        self.assertEqual(client.calls, 0)
        self.assertEqual(review.decision, "PASS")
        self.assertTrue(review.preserve_template)

    def test_design_agent_cannot_override_failed_contrast(self):
        unsafe = DesignTokens(
            company="Example",
            brand_verified=True,
            brand_source_kind="verified_manual",
            brand_source_url="https://example.com/brand",
            primary="#FFFFFF",
            secondary="#FFFFFF",
            accent="#FFFFFF",
            surface="#FFFFFF",
            text="#EEEEEE",
            muted="#EEEEEE",
            heading_font_stack="Arial, sans-serif",
            body_font_stack="Arial, sans-serif",
        )
        client = FakeDesignClient(DesignReview(decision="PASS", ats_safe=True, print_safe=True))
        with self.assertRaises(ValueError):
            asyncio.run(review_design(
                client=client,
                template_id="executive_letter_v1",
                tokens=unsafe,
                target_pages=2,
            ))


if __name__ == "__main__":
    unittest.main()
