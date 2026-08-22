from __future__ import annotations

import unittest

from cv_agent.editorial_policy import validate_editorial_policy
from cv_agent.schemas import CVDocument, CVEvidenceLine, CVExperienceItem, CVProjectItem


REF = ["evidence"]


def line(text: str) -> CVEvidenceLine:
    return CVEvidenceLine(text=text, evidence_refs=REF)


def valid_cv() -> CVDocument:
    return CVDocument(
        language="en",
        target_role="Senior Data Scientist",
        headline=line("Senior Data Scientist | Applied AI & Machine Learning"),
        summary=line("Senior data scientist focused on production analytics and AI."),
        experience=[
            CVExperienceItem(
                organization="BBVA México", title="Senior Data Scientist", period="Apr 2024 – Present", evidence_refs=REF,
                bullets=[line("Led analytical and AI initiatives with governed delivery.")],
            ),
            CVExperienceItem(
                organization="BBVA México", title="Data Scientist — Associate", period="May 2022 – Mar 2024", evidence_refs=REF,
                bullets=[line("Built commercial analytics and recommendation workflows.")],
            ),
            CVExperienceItem(
                organization="Management Solutions", title="Senior Data Scientist", period="2017 – 2021", evidence_refs=REF,
                bullets=[line("Delivered quantitative consulting and data science work.")],
            ),
        ],
        education=[line("M.Sc. Data Science — Universidad Panamericana"), line("B.Sc. Actuarial Science — UNAM")],
        projects=[CVProjectItem(name="Project A", evidence_refs=REF, bullets=[line("Relevant implementation.")])],
        skills=[line("Python"), line("SQL"), line("Machine Learning"), line("GenAI / Generative AI")],
        certifications=[
            line("GenAI Aplicado: ChatGPT & Gemini — Colegio de Matemáticas Bourbaki"),
            line("Professional Scrum Master I — Scrum.org"),
            line("CS50's Introduction to Computer Science — HarvardX"),
        ],
    )


class EditorialPolicyTests(unittest.TestCase):
    def test_valid_senior_cv_passes(self):
        result = validate_editorial_policy(valid_cv())
        self.assertEqual(result.status, "PASS", result.issues)

    def test_management_solutions_is_mandatory_and_below_bbva(self):
        cv = valid_cv()
        cv.experience = [item for item in cv.experience if "Management Solutions" not in item.organization]
        result = validate_editorial_policy(cv)
        self.assertTrue(any(issue.code == "management_solutions_missing" for issue in result.issues))

    def test_genai_and_three_sticky_certifications_are_mandatory(self):
        cv = valid_cv()
        cv.skills = [line("Python"), line("SQL")]
        cv.certifications = [line("Professional Scrum Master I — Scrum.org")]
        result = validate_editorial_policy(cv)
        codes = {issue.code for issue in result.issues}
        self.assertIn("genai_skill_missing", codes)
        self.assertIn("mandatory_certification_missing_bourbaki", codes)
        self.assertIn("mandatory_certification_missing_harvard_cs50", codes)

    def test_projects_and_skills_are_bounded(self):
        cv = valid_cv()
        cv.projects = [CVProjectItem(name=f"P{i}", evidence_refs=REF, bullets=[line("Relevant")]) for i in range(3)]
        cv.skills = [line("GenAI")] + [line(f"Skill {i}") for i in range(15)]
        result = validate_editorial_policy(cv)
        codes = {issue.code for issue in result.issues}
        self.assertIn("too_many_projects", codes)
        self.assertIn("too_many_skills", codes)

    def test_internal_diagnostics_are_blocked(self):
        cv = valid_cv()
        cv.experience[0].period = "Employment dates not provided in supplied evidence"
        result = validate_editorial_policy(cv)
        self.assertTrue(any(issue.code == "diagnostic_language_exposed" for issue in result.issues))

    def test_identity_cannot_drift_to_unrelated_title(self):
        cv = valid_cv()
        cv.target_role = "Cloud Architect"
        cv.headline = line("Cloud Architect | Platform Engineering")
        result = validate_editorial_policy(cv)
        self.assertTrue(any(issue.code == "identity_outside_canonical_family" for issue in result.issues))


if __name__ == "__main__":
    unittest.main()
