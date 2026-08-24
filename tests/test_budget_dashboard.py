from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cv_presentation.budget_dashboard import build_budget_dashboard


class BudgetDashboardTests(unittest.TestCase):
    def _write(self, path: Path, payload) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def test_dashboard_exposes_totals_agent_detail_and_navigation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / "generation_state" / "cost_ledger.json"
            manifest = root / "generation_state" / "manifest.json"
            vacancy_state = root / "vacancy_state"
            site = root / "_site"
            site.mkdir(parents=True)
            (site / "index.html").write_text('<html><head></head><body><div class="top-stats"></div></body></html>', encoding="utf-8")
            self._write(vacancy_state / "records" / "vac-1.json", {
                "vacancy_id": "vac-1",
                "company": "ExampleCo",
                "role_title": "Senior Data Scientist",
                "url": "https://example.com/job",
                "fit_score": 91,
            })
            self._write(manifest, {"entries": {"vac-1": {
                "status": "PASS",
                "ready_to_send": True,
                "application_bundle_file": "application_bundle_report.json",
            }}})
            self._write(ledger, {
                "schema_version": 1,
                "pricing_snapshot_date": "2026-08-21",
                "pricing_basis": "test pricing",
                "pricing_source": "https://example.com",
                "legacy_baseline": {
                    "known_cost_usd": 0.5,
                    "vacancy_count": 1,
                    "historical_cost_complete": False,
                    "note": "legacy lower bound",
                    "entries": {"vac-1": {"known_cost_usd": 0.5, "stages": {"generation": 0.5}}},
                },
                "runs": {"auto-1": {
                    "run_id": "auto-1",
                    "recorded_at": "2026-08-24T17:00:00+00:00",
                    "budget_usd": 2.0,
                    "known_spend_usd": 0.2,
                    "telemetry_coverage_pct": 100.0,
                    "source_candidate_count": 1,
                    "generation_attempts": 1,
                    "ready_count": 1,
                }},
                "events": {"e1": {
                    "event_id": "e1",
                    "batch_run_id": "auto-1",
                    "vacancy_id": "vac-1",
                    "vacancy_run_id": "auto-1-vac-1",
                    "stage": "generation",
                    "agent": "cv_writer",
                    "model": "gpt-5.6-terra",
                    "call_index": 1,
                    "prompt_tokens": 100,
                    "cached_input_tokens": 0,
                    "candidate_tokens": 20,
                    "reasoning_tokens": 5,
                    "total_tokens": 125,
                    "duration_ms": 10,
                    "cost_usd": 0.2,
                    "status": "PASS",
                    "error_type": None,
                    "precision": "call_telemetry",
                }},
            })

            report = build_budget_dashboard(
                ledger_path=ledger,
                manifest_path=manifest,
                vacancy_state=vacancy_state,
                site_dir=site,
            )
            self.assertAlmostEqual(report["known_spend_usd"], 0.7)
            self.assertEqual(report["application_bundles"], 1)
            self.assertTrue((site / "budget" / "index.html").exists())
            payload = json.loads((site / "budget" / "cost_ledger_public.json").read_text(encoding="utf-8"))
            self.assertAlmostEqual(payload["summary"]["known_spend_usd"], 0.7)
            self.assertEqual(payload["agents"][0]["name"], "cv_writer")
            self.assertEqual(payload["applications"][0]["company"], "ExampleCo")
            root_html = (site / "index.html").read_text(encoding="utf-8")
            self.assertIn('id="cvfit-budget-nav"', root_html)
            self.assertIn("budget/index.html", root_html)
            budget_html = (site / "budget" / "index.html").read_text(encoding="utf-8")
            self.assertIn("Exact call ledger", budget_html)
            self.assertIn("cv_writer", budget_html)


if __name__ == "__main__":
    unittest.main()
