from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cv_presentation.decision_readiness import enforce_readiness


class DecisionReadinessTests(unittest.TestCase):
    def _write(self, path: Path, payload) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def _payload(self) -> dict:
        return {
            "summary": {"since_ledger_telemetry_coverage_pct": 100.0},
            "cost_concentrations": {"review_loop_spend_usd": 0.30},
            "decision_grade": {
                "readiness": {
                    "status": "DECISION_GRADE_RECONCILED",
                    "ledger_call_cost_coverage_pct": 100.0,
                    "truth_rule": "missing stays missing",
                },
                "application_economics": {
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
            self.assertTrue(readiness["completely_informed"])
            self.assertIn("Completeness gate", html.read_text(encoding="utf-8"))

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


if __name__ == "__main__":
    unittest.main()
