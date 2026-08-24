from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cv_presentation.budget_dashboard import build_budget_dashboard
from cv_presentation.decision_dashboard import build_decision_payload, enrich_dashboard


class BudgetDashboardTests(unittest.TestCase):
    def _write(self, path: Path, payload) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def _fixture(self, root: Path):
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
                "generation_known_spend_usd": 0.2,
                "downstream_known_spend_usd": 0.0,
                "telemetry_coverage_pct": 100.0,
                "unpriced_call_count": 0,
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
        return ledger, manifest, vacancy_state, site

    def test_dashboard_exposes_totals_agent_detail_and_navigation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger, manifest, vacancy_state, site = self._fixture(root)
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

    def test_ready_cv_is_not_counted_as_application_when_outcome_is_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger, manifest, vacancy_state, site = self._fixture(root)
            application_state = root / "generation_state" / "application_state.json"
            decision_evidence = root / "generation_state" / "decision_evidence.json"
            reconciliation = root / "generation_state" / "provider_reconciliation.json"
            self._write(application_state, {"schema_version": 1, "entries": {}})
            self._write(decision_evidence, {"schema_version": 1, "spend_attribution": {}, "review_cycles": {}, "unpaired_revisions": {}})
            self._write(reconciliation, {"schema_version": 1, "entries": {}})
            build_budget_dashboard(ledger_path=ledger, manifest_path=manifest, vacancy_state=vacancy_state, site_dir=site)
            result = enrich_dashboard(
                site_dir=site,
                ledger_path=ledger,
                application_state_path=application_state,
                decision_evidence_path=decision_evidence,
                reconciliation_path=reconciliation,
            )
            self.assertEqual(result["readiness"], "WAITING_APPLICATION_DISPOSITIONS")
            payload = json.loads((site / "budget" / "cost_ledger_public.json").read_text(encoding="utf-8"))
            economics = payload["decision_grade"]["application_economics"]
            self.assertEqual(economics["confirmed_application_count"], 0)
            self.assertEqual(economics["application_disposition_coverage_pct"], 0.0)
            self.assertIsNone(economics["cost_per_application_usd"])
            html = (site / "budget" / "index.html").read_text(encoding="utf-8")
            self.assertIn('id="decision-grade-economics"', html)
            self.assertIn("never converts READY into APPLIED", html)

    def test_complete_observed_cohort_and_provider_statement_enable_reconciled_decision_grade_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger_path, manifest, vacancy_state, site = self._fixture(root)
            build_budget_dashboard(ledger_path=ledger_path, manifest_path=manifest, vacancy_state=vacancy_state, site_dir=site)
            base = json.loads((site / "budget" / "cost_ledger_public.json").read_text(encoding="utf-8"))
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            application_state = {"schema_version": 1, "entries": {"vac-1": {
                "vacancy_id": "vac-1",
                "current_status": "REJECTED",
                "events": [
                    {"status": "APPLIED", "event_id": "a1"},
                    {"status": "INTERVIEW", "event_id": "a2"},
                    {"status": "REJECTED", "event_id": "a3"},
                ],
            }}}
            decision_evidence = {"schema_version": 1, "spend_attribution": {"s1": {
                "batch_run_id": "auto-1",
                "vacancy_id": "vac-1",
                "spend_reason": "NEW_OR_MODIFIED_VACANCY",
                "attribution_precision": "candidate_plan_exact",
            }}, "review_cycles": {}, "unpaired_revisions": {}}
            reconciliation = {"schema_version": 1, "entries": {"p1": {
                "entry_id": "p1",
                "period_start": "2026-08-24T16:00:00+00:00",
                "period_end": "2026-08-24T18:00:00+00:00",
                "actual_cost_usd": 0.2,
                "source_kind": "PROVIDER_STATEMENT_USER_RECORDED",
            }}}
            payload = build_decision_payload(
                base=base,
                ledger=ledger,
                application_state=application_state,
                decision_evidence=decision_evidence,
                reconciliation=reconciliation,
            )
            self.assertEqual(payload["readiness"]["status"], "DECISION_GRADE_RECONCILED")
            economics = payload["application_economics"]
            self.assertEqual(economics["confirmed_application_count"], 1)
            self.assertEqual(economics["confirmed_interview_count"], 1)
            self.assertEqual(economics["final_applied_outcome_coverage_pct"], 100.0)
            self.assertAlmostEqual(economics["cost_per_application_usd"], 0.2)
            self.assertAlmostEqual(economics["cost_per_interview_usd"], 0.2)
            self.assertEqual(payload["spend_reasons"]["candidate_plan_exact_spend_pct"], 100.0)
            provider = payload["provider_reconciliation"]
            self.assertTrue(provider["fully_reconciled"])
            self.assertAlmostEqual(provider["rows"][0]["variance_actual_minus_telemetry_usd"], 0.0)


if __name__ == "__main__":
    unittest.main()
