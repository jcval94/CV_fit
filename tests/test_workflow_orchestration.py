from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WorkflowOrchestrationTests(unittest.TestCase):
    def test_raw_vacancies_are_serialized_through_enrichment(self) -> None:
        enrich = (ROOT / ".github/workflows/auto-enrich-jd.yml").read_text(encoding="utf-8")
        ingest = (ROOT / ".github/workflows/vacancy-ingest.yml").read_text(encoding="utf-8")

        self.assertIn("Dispatch canonical ingest after enrichment gate", enrich)
        self.assertNotIn("if: steps.persist.outputs.changed == 'true'", enrich)

        push_block = ingest.split("  push:\n", 1)[1].split("  workflow_dispatch:", 1)[0]
        self.assertNotIn('"GPTW/**/*.json"', push_block)
        self.assertNotIn('"Vacantes/**/*.json"', push_block)
        self.assertIn('"cv_handoff/**"', push_block)

    def test_morning_watchdog_is_recovery_only(self) -> None:
        workflow = (ROOT / ".github/workflows/morning-readiness.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "55 14 * * *"', workflow)
        self.assertIn('cron: "10 15 * * *"', workflow)
        self.assertIn("handoff/index.json", workflow)
        self.assertIn("gh workflow run auto-enrich-jd.yml --ref main", workflow)
        self.assertIn("needs_refresh == 'true'", workflow)


if __name__ == "__main__":
    unittest.main()
