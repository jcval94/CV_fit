from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cv_presentation.showcase import build_showcase


class ShowcaseTests(unittest.TestCase):
    def _write_json(self, path: Path, payload) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def test_showcase_links_vacancy_branded_and_harvard_html_without_private_contact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vacancy_id = "vac-demo"
            vacancy_state = root / "vacancy_state"
            outputs = root / "outputs"
            site = root / "site"
            run_id = "run-1"
            run_dir = outputs / vacancy_id / run_id
            self._write_json(vacancy_state / "records" / f"{vacancy_id}.json", {
                "vacancy_id": vacancy_id,
                "company": "Example Co",
                "role_title": "Senior Data Scientist",
                "url": "https://example.com/jobs/1",
                "fit_score": 93,
                "fit_summary": "Strong source fit.",
                "jd_fidelity": "full",
                "work_model": "Remote",
                "location_raw": "Mexico",
                "provenance": [{"source_search_date": "2026-08-21"}],
            })
            run_dir.mkdir(parents=True)
            for name in ("cv_primary.html", "cv_alternate.html", "cv_primary.pdf", "cv_alternate.pdf"):
                (run_dir / name).write_text("public artifact", encoding="utf-8")
            for name in ("cv_primary.png", "cv_alternate.png"):
                (run_dir / name).write_bytes(b"png")
            for name in (
                "fit_report_primary.json", "fit_report_alternate.json",
                "design_report_primary.json", "design_report_alternate.json",
                "physical_layout_primary.json", "physical_layout_alternate.json",
            ):
                self._write_json(run_dir / name, {"status": "PASS"})
            (run_dir / "cover_letter_final.md").write_text("Dear Hiring Team", encoding="utf-8")
            self._write_json(run_dir / "run_report.json", {"match_coverage_score": 84.2})
            bundle = {
                "vacancy_id": vacancy_id,
                "company": "Example Co",
                "role_title": "Senior Data Scientist",
                "application_url": "https://example.com/jobs/1",
                "ready_to_send": True,
                "templates": [
                    {"role": "primary", "html_file": "cv_primary.html", "pdf_file": "cv_primary.pdf", "screenshot_file": "cv_primary.png", "fit_report_file": "fit_report_primary.json", "design_report_file": "design_report_primary.json", "physical_report_file": "physical_layout_primary.json", "physical_status": "PASS", "expected_pages": 2},
                    {"role": "alternate", "html_file": "cv_alternate.html", "pdf_file": "cv_alternate.pdf", "screenshot_file": "cv_alternate.png", "fit_report_file": "fit_report_alternate.json", "design_report_file": "design_report_alternate.json", "physical_report_file": "physical_layout_alternate.json", "physical_status": "PASS", "expected_pages": 2},
                ],
            }
            self._write_json(run_dir / "application_bundle_report.json", bundle)
            batch = root / "batch.json"
            self._write_json(batch, {"results": [{"vacancy_id": vacancy_id, "run_id": run_id, "status": "PASS"}]})

            report = build_showcase(
                target_date="2026-08-21",
                vacancy_state=vacancy_state,
                bundle_batch_report=batch,
                outputs=outputs,
                site_dir=site,
            )
            self.assertEqual(report["vacancy_count"], 1)
            self.assertEqual(report["ready_count"], 1)
            index = (site / "index.html").read_text(encoding="utf-8")
            detail = (site / "vacancies" / vacancy_id / "index.html").read_text(encoding="utf-8")
            self.assertIn("Branded HTML", index)
            self.assertIn("Harvard HTML", index)
            self.assertIn("https://example.com/jobs/1", detail)
            self.assertIn("cv_primary.html", detail)
            self.assertIn("cv_alternate.html", detail)
            self.assertNotIn("email", index.casefold())
            self.assertTrue((site / ".nojekyll").exists())


if __name__ == "__main__":
    unittest.main()
