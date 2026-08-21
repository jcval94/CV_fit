from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rag.normalize import normalize_corpus, normalize_file, retrieval_class_for_path


ROOT = Path(__file__).resolve().parents[1]


class NormalizeUnitTests(unittest.TestCase):
    def _write_fixture(self, relative_path: str, content: str) -> tuple[Path, Path]:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return root, path

    def test_project_normalization_preserves_structure_and_relations(self) -> None:
        root, path = self._write_fixture(
            "experience/projects/example.md",
            """---
schema_version: 3
record_id: project-example
record_type: project
status: validated_public
last_updated: 2026-08-20
confidence: high
visibility: public
public_safe: true
organization: Example
source_refs:
  - SRC-EXAMPLE
---
# Example Project

## Contribution and ownership

Built a deterministic workflow.

## Outcome references

- `ACH-EXAMPLE-001` — approved impact

## Boundaries

Do not overclaim ownership.

## Related records

- [Role](../roles/example.md)
""",
        )

        record = normalize_file(path, root, source_commit="abc123")

        self.assertEqual(record.record_id, "project-example")
        self.assertEqual(record.retrieval_class, "evidence")
        self.assertTrue(record.automatic_reuse_eligible)
        self.assertTrue(record.embedding_candidate)
        self.assertEqual(record.metric_refs, ["ACH-EXAMPLE-001"])
        self.assertEqual(record.linked_markdown_paths, ["../roles/example.md"])
        self.assertEqual(record.attributes["organization"], "Example")
        self.assertEqual(record.source_commit, "abc123")
        self.assertTrue(any(section.semantic_type == "ownership" for section in record.sections))
        self.assertTrue(any(section.semantic_type == "boundary" for section in record.sections))

    def test_needs_reconciliation_is_not_eligible_for_automatic_reuse(self) -> None:
        root, path = self._write_fixture(
            "experience/example.md",
            """---
schema_version: 3
record_id: example
record_type: profile
status: needs_reconciliation
last_updated: 2026-08-20
confidence: medium
visibility: public
public_safe: true
source_refs: []
---
# Example
""",
        )
        record = normalize_file(path, root, source_commit="abc123")
        self.assertFalse(record.automatic_reuse_eligible)
        self.assertFalse(record.embedding_candidate)

    def test_retrieval_class_is_deterministic(self) -> None:
        self.assertEqual(retrieval_class_for_path("experience/_meta/conflicts.md"), "policy")
        self.assertEqual(retrieval_class_for_path("experience/projects/index.md"), "router")
        self.assertEqual(retrieval_class_for_path("experience/roles/index.md"), "router")
        self.assertEqual(retrieval_class_for_path("experience/projects/github_portfolio.md"), "router")
        self.assertEqual(retrieval_class_for_path("experience/projects/insideforest.md"), "evidence")


class NormalizeRepositoryIntegrationTests(unittest.TestCase):
    def test_current_experience_corpus_normalizes_without_duplicate_ids(self) -> None:
        records = normalize_corpus(ROOT, source_commit="test-commit")
        self.assertGreaterEqual(len(records), 20)

        ids = [record.record_id for record in records]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("professional-profile", ids)
        self.assertIn("project-retrieval-index", ids)
        self.assertIn("governance-conflict-log", ids)

        by_id = {record.record_id: record for record in records}
        self.assertEqual(by_id["project-retrieval-index"].retrieval_class, "router")
        self.assertFalse(by_id["project-retrieval-index"].embedding_candidate)
        self.assertEqual(by_id["governance-conflict-log"].retrieval_class, "policy")
        self.assertFalse(by_id["governance-conflict-log"].embedding_candidate)
        self.assertEqual(by_id["professional-profile"].retrieval_class, "evidence")
        self.assertTrue(by_id["professional-profile"].embedding_candidate)

        for record in records:
            self.assertTrue(record.content_hash)
            self.assertTrue(record.source_path.startswith("experience/"))
            self.assertIsInstance(record.sections, list)


if __name__ == "__main__":
    unittest.main()
