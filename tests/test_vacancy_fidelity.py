from __future__ import annotations

import unittest

from cv_agent.context import assert_vacancy_generation_ready
from vacancy_pipeline.fidelity import assess_jd_fidelity


class VacancyFidelityTests(unittest.TestCase):
    def test_sparse_summary_only_source_is_blocked(self) -> None:
        assessment = assess_jd_fidelity(description=None, requirements=[], responsibilities=[])
        self.assertEqual(assessment.classification, "sparse")
        self.assertFalse(assessment.generation_eligible)
        self.assertEqual(assessment.score, 0.0)

        vacancy = {
            "vacancy_id": "vac-sparse",
            "application_language": "en",
            "jd_fidelity": assessment.classification,
            "jd_fidelity_score": assessment.score,
            "jd_fidelity_reasons": assessment.reasons,
            "jd_generation_eligible": assessment.generation_eligible,
        }
        with self.assertRaisesRegex(ValueError, "not CV-generation eligible"):
            assert_vacancy_generation_ready(vacancy)

    def test_partial_jd_is_generation_eligible(self) -> None:
        assessment = assess_jd_fidelity(
            description=(
                "We are looking for a senior data scientist to own analytical workstreams, build production-ready "
                "machine-learning solutions, partner with product and engineering, define experiments, monitor "
                "model performance, and communicate recommendations to senior stakeholders across the business."
            ),
            requirements=[
                "Professional experience building and deploying machine-learning models in production.",
                "Strong Python and SQL skills for analytical and production workflows.",
                "Ability to communicate technical trade-offs to senior business stakeholders.",
            ],
            responsibilities=[],
        )
        self.assertEqual(assessment.classification, "partial")
        self.assertTrue(assessment.generation_eligible)

    def test_full_jd_requires_substantive_employer_detail(self) -> None:
        description = " ".join([
            "This role owns end-to-end data science initiatives across discovery, experimentation, modeling, deployment, monitoring, stakeholder alignment, documentation and measurable business outcomes."
        ] * 8)
        assessment = assess_jd_fidelity(
            description=description,
            requirements=[
                "Five or more years of applied data science experience in production environments.",
                "Advanced Python and SQL with reproducible software engineering practices.",
                "Experience with model deployment, monitoring and ML lifecycle ownership.",
            ],
            responsibilities=[
                "Lead analytical problem framing and translate business questions into measurable technical work.",
                "Build, validate and deploy machine-learning systems with engineering partners.",
                "Present recommendations and trade-offs to senior stakeholders and product leaders.",
            ],
        )
        self.assertEqual(assessment.classification, "full")
        self.assertTrue(assessment.generation_eligible)
        self.assertGreaterEqual(assessment.score, 70.0)

    def test_source_fit_and_tech_stack_do_not_count_as_jd_fidelity(self) -> None:
        assessment = assess_jd_fidelity(description=None, requirements=[], responsibilities=[])
        self.assertEqual(assessment.classification, "sparse")
        self.assertIn("source-fit commentary", assessment.reasons[-1])


if __name__ == "__main__":
    unittest.main()
