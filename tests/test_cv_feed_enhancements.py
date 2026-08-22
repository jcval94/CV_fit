from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cv_presentation.feed_enhancements import ENHANCEMENT_MARKER, enhance_feed_index


class FeedEnhancementTests(unittest.TestCase):
    def test_enhancement_adds_search_accessibility_and_local_decision_styles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            index = site / "index.html"
            index.write_text(
                """<!doctype html><html><head><style>.feed-post{display:block}</style></head><body>
                <section class=\"feed\">
                  <article class=\"feed-post\" data-status=\"ready\" data-vacancy=\"vac-1\">
                    <h2>Example Company</h2><h3>Senior Data Scientist</h3>
                    <button data-review=\"SEND\">SEND</button>
                  </article>
                </section>
                <button data-filter=\"all\">All</button><button data-filter=\"ready\">Ready</button>
                </body></html>""",
                encoding="utf-8",
            )

            report = enhance_feed_index(site)
            html = index.read_text(encoding="utf-8")

            self.assertTrue(report["enhanced"])
            self.assertIn(ENHANCEMENT_MARKER, html)
            self.assertIn('id="vacancy-search"', html)
            self.assertIn('role="search"', html)
            self.assertIn('aria-live="polite"', html)
            self.assertIn("post.dataset.searchText", html)
            self.assertIn("aria-pressed", html)
            self.assertIn('button[data-review="SEND"].selected', html)
            self.assertIn('button[data-review="REVISE"].selected', html)
            self.assertIn('button[data-review="REJECT"].selected', html)
            self.assertNotIn("secret@example.com", html)

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
