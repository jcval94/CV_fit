from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cv_agent.model_policy import MAX_REVIEW_ITERATIONS, policy_for_iteration
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
        "evidence_chunks": [chunk],
    }


def catalog_fixture() -> dict:
    chunk = context_fixture()["evidence_chunks"][0]
    return {EVIDENCE_ID: chunk}


def cv_fixture() -> CVDocument:
    ref = [EVIDENCE_ID]
    return CVDocument(
        language="en",
        target_role="Senior Data Scientist",
        headline=CVEvidenceLine(text="Senior Data Scientist | Python & Machine Learning", evidence_refs=ref),
        summary=CVEvidenceLine(text="Data scientist building analytical solutions for business decisions.", evidence_refs=ref),
        experience=[CVExperienceItem(
            organization="Example", title="Data Scientist", period="2024-present", evidence_refs=ref,
            bullets=[
                CVEvidenceLine(text="Built Python analytical workflows for business decisions.", evidence_refs=ref),
                CVEvidenceLine(text="Developed maintainable machine-learning pipelines.", evidence_refs=ref),
                CVEvidenceLine(text="Partnered with stakeholders on analytical delivery.", evidence_refs=ref),
            ],
        )],
        skills=[CVEvidenceLine(text="Python — core", evidence_refs=ref)],
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
                target_role="Senior Data Scientist", language="en", positioning="Evidence-grounded data scientist",
                selected_evidence_chunk_ids=[EVIDENCE_ID], selected_skills=["Python"],
            )
        if name == "cv_writer" or name.startswith("cv_reviser_"):
            return self.cv
        if name.startswith("senior_headhunter_"):
            return self.reviews.pop(0)
        raise AssertionError(f"unexpected agent call: {name}")


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
            self.assertFalse(report["premium_model_used"])

    async def test_fifth_failure_returns_best_cv_with_explicit_note(self) -> None:
        client = FakeClient([make_review(70), make_review(80), make_review(86), make_review(89), make_review(90)])
        with tempfile.TemporaryDirectory() as temp, patch("cv_agent.workflow.assemble_application_context", return_value=context_fixture()), patch("cv_agent.workflow.load_evidence_catalog", return_value=catalog_fixture()):
            output = Path(temp)
            report = await run_agentic_cv(vacancy_id="vac-test", client=client, output_dir=output, run_id="five-fail")
            self.assertEqual(report["status"], "COMPLETED_BELOW_TARGET")
            self.assertFalse(report["quality_target_reached"])
            self.assertEqual(report["iterations_executed"], 5)
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
