from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cv_notifications.whatsapp import (
    build_template_payload,
    reserve_notifications,
    send_reserved_notifications,
)


class WhatsAppNotificationTests(unittest.TestCase):
    def _write_json(self, path: Path, payload) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def _site(self, root: Path) -> Path:
        site = root / "site"
        site.mkdir()
        self._write_json(site / "showcase.json", {
            "vacancies": [
                {
                    "vacancy_id": "vac-ready",
                    "company": "Acme",
                    "role_title": "Senior Data Scientist",
                    "url": "https://jobs.example/acme-ds",
                    "fit_score": 94,
                    "ready_to_send": True,
                },
                {
                    "vacancy_id": "vac-review",
                    "company": "Beta",
                    "role_title": "ML Engineer",
                    "url": "https://jobs.example/beta-ml",
                    "fit_score": 80,
                    "ready_to_send": False,
                },
            ]
        })
        self._write_json(site / "process_metrics.json", {
            "entries": {
                "vac-ready": {"headhunter_score": 96, "coverage_score": 91.5},
            }
        })
        bundle_dir = site / "vacancies" / "vac-ready"
        bundle_dir.mkdir(parents=True)
        self._write_json(bundle_dir / "application_bundle_report.json", {
            "templates": [
                {"role": "primary", "html_file": "cv_primary.html"},
                {"role": "alternate", "html_file": "cv_alternate.html"},
            ]
        })
        (bundle_dir / "cv_primary.html").write_text("<html>primary</html>", encoding="utf-8")
        return site

    def test_reserve_only_ready_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site = self._site(root)
            state = root / "state.json"
            plan = root / "plan.json"

            first = reserve_notifications(
                site_dir=site,
                state_path=state,
                plan_path=plan,
                page_url="https://jcval94.github.io/CV_fit/",
                recipient="5215555555555",
            )
            second = reserve_notifications(
                site_dir=site,
                state_path=state,
                plan_path=plan,
                page_url="https://jcval94.github.io/CV_fit/",
                recipient="5215555555555",
            )

            self.assertEqual(first["count"], 1)
            item = first["notifications"][0]
            self.assertEqual(item["vacancy_id"], "vac-ready")
            self.assertEqual(item["headhunter_score"], "96")
            self.assertEqual(item["rag_coverage"], "91.5")
            self.assertTrue(item["cv_url"].endswith("/vacancies/vac-ready/cv_primary.html"))
            self.assertEqual(second["count"], 0)
            state_payload = json.loads(state.read_text(encoding="utf-8"))
            entry = next(iter(state_payload["entries"].values()))
            self.assertEqual(entry["status"], "RESERVED")
            self.assertNotIn("5215555555555", state.read_text(encoding="utf-8"))

    def test_changed_cv_gets_new_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site = self._site(root)
            state = root / "state.json"
            plan = root / "plan.json"
            first = reserve_notifications(
                site_dir=site,
                state_path=state,
                plan_path=plan,
                page_url="https://example.pages",
                recipient="5215555555555",
            )
            cv = site / "vacancies" / "vac-ready" / "cv_primary.html"
            cv.write_text("<html>changed</html>", encoding="utf-8")
            second = reserve_notifications(
                site_dir=site,
                state_path=state,
                plan_path=plan,
                page_url="https://example.pages",
                recipient="5215555555555",
            )
            self.assertEqual(first["count"], 1)
            self.assertEqual(second["count"], 1)
            self.assertNotEqual(first["notifications"][0]["fingerprint"], second["notifications"][0]["fingerprint"])

    def test_template_payload_contains_expected_seven_variables(self) -> None:
        payload = build_template_payload(
            notification={
                "company": "Acme",
                "role_title": "Senior DS",
                "source_fit": "94",
                "headhunter_score": "96",
                "rag_coverage": "91.5",
                "cv_url": "https://example/cv",
                "vacancy_url": "https://example/job",
                "template_name": "cv_fit_opportunity_ready",
                "template_language": "es_MX",
            },
            recipient="5215555555555",
        )
        self.assertEqual(payload["messaging_product"], "whatsapp")
        self.assertEqual(payload["type"], "template")
        self.assertEqual(payload["template"]["name"], "cv_fit_opportunity_ready")
        params = payload["template"]["components"][0]["parameters"]
        self.assertEqual(len(params), 7)
        self.assertEqual(params[0]["text"], "Acme")
        self.assertEqual(params[5]["text"], "https://example/cv")
        self.assertEqual(params[6]["text"], "https://example/job")

    def test_successful_send_marks_state_sent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site = self._site(root)
            state = root / "state.json"
            plan = root / "plan.json"
            reserve_notifications(
                site_dir=site,
                state_path=state,
                plan_path=plan,
                page_url="https://example.pages",
                recipient="5215555555555",
            )
            with patch("cv_notifications.whatsapp._post_json", return_value={"messages": [{"id": "wamid.test"}]}) as post:
                report = send_reserved_notifications(
                    state_path=state,
                    plan_path=plan,
                    access_token="secret-token",
                    phone_number_id="12345",
                    recipient="5215555555555",
                    graph_version="v23.0",
                )
            self.assertEqual(report["result_counts"].get("SENT"), 1)
            self.assertIn("/v23.0/12345/messages", post.call_args.kwargs["url"])
            state_payload = json.loads(state.read_text(encoding="utf-8"))
            entry = next(iter(state_payload["entries"].values()))
            self.assertEqual(entry["status"], "SENT")
            self.assertEqual(entry["provider_message_id"], "wamid.test")
            self.assertNotIn("secret-token", state.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
