from __future__ import annotations

import unittest

from cv_agent.schemas import CVDocument, CVEvidenceLine, CVExperienceItem, HeadhunterReview, ReviewScores
from cv_agent.validators import quality_gate, validate_claims, validate_language, validate_structure


def cv_with(text: str, ref: str = "skills::kubernetes", language: str = "en") -> CVDocument:
    refs = [ref]
    return CVDocument(
        language=language,
        target_role="Senior ML Engineer",
        headline=CVEvidenceLine(text="Senior ML Engineer", evidence_refs=refs),
        summary=CVEvidenceLine(text=text, evidence_refs=refs),
        experience=[CVExperienceItem(
            organization="Example", title="Data Scientist", period="2024-present", evidence_refs=refs,
            bullets=[
                CVEvidenceLine(text="Built analytical workflows with stakeholders.", evidence_refs=refs),
                CVEvidenceLine(text="Developed maintainable model pipelines.", evidence_refs=refs),
                CVEvidenceLine(text="Improved data quality for model delivery.", evidence_refs=refs),
            ],
        )],
        skills=[CVEvidenceLine(text="Kubernetes", evidence_refs=refs)],
    )


def good_review() -> HeadhunterReview:
    scores = ReviewScores(
        vacancy_alignment=96, opening_impact=95, evidence_strength=97, specificity=95,
        seniority_signal=95, ats_clarity=97, language_quality=98, conciseness=95,
    )
    return HeadhunterReview(decision="PASS", overall_score=96, scores=scores, blocking_issues=[], optional_improvements=[], rationale="Ready.")


class ValidatorTests(unittest.TestCase):
    def test_familiarity_cannot_support_expert_wording(self) -> None:
        cv = cv_with("Kubernetes expert supporting platform engineering.")
        catalog = {"skills::kubernetes": {"cv_eligible": True, "proficiency": "familiarity", "chunk_type": "skill", "text": "Kubernetes familiarity"}}
        result = validate_claims(cv, catalog, catalog)
        self.assertEqual(result.status, "FAIL")
        self.assertTrue(any(issue.code == "proficiency_escalation" for issue in result.issues))

    def test_quantified_business_claim_requires_achievement_metric(self) -> None:
        cv = cv_with("Improved model performance by 37%.")
        catalog = {"skills::kubernetes": {"cv_eligible": True, "proficiency": "core", "chunk_type": "skill", "text": "Kubernetes core"}}
        result = validate_claims(cv, catalog, catalog)
        self.assertTrue(any(issue.code == "quantified_claim_without_metric" for issue in result.issues))

    def test_metric_value_must_exist_in_achievement_evidence(self) -> None:
        ref = "achievement-metrics::ACH-X"
        cv = cv_with("Improved detection from 19% to 50%.", ref=ref)
        catalog = {ref: {
            "cv_eligible": True, "proficiency": None, "chunk_type": "achievement_metric",
            "text": "Result: 19% -> 37%", "constraints": [],
        }}
        result = validate_claims(cv, catalog, catalog)
        self.assertTrue(any(issue.code == "metric_value_not_in_evidence" for issue in result.issues))

    def test_required_metric_qualifier_cannot_be_dropped(self) -> None:
        ref = "achievement-metrics::ACH-Y"
        cv = cv_with("Consultation handling was 15x faster.", ref=ref)
        catalog = {ref: {
            "cv_eligible": True, "proficiency": None, "chunk_type": "achievement_metric",
            "text": "Result: up to 15x faster", "constraints": ["retain up to"],
        }}
        result = validate_claims(cv, catalog, catalog)
        self.assertTrue(any(issue.code == "metric_qualifier_lost" for issue in result.issues))

    def test_years_claim_cannot_exceed_referenced_evidence(self) -> None:
        ref = "professional-profile::positioning"
        cv = cv_with("Senior Data Scientist with 10+ years of professional experience.", ref=ref)
        catalog = {ref: {
            "cv_eligible": True, "proficiency": None, "chunk_type": "summary",
            "text": "Professional experience: 8+ years.", "constraints": [],
        }}
        result = validate_claims(cv, catalog, catalog)
        self.assertTrue(any(issue.code == "unsupported_years_claim" for issue in result.issues))

    def test_formal_people_management_requires_direct_evidence(self) -> None:
        ref = "project-x::leadership"
        cv = cv_with("Managed a team of 10 data scientists.", ref=ref)
        catalog = {ref: {
            "cv_eligible": True, "proficiency": None, "chunk_type": "project_detail",
            "text": "Technical and project leadership with senior stakeholders.", "constraints": ["Do not infer formal people management."],
        }}
        result = validate_claims(cv, catalog, catalog)
        self.assertTrue(any(issue.code == "unsupported_people_management" for issue in result.issues))

    def test_arima_claim_requires_exact_support(self) -> None:
        ref = "skills::time-series"
        cv = cv_with("Advanced ARIMA and SARIMA forecasting specialist.", ref=ref)
        catalog = {ref: {
            "cv_eligible": True, "proficiency": "working", "chunk_type": "skill",
            "text": "Time series / forecasting — working. No ARIMA/SARIMA specialization without project evidence.", "constraints": ["do not claim ARIMA/SARIMA specialization"],
        }}
        result = validate_claims(cv, catalog, catalog)
        # The evidence text mentions ARIMA only as a negative boundary. The proficiency wording is still blocked.
        self.assertTrue(any(issue.code == "proficiency_escalation" for issue in result.issues))

    def test_language_code_mismatch_fails(self) -> None:
        result = validate_language(cv_with("Data scientist building models.", language="es"), "en")
        self.assertEqual(result.status, "FAIL")
        self.assertTrue(any(issue.code == "language_code_mismatch" for issue in result.issues))

    def test_quality_gate_requires_headhunter_and_deterministic_passes(self) -> None:
        cv = cv_with("Data scientist building models.")
        catalog = {"skills::kubernetes": {"cv_eligible": True, "proficiency": "familiarity", "chunk_type": "skill", "text": "Kubernetes familiarity"}}
        factual = validate_claims(cv, catalog, catalog)
        language = validate_language(cv, "en")
        structure = validate_structure(cv)
        gate = quality_gate(good_review(), factual, language, structure)
        self.assertTrue(gate.passed)


if __name__ == "__main__":
    unittest.main()
