from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cv_auto.recovery import build_generation_candidate_report, is_recoverable_failure


class GenerationRecoveryTests(unittest.TestCase):
    def _write(self, path: Path, payload) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def test_quota_and_network_failures_are_recoverable_but_quality_failures_are_not(self):
        self.assertTrue(is_recoverable_failure({"status": "FAILED_REVIEW_REQUIRED", "error": "RateLimitError 429 insufficient_quota credit_balance_exhausted"}))
        self.assertTrue(is_recoverable_failure({"status": "FAILED_REVIEW_REQUIRED", "error": "TimeoutError: timed out"}))
        self.assertFalse(is_recoverable_failure({"status": "FAILED_REVIEW_REQUIRED", "error": "ValueError: invalid grounded CV schema"}))
        self.assertFalse(is_recoverable_failure({"status": "PASS", "error": "429"}))

    def test_daily_new_candidates_are_kept_before_recovery_and_recovery_uses_only_spare_capacity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ingest = root / "ingest.json"
            manifest = root / "generation_state" / "manifest.json"
            vacancy_state = root / "vacancy_state"
            output = root / "candidates.json"
            self._write(ingest, {"reindexed_vacancy_ids": ["vac-new-1", "vac-new-2"]})
            self._write(manifest, {"entries": {
                "vac-old-a": {"status": "FAILED_REVIEW_REQUIRED", "error": "HTTP 429 rate limit"},
                "vac-old-b": {"status": "FAILED_REVIEW_REQUIRED", "error": "credit_balance_exhausted"},
                "vac-old-c": {"status": "FAILED_REVIEW_REQUIRED", "error": "ValueError: deterministic failure"},
            }})
            for vacancy_id in ("vac-old-a", "vac-old-b", "vac-old-c"):
                self._write(vacancy_state / "records" / f"{vacancy_id}.json", {"jd_generation_eligible": True})

            report = build_generation_candidate_report(
                ingest_report=ingest,
                generation_manifest=manifest,
                vacancy_state=vacancy_state,
                output=output,
                max_vacancies_per_run=3,
                max_recovery_candidates=3,
            )
            self.assertEqual(report["original_reindexed_vacancy_ids"], ["vac-new-1", "vac-new-2"])
            self.assertEqual(report["auto_retry_vacancy_ids"], ["vac-old-a"])
            self.assertEqual(report["reindexed_vacancy_ids"], ["vac-new-1", "vac-new-2", "vac-old-a"])

    def test_sparse_old_failure_is_not_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ingest = root / "ingest.json"
            manifest = root / "manifest.json"
            vacancy_state = root / "vacancy_state"
            output = root / "candidates.json"
            self._write(ingest, {"reindexed_vacancy_ids": []})
            self._write(manifest, {"entries": {"vac-old": {"status": "FAILED_REVIEW_REQUIRED", "error": "HTTP 503 server_error"}}})
            self._write(vacancy_state / "records" / "vac-old.json", {"jd_generation_eligible": False})
            report = build_generation_candidate_report(
                ingest_report=ingest,
                generation_manifest=manifest,
                vacancy_state=vacancy_state,
                output=output,
                max_vacancies_per_run=6,
            )
            self.assertEqual(report["auto_retry_vacancy_ids"], [])


if __name__ == "__main__":
    unittest.main()
