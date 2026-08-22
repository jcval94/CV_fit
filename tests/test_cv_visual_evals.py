from __future__ import annotations

import asyncio
import unittest

from cv_presentation.physical_layout import PhysicalLayoutReport
from cv_presentation.presentation_reviewer import PresentationReview, review_presentation
from cv_presentation.visual_evals import VisualThresholds, evaluate_visual_balance


def physical(
    *,
    pages: int = 2,
    utilization: list[float] | None = None,
    ratios: dict[str, float] | None = None,
    counts: dict[str, int] | None = None,
    status: str = "PASS",
) -> PhysicalLayoutReport:
    utilization = utilization or ([0.82, 0.71] if pages == 2 else [0.76])
    ratios = ratios or {
        "experience": 0.56,
        "education": 0.10,
        "projects": 0.14,
        "skills": 0.11,
        "certifications": 0.09,
    }
    counts = counts or {
        "experience": 3,
        "education": 2,
        "projects": 1,
        "skills": 12,
        "certifications": 3,
    }
    return PhysicalLayoutReport(
        status=status,
        html_file="cv.html",
        pdf_file="cv.pdf",
        expected_pages=pages,
        dom_pages=pages,
        pdf_pages=pages,
        pdf_page_sizes_points=[(612.0, 792.0)] * pages,
        pages=[],
        reasons=[] if status == "PASS" else ["mechanical failure"],
        page_utilization=utilization,
        section_area_ratios=ratios,
        section_item_counts=counts,
        empty_rendered_sections=[],
    )


class FakeClient:
    def __init__(self, output: PresentationReview) -> None:
        self.output = output
        self.calls = 0
        self.last_payload = None

    async def call(self, **kwargs):
        self.calls += 1
        self.last_payload = kwargs["payload"]
        return self.output


class VisualEvalTests(unittest.TestCase):
    def test_balanced_senior_cv_passes(self):
        report = evaluate_visual_balance(physical(), template_id="technical_modern_v1")
        self.assertEqual(report.status, "PASS", report.reasons)
        self.assertEqual(report.section_item_counts["skills"], 12)

    def test_underfilled_second_page_fails(self):
        report = evaluate_visual_balance(
            physical(utilization=[0.88, 0.21]),
            template_id="technical_modern_v1",
        )
        self.assertEqual(report.status, "FAIL")
        self.assertTrue(any(reason.startswith("page_2_underutilized") for reason in report.reasons))

    def test_skills_cannot_outweigh_experience(self):
        report = evaluate_visual_balance(
            physical(ratios={
                "experience": 0.24,
                "education": 0.08,
                "projects": 0.16,
                "skills": 0.38,
                "certifications": 0.14,
            }),
            template_id="technical_modern_v1",
        )
        self.assertEqual(report.status, "FAIL")
        self.assertTrue(any("skills_not_subordinate_to_experience" in reason for reason in report.reasons))
        self.assertTrue(any("skills_area_too_large" in reason for reason in report.reasons))

    def test_rendered_caps_are_enforced(self):
        report = evaluate_visual_balance(
            physical(counts={
                "experience": 1,
                "education": 0,
                "projects": 3,
                "skills": 18,
                "certifications": 2,
            }),
            template_id="technical_modern_v1",
        )
        codes = " ".join(report.reasons)
        self.assertIn("rendered_experience_items_too_few", codes)
        self.assertIn("rendered_education_missing", codes)
        self.assertIn("rendered_project_count_exceeded", codes)
        self.assertIn("rendered_skill_count_exceeded", codes)
        self.assertIn("rendered_mandatory_certifications_missing", codes)

    def test_thresholds_are_explicit_and_versionable(self):
        thresholds = VisualThresholds(two_page_page2_min_utilization=0.50)
        report = evaluate_visual_balance(
            physical(utilization=[0.80, 0.48]),
            template_id="technical_modern_v1",
            thresholds=thresholds,
        )
        self.assertEqual(report.status, "FAIL")
        self.assertEqual(report.thresholds.two_page_page2_min_utilization, 0.50)


class PresentationReviewerTests(unittest.IsolatedAsyncioTestCase):
    async def test_deterministic_failure_never_calls_model(self):
        bad_visual = evaluate_visual_balance(
            physical(utilization=[0.90, 0.10]),
            template_id="technical_modern_v1",
        )
        client = FakeClient(PresentationReview(
            decision="PASS",
            senior_hierarchy="PASS",
            page_balance="PASS",
            section_balance="PASS",
        ))
        result = await review_presentation(
            client=client,
            template_id="technical_modern_v1",
            role="primary",
            visual=bad_visual,
            physical=physical(utilization=[0.90, 0.10]),
        )
        self.assertEqual(client.calls, 0)
        self.assertEqual(result.decision, "REVIEW_REQUIRED")

    async def test_passing_metrics_are_sent_to_reviewer(self):
        good_physical = physical()
        good_visual = evaluate_visual_balance(good_physical, template_id="technical_modern_v1")
        client = FakeClient(PresentationReview(
            decision="PASS",
            senior_hierarchy="PASS",
            page_balance="PASS",
            section_balance="PASS",
            reasons=["Metrics support senior hierarchy."],
        ))
        result = await review_presentation(
            client=client,
            template_id="technical_modern_v1",
            role="primary",
            visual=good_visual,
            physical=good_physical,
        )
        self.assertEqual(result.decision, "PASS")
        self.assertEqual(client.calls, 1)
        self.assertEqual(client.last_payload["deterministic_visual_status"], "PASS")
        self.assertEqual(client.last_payload["section_item_counts"]["projects"], 1)

    async def test_model_pass_with_component_concern_fails_closed(self):
        good_physical = physical()
        good_visual = evaluate_visual_balance(good_physical, template_id="technical_modern_v1")
        client = FakeClient(PresentationReview(
            decision="PASS",
            senior_hierarchy="PASS",
            page_balance="CONCERN",
            section_balance="PASS",
            reasons=["Second page feels borderline."],
        ))
        result = await review_presentation(
            client=client,
            template_id="technical_modern_v1",
            role="primary",
            visual=good_visual,
            physical=good_physical,
        )
        self.assertEqual(client.calls, 1)
        self.assertEqual(result.decision, "REVIEW_REQUIRED")
        self.assertTrue(any("fail-closed" in reason for reason in result.reasons))


if __name__ == "__main__":
    unittest.main()
