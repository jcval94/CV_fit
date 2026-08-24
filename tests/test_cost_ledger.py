from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cv_observability.cost_ledger import capture_legacy_baseline, record_run


class CostLedgerTests(unittest.TestCase):
    def _write(self, path: Path, payload) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def test_baseline_is_frozen_once_and_run_events_are_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / "generation_state" / "cost_ledger.json"
            manifest = root / "generation_state" / "manifest.json"
            recovered = root / "generation_state" / "recovered_metrics.json"
            outputs = root / "outputs"
            generation_report = root / "generation.json"
            cover_report = root / "cover.json"
            bundle_report = root / "bundle.json"

            self._write(manifest, {"entries": {"vac-1": {
                "cumulative_known_cost_usd": 0.8,
                "cover_letter_cost_usd": 0.01,
                "presentation_cost_usd": 0.005,
                "status": "COMPLETED_BELOW_TARGET",
            }}})
            self._write(recovered, {"entries": {}})
            baseline = capture_legacy_baseline(
                manifest_path=manifest,
                recovered_metrics_path=recovered,
                ledger_path=ledger,
                source_commit="before",
            )
            self.assertAlmostEqual(baseline["known_cost_usd"], 0.815)
            self.assertFalse(baseline["historical_cost_complete"])

            # A later manifest edit must not move the historical boundary.
            self._write(manifest, {"entries": {"vac-1": {"cumulative_known_cost_usd": 99.0}}})
            frozen = capture_legacy_baseline(
                manifest_path=manifest,
                recovered_metrics_path=recovered,
                ledger_path=ledger,
                source_commit="after",
            )
            self.assertAlmostEqual(frozen["known_cost_usd"], 0.815)

            run_id = "auto-abc"
            vacancy_run_id = f"{run_id}-vac-1"
            run_dir = outputs / "vac-1" / vacancy_run_id
            self._write(run_dir / "usage_report.json", {
                "estimated_cost_usd": 0.3,
                "known_estimated_cost_usd": 0.3,
                "calls": [
                    {"name": "cv_strategist", "model": "gpt-5.6-terra", "prompt_tokens": 100, "cached_input_tokens": 0, "candidate_tokens": 20, "reasoning_tokens": 5, "total_tokens": 125, "duration_ms": 10, "estimated_cost_usd": 0.1, "error": None},
                    {"name": "cv_writer", "model": "gpt-5.6-terra", "prompt_tokens": 200, "cached_input_tokens": 0, "candidate_tokens": 40, "reasoning_tokens": 10, "total_tokens": 250, "duration_ms": 20, "estimated_cost_usd": 0.2, "error": None},
                ],
            })
            self._write(run_dir / "run_report.json", {"stage_usage": {
                "cover_letter": {
                    "estimated_cost_usd": 0.01,
                    "known_estimated_cost_usd": 0.01,
                    "calls": [{"name": "cover_letter_writer", "model": "gpt-5.6-luna", "prompt_tokens": 50, "cached_input_tokens": 0, "candidate_tokens": 10, "reasoning_tokens": 0, "total_tokens": 60, "duration_ms": 5, "estimated_cost_usd": 0.01, "error": None}],
                },
                "presentation": {
                    "estimated_cost_usd": 0.02,
                    "known_estimated_cost_usd": 0.02,
                    "calls": [{"name": "cv_design_reviewer", "model": "gpt-5.6-luna", "prompt_tokens": 60, "cached_input_tokens": 0, "candidate_tokens": 10, "reasoning_tokens": 0, "total_tokens": 70, "duration_ms": 5, "estimated_cost_usd": 0.02, "error": None}],
                },
            }})
            self._write(generation_report, {"run_id": run_id, "candidate_count": 1, "source_candidate_count": 1, "generation_attempts": 1, "result_counts": {"PASS": 1}, "results": [{"vacancy_id": "vac-1", "run_id": vacancy_run_id, "status": "PASS", "known_estimated_cost_usd": 0.3}]})
            self._write(cover_report, {"results": [{"vacancy_id": "vac-1", "run_id": vacancy_run_id, "status": "PASS", "known_estimated_cost_usd": 0.01}]})
            self._write(bundle_report, {"result_counts": {"PASS": 1}, "results": [{"vacancy_id": "vac-1", "run_id": vacancy_run_id, "status": "PASS", "ready_to_send": True, "presentation_cost_usd": 0.02}]})

            first = record_run(
                generation_report_path=generation_report,
                cover_report_path=cover_report,
                bundle_report_path=bundle_report,
                outputs=outputs,
                ledger_path=ledger,
                source_commit="abc",
                batch_budget_usd=2.0,
            )
            second = record_run(
                generation_report_path=generation_report,
                cover_report_path=cover_report,
                bundle_report_path=bundle_report,
                outputs=outputs,
                ledger_path=ledger,
                source_commit="abc",
                batch_budget_usd=2.0,
            )
            self.assertAlmostEqual(first["known_spend_usd"], 0.33)
            self.assertEqual(first["call_count"], 4)
            self.assertEqual(first["telemetry_coverage_pct"], 100.0)
            self.assertEqual(second["event_ids"], first["event_ids"])
            persisted = json.loads(ledger.read_text(encoding="utf-8"))
            self.assertEqual(len(persisted["events"]), 4)
            self.assertEqual(len(persisted["runs"]), 1)


if __name__ == "__main__":
    unittest.main()
