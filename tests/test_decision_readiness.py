from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cv_presentation.decision_readiness import enforce_readiness
from cv_presentation.decision_scope import build_scoped_decision_grade


class DecisionReadinessTests(unittest.TestCase):
    def _write(self, path: Path, payload) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def _payload(self) -> dict:
        return {
            "summary": {"since_ledger_telemetry_coverage_pct": 100.0},
            "cost_concentrations": {"review_loop_spend_usd": 9.99},
            "events": [
                {"batch_run_id": "run-1", "agent": "senior_headhunter_1", "cost_usd": 0.10},
                {"batch_run_id": "run-1", "agent": "cv_reviser_1", "cost_usd": 0.12},
                {"batch_run_id": "run-1", "agent": "senior_headhunter_2", "cost_usd": 0.08},
                {"batch_run_id": "old-run", "agent": "senior_headhunter_1", "cost_usd": 9.69},
            ],
            "decision_grade": {
                "scope": {
                    "scope_kind": "FULLY_OBSERVABLE_DECISION_GRADE_RUNS",
                    "run_count": 1,
                    "run_ids": ["run-1"],
                },
                "readiness": {
                    "status": "DECISION_GRADE_RECONCILED",
                    "ledger_call_cost_coverage_pct": 100.0,
                    "truth_rule": "missing stays missing",
                },
                "application_economics": {
                    "cohort_vacancy_count": 1,
                    "application_disposition_coverage_pct": 100.0,
                    "final_applied_outcome_coverage_pct": 100.0,
                },
                "spend_reasons": {
                    "classified_spend_pct": 100.0,
                },
                "marginal_reviews": {
                    "initial_evaluation_spend_usd": 0.10,
                    "improving_followup_spend_usd": 0.20,
                    "non_improving_followup_spend_usd": 0.0,
                    "incomplete_marginal_attribution_spend_usd": 0.0,
                    "unpaired_revision_spend_usd": 0.0,
                },
                "provider_reconciliation": {
                    "fully_reconciled": True,
                },
            },
        }

    def test_all_complete_dimensions_produce_decision_grade_reconciled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            public = root / "payload.json"
            html = root / "index.html"
            self._write(public, self._payload())
            html.write_text('<html><body><section class="panel section" id="decision-grade-economics"><p><strong>Readiness: DECISION_GRADE_RECONCILED</strong></p></section></body></html>', encoding="utf-8")
            result = enforce_readiness(public_payload_path=public, html_path=html)
            self.assertEqual(result["status"], "DECISION_GRADE_RECONCILED")
            self.assertTrue(result["completely_informed"])
            persisted = json.loads(public.read_text(encoding="utf-8"))
            readiness = persisted["decision_grade"]["readiness"]
            self.assertEqual(readiness["marginal_review_spend_coverage_pct"], 100.0)
            self.assertEqual(readiness["review_loop_known_spend_usd"], 0.30)
            self.assertTrue(readiness["completely_informed"])
            self.assertIn("Completeness gate", html.read_text(encoding="utf-8"))

    def test_zero_paid_cohort_is_not_falsely_decision_grade_even_with_observable_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            public = root / "payload.json"
            payload = self._payload()
            payload["decision_grade"]["application_economics"]["cohort_vacancy_count"] = 0
            self._write(public, payload)
            result = enforce_readiness(public_payload_path=public)
            self.assertEqual(result["status"], "NO_DECISION_GRADE_COHORT_YET")
            self.assertFalse(result["completely_informed"])

    def test_unclassified_spend_blocks_reconciled_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            public = root / "payload.json"
            payload = self._payload()
            payload["decision_grade"]["spend_reasons"]["classified_spend_pct"] = 84.0
            self._write(public, payload)
            result = enforce_readiness(public_payload_path=public)
            self.assertEqual(result["status"], "PARTIAL_SPEND_ORIGIN")
            self.assertFalse(result["completely_informed"])

    def test_missing_review_attribution_blocks_reconciled_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            public = root / "payload.json"
            payload = self._payload()
            payload["decision_grade"]["marginal_reviews"]["improving_followup_spend_usd"] = 0.10
            self._write(public, payload)
            result = enforce_readiness(public_payload_path=public)
            self.assertEqual(result["status"], "PARTIAL_REVIEW_ATTRIBUTION")
            self.assertAlmostEqual(result["marginal_review_spend_coverage_pct"], 66.67)

    def test_review_over_attribution_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            public = root / "payload.json"
            payload = self._payload()
            payload["decision_grade"]["marginal_reviews"]["unpaired_revision_spend_usd"] = 0.05
            self._write(public, payload)
            with self.assertRaisesRegex(ValueError, "over-attributes"):
                enforce_readiness(public_payload_path=public)

    def test_decision_scope_excludes_old_unobservable_runs_from_roi(self) -> None:
        base = {
            "summary": {"since_ledger_telemetry_coverage_pct": 100.0},
            "applications": [
                {"vacancy_id": "vac-old", "company": "OldCo", "recorded_cost_usd": 9.0},
                {"vacancy_id": "vac-new", "company": "NewCo", "recorded_cost_usd": 0.2},
            ],
            "events": [
                {"batch_run_id": "old-run", "vacancy_id": "vac-old", "stage": "generation", "agent": "cv_writer", "cost_usd": 9.0, "precision": "call_telemetry"},
                {"batch_run_id": "new-run", "vacancy_id": "vac-new", "stage": "generation", "agent": "cv_writer", "cost_usd": 0.2, "precision": "call_telemetry"},
            ],
            "cost_concentrations": {"review_loop_spend_usd": 0.0},
        }
        ledger = {
            "runs": {
                "old-run": {"run_id": "old-run", "recorded_at": "2026-08-23T10:00:00+00:00", "known_spend_usd": 9.0},
                "new-run": {"run_id": "new-run", "recorded_at": "2026-08-24T10:00:00+00:00", "known_spend_usd": 0.2},
            },
            "events": {
                "old": {"batch_run_id": "old-run", "vacancy_id": "vac-old", "stage": "generation", "agent": "cv_writer", "cost_usd": 9.0, "precision": "call_telemetry"},
                "new": {"batch_run_id": "new-run", "vacancy_id": "vac-new", "stage": "generation", "agent": "cv_writer", "cost_usd": 0.2, "precision": "call_telemetry"},
            },
        }
        evidence = {
            "runs": {
                "new-run": {"candidate_plan_available": True},
            },
            "spend_attribution": {
                "s": {"batch_run_id": "new-run", "vacancy_id": "vac-new", "spend_reason": "NEW_OR_MODIFIED_VACANCY", "attribution_precision": "candidate_plan_exact"},
            },
            "review_cycles": {},
            "unpaired_revisions": {},
        }
        app_state = {"entries": {"vac-new": {"current_status": "NOT_APPLIED", "events": [{"status": "NOT_APPLIED"}]}}}
        payload = build_scoped_decision_grade(
            base=base,
            ledger=ledger,
            application_state=app_state,
            decision_evidence=evidence,
            reconciliation={"entries": {}},
        )
        economics = payload["application_economics"]
        self.assertEqual(payload["scope"]["run_ids"], ["new-run"])
        self.assertEqual(economics["cohort_vacancy_count"], 1)
        self.assertAlmostEqual(economics["cohort_known_spend_usd"], 0.2)
        self.assertNotIn("vac-old", [row["vacancy_id"] for row in economics["rows"]])


if __name__ == "__main__":
    unittest.main()
