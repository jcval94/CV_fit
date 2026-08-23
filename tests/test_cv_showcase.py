from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cv_presentation.showcase import build_showcase, refresh_existing_showcase
from tests.test_cv_showcase_snapshot import ShowcaseSnapshotTests


class ShowcaseTests(unittest.TestCase):
    def _write_json(self, path: Path, payload) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def _fixture(self, root: Path) -> tuple[Path, Path, Path, Path, str]:
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
        self._write_json(run_dir / "run_report.json", {"match_coverage_score": 84.2, "final_review": {"overall_score": 94}})
        bundle = {
            "vacancy_id": vacancy_id,
            "company": "Example Co",
            "role_title": "Senior Data Scientist",
            "application_url": "https://example.com/jobs/1",
            "ready_to_send": True,
            "templates": [
                {"role": "primary", "template_id": "branded_modern_v1", "html_file": "cv_primary.html", "pdf_file": "cv_primary.pdf", "screenshot_file": "cv_primary.png", "fit_report_file": "fit_report_primary.json", "design_report_file": "design_report_primary.json", "physical_report_file": "physical_layout_primary.json", "physical_status": "PASS", "expected_pages": 2},
                {"role": "alternate", "template_id": "harvard_v1", "html_file": "cv_alternate.html", "pdf_file": "cv_alternate.pdf", "screenshot_file": "cv_alternate.png", "fit_report_file": "fit_report_alternate.json", "design_report_file": "design_report_alternate.json", "physical_report_file": "physical_layout_alternate.json", "physical_status": "PASS", "expected_pages": 2},
            ],
        }
        self._write_json(run_dir / "application_bundle_report.json", bundle)
        batch = root / "batch.json"
        self._write_json(batch, {"results": [{"vacancy_id": vacancy_id, "run_id": run_id, "status": "PASS"}]})
        return vacancy_state, outputs, site, batch, vacancy_id

    def test_showcase_is_vertical_feed_with_vacancy_and_two_cv_previews(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vacancy_state, outputs, site, batch, vacancy_id = self._fixture(root)
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
            showcase = json.loads((site / "showcase.json").read_text(encoding="utf-8"))

            self.assertIn("CV_fit Review Feed", index)
            self.assertIn("Today's vacancies and generated CVs", index)
            self.assertIn("Example Co", index)
            self.assertIn("Senior Data Scientist", index)
            self.assertIn("View vacancy", index)
            self.assertIn("https://example.com/jobs/1", index)
            self.assertIn("Branded CV", index)
            self.assertIn("Harvard Executive", index)
            self.assertIn("cv_primary.png", index)
            self.assertIn("cv_alternate.png", index)
            self.assertIn("cv_primary.html", index)
            self.assertIn("cv_alternate.html", index)
            self.assertIn("cv_primary.pdf", index)
            self.assertIn("cv_alternate.pdf", index)
            self.assertIn("Source fit", index)
            self.assertIn("RAG coverage", index)
            self.assertIn("Headhunter", index)
            self.assertIn("data-filter=\"ready\"", index)
            self.assertIn("data-filter=\"review\"", index)
            self.assertIn("data-review=\"SEND\"", index)
            self.assertIn("data-review=\"REVISE\"", index)
            self.assertIn("data-review=\"REJECT\"", index)
            self.assertIn("localStorage", index)
            self.assertIn("cvfit-human-review:", index)
            self.assertIn("cv_primary.html", detail)
            self.assertIn("cv_alternate.html", detail)
            self.assertEqual(showcase["view"], "vacancy_cv_feed")
            self.assertNotIn("email", index.casefold())
            self.assertTrue((site / ".nojekyll").exists())

    def test_existing_pages_artifact_can_be_refreshed_without_cv_regeneration(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp) / "site"
            vacancy_dir = site / "vacancies" / "vac-old"
            vacancy_dir.mkdir(parents=True)
            for name in ("cv_primary.html", "cv_alternate.html", "cv_primary.pdf", "cv_alternate.pdf", "cv_primary.png", "cv_alternate.png"):
                (vacancy_dir / name).write_bytes(b"artifact")
            (vacancy_dir / "index.html").write_text("old details", encoding="utf-8")
            self._write_json(site / "showcase.json", {
                "date": "2026-08-21",
                "vacancies": [{
                    "vacancy_id": "vac-old",
                    "company": "Old Artifact Co",
                    "role_title": "ML Engineer",
                    "url": "https://example.com/old",
                    "fit_score": 90,
                    "jd_fidelity": "full",
                    "generation_status": "READY",
                    "ready_to_send": True,
                    "has_branded_html": True,
                    "has_harvard_html": True,
                }],
            })
            (site / "index.html").write_text("legacy grid", encoding="utf-8")

            report = refresh_existing_showcase(site)
            index = (site / "index.html").read_text(encoding="utf-8")
            payload = json.loads((site / "showcase.json").read_text(encoding="utf-8"))

            self.assertEqual(report["vacancy_count"], 1)
            self.assertIn("CV_fit Review Feed", index)
            self.assertIn("Old Artifact Co", index)
            self.assertIn("View vacancy", index)
            self.assertIn("cv_primary.png", index)
            self.assertIn("cv_alternate.png", index)
            self.assertEqual(payload["view"], "vacancy_cv_feed")
            self.assertEqual((vacancy_dir / "cv_primary.html").read_bytes(), b"artifact")
            self.assertEqual((vacancy_dir / "index.html").read_text(encoding="utf-8"), "old details")


if __name__ == "__main__":
    unittest.main()
