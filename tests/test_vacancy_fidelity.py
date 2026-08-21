from __future__ import annotations

import unittest

from cv_agent.preflight import assert_vacancy_generation_ready
from vacancy_pipeline.chunking import merge_records
from vacancy_pipeline.contract import adapt_source_document
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
        assert_vacancy_generation_ready(vacancy, allow_sparse_jd=True)

    def test_adapter_marks_summary_and_stack_only_vacancy_sparse(self) -> None:
        doc = {
            "vacancies": [{
                "company": "Example",
                "role_title": "Senior Data Scientist",
                "tech_stack": ["Python", "SQL", "Machine Learning"],
                "fit_evaluation": "Strong fit based on the candidate profile.",
            }]
        }
        record = adapt_source_document(doc, "GPTW/example.json", "abc")[0]
        self.assertEqual(record.schema_version, 2)
        self.assertEqual(record.jd_fidelity, "sparse")
        self.assertFalse(record.jd_generation_eligible)
        self.assertEqual(record.jd_fidelity_score, 0.0)

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

    def test_cross_source_merge_recomputes_fidelity_from_combined_jd(self) -> None:
        common = {
            "company": "Example",
            "role_title": "Senior Data Scientist",
            "location": {"city": "Mexico City", "work_model": "Hybrid"},
            "application_language": "en",
        }
        first = {
            "vacancies": [{
                **common,
                "description": (
                    "This senior role owns analytical delivery from problem framing through model deployment and monitoring, "
                    "working closely with product, engineering and business stakeholders to build reliable machine-learning "
                    "solutions, document decisions, evaluate outcomes and improve production systems over time."
                ),
                "requirements": [
                    "Strong Python and SQL for production analytical workflows.",
                    "Experience deploying machine-learning systems to production environments.",
                ],
            }]
        }
        second = {
            "vacancies": [{
                **common,
                "responsibilities": [
                    f"Own substantive production responsibility number {index} across the ML lifecycle."
                    for index in range(1, 9)
                ],
            }]
        }
        a = adapt_source_document(first, "GPTW/a.json", "a")[0]
        b = adapt_source_document(second, "GPTW/b.json", "b")[0]
        # The first fragment is intentionally sparse by itself: fewer than
        # three substantive list items and a description below the partial
        # threshold. The second is partial. Together they preserve ten pieces
        # of substantive employer detail and must become full.
        self.assertEqual(a.jd_fidelity, "sparse")
        self.assertEqual(b.jd_fidelity, "partial")
        merged = merge_records([a, b])
        self.assertEqual(merged.jd_fidelity, "full")
        self.assertTrue(merged.jd_generation_eligible)
        self.assertEqual(len(merged.requirements) + len(merged.responsibilities), 10)

    def test_source_fit_and_tech_stack_do_not_count_as_jd_fidelity(self) -> None:
        assessment = assess_jd_fidelity(description=None, requirements=[], responsibilities=[])
        self.assertEqual(assessment.classification, "sparse")
        self.assertIn("source-fit commentary", assessment.reasons[-1])


if __name__ == "__main__":
    unittest.main()
