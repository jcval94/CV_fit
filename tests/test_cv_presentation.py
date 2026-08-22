from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cv_agent.schemas import CVDocument, CVEvidenceLine, CVExperienceItem, CVProjectItem
from cv_presentation.build import build_presentation_model
from cv_presentation.fit import fit_presentation_model
from cv_presentation.identity import resolve_candidate_identity
from cv_presentation.schemas import DensitySpec, DocumentSpec, LayoutSpec, PresentationConfig


def line(text: str, ref: str) -> CVEvidenceLine:
    return CVEvidenceLine(text=text, evidence_refs=[ref])


def sample_cv(*, long_summary: bool = False) -> CVDocument:
    summary = " ".join(["evidence"] * 90) if long_summary else "Senior data and AI professional with production-focused delivery."
    return CVDocument(
        language="en",
        target_role="Senior AI Engineer",
        headline=line("Senior AI Engineer | ML, RAG and production analytics", "p-head"),
        summary=line(summary, "p-summary"),
        experience=[
            CVExperienceItem(
                organization="Example Bank",
                title="Senior Data Scientist",
                period="2024–Present",
                evidence_refs=["role-bank"],
                bullets=[line(f"Bank impact bullet {i} with grounded evidence and production detail.", f"b{i}") for i in range(6)],
            ),
            CVExperienceItem(
                organization="Example Consulting",
                title="Data Scientist",
                period="2018–2021",
                evidence_refs=["role-consulting"],
                bullets=[line(f"Consulting bullet {i} with analytical delivery detail.", f"c{i}") for i in range(4)],
            ),
        ],
        projects=[
            CVProjectItem(
                name=f"Project {i}",
                evidence_refs=[f"project-{i}"],
                bullets=[line(f"Project {i} bullet {j} with implementation evidence.", f"p{i}-{j}") for j in range(4)],
            )
            for i in range(3)
        ],
        skills=[line(f"Skill {i}", f"skill-{i}") for i in range(12)],
        education=[line(f"Education {i}", f"edu-{i}") for i in range(3)],
        certifications=[line(f"Certification {i}", f"cert-{i}") for i in range(6)],
    )


class PresentationTests(unittest.TestCase):
    def test_public_identity_file_rejects_private_contact(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "identity.yaml"
            path.write_text("name: Test Candidate\nemail: secret@example.com\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "private contact fields"):
                resolve_candidate_identity(public_identity_path=path)

    def test_private_contact_is_opt_in_and_blocked_for_public_artifacts(self):
        env = {"CV_IDENTITY_NAME": "Test Candidate", "CV_IDENTITY_EMAIL": "secret@example.com"}
        public = resolve_candidate_identity(env=env)
        self.assertIsNone(public.identity.email)
        with self.assertRaisesRegex(ValueError, "public artifact"):
            resolve_candidate_identity(env=env, include_private_contact=True, artifact_visibility="public")
        private = resolve_candidate_identity(env=env, include_private_contact=True, artifact_visibility="private")
        self.assertEqual(private.identity.email, "secret@example.com")
        self.assertEqual(private.private_fields_included, ["email"])

    def test_build_preserves_evidence_refs(self):
        cv = sample_cv()
        identity = resolve_candidate_identity(env={"CV_IDENTITY_NAME": "Test Candidate"}).identity
        model = build_presentation_model(cv, candidate=identity, config=PresentationConfig())
        self.assertEqual(model.headline.evidence_refs, ["p-head"])
        self.assertEqual(model.experience[0].bullets[0].evidence_refs, ["b0"])
        second = build_presentation_model(cv, candidate=identity, config=PresentationConfig())
        self.assertEqual(model.source_cv_hash, second.source_cv_hash)

    def test_initial_caps_keep_head_items_without_rewriting(self):
        cv = sample_cv()
        identity = resolve_candidate_identity(env={"CV_IDENTITY_NAME": "Test Candidate"}).identity
        config = PresentationConfig(document=DocumentSpec(target_pages=3))
        model = build_presentation_model(cv, candidate=identity, config=config)
        fitted, report = fit_presentation_model(model)
        self.assertEqual(
            [bullet.text for bullet in fitted.experience[0].bullets],
            [bullet.text for bullet in model.experience[0].bullets[:4]],
        )
        self.assertEqual([project.name for project in fitted.projects], ["Project 0", "Project 1"])
        self.assertEqual(len(fitted.certifications), 5)
        self.assertGreater(len(report.omissions), 0)

    def test_budget_prunes_optional_content_before_core_experience(self):
        cv = sample_cv()
        identity = resolve_candidate_identity(env={"CV_IDENTITY_NAME": "Test Candidate"}).identity
        config = PresentationConfig(
            document=DocumentSpec(target_pages=1),
            layout=LayoutSpec(
                section_modes={
                    "summary": "always",
                    "experience": "always",
                    "projects": "auto",
                    "skills": "auto",
                    "education": "always",
                    "certifications": "auto",
                }
            ),
            density=DensitySpec(estimated_lines_per_page=35, max_summary_words=100),
        )
        model = build_presentation_model(cv, candidate=identity, config=config)
        fitted, report = fit_presentation_model(model)
        omitted_sections = [item.section for item in report.omissions]
        self.assertIn("certifications", omitted_sections)
        self.assertIn("projects", omitted_sections)
        self.assertTrue(all(len(role.bullets) >= 1 for role in fitted.experience))
        source_texts = {bullet.text for role in model.experience for bullet in role.bullets}
        self.assertTrue(all(bullet.text in source_texts for role in fitted.experience for bullet in role.bullets))

    def test_long_summary_requires_upstream_revision_not_truncation(self):
        cv = sample_cv(long_summary=True)
        identity = resolve_candidate_identity(env={"CV_IDENTITY_NAME": "Test Candidate"}).identity
        config = PresentationConfig(
            document=DocumentSpec(target_pages=3),
            density=DensitySpec(max_summary_words=80),
        )
        model = build_presentation_model(cv, candidate=identity, config=config)
        fitted, report = fit_presentation_model(model)
        self.assertEqual(fitted.summary.text, cv.summary.text)
        self.assertEqual(report.status, "NEEDS_REVISION")
        self.assertTrue(any(reason.startswith("summary_word_limit_exceeded") for reason in report.reasons))

    def test_section_order_contract_rejects_missing_section(self):
        with self.assertRaises(ValueError):
            LayoutSpec(section_order=["summary", "experience", "skills", "education", "certifications"])


if __name__ == "__main__":
    unittest.main()
