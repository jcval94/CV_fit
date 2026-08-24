from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cv_agent.model_policy import MAX_REVIEW_ITERATIONS, model_ids, policy_for_iteration
from cv_agent.schemas import CVDocument, CVEvidenceLine, CVExperienceItem, HeadhunterReview, ReviewScores, StrategyOutput
from cv_agent.workflow import run_agentic_cv

EVIDENCE_ID = "skills::python"


def context_fixture() -> dict:
    chunk = {
        "schema_version": 1, "chunk_id": EVIDENCE_ID, "record_id": "skills", "record_type": "skills",
        "chunk_type": "skill", "title": "Python", "heading_path": ["Skills", "Python"],
        "text": "Python\nLevel: core; repeated professional use.", "source_path": "experience/skills.md",
        "source_commit": "abc", "source_refs": [], "metric_refs": [], "constraints": [],
        "retrieval_class": "evidence", "public_safe": True, "cv_eligible": True, "confidence": "high",
        "proficiency": "core", "attributes": {"level": "core"}, "content_hash": "evidence-hash",
    }
    return {
        "vacancy": {
            "vacancy_id": "vac-test", "company": "Example", "role_title": "Senior Data Scientist",
            "application_language": "en", "language_confidence": 0.95, "language_source": "vacancy_text",
            "content_hash": "vac-hash", "provenance": [{"source_path": "Vacantes/example.json"}],
            "tech_stack": ["Python"],
        },
        "match_plan": {
            "coverage_score": 100.0,
            "requirements": [{"requirement": "Python", "coverage": "strong", "evidence_chunk_ids": [EVIDENCE_ID]}],
            "selected_evidence_chunk_ids": [EVIDENCE_ID],
        },
        "canonical_backbone_chunk_ids": [],
        "editorial_anchor_chunk_ids": [],
        "evidence_chunks": [chunk],
    }


def catalog_fixture() -> dict:
    chunk = context_fixture()["evidence_chunks"][0]
    return {EVIDENCE_ID: chunk}


def cv_fixture() -> CVDocument:
    ref = [EVIDENCE_ID]
    line = lambda text: CVEvidenceLine(text=text, evidence_refs=ref)
    return CVDocument(
        language="en",
        target_role="Senior Data Scientist",
        headline=line("Senior Data Scientist | Applied AI & Machine Learning"),
        summary=line("Senior data scientist building evidence-grounded analytical solutions for business decisions."),
        experience=[
            CVExperienceItem(
                organization="BBVA México", title="Senior Data Scientist", period="Current", evidence_refs=ref,
                bullets=[line("Built Python analytical workflows for business decisions."), line("Led evidence-grounded analytical delivery.")],
            ),
            CVExperienceItem(
                organization="BBVA México", title="Data Scientist — Associate", period="Previous stage", evidence_refs=ref,
                bullets=[line("Developed maintainable machine-learning pipelines.")],
            ),
            CVExperienceItem(
                organization="Management Solutions", title="Senior Data Scientist", period="Earlier role", evidence_refs=ref,
                bullets=[line("Partnered with stakeholders on analytical delivery.")],
            ),
        ],
        projects=[],
        skills=[line("Python — core"), line("GenAI / Generative AI — core")],
        education=[line("Master's Degree in Data Science")],
        certifications=[
            line("GenAI Aplicado: ChatGPT & Gemini — Colegio de Matemáticas Bourbaki"),
            line("Professional Scrum Master I — Scrum.org"),
            line("CS50's Introduction to Computer Science — HarvardX"),
        ],
    )


def make_review(score: int, decision: str = "REVISE") -> HeadhunterReview:
    return HeadhunterReview(
        decision=decision,
        overall_score=score,
        scores=ReviewScores(
            vacancy_alignment=score, opening_impact=score, evidence_strength=score, specificity=score,
            seniority_signal=score, ats_clarity=score, language_quality=score, conciseness=score,
        ),
        blocking_issues=[] if decision == "PASS" else [{
            "section": "summary", "problem": "Needs stronger positioning.",
            "required_change": "Improve supported positioning only."
        }],
        optional_improvements=[], rationale="Structured test review.",
    )


class FakeClient:
    def __init__(self, reviews: list[HeadhunterReview]) -> None:
        self.reviews = list(reviews)
        self.calls: list[dict] = []
        self.cv = cv_fixture()

    async def call(self, **kwargs):
        self.calls.append(kwargs)
        name = kwargs["name"]
        if name == "cv_strategist":
            return StrategyOutput(
                target_role="Senior Data Scientist", language="en", positioning="Evidence-grounded senior data scientist",
                selected_evidence_chunk_ids=[EVIDENCE_ID], selected_skills=["Python", "GenAI"],
            )
        if name in {"cv_writer", "cv_style_reviser"} or name.startswith("cv_reviser_"):
            return self.cv
        if name.startswith("senior_headhunter_"):
            return self.reviews.pop(0)
        raise AssertionError(f"unexpected agent call: {name}")


