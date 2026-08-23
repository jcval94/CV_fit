from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cv_presentation.p0_decision_ux import P0_UX_MARKER, apply_p0_decision_ux


class P0DecisionUxTests(unittest.TestCase):
    def _index(self) -> str:
        return """<!doctype html><html><head><style>
        .feed-post{display:block}.process-metrics{display:grid}
        </style></head><body>
        <article class=\"feed-post\" data-status=\"review\" data-vacancy=\"vac-1\">
          <header class=\"post-head\"><a class=\"vacancy-cta\" href=\"#\">View vacancy</a></header>
          <div class=\"post-body\">
            <div class=\"fit-strip\"></div>
            <p class=\"post-summary\">Strong fit summary.</p>
            <div class=\"post-links\"><a class=\"cv-send-cta\" href=\"cv.html\">Open CV</a></div>
            <div class=\"process-metrics\"></div>
          </div>
          <div class=\"cv-gallery\">
            <section class=\"cv-tile\"><div class=\"cv-canvas\"></div></section>
            <section class=\"cv-tile\"><div class=\"cv-canvas\"></div></section>
          </div>
          <footer class=\"post-review\">
            <div><strong>Human decision</strong><span class=\"local-note\">local</span></div>
            <div class=\"feed-review-actions\">
              <button data-review=\"SEND\">SEND</button>
              <button data-review=\"REVISE\">REVISE</button>
              <button data-review=\"REJECT\">REJECT</button>
              <span data-review-current></span>
            </div>
          </footer>
        </article>
        </body></html>"""

    def test_layer_adds_all_p0_contracts_without_removing_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            index = site / "index.html"
            index.write_text(self._index(), encoding="utf-8")

            report = apply_p0_decision_ux(site)
            html = index.read_text(encoding="utf-8")

            self.assertTrue(report["applied"])
            self.assertIn(P0_UX_MARKER, html)

            # P0: dominant recommendation.
            self.assertIn("Application recommendation", html)
            self.assertIn("Ready to apply with the recommended CV", html)
            self.assertIn("Review before applying", html)
            self.assertIn("Do not apply with this artifact yet", html)

            # P0 with user's constraint: several metrics stay visible, but hierarchical.
            self.assertIn("decision-metrics", html)
            self.assertIn("supporting-metrics", html)
            self.assertIn("Source fit", html)
            self.assertIn("Headhunter", html)
            self.assertIn("RAG coverage", html)
            self.assertIn("Unsupported gaps", html)
            self.assertIn("Pipeline cost", html)
            self.assertIn("Review rounds", html)
            self.assertIn("Generation cost", html)
            self.assertIn("Cover cost", html)
            self.assertIn("Presentation cost", html)
            self.assertIn(".fit-strip,.process-metrics{display:none!important}", html)

            # P0: recommended CV only by default, alternate available on demand.
            self.assertIn("alternate-cv", html)
            self.assertIn("Compare alternate CV", html)
            self.assertIn("aria-expanded", html)
            self.assertIn("Harvard Executive stays available", html)

            # P0: one clear primary decision action.
            self.assertIn("Approve CV", html)
            self.assertIn("Needs edits", html)
            self.assertIn("Dismiss", html)
            self.assertIn('button[data-review="SEND"]{background:var(--blue)!important', html)
            self.assertIn("Open recommended CV", html)
            self.assertIn("Application decision", html)

    def test_layer_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            index = site / "index.html"
            index.write_text(self._index(), encoding="utf-8")
            first = apply_p0_decision_ux(site)
            once = index.read_text(encoding="utf-8")
            second = apply_p0_decision_ux(site)
            twice = index.read_text(encoding="utf-8")
            self.assertTrue(first["applied"])
            self.assertFalse(second["applied"])
            self.assertEqual(second["reason"], "already_applied")
            self.assertEqual(once, twice)
            self.assertEqual(twice.count(P0_UX_MARKER), 1)

    def test_missing_index_fails_loudly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                apply_p0_decision_ux(Path(tmp))


if __name__ == "__main__":
    unittest.main()
