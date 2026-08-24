from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cv_observability.manual_attribution import classify_manual_request


class ManualAttributionTests(unittest.TestCase):
    def test_classifies_only_requested_vacancies_without_touching_costs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = root / "generation.json"
            state = root / "decision_evidence.json"
            report.write_text(json.dumps({
                "run_id": "manual-123",
                "results": [
                    {"vacancy_id": "vac-a", "run_id": "run-a", "status": "PASS"},
                    {"vacancy_id": "vac-b", "run_id": "run-b", "status": "COMPLETED_BELOW_TARGET"},
                ],
            }), encoding="utf-8")
            state.write_text(json.dumps({
                "schema_version": 1,
                "runs": {"manual-123": {"spend_attribution_ids": []}},
                "spend_attribution": {},
                "review_cycles": {"cycle": {"cycle_known_cost_usd": 0.1234}},
                "unpaired_revisions": {},
            }), encoding="utf-8")

            result = classify_manual_request(
                generation_report=report,
                decision_state=state,
                request_id="request-1",
                vacancy_ids={"vac-a"},
            )
            payload = json.loads(state.read_text(encoding="utf-8"))
            rows = list(payload["spend_attribution"].values())
            self.assertEqual(result["classified_vacancies"], 1)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["vacancy_id"], "vac-a")
            self.assertEqual(rows[0]["spend_reason"], "MANUAL_POLICY_TEST")
            self.assertEqual(rows[0]["attribution_precision"], "explicit_manual_request")
            self.assertEqual(rows[0]["manual_request_id"], "request-1")
            self.assertEqual(payload["review_cycles"]["cycle"]["cycle_known_cost_usd"], 0.1234)
            self.assertEqual(payload["runs"]["manual-123"]["manual_request_id"], "request-1")


if __name__ == "__main__":
    unittest.main()