class StyleRepairClient(FakeClient):
    def __init__(self, reviews: list[HeadhunterReview]) -> None:
        super().__init__(reviews)
        self.bad_cv = cv_fixture()
        self.bad_cv.summary = CVEvidenceLine(
            text="He builds evidence-grounded analytical solutions for business decisions.",
            evidence_refs=[EVIDENCE_ID],
        )
        self.good_cv = cv_fixture()

    async def call(self, **kwargs):
        name = kwargs["name"]
        if name == "cv_writer":
            self.calls.append(kwargs)
            return self.bad_cv
        if name == "cv_style_reviser":
            self.calls.append(kwargs)
            return self.good_cv
        return await super().call(**kwargs)


class ModelPolicyTests(unittest.TestCase):
    def test_exact_five_iteration_escalation(self) -> None:
        self.assertEqual(MAX_REVIEW_ITERATIONS, 5)
        self.assertEqual([policy_for_iteration(i).tier for i in range(1, 6)], ["economy", "economy", "balanced", "balanced", "premium"])
        self.assertTrue(policy_for_iteration(5).premium)


class WorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def test_early_pass_avoids_premium_model(self) -> None:
        client = FakeClient([make_review(97, "PASS")])
        with tempfile.TemporaryDirectory() as temp, patch("cv_agent.workflow.assemble_application_context", return_value=context_fixture()), patch("cv_agent.workflow.load_evidence_catalog", return_value=catalog_fixture()):
            report = await run_agentic_cv(vacancy_id="vac-test", client=client, output_dir=Path(temp), run_id="early-pass")
            self.assertEqual(report["status"], "PASS")
            self.assertTrue(report["quality_target_reached"])
            self.assertEqual(report["iterations_executed"], 1)
            self.assertEqual(report["best_review_iteration"], 1)
            self.assertFalse(report["premium_model_used"])
            self.assertEqual(report["final_validation"]["editorial"]["status"], "PASS")
            self.assertFalse(report["style_preflight"]["attempted"])
            self.assertFalse(any(call["name"] == "cv_style_reviser" for call in client.calls))

    async def test_style_violation_is_repaired_before_headhunter(self) -> None:
        client = StyleRepairClient([make_review(97, "PASS")])
        with tempfile.TemporaryDirectory() as temp, patch("cv_agent.workflow.assemble_application_context", return_value=context_fixture()), patch("cv_agent.workflow.load_evidence_catalog", return_value=catalog_fixture()):
            output = Path(temp)
            report = await run_agentic_cv(vacancy_id="vac-test", client=client, output_dir=output, run_id="style-repair")

            names = [call["name"] for call in client.calls]
            self.assertLess(names.index("cv_style_reviser"), names.index("senior_headhunter_1"))
            self.assertTrue(report["style_preflight"]["attempted"])
            self.assertTrue(report["style_preflight"]["repaired"])
            self.assertEqual(report["style_preflight"]["model"], model_ids()["economy"])
            self.assertTrue((output / "style_preflight.json").exists())
            self.assertTrue((output / "drafts" / "cv_style_repaired.json").exists())

    async def test_fifth_failure_returns_best_cv_with_explicit_note(self) -> None:
        client = FakeClient([make_review(70), make_review(91), make_review(86), make_review(89), make_review(88)])
        with tempfile.TemporaryDirectory() as temp, patch("cv_agent.workflow.assemble_application_context", return_value=context_fixture()), patch("cv_agent.workflow.load_evidence_catalog", return_value=catalog_fixture()):
            output = Path(temp)
            report = await run_agentic_cv(vacancy_id="vac-test", client=client, output_dir=output, run_id="five-fail")
            self.assertEqual(report["status"], "COMPLETED_BELOW_TARGET")
            self.assertFalse(report["quality_target_reached"])
            self.assertEqual(report["iterations_executed"], 5)
            self.assertEqual(report["best_review_iteration"], 2)
            self.assertEqual(report["final_review"]["overall_score"], 91)
            self.assertTrue(report["premium_model_used"])
            self.assertIn("Maximum of 5", report["quality_note"])
            self.assertTrue((output / "cv_final.md").exists())
            reviewers = [call for call in client.calls if call["name"].startswith("senior_headhunter_")]
            revisers = [call for call in client.calls if call["name"].startswith("cv_reviser_")]
            self.assertEqual(len(reviewers), 5)
            self.assertEqual(len(revisers), 4)
            self.assertEqual(reviewers[-1]["model"], policy_for_iteration(5).reviewer_model)


if __name__ == "__main__":
    unittest.main()
