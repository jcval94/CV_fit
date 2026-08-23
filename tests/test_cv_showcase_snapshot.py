import json
import tempfile
import unittest
from pathlib import Path

from cv_presentation.showcase_snapshot import inherit_missing_bundles


class ShowcaseSnapshotTests(unittest.TestCase):
    def _write_json(self, path: Path, payload) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def _bundle(self):
        return {
            "ready_to_send": True,
            "templates": [
                {
                    "role": "primary",
                    "template_id": "technical_modern_v1",
                    "html_file": "cv_primary.html",
                    "pdf_file": "cv_primary.pdf",
                    "screenshot_file": "cv_primary.png",
                    "physical_report_file": "physical_primary.json",
                    "visual_status": "PASS",
                    "presentation_review_status": "PASS",
                    "expected_pages": 2,
                }
            ],
        }

    def test_inherits_public_assets_but_rebuilds_detail_with_current_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            current = root / "current"
            previous = root / "previous"
            vacancy_id = "vac-demo"
            current_row = {
                "vacancy_id": vacancy_id,
                "company": "Current Co",
                "role_title": "Current Role",
                "url": "https://example.com/current",
                "fit_score": 91,
                "jd_fidelity": "full",
                "source_date": "2026-08-22",
            }
            previous_row = {
                **current_row,
                "company": "Old Co",
                "role_title": "Old Role",
                "url": "https://example.com/old",
                "primary_html_file": "cv_primary.html",
                "primary_pdf_file": "cv_primary.pdf",
                "primary_screenshot_file": "cv_primary.png",
                "rag_coverage": 0.88,
                "ready_to_send": True,
            }
            self._write_json(current / "showcase.json", {"vacancies": [current_row], "generated_count": 0, "ready_count": 0})
            self._write_json(previous / "showcase.json", {"vacancies": [previous_row]})
            previous_vacancy = previous / "vacancies" / vacancy_id
            previous_vacancy.mkdir(parents=True)
            self._write_json(previous_vacancy / "application_bundle_report.json", self._bundle())
            (previous_vacancy / "cv_primary.html").write_text("CURRENT CV BODY", encoding="utf-8")
            (previous_vacancy / "cv_primary.pdf").write_bytes(b"pdf")
            (previous_vacancy / "cv_primary.png").write_bytes(b"png")
            (previous_vacancy / "physical_primary.json").write_text("{}", encoding="utf-8")
            (previous_vacancy / "index.html").write_text("STALE DETAIL PAGE", encoding="utf-8")

            result = inherit_missing_bundles(site_dir=current, previous_site_dir=previous)

            self.assertEqual(result, {"inherited_count": 1, "vacancy_ids": [vacancy_id]})
            detail = (current / "vacancies" / vacancy_id / "index.html").read_text(encoding="utf-8")
            self.assertIn("Current Co", detail)
            self.assertIn("Current Role", detail)
            self.assertIn("https://example.com/current", detail)
            self.assertNotIn("STALE DETAIL PAGE", detail)
            self.assertTrue((current / "vacancies" / vacancy_id / "cv_primary.html").is_file())
            showcase = json.loads((current / "showcase.json").read_text(encoding="utf-8"))
            self.assertEqual(showcase["generated_count"], 1)
            self.assertEqual(showcase["ready_count"], 1)
            self.assertEqual(showcase["vacancies"][0]["artifact_source"], "inherited_previous_showcase")
            self.assertEqual(showcase["vacancies"][0]["company"], "Current Co")

    def test_does_not_overwrite_current_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            current = root / "current"
            previous = root / "previous"
            vacancy_id = "vac-demo"
            row = {"vacancy_id": vacancy_id, "primary_html_file": "cv_primary.html"}
            self._write_json(current / "showcase.json", {"vacancies": [row]})
            self._write_json(previous / "showcase.json", {"vacancies": [row]})
            current_dir = current / "vacancies" / vacancy_id
            previous_dir = previous / "vacancies" / vacancy_id
            current_dir.mkdir(parents=True)
            previous_dir.mkdir(parents=True)
            (current_dir / "cv_primary.html").write_text("new", encoding="utf-8")
            (previous_dir / "cv_primary.html").write_text("old", encoding="utf-8")

            result = inherit_missing_bundles(site_dir=current, previous_site_dir=previous)

            self.assertEqual(result["inherited_count"], 0)
            self.assertEqual((current_dir / "cv_primary.html").read_text(encoding="utf-8"), "new")


if __name__ == "__main__":
    unittest.main()
