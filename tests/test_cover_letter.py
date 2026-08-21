from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from cv_agent.cover_letter import collect_cv_evidence_refs, generate_cover_letter, render_cover_letter_markdown, validate_cover_letter
from cv_agent.schemas import (
    CVDocument,
    CVEvidenceLine,
    CVExperienceItem,
    CoverLetterDocument,
    CoverLetterParagraph,
)


class FakeClient:
    def __init__(self, output: CoverLetterDocument) -> None:
        self.output = output
        self.calls = []

    async def call(self, **kwargs):
        self.calls.append(kwargs)
        return self.output


def cv_fixture() -> CVDocument:
    return CVDocument(
        language="en",
        target_role="Senior Data Scientist",
        headline=CVEvidenceLine(text="Senior Data Scientist", evidence_refs=["profile-1"]),
        summary=CVEvidenceLine(text="Production machine learning and analytics.", evidence_refs=["profile-1"]),
        experience=[
            CVExperienceItem(
                organization="Example Bank",
                title="Data Scientist",
                period="2021 – Present",
                evidence_refs=["role-1"],
                bullets=[
                    CVEvidenceLine(text="Built production analytics workflows.", evidence_refs=["project-1"]),
                    CVEvidenceLine(text="Improved a governed review process.", evidence_refs=["metric-1"]),
                ],
            )
        ],
        projects=[],
        skills=[CVEvidenceLine(text="Python, SQL", evidence_refs=["skills-1"])],
        education=[],
        certifications=[],
    )


def vacancy_fixture() -> dict:
    return {
        "application_language": "en",
        "company": "Example Company",
        "role_title": "Senior Data Scientist",
        "location": "Remote",
        "requirements": ["Production machine learning"],
        "responsibilities": ["Build reliable models"],
    }


class CoverLetterTests(unittest.TestCase):
    def test_collects_only_final_cv_evidence_refs(self):
        refs = collect_cv_evidence_refs(cv_fixture())
        self.assertEqual(refs, {"profile-1", "role-1", "project-1", "metric-1", "skills-1"})

    def test_generates_brief_grounded_letter_and_writes_artifacts(self):
        output = CoverLetterDocument(
            language="en",
            company="Example Company",
            role="Senior Data Scientist",
            salutation="Dear Hiring Team,",
            paragraphs=[
                CoverLetterParagraph(
                    text="I am applying for the Senior Data Scientist role, bringing production analytics experience aligned with the team's machine-learning needs.",
                    evidence_refs=["profile-1", "project-1"],
                ),
                CoverLetterParagraph(
                    text="My work includes governed analytical workflows and measurable process improvement, with an emphasis on reliable implementation rather than unsupported technology claims.",
                    evidence_refs=["metric-1", "role-1"],
                ),
            ],
            closing="Sincerely,",
        )
        client = FakeClient(output)
        with tempfile.TemporaryDirectory() as tmp:
            result = asyncio.run(generate_cover_letter(
                client=client,
                vacancy=vacancy_fixture(),
                final_cv=cv_fixture(),
                output_dir=Path(tmp),
            ))
            self.assertEqual(result.company, "Example Company")
            self.assertEqual(len(client.calls), 1)
            self.assertEqual(client.calls[0]["name"], "cover_letter_writer")
            self.assertTrue((Path(tmp) / "cover_letter_final.json").exists())
            self.assertTrue((Path(tmp) / "cover_letter_final.md").exists())
            self.assertIn("Dear Hiring Team", render_cover_letter_markdown(result))

    def test_rejects_unknown_evidence_ref(self):
        letter = CoverLetterDocument(
            language="en",
            company="Example Company",
            role="Senior Data Scientist",
            salutation="Dear Hiring Team,",
            paragraphs=[
                CoverLetterParagraph(text="Supported paragraph.", evidence_refs=["profile-1"]),
                CoverLetterParagraph(text="Unsupported paragraph.", evidence_refs=["not-approved"]),
            ],
            closing="Sincerely,",
        )
        with self.assertRaises(ValueError):
            validate_cover_letter(letter, vacancy=vacancy_fixture(), allowed_evidence_refs=collect_cv_evidence_refs(cv_fixture()))

    def test_rejects_overlong_letter(self):
        long_text = "word " * 110
        letter = CoverLetterDocument(
            language="en",
            company="Example Company",
            role="Senior Data Scientist",
            salutation="Dear Hiring Team,",
            paragraphs=[
                CoverLetterParagraph(text=long_text, evidence_refs=["profile-1"]),
                CoverLetterParagraph(text=long_text, evidence_refs=["role-1"]),
            ],
            closing="Sincerely,",
        )
        with self.assertRaises(ValueError):
            validate_cover_letter(letter, vacancy=vacancy_fixture(), allowed_evidence_refs=collect_cv_evidence_refs(cv_fixture()))


if __name__ == "__main__":
    unittest.main()
