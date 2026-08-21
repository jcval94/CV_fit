from __future__ import annotations

import unittest

from cv_matching.match import extract_requirements, match_vacancy_to_evidence


class MatchingTests(unittest.TestCase):
    def test_extract_requirements_prefers_structured_vacancy_fields(self) -> None:
        vacancy = {
            "role_title": "Senior ML Engineer",
            "tech_stack": ["Python", "Kubernetes"],
            "requirements": ["Own production ML systems"],
            "responsibilities": ["Partner with product"],
        }
        values = extract_requirements(vacancy)
        self.assertEqual(values[0], ("Python", "technology_or_capability", "critical"))
        self.assertIn(("Own production ML systems", "requirement", "critical"), values)

    def test_familiarity_skill_never_becomes_strong(self) -> None:
        vacancy = {"vacancy_id": "v1", "content_hash": "h", "role_title": "Platform ML", "tech_stack": ["Kubernetes"], "requirements": [], "responsibilities": []}
        index = {
            "chunks": {
                "skills::kubernetes": {
                    "record_id": "skills", "chunk_type": "skill", "source_path": "experience/skills.md",
                    "content_hash": "x", "proficiency": "familiarity", "constraints": ["do not overclaim"],
                    "metric_refs": [], "terms": {"kubernetes": 1}, "text": "Kubernetes familiarity"
                }
            },
            "postings": {"kubernetes": ["skills::kubernetes"]},
            "record_chunks": {"skills": ["skills::kubernetes"]},
        }
        result = match_vacancy_to_evidence(vacancy, index)
        self.assertEqual(result["requirements"][0]["coverage"], "weak")
        self.assertNotEqual(result["requirements"][0]["coverage"], "strong")

    def test_missing_evidence_is_explicitly_unsupported(self) -> None:
        vacancy = {"vacancy_id": "v1", "content_hash": "h", "role_title": "Quant", "tech_stack": ["COBOL"], "requirements": [], "responsibilities": []}
        index = {"chunks": {}, "postings": {}, "record_chunks": {}}
        result = match_vacancy_to_evidence(vacancy, index)
        self.assertEqual(result["requirements"][0]["coverage"], "unsupported")
        self.assertEqual(result["coverage_score"], 0.0)


if __name__ == "__main__":
    unittest.main()
