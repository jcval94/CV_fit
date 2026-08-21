from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from rag.evidence import chunk_record, retrieve_evidence, run_evidence_pipeline
from rag.normalize import normalize_file


ROOT = Path(__file__).resolve().parents[1]


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class EvidenceChunkTests(unittest.TestCase):
    def test_metric_entry_policy_is_atomic(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "experience" / "achievements" / "metrics.md"
            write(path, """---
schema_version: 3
record_id: achievement-metrics
record_type: achievement_registry
status: canonical
last_updated: 2026-08-21
confidence: high
visibility: public
public_safe: true
source_refs: []
---
# Metrics

## ACH-OK-001 — Approved
- **Status:** validated_public
- **Public safe:** true
- **CV usage:** approved
- **Result:** `10x`
- **Approved CV wording:** "Improved throughput by up to 10x."
- **Usage constraint:** retain up to

## ACH-BLOCKED-001 — Blocked
- **Status:** needs_reconciliation
- **Public safe:** true
- **CV usage:** conditional
- **Result:** `99%`
""")
            record = normalize_file(path, root, source_commit="abc")
            chunks = {chunk.chunk_id: chunk for chunk in chunk_record(record)}
            self.assertTrue(chunks["achievement-metrics::ACH-OK-001"].cv_eligible)
            self.assertFalse(chunks["achievement-metrics::ACH-BLOCKED-001"].cv_eligible)
            self.assertEqual(chunks["achievement-metrics::ACH-OK-001"].metric_refs, ["ACH-OK-001"])
            self.assertIn("retain up to", chunks["achievement-metrics::ACH-OK-001"].constraints)

    def test_skill_level_is_preserved_as_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "experience" / "skills.md"
            write(path, """---
schema_version: 3
record_id: skills
record_type: skills
status: canonical
last_updated: 2026-08-21
confidence: high
visibility: public
public_safe: true
source_refs: []
---
# Skills

### Kubernetes
- **Level:** familiarity
- **Usage note:** do not present as platform engineering expertise
""")
            record = normalize_file(path, root, source_commit="abc")
            chunks = chunk_record(record)
            self.assertEqual(len(chunks), 1)
            self.assertEqual(chunks[0].proficiency, "familiarity")
            self.assertIn("do not present", chunks[0].constraints[0])

    def test_project_boundaries_attach_to_each_evidence_chunk(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "experience" / "projects" / "x.md"
            write(path, """---
schema_version: 3
record_id: project-x
record_type: project
status: validated_public
last_updated: 2026-08-21
confidence: high
visibility: public
public_safe: true
source_refs: []
---
# X

## Implementation
Built a model.

## Boundaries
Do not claim sole ownership.
""")
            record = normalize_file(path, root, source_commit="abc")
            chunks = chunk_record(record)
            implementation = next(chunk for chunk in chunks if chunk.title == "Implementation")
            self.assertIn("Do not claim sole ownership.", implementation.constraints)


class EvidenceIncrementalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / "rag_state"
        write(self.root / "experience" / "projects" / "a.md", """---
schema_version: 3
record_id: project-a
record_type: project
status: validated_public
last_updated: 2026-08-21
confidence: high
visibility: public
public_safe: true
source_refs: []
---
# Project A
## Implementation
Python fraud model.
""")
        write(self.root / "experience" / "projects" / "b.md", """---
schema_version: 3
record_id: project-b
record_type: project
status: validated_public
last_updated: 2026-08-21
confidence: high
visibility: public
public_safe: true
source_refs: []
---
# Project B
## Implementation
SQL forecasting workflow.
""")

    def test_second_run_is_idempotent_and_one_change_reindexes_one_record(self) -> None:
        first = run_evidence_pipeline(self.root, self.state, run_id="one", source_commit="c1")
        self.assertEqual(first["record_counts"]["reindexed"], 2)
        second = run_evidence_pipeline(self.root, self.state, run_id="two", source_commit="c2")
        self.assertEqual(second["source_counts"]["unchanged"], 2)
        self.assertEqual(second["record_counts"]["impacted"], 0)
        self.assertEqual(second["record_counts"]["reindexed"], 0)

        path = self.root / "experience" / "projects" / "a.md"
        path.write_text(path.read_text(encoding="utf-8") + "\n## Outcome\nImproved prioritization.\n", encoding="utf-8")
        third = run_evidence_pipeline(self.root, self.state, run_id="three", source_commit="c3")
        self.assertEqual(third["source_counts"]["modified"], 1)
        self.assertEqual(third["record_counts"]["reindexed"], 1)

    def test_retrieval_returns_source_and_constraints(self) -> None:
        run_evidence_pipeline(self.root, self.state, run_id="one", source_commit="c1")
        index = json.loads((self.state / "lexical_index.json").read_text(encoding="utf-8"))
        hits = retrieve_evidence(index, "fraud Python", top_k=3)
        self.assertTrue(hits)
        self.assertEqual(hits[0]["record_id"], "project-a")
        self.assertEqual(hits[0]["source_path"], "experience/projects/a.md")


class EvidenceRepositorySmokeTest(unittest.TestCase):
    def test_current_repository_builds_semantic_evidence_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            report = run_evidence_pipeline(ROOT, Path(temp) / "rag_state", run_id="repo", source_commit="test")
            self.assertGreaterEqual(report["record_counts"]["active"], 20)
            state = Path(temp) / "rag_state"
            index = json.loads((state / "lexical_index.json").read_text(encoding="utf-8"))
            self.assertIn("skills", index["record_chunks"])
            self.assertTrue(any(chunk_id.startswith("achievement-metrics::ACH-") for chunk_id in index["chunks"]))
            hits = retrieve_evidence(index, "fraud anomaly detection PySpark", top_k=10)
            self.assertTrue(hits)


if __name__ == "__main__":
    unittest.main()
