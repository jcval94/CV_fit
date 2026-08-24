from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cv_observability.cost_ledger import capture_legacy_baseline, record_run
from cv_observability.decision_evidence import enrich_from_outputs


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

    def test_decision_evidence_uses_candidate_plan_and_attributes_delta_only_to_observed_followup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outputs = root / "auto"
            ledger = root / "cost_ledger.json"
            state = root / "decision_evidence.json"
            run_id = "auto-xyz"
            vacancy_id = "vac-1"
            vacancy_run_id = f"{run_id}-{vacancy_id}"
            batch_dir = outputs / "_batch" / run_id
            run_dir = outputs / vacancy_id / vacancy_run_id
            self._write(batch_dir / "generation_run_report.json", {
                "run_id": run_id,
                "source_commit": "xyz",
                "deferred_candidate_count": 0,
                "stale_logic_included_count": 0,
                "results": [{"vacancy_id": vacancy_id, "run_id": vacancy_run_id, "status": "COMPLETED_BELOW_TARGET"}],
            })
            self._write(batch_dir / "candidate_plan.json", {
                "original_reindexed_vacancy_ids": [vacancy_id],
                "auto_retry_vacancy_ids": [],
            })
            self._write(run_dir / "reviews" / "iteration_01.json", {
                "iteration": 1,
                "review": {"overall_score": 80, "decision": "REVISE"},
                "validation": {"quality_gate": {"passed": False}},
            })
            self._write(run_dir / "reviews" / "iteration_02.json", {
                "iteration": 2,
                "review": {"overall_score": 86, "decision": "REVISE"},
                "validation": {"quality_gate": {"passed": False}},
            })
            self._write(ledger, {
                "schema_version": 1,
                "events": {
                    "h1": {"batch_run_id": run_id, "vacancy_id": vacancy_id, "stage": "generation", "agent": "senior_headhunter_1", "cost_usd": 0.10, "precision": "call_telemetry"},
                    "r1": {"batch_run_id": run_id, "vacancy_id": vacancy_id, "stage": "generation", "agent": "cv_reviser_1", "cost_usd": 0.12, "precision": "call_telemetry"},
                    "h2": {"batch_run_id": run_id, "vacancy_id": vacancy_id, "stage": "generation", "agent": "senior_headhunter_2", "cost_usd": 0.08, "precision": "call_telemetry"},
                    "r2": {"batch_run_id": run_id, "vacancy_id": vacancy_id, "stage": "generation", "agent": "cv_reviser_2", "cost_usd": 0.11, "precision": "call_telemetry"},
                },
                "runs": {},
            })

            report = enrich_from_outputs(outputs_root=outputs, ledger_path=ledger, state_path=state)
            self.assertEqual(report["processed_runs"], 1)
            persisted = json.loads(state.read_text(encoding="utf-8"))
            attribution = next(iter(persisted["spend_attribution"].values()))
            self.assertEqual(attribution["spend_reason"], "NEW_OR_MODIFIED_VACANCY")
            self.assertEqual(attribution["attribution_precision"], "candidate_plan_exact")
            cycles = sorted(persisted["review_cycles"].values(), key=lambda row: row["iteration"])
            self.assertIsNone(cycles[0]["score_delta"])
            self.assertAlmostEqual(cycles[0]["cycle_known_cost_usd"], 0.10)
            self.assertEqual(cycles[1]["score_delta"], 6.0)
            self.assertAlmostEqual(cycles[1]["cycle_known_cost_usd"], 0.20)
            self.assertAlmostEqual(cycles[1]["cost_per_positive_score_point_usd"], 0.20 / 6.0)
            unpaired = next(iter(persisted["unpaired_revisions"].values()))
            self.assertEqual(unpaired["agent"], "cv_reviser_2")
            self.assertIn("no subsequent persisted headhunter score", unpaired["reason"])


if __name__ == "__main__":
    unittest.main()
