from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cv_presentation.feed_enhancements import (
    ENHANCEMENT_MARKER,
    PROCESS_METRICS_FILE,
    build_process_metrics,
    enhance_feed_index,
)


class FeedEnhancementTests(unittest.TestCase):
    def _write_json(self, path: Path, payload) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def _index_source(self) -> str:
        return """<!doctype html><html><head><style>.feed-post{display:block}</style></head><body>
        <section class=\"feed\">
          <article class=\"feed-post\" data-status=\"ready\" data-vacancy=\"vac-1\">
            <div class=\"post-body\"><div class=\"post-links\"></div></div>
            <div class=\"cv-gallery\">
              <section class=\"cv-tile\"><div class=\"cv-tile-head\"><h4>Technical Modern</h4></div><div class=\"cv-canvas\"><a class=\"cv-image-link\" href=\"vacancies/vac-1/cv_primary.html\"><img src=\"vacancies/vac-1/cv_primary.png\" alt=\"Technical Modern CV preview\"></a></div><div class=\"cv-actions\"><a href=\"vacancies/vac-1/cv_primary.html\">Open HTML</a><a href=\"vacancies/vac-1/cv_primary.pdf\">PDF</a></div></section>
              <section class=\"cv-tile\"><div class=\"cv-tile-head\"><h4>Harvard Executive</h4></div><div class=\"cv-canvas\"><a class=\"cv-image-link\" href=\"vacancies/vac-1/cv_alternate.html\"><img src=\"vacancies/vac-1/cv_alternate.png\" alt=\"Harvard Executive CV preview\"></a></div><div class=\"cv-actions\"><a href=\"vacancies/vac-1/cv_alternate.html\">Open HTML</a><a href=\"vacancies/vac-1/cv_alternate.pdf\">PDF</a></div></section>
            </div>
            <button data-review=\"SEND\">SEND</button>
          </article>
        </section>
        <button data-filter=\"all\">All</button><button data-filter=\"ready\">Ready</button>
        </body></html>"""

    def test_enhancement_adds_live_html_previews_search_and_truthful_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site = root / "site"
            site.mkdir()
            index = site / "index.html"
            index.write_text(self._index_source(), encoding="utf-8")
            manifest = root / "generation_state" / "manifest.json"
            self._write_json(manifest, {
                "entries": {
                    "vac-1": {
                        "status": "COMPLETED_BELOW_TARGET",
                        "ready_to_send": False,
                        "review_required": True,
                        "coverage_score": 84.6,
                        "estimated_cost_usd": 0.83062,
                        "unsupported_requirements": ["Temporal", "LangGraph"],
                        "content_quality_target_reached": False,
                        "retrieval_mode": "hybrid-rerank",
                        "generation_logic_version": 4,
                        "presentation_gate": {
                            "status": "REVIEW_REQUIRED",
                            "primary_template": "technical_modern_v1",
                            "cover_letter_ready": True,
                        },
                    }
                }
            })

            report = enhance_feed_index(site, generation_manifest_path=manifest)
            html = index.read_text(encoding="utf-8")
            process = json.loads((site / PROCESS_METRICS_FILE).read_text(encoding="utf-8"))
            row = process["entries"]["vac-1"]

            self.assertTrue(report["enhanced"])
            self.assertIn(ENHANCEMENT_MARKER, html)
            self.assertIn('id="vacancy-search"', html)
            self.assertIn('role="search"', html)
            self.assertIn('aria-live="polite"', html)
            self.assertIn("post.dataset.searchText", html)
            self.assertIn("aria-pressed", html)
            self.assertIn("Open CV to send", html)
            self.assertIn("Review recommended CV", html)
            self.assertIn("Review rounds", html)
            self.assertIn("Pipeline OpenAI cost", html)
            self.assertIn("Generation cost", html)
            self.assertIn("Cover-letter cost", html)
            self.assertIn("Presentation cost", html)
            self.assertIn("Cost coverage", html)
            self.assertIn("application_bundle_report.json", html)
            self.assertIn("upgradeHtmlPreviews", html)
            self.assertIn("cv-html-preview", html)
            self.assertIn("live HTML preview", html)
            self.assertIn("grid-template-columns:1fr!important", html)
            self.assertIn("value===null||value===undefined||value===''", html)
            self.assertIn("toFixed(4)", html)
            self.assertNotIn("page-divider", html)
            self.assertIn('button[data-review="SEND"].selected', html)
            self.assertIn('button[data-review="REVISE"].selected', html)
            self.assertIn('button[data-review="REJECT"].selected', html)
            self.assertEqual(row["headhunter_iterations"], 5)
            self.assertEqual(row["unsupported_requirements_count"], 2)
            self.assertEqual(row["coverage_score"], 84.6)
            self.assertEqual(row["generation_cost_usd"], 0.83062)
            self.assertEqual(row["total_pipeline_known_cost_usd"], 0.83062)
            self.assertFalse(row["total_pipeline_cost_complete"])
            self.assertNotIn("secret@example.com", html)

    def test_process_metrics_prefers_exact_headhunter_rounds_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "manifest.json"
            self._write_json(manifest, {
                "entries": {
                    "vac-pass": {
                        "status": "PASS",
                        "headhunter_iterations": 2,
                        "best_review_iteration": 2,
                        "headhunter_score": 96,
                        "premium_model_used": False,
                    }
                }
            })
            metrics = build_process_metrics(manifest)["entries"]["vac-pass"]
            self.assertEqual(metrics["headhunter_iterations"], 2)
            self.assertEqual(metrics["best_review_iteration"], 2)
            self.assertEqual(metrics["headhunter_score"], 96)
            self.assertFalse(metrics["premium_model_used"])

    def test_verified_history_recovery_fills_only_missing_observability(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site = root / "site"
            site.mkdir()
            (site / "index.html").write_text(self._index_source(), encoding="utf-8")
            generation = root / "generation_state"
            manifest = generation / "manifest.json"
            self._write_json(manifest, {
                "entries": {
                    "vac-1": {
                        "status": "FAILED_REVIEW_REQUIRED",
                        "ready_to_send": False,
                        "review_required": True,
                        "retrieval_mode": "hybrid-rerank",
                        "generation_logic_version": 5,
                    }
                }
            })
            self._write_json(generation / "recovered_metrics.json", {
                "entries": {
                    "vac-1": {
                        "coverage_score": 79.8,
                        "estimated_cost_usd": 0.9426075,
                        "generation_cost_usd": 0.9426075,
                        "unsupported_requirements_count": 0,
                        "headhunter_iterations": 5,
                    }
                }
            })

            enhance_feed_index(site, generation_manifest_path=manifest)
            row = json.loads((site / PROCESS_METRICS_FILE).read_text(encoding="utf-8"))["entries"]["vac-1"]
            self.assertEqual(row["status"], "FAILED_REVIEW_REQUIRED")
            self.assertEqual(row["coverage_score"], 79.8)
            self.assertEqual(row["generation_cost_usd"], 0.9426075)
            self.assertEqual(row["total_pipeline_known_cost_usd"], 0.9426075)
            self.assertFalse(row["total_pipeline_cost_complete"])
            self.assertEqual(row["metrics_origin"], "recovered_versioned_history")

    def test_enhancement_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            index = site / "index.html"
            index.write_text(
                "<html><head><style></style></head><body><section class=\"feed\"></section></body></html>",
                encoding="utf-8",
            )
            first = enhance_feed_index(site)
            first_html = index.read_text(encoding="utf-8")
            second = enhance_feed_index(site)
            second_html = index.read_text(encoding="utf-8")

            self.assertTrue(first["enhanced"])
            self.assertFalse(second["enhanced"])
            self.assertEqual(second["reason"], "already_enhanced")
            self.assertEqual(first_html, second_html)
            self.assertEqual(first_html.count(ENHANCEMENT_MARKER), 1)
            self.assertTrue((site / PROCESS_METRICS_FILE).exists())

    def test_missing_feed_markup_fails_loudly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            (site / "index.html").write_text(
                "<html><head><style></style></head><body><p>old layout</p></body></html>",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "vacancy feed markup"):
                enhance_feed_index(site)


if __name__ == "__main__":
    unittest.main()
