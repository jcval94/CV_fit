from __future__ import annotations

import unittest
from pathlib import Path

from cv_agent.backbone import select_canonical_backbone
from cv_agent.context import load_evidence_catalog
from cv_agent.schemas import StrategyOutput
from cv_agent.workflow import _attach_required_evidence, _budget_evidence


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

    def test_backbone_is_budgeted_before_requirement_evidence_and_forced_into_strategy(self) -> None:
        def evidence(chunk_id: str, record_id: str):
            return {
                "chunk_id": chunk_id,
                "record_id": record_id,
                "chunk_type": "section",
                "title": chunk_id,
                "text": f"Evidence for {chunk_id}",
                "proficiency": None,
                "metric_refs": [],
                "constraints": [],
                "source_path": f"experience/{record_id}.md",
                "attributes": {},
                "cv_eligible": True,
            }

        backbone_id = "role-bbva::canonical"
        requirement_id = "project-role-specific"
        chunks = [evidence(requirement_id, "project-example"), evidence(backbone_id, "role-bbva")]
        match_plan = {
            "requirements": [{"requirement": "Role-specific need", "evidence_chunk_ids": [requirement_id]}]
        }
        budgeted = _budget_evidence(chunks, match_plan, [backbone_id])
        self.assertEqual([item["chunk_id"] for item in budgeted][:2], [backbone_id, requirement_id])

        strategy = StrategyOutput(
            target_role="Senior Data Scientist",
            language="en",
            positioning="test",
            selected_evidence_chunk_ids=[requirement_id],
        )
        _attach_required_evidence(strategy, [backbone_id])
        self.assertEqual(strategy.selected_evidence_chunk_ids, [backbone_id, requirement_id])

    def test_default_submission_template_is_technical_modern_with_harvard_alternate(self) -> None:
        source = Path("cv_presentation/application_bundle.py").read_text(encoding="utf-8")
        self.assertIn('primary_template: str = "technical_modern_v1"', source)
        self.assertIn('alternate_template: str = "harvard_v1"', source)


if __name__ == "__main__":
    unittest.main()
