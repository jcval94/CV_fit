from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cv_presentation.showcase import build_showcase, refresh_existing_showcase


class ShowcaseTests(unittest.TestCase):
    def _write_json(self, path: Path, payload) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def test_showcase_v2_builds_social_style_vacancy_feed_with_both_cvs(self):
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
                "visual_eval_primary.json", "visual_eval_alternate.json",
                "presentation_review_primary.json", "presentation_review_alternate.json",
            ):
                self._write_json(run_dir / name, {"status": "PASS"})
            (run_dir / "cover_letter_final.md").write_text("Dear Hiring Team", encoding="utf-8")
            self._write_json(run_dir / "run_report.json", {
                "match_coverage_score": 84.2,
                "final_review": {"overall_score": 94},
                "final_validation": {
                    "factual": {"status": "PASS"},
                    "editorial": {"status": "PASS"},
                    "language": {"status": "PASS"},
                },
            })
            primary = {
                "role": "primary",
                "template_id": "technical_modern_v1",
                "html_file": "cv_primary.html",
                "pdf_file": "cv_primary.pdf",
                "screenshot_file": "cv_primary.png",
                "fit_report_file": "fit_report_primary.json",
                "design_report_file": "design_report_primary.json",
                "physical_report_file": "physical_layout_primary.json",
                "visual_eval_file": "visual_eval_primary.json",
                "presentation_review_file": "presentation_review_primary.json",
                "physical_status": "PASS",
                "visual_status": "PASS",
                "presentation_review_status": "PASS",
                "expected_pages": 2,
                "page_utilization": [0.84, 0.73],
                "section_area_ratios": {"experience": 0.58, "education": 0.08, "projects": 0.14, "skills": 0.10, "certifications": 0.10},
                "section_item_counts": {"experience": 3, "education": 2, "projects": 1, "skills": 12, "certifications": 3},
            }
            alternate = dict(primary)
            alternate.update({
                "role": "alternate",
                "template_id": "harvard_v1",
                "html_file": "cv_alternate.html",
                "pdf_file": "cv_alternate.pdf",
                "screenshot_file": "cv_alternate.png",
                "fit_report_file": "fit_report_alternate.json",
                "design_report_file": "design_report_alternate.json",
                "physical_report_file": "physical_layout_alternate.json",
                "visual_eval_file": "visual_eval_alternate.json",
                "presentation_review_file": "presentation_review_alternate.json",
            })
            bundle = {
                "schema_version": 2,
                "vacancy_id": vacancy_id,
                "company": "Example Co",
                "role_title": "Senior Data Scientist",
                "application_url": "https://example.com/jobs/1",
                "ready_to_send": True,
                "templates": [primary, alternate],
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
            self.assertEqual(report["generated_count"], 1)
            self.assertEqual(report["ready_count"], 1)
            index = (site / "index.html").read_text(encoding="utf-8")
            detail = (site / "vacancies" / vacancy_id / "index.html").read_text(encoding="utf-8")
            showcase = json.loads((site / "showcase.json").read_text(encoding="utf-8"))

            # Feed home: vacancy + two CV previews in one post.
            self.assertIn("CV_fit Review Feed", index)
            self.assertIn("Today's vacancies and generated CVs", index)
            self.assertIn("Example Co", index)
            self.assertIn("Senior Data Scientist", index)
            self.assertIn("https://example.com/jobs/1", index)
            self.assertIn("View vacancy", index)
            self.assertIn("Technical Modern", index)
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

            # Human decisions can be made without opening the detail page and stay local.
            self.assertIn("Human decision", index)
            self.assertIn("data-review=\"SEND\"", index)
            self.assertIn("data-review=\"REVISE\"", index)
            self.assertIn("data-review=\"REJECT\"", index)
            self.assertIn("localStorage", index)
            self.assertIn("cvfit-human-review:", index)

            # Detailed metrics and reports remain available.
            self.assertIn("Experience area", detail)
            self.assertIn("58%", detail)
            self.assertIn("Page 1 use", detail)
            self.assertIn("84%", detail)
            self.assertIn("Human review — local browser only", detail)
            self.assertIn("cvfit-human-review:vac-demo", detail)
            self.assertIn("visual_eval_primary.json", detail)
            self.assertIn("presentation_review_primary.json", detail)

            self.assertEqual(showcase["schema_version"], 2)
            self.assertEqual(showcase["view"], "vacancy_cv_feed")
            self.assertEqual(showcase["vacancies"][0]["primary_visual_status"], "PASS")
            self.assertEqual(showcase["vacancies"][0]["section_item_counts"]["skills"], 12)
            self.assertNotIn("secret@example.com", index)
            self.assertTrue((site / ".nojekyll").exists())


    def test_review_required_bundle_remains_sendable_and_exposes_quality_kpi(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vacancy_id = "vac-review"
            vacancy_state = root / "vacancy_state"
            outputs = root / "outputs"
            site = root / "site"
            run_id = "run-review"
            run_dir = outputs / vacancy_id / run_id

            self._write_json(vacancy_state / "records" / f"{vacancy_id}.json", {
                "vacancy_id": vacancy_id,
                "company": "Review Co",
                "role_title": "Senior ML Engineer",
                "url": "https://example.com/jobs/review",
                "fit_score": 97,
                "fit_summary": "Strong fit but below the automated quality target.",
                "jd_fidelity": "full",
                "provenance": [{"source_search_date": "2026-08-26"}],
            })
            run_dir.mkdir(parents=True)
            for name in ("primary.html", "alternate.html", "primary.pdf", "alternate.pdf"):
                (run_dir / name).write_text("artifact", encoding="utf-8")
            self._write_json(run_dir / "run_report.json", {
                "match_coverage_score": 81.3,
                "final_review": {"overall_score": 80},
                "final_validation": {},
            })
            primary = {
                "role": "primary",
                "html_file": "primary.html",
                "pdf_file": "primary.pdf",
                "physical_status": "PASS",
                "visual_status": "PASS",
                "presentation_review_status": "PASS",
                "expected_pages": 2,
            }
            alternate = {
                "role": "alternate",
                "html_file": "alternate.html",
                "pdf_file": "alternate.pdf",
                "physical_status": "PASS",
                "visual_status": "PASS",
                "presentation_review_status": "PASS",
                "expected_pages": 2,
            }
            self._write_json(run_dir / "application_bundle_report.json", {
                "ready_to_send": False,
                "templates": [primary, alternate],
            })
            batch = root / "batch.json"
            self._write_json(batch, {
                "results": [{
                    "vacancy_id": vacancy_id,
                    "run_id": run_id,
                    "status": "REVIEW_REQUIRED",
                    "ready_to_send": False,
                }]
            })

            report = build_showcase(
                target_date="2026-08-26",
                vacancy_state=vacancy_state,
                bundle_batch_report=batch,
                outputs=outputs,
                site_dir=site,
            )
            self.assertEqual(report["generated_count"], 1)
            self.assertEqual(report["ready_count"], 0)

            index = (site / "index.html").read_text(encoding="utf-8")
            payload = json.loads((site / "showcase.json").read_text(encoding="utf-8"))
            row = payload["vacancies"][0]

            self.assertIn("SENDABLE · REVIEW ADVISED", index)
            self.assertIn("Quality KPI", index)
            self.assertIn("80/100", index)
            self.assertIn("primary.html", index)
            self.assertIn("primary.pdf", index)
            self.assertTrue(row["sendable"])
            self.assertFalse(row["ready_to_send"])
            self.assertEqual(row["quality_score"], 80)

            refreshed = refresh_existing_showcase(site)
            self.assertEqual(refreshed["sendable_count"], 1)
            self.assertEqual(refreshed["ready_count"], 0)


if __name__ == "__main__":
    unittest.main()
