from __future__ import annotations

import unittest
from pathlib import Path

from cv_agent.backbone import select_canonical_backbone
from cv_agent.context import load_evidence_catalog


class CanonicalBackboneTests(unittest.TestCase):
    def test_versioned_rag_state_contains_required_structural_backbone(self) -> None:
        catalog = load_evidence_catalog(Path("rag_state"))
        selected = select_canonical_backbone(catalog)
        self.assertTrue(selected, "expected canonical CV backbone chunks")

        ids = {item["chunk_id"] for item in selected}
        record_ids = {item["record_id"] for item in selected}
        titles = {item["title"] for item in selected}

        self.assertTrue(any(value.startswith("role-bbva::") for value in ids))
        self.assertTrue(any(value.startswith("role-management-solutions::") for value in ids))
        self.assertIn("role-bbva", record_ids)
        self.assertIn("role-management-solutions", record_ids)
        self.assertIn("professional-profile", record_ids)
        self.assertIn("education", record_ids)
        self.assertIn("Master's Degree in Data Science", titles)
        self.assertIn("Bachelor's Degree in Actuarial Science", titles)
        self.assertTrue(all(item["cv_eligible"] and item["public_safe"] for item in selected))

    def test_backbone_excludes_projects_skills_and_private_chunks(self) -> None:
        def chunk(chunk_id: str, record_id: str, title: str, *, public_safe: bool = True):
            return {
                "chunk_id": chunk_id,
                "record_id": record_id,
                "title": title,
                "heading_path": ["Root", title],
                "cv_eligible": True,
                "public_safe": public_safe,
            }

        catalog = {
            "profile": chunk("profile", "professional-profile", "Professional positioning"),
            "education": chunk("education", "education", "Master's Degree in Data Science"),
            "project": chunk("project", "project-example", "Project"),
            "skill": chunk("skill", "skills", "Python"),
            "private": chunk("private", "professional-profile", "Canonical summary", public_safe=False),
        }
        ids = {item["chunk_id"] for item in select_canonical_backbone(catalog)}
        self.assertEqual(ids, {"profile", "education"})


if __name__ == "__main__":
    unittest.main()
