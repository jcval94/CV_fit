from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cv_presentation.history_merge import merge_showcase_history
from cv_presentation.manual_send_status import apply_manual_send_status


class SevenDayHistoryTests(unittest.TestCase):
    def _write_json(self, path: Path, payload) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def _snapshot(self, root: Path, name: str, day: str, vacancy_id: str, *, generated: bool = True) -> Path:
        site = root / name
        vacancy = site / "vacancies" / vacancy_id
        vacancy.mkdir(parents=True)
        if generated:
            (vacancy / "cv_primary.html").write_text("<html>cv</html>", encoding="utf-8")
            cv = (
                f'<section class="cv-tile"><div class="cv-tile-head"><h4>Technical Modern</h4></div>'
                f'<div class="cv-canvas"><a class="cv-image-link" href="vacancies/{vacancy_id}/cv_primary.html">CV</a></div>'
                f'<div class="cv-actions"><a href="vacancies/{vacancy_id}/cv_primary.html">Open HTML</a></div></section>'
            )
        else:
            cv = '<section class="cv-tile unavailable"><div class="cv-empty">not generated</div></section>'
        detail = f'''<html><head><style></style></head><body>
        <div class="review-box"><strong>Human review — local browser only</strong>
        <div class="review-actions"><button data-decision="SEND">Mark send</button><button data-decision="REVISE">Mark revise</button></div>
        <span id="human-review">not reviewed</span></div></body></html>'''
        (vacancy / "index.html").write_text(detail, encoding="utf-8")
        index = f'''<!doctype html><html><head><style>.feed-post{{display:block}}</style></head><body>
        <div class="topbar"><small>{day} · vacancy-to-CV pipeline</small>
          <span class="top-stat">1 vacancies</span><span class="top-stat">{1 if generated else 0} generated</span><span class="top-stat">0 ready</span></div>
        <button class="filter active" data-filter="all">All (1)</button><button class="filter" data-filter="ready">Ready (0)</button><button class="filter" data-filter="review">Review (1)</button>
        <section class="feed"><div class="feed-intro"><h2>Today's vacancies and generated CVs</h2><p>Each post contains the original vacancy link plus both employer-facing CV variants.</p></div>
        <article class="feed-post" data-status="review" data-vacancy="{vacancy_id}">
          <div class="post-body"><div class="post-links"></div></div><div class="cv-gallery">{cv}</div>
          <footer class="post-review"><div><strong>Human decision</strong><span class="local-note">stored only in this browser</span></div>
          <div class="feed-review-actions"><button data-review="SEND">SEND</button><button data-review="REVISE">REVISE</button><button data-review="REJECT">REJECT</button><span data-review-current>not reviewed</span></div></footer>
        </article></section></body></html>'''
        (site / "index.html").write_text(index, encoding="utf-8")
        self._write_json(site / "showcase.json", {
            "schema_version": 2,
            "view": "vacancy_cv_feed",
            "date": day,
            "vacancies": [{
                "vacancy_id": vacancy_id,
                "company": vacancy_id,
                "role_title": "Role",
                "fit_score": 90,
                "ready_to_send": False,
                "has_technical_modern_html": generated,
                "has_harvard_html": False,
            }],
        })
        return site

    def test_merge_keeps_only_last_seven_days_and_adds_status_toggle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshots = root / "snapshots"
            snapshots.mkdir()
            self._snapshot(snapshots, "20260824T120000_3", "2026-08-24", "vac-current")
            self._snapshot(snapshots, "20260820T120000_2", "2026-08-20", "vac-old")
            self._snapshot(snapshots, "20260817T120000_1", "2026-08-17", "vac-expired")
            manifest = root / "generation_state" / "manifest.json"
            self._write_json(manifest, {"entries": {
                "vac-current": {"status": "COMPLETED_BELOW_TARGET", "headhunter_iterations": 2},
                "vac-old": {"status": "PASS", "headhunter_iterations": 1},
            }})
            output = root / "site"

            with patch("cv_presentation.history_merge.apply_p0_decision_ux", return_value={}), patch(
                "cv_presentation.history_merge.attach_navigation", return_value=None
            ):
                report = merge_showcase_history(
                    sites_root=snapshots,
                    site_dir=output,
                    history_days=7,
                    generation_manifest=manifest,
                )

            self.assertEqual(report["window_start"], "2026-08-18")
            self.assertEqual(report["window_end"], "2026-08-24")
            self.assertEqual(report["vacancy_count"], 2)
            html = (output / "index.html").read_text(encoding="utf-8")
            payload = json.loads((output / "showcase.json").read_text(encoding="utf-8"))
            self.assertIn("Vacancies from the last 7 days", html)
            self.assertIn("vac-current", html)
            self.assertIn("vac-old", html)
            self.assertNotIn("vac-expired", html)
            self.assertIn('data-cv-send-status="vac-current"', html)
            self.assertIn("Status: CV no enviado", html)
            self.assertIn("cvfit-send-status:", html)
            self.assertIn("CV enviado", html)
            self.assertIn("CV no enviado", html)
            self.assertNotIn("`${rounds}/5`", html)
            self.assertEqual(payload["schema_version"], 3)
            self.assertEqual(payload["view"], "vacancy_cv_feed_7d")
            self.assertEqual(payload["history_days"], 7)
            self.assertEqual({row["vacancy_id"] for row in payload["vacancies"]}, {"vac-current", "vac-old"})
            self.assertTrue((output / "vacancies" / "vac-old" / "cv_primary.html").exists())

    def test_manual_status_is_idempotent_and_detail_uses_same_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            vacancy = site / "vacancies" / "vac-1"
            vacancy.mkdir(parents=True)
            (site / "index.html").write_text('''<html><head><style></style></head><body>
            <article class="feed-post" data-vacancy="vac-1"><footer class="post-review">
            <div><strong>Human decision</strong><span class="local-note">stored only in this browser</span></div>
            <div class="feed-review-actions"><button data-review="SEND">SEND</button><span data-review-current>not reviewed</span></div>
            </footer></article></body></html>''', encoding="utf-8")
            (vacancy / "index.html").write_text('''<html><head><style></style></head><body><div class="review-box">
            <strong>Human review — local browser only</strong><div class="review-actions"><button data-decision="SEND">Mark send</button></div>
            <span id="human-review">not reviewed</span></div></body></html>''', encoding="utf-8")

            first = apply_manual_send_status(site)
            second = apply_manual_send_status(site)
            feed = (site / "index.html").read_text(encoding="utf-8")
            detail = (vacancy / "index.html").read_text(encoding="utf-8")
            self.assertTrue(first["applied"])
            self.assertTrue(second["applied"])
            self.assertEqual(feed.count('data-cvfit-send-status="1"'), 1)
            self.assertEqual(detail.count('data-cvfit-send-status="1"'), 1)
            self.assertIn('data-cv-send-status="vac-1"', feed)
            self.assertIn('data-cv-send-status="vac-1"', detail)
            self.assertIn("cvfit-human-review:", feed)
            self.assertIn("control manual", detail)


if __name__ == "__main__":
    unittest.main()
