from __future__ import annotations

import unittest

from cv_presentation.fit import fit_presentation_model
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


def line(text: str, ref: str = "e") -> PresentationLine:
    return PresentationLine(text=text, evidence_refs=[ref])


def model() -> CVPresentationModel:
    return CVPresentationModel(
        source_cv_hash="source",
        config_hash="config",
        candidate=CandidateIdentity(name="Candidate"),
        language="en",
        target_role="Senior Data Scientist",
        headline=line("Senior Data Scientist | Applied AI & ML"),
        summary=line("Senior data scientist with evidence-grounded analytical and AI delivery."),
        experience=[
            PresentationExperienceItem(
                organization="BBVA México", title="Senior Data Scientist", period="2024 – Present", evidence_refs=["bbva"],
                bullets=[line("High-priority experience result.", "bbva"), line("Secondary experience result.", "bbva")],
            ),
            PresentationExperienceItem(
                organization="Management Solutions", title="Senior Data Scientist", period="2017 – 2021", evidence_refs=["ms"],
                bullets=[line("Earlier quantitative consulting result.", "ms")],
            ),
        ],
        education=[line("M.Sc. Data Science"), line("B.Sc. Actuarial Science")],
        projects=[
            PresentationProjectItem(name="Project 1", evidence_refs=["p1"], bullets=[line("Relevant project.", "p1")]),
            PresentationProjectItem(name="Project 2", evidence_refs=["p2"], bullets=[line("Second relevant project.", "p2")]),
        ],
        skills=[line("Python"), line("SQL"), line("Machine Learning"), line("GenAI / Generative AI"), line("AWS"), line("GCP"), line("MLOps"), line("Statistics")],
        certifications=[
            line("Optional cloud credential"),
            line("GenAI Aplicado: ChatGPT & Gemini — Colegio de Matemáticas Bourbaki"),
            line("Professional Scrum Master I — Scrum.org"),
            line("CS50's Introduction to Computer Science — HarvardX"),
        ],
        document=DocumentSpec(page_size="letter", target_pages=1, template_id="ats_classic_v1"),
        layout=LayoutSpec(),
        density=DensitySpec(
            max_projects=2,
            max_skills=15,
            min_skills=3,
            max_certifications=5,
            estimated_chars_per_line=60,
            estimated_lines_per_page=35,
        ),
    )


class EditorialFittingTests(unittest.TestCase):
    def test_default_section_order_matches_user_priority(self):
        self.assertEqual(
            LayoutSpec().section_order,
            ["summary", "experience", "education", "projects", "skills", "certifications"],
        )

    def test_fitter_never_drops_genai_or_sticky_certifications(self):
        fitted, _ = fit_presentation_model(model())
        skills = " ".join(item.text for item in fitted.skills).casefold()
        certs = " ".join(item.text for item in fitted.certifications).casefold()
        self.assertTrue("genai" in skills or "generative ai" in skills)
        self.assertIn("bourbaki", certs)
        self.assertIn("professional scrum master", certs)
        self.assertIn("cs50", certs)
        self.assertTrue(fitted.education)
        self.assertTrue(any("Management Solutions" in item.organization for item in fitted.experience))


if __name__ == "__main__":
    unittest.main()
