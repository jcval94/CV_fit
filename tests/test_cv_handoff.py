from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cv_handoff.builder import build_handoffs, rebuild_index


class WorkHandoffTests(unittest.TestCase):
    def _write_json(self, path: Path, payload) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def test_builder_creates_public_safe_final_review_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vacancy_id = "vac-demo"
            run_id = "run-1"
            outputs = root / "outputs"
            run_dir = outputs / vacancy_id / run_id
            vacancy_state = root / "vacancy_state"
            handoff = root / "handoff"
            template = root / "technical_modern_v1.html.j2"
            template.write_text("<html>{{ cv }}</html>", encoding="utf-8")

            self._write_json(vacancy_state / "records" / f"{vacancy_id}.json", {
                "vacancy_id": vacancy_id,
                "company": "Example Co",
                "role_title": "Senior Data Scientist",
                "url": "https://example.com/jobs/1",
                "fit_score": 97,
                "jd_fidelity": "full",
                "description": "Build production data science systems.",
                "requirements": ["Python", "ML"],
                "responsibilities": ["Own models"],
                "email": "private@example.com",
                "provenance": [{"source_search_date": "2026-08-27"}],
            })
            self._write_json(run_dir / "cv_final.json", {
                "headline": "Senior Data Scientist",
                "email": "private@example.com",
                "experience": [{"company": "BBVA", "phone": "555"}],
            })
            self._write_json(run_dir / "run_report.json", {
                "final_review": {"overall_score": 81},
            })
            (run_dir / "cv_primary.html").write_text("<html>proposal</html>", encoding="utf-8")
            self._write_json(run_dir / "application_bundle_report.json", {
                "ready_to_send": False,
                "templates": [{
                    "role": "primary",
                    "html_file": "cv_primary.html",
                }],
            })
            batch = root / "batch.json"
            self._write_json(batch, {
                "results": [{
                    "vacancy_id": vacancy_id,
                    "run_id": run_id,
                    "status": "REVIEW_REQUIRED",
                }]
            })

            report = build_handoffs(
                batch_report=batch,
                outputs=outputs,
                vacancy_state=vacancy_state,
                template_file=template,
                handoff_dir=handoff,
                repository="jcval94/CV_fit",
            )

            self.assertEqual(report["built"], [vacancy_id])
            package = handoff / vacancy_id
            for name in (
                "vacancy.md",
                "vacancy.json",
                "cv_proposed.json",
                "cv_proposed.html",
                "html_base.html.j2",
                "prompt.md",
                "handoff.json",
            ):
                self.assertTrue((package / name).exists(), name)

            proposed = json.loads((package / "cv_proposed.json").read_text(encoding="utf-8"))
            vacancy = json.loads((package / "vacancy.json").read_text(encoding="utf-8"))
            manifest = json.loads((package / "handoff.json").read_text(encoding="utf-8"))
            index = json.loads((handoff / "index.json").read_text(encoding="utf-8"))

            self.assertNotIn("email", proposed)
            self.assertNotIn("phone", proposed["experience"][0])
            self.assertNotIn("email", vacancy)
            self.assertEqual(manifest["quality_kpi"], 81)
            self.assertEqual(manifest["status"], "pending_final_review")
            self.assertEqual(manifest["source_fit"], 97)
            self.assertIn("Final CV review", (package / "prompt.md").read_text(encoding="utf-8"))
            self.assertEqual(index["pending_count"], 1)

    def test_existing_final_html_is_preserved_as_finalized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            handoff = Path(tmp) / "handoff"
            package = handoff / "vac-existing"
            package.mkdir(parents=True)
            (package / "final.html").write_text("<html>final</html>", encoding="utf-8")
            self._write_json(package / "handoff.json", {
                "vacancy_id": "vac-existing",
                "company": "Existing",
                "source_fit": 90,
                "status": "finalized",
            })
            payload = rebuild_index(handoff)
            self.assertEqual(payload["finalized_count"], 1)
            self.assertEqual(payload["pending_count"], 0)


if __name__ == "__main__":
    unittest.main()
