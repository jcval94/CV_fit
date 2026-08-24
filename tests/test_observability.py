from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path

from cv_observability.application_state import record_application_event, summarize_entry
from cv_observability.decision_truth import validate_decision_sources
from cv_observability.logging import EventLogger, sanitize
from cv_observability.pipeline_summary import build_summary, render_markdown
from cv_observability.provider_reconciliation import record_provider_statement


class ObservabilityTests(unittest.TestCase):
    def test_logger_redacts_secrets_pii_but_keeps_metrics_and_run_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            event_path = Path(tmp) / "events.jsonl"
            stream = io.StringIO()
            logger = EventLogger(
                "test",
                run_id="gha-32658712054-1",
                event_log_path=event_path,
                stream=stream,
            )
            logger.info(
                "example",
                access_token="secret-token",
                recipient="5215555555555",
                detail="Bearer abcdefghijk user@example.com +5215512345678 sk-proj-abcdefghijklmnop",
                prompt_tokens=123,
                cached_input_tokens=7,
                candidate_tokens=45,
                reasoning_tokens=8,
                total_tokens=183,
                cost=0.1234,
            )
            text = stream.getvalue()
            persisted = event_path.read_text(encoding="utf-8")
            for raw in ("secret-token", "5215555555555", "user@example.com", "+5215512345678", "sk-proj-abcdefghijklmnop"):
                self.assertNotIn(raw, text)
                self.assertNotIn(raw, persisted)
            self.assertIn("[REDACTED]", text)
            self.assertIn("[REDACTED_EMAIL]", text)
            self.assertIn("run_id=gha-32658712054-1", text)
            self.assertIn("prompt_tokens=123", text)
            self.assertIn("total_tokens=183", text)
            payload = json.loads(persisted)
            self.assertEqual(payload["component"], "test")
            self.assertEqual(payload["run_id"], "gha-32658712054-1")
            self.assertEqual(payload["prompt_tokens"], 123)
            self.assertEqual(payload["total_tokens"], 183)
            self.assertEqual(payload["cost"], 0.1234)

    def test_span_logs_duration_on_success_and_failure(self) -> None:
        stream = io.StringIO()
        logger = EventLogger("span-test", stream=stream)
        with logger.span("ok"):
            pass
        with self.assertRaisesRegex(RuntimeError, "boom"):
            with logger.span("bad"):
                raise RuntimeError("boom")
        text = stream.getvalue()
        self.assertIn("event=stage_started", text)
        self.assertIn("event=stage_completed", text)
        self.assertIn("event=stage_failed", text)
        self.assertIn("duration_ms=", text)
        self.assertIn("error_type=RuntimeError", text)

    def test_sanitize_nested_sensitive_keys_without_redacting_token_counts(self) -> None:
        value = sanitize({
            "safe": 1,
            "phone_number_id": "123",
            "nested": {"prompt": "private", "prompt_tokens": 22, "total_tokens": 30},
        })
        self.assertEqual(value["safe"], 1)
        self.assertEqual(value["phone_number_id"], "[REDACTED]")
        self.assertEqual(value["nested"]["prompt"], "[REDACTED]")
        self.assertEqual(value["nested"]["prompt_tokens"], 22)
        self.assertEqual(value["nested"]["total_tokens"], 30)

    def test_pipeline_summary_reconciles_stage_reports_and_costs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ingest = root / "ingest.json"
            generation = root / "generation.json"
            cover = root / "cover.json"
            bundle = root / "bundle.json"
            manifest = root / "manifest.json"
            whatsapp = root / "whatsapp.json"

            ingest.write_text(json.dumps({
                "status": "success",
                "source_counts": {"new": 1},
                "vacancy_counts": {"reindexed": 1},
            }), encoding="utf-8")
            generation.write_text(json.dumps({"results": [{
                "vacancy_id": "vac-1", "status": "PASS", "run_id": "run-vac-1"
            }]}), encoding="utf-8")
            cover.write_text(json.dumps({"generated": 1, "failed": 0, "results": [{
                "vacancy_id": "vac-1", "status": "PASS"
            }]}), encoding="utf-8")
            bundle.write_text(json.dumps({"result_counts": {"PASS": 1}, "results": [{
                "vacancy_id": "vac-1",
                "status": "PASS",
                "ready_to_send": True,
                "generation_cost_usd": 0.5,
                "cover_letter_cost_usd": 0.1,
                "presentation_cost_usd": 0.2,
                "total_pipeline_known_cost_usd": 0.8,
                "total_pipeline_cost_complete": True,
            }]}), encoding="utf-8")
            manifest.write_text(json.dumps({"entries": {"vac-1": {
                "headhunter_score": 94,
                "coverage_score": 87.5,
                "ready_to_send": True,
            }}}), encoding="utf-8")
            whatsapp.write_text(json.dumps({"entries": {
                "old": {"vacancy_id": "vac-1", "status": "RESERVED", "reserved_at": "2026-08-23T10:00:00Z"},
                "new": {"vacancy_id": "vac-1", "status": "ACCEPTED", "accepted_at": "2026-08-23T10:01:00Z"},
            }}), encoding="utf-8")

            summary = build_summary(
                ingest_report=ingest,
                generation_report=generation,
                cover_report=cover,
                bundle_report=bundle,
                generation_manifest=manifest,
                whatsapp_state=whatsapp,
            )
            row = summary["rows"][0]
            self.assertEqual(row["generation"], "PASS")
            self.assertEqual(row["headhunter"], 94)
            self.assertEqual(row["pipeline_cost_usd"], 0.8)
            self.assertEqual(row["whatsapp"], "ACCEPTED")
            markdown = render_markdown(summary)
            self.assertIn("CV_fit E2E observability", markdown)
            self.assertIn("vac-1", markdown)
            self.assertIn("0.8000", markdown)
            self.assertIn("ACCEPTED", markdown)

    def test_pipeline_summary_preserves_known_zero_cost(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, payload in {
                "ingest.json": {},
                "generation.json": {"results": [{"vacancy_id": "vac-zero", "status": "PASS"}]},
                "cover.json": {"results": []},
                "bundle.json": {"results": [{
                    "vacancy_id": "vac-zero",
                    "generation_cost_usd": 0.0,
                    "total_pipeline_known_cost_usd": 0.0,
                    "total_pipeline_cost_complete": False,
                }]},
                "manifest.json": {"entries": {"vac-zero": {
                    "known_estimated_cost_usd": 9.99,
                    "total_pipeline_known_cost_usd": 9.99,
                }}},
            }.items():
                (root / name).write_text(json.dumps(payload), encoding="utf-8")
            summary = build_summary(
                ingest_report=root / "ingest.json",
                generation_report=root / "generation.json",
                cover_report=root / "cover.json",
                bundle_report=root / "bundle.json",
                generation_manifest=root / "manifest.json",
            )
            row = summary["rows"][0]
            self.assertEqual(row["generation_cost_usd"], 0.0)
            self.assertEqual(row["pipeline_cost_usd"], 0.0)
            self.assertFalse(row["cost_complete"])

    def test_application_state_is_explicit_append_only_and_never_stores_raw_evidence_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vacancy_state = root / "vacancy_state"
            state_path = root / "generation_state" / "application_state.json"
            record_path = vacancy_state / "records" / "vac-1.json"
            record_path.parent.mkdir(parents=True)
            record_path.write_text("{}", encoding="utf-8")

            first = record_application_event(
                state_path=state_path,
                vacancy_state=vacancy_state,
                vacancy_id="vac-1",
                status="APPLIED",
                occurred_at="2026-08-24T12:00:00-06:00",
                evidence_kind="EXTERNAL_RECORD",
                evidence_ref="private-email-message-id-123",
                recorded_by="tester",
            )
            duplicate = record_application_event(
                state_path=state_path,
                vacancy_state=vacancy_state,
                vacancy_id="vac-1",
                status="APPLIED",
                occurred_at="2026-08-24T12:00:00-06:00",
                evidence_kind="EXTERNAL_RECORD",
                evidence_ref="private-email-message-id-123",
                recorded_by="tester",
            )
            record_application_event(
                state_path=state_path,
                vacancy_state=vacancy_state,
                vacancy_id="vac-1",
                status="INTERVIEW",
                occurred_at="2026-08-25T10:00:00-06:00",
                evidence_kind="USER_CONFIRMED",
                recorded_by="tester",
            )
            state = json.loads(state_path.read_text(encoding="utf-8"))
            entry = state["entries"]["vac-1"]
            self.assertEqual(first["event_id"], duplicate["event_id"])
            self.assertEqual(len(entry["events"]), 2)
            self.assertEqual(entry["current_status"], "INTERVIEW")
            summary = summarize_entry(entry)
            self.assertTrue(summary["applied"])
            self.assertTrue(summary["interviewed"])
            self.assertFalse(summary["terminal"])
            persisted = state_path.read_text(encoding="utf-8")
            self.assertNotIn("private-email-message-id-123", persisted)
            self.assertIn("evidence_ref_sha256", persisted)

    def test_missing_application_event_remains_unknown_not_not_applied(self) -> None:
        summary = summarize_entry({})
        self.assertIsNone(summary["current_status"])
        self.assertFalse(summary["applied"])
        self.assertFalse(summary["explicitly_not_applied"])
        self.assertFalse(summary["terminal"])

    def test_provider_reconciliation_is_idempotent_hashes_reference_and_requires_dedicated_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "provider.json"
            with self.assertRaisesRegex(ValueError, "dedicated to CV_fit"):
                record_provider_statement(
                    state_path=path,
                    period_start="2026-08-24T00:00:00Z",
                    period_end="2026-08-25T00:00:00Z",
                    actual_cost_usd=1.2345,
                    scope_kind="MIXED_PROVIDER_ACCOUNT",
                    recorded_by="tester",
                )
            first = record_provider_statement(
                state_path=path,
                period_start="2026-08-24T00:00:00Z",
                period_end="2026-08-25T00:00:00Z",
                actual_cost_usd=1.2345,
                scope_kind="CV_FIT_DEDICATED_SCOPE",
                evidence_ref="invoice-secret-reference",
                recorded_by="tester",
            )
            second = record_provider_statement(
                state_path=path,
                period_start="2026-08-24T00:00:00Z",
                period_end="2026-08-25T00:00:00Z",
                actual_cost_usd=1.2345,
                scope_kind="CV_FIT_DEDICATED_SCOPE",
                evidence_ref="invoice-secret-reference",
                recorded_by="tester",
            )
            self.assertEqual(first["entry_id"], second["entry_id"])
            state = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(state["entries"]), 1)
            self.assertNotIn("invoice-secret-reference", path.read_text(encoding="utf-8"))
            self.assertEqual(first["currency"], "USD")
            self.assertEqual(first["scope_kind"], "CV_FIT_DEDICATED_SCOPE")

    def test_truth_validator_fails_closed_on_mixed_provider_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app = root / "application.json"
            provider = root / "provider.json"
            evidence = root / "decision.json"
            app.write_text(json.dumps({"schema_version": 1, "entries": {}}), encoding="utf-8")
            provider.write_text(json.dumps({"schema_version": 1, "entries": {"bad": {
                "scope_kind": "MIXED_PROVIDER_ACCOUNT",
                "source_kind": "PROVIDER_STATEMENT_USER_RECORDED",
            }}}), encoding="utf-8")
            evidence.write_text(json.dumps({"schema_version": 1, "spend_attribution": {}, "review_cycles": {}, "unpaired_revisions": {}}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "only CV_FIT_DEDICATED_SCOPE"):
                validate_decision_sources(
                    application_state_path=app,
                    provider_reconciliation_path=provider,
                    decision_evidence_path=evidence,
                )


if __name__ == "__main__":
    unittest.main()
