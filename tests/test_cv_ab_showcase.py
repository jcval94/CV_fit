from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cv_presentation.ab_showcase import attach_navigation, build_ab_showcase, restore_persisted
from tests.test_cv_agent_workflow import cv_fixture


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


class BlindABShowcaseTests(unittest.TestCase):
    def test_build_hides_mapping_until_all_votes_and_has_second_tab(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "experiment"
            case_dir = root / "cases" / "vac-test"
            cv = cv_fixture().model_dump()
            _write_json(case_dir / "candidate_left.json", cv)
            _write_json(case_dir / "candidate_right.json", cv)
            _write_json(root / "ab_report.json", {
                "experiment_id": "ab-1",
                "completed_case_count": 1,
                "machine_gate_pass_count": 1,
                "mean_cost_savings_pct": 35.0,
                "mean_headhunter_score_delta": -1.0,
                "cases": [{
                    "vacancy_id": "vac-test",
                    "company": "Example",
                    "role_title": "Senior Data Scientist",
                    "url": "https://example.com/job",
                    "coverage_score": 90.0,
                    "blind_mapping": {"left": "optimized", "right": "baseline"},
                    "baseline": {"cost_usd": 0.9, "headhunter_score": 93},
                    "optimized": {"cost_usd": 0.55, "headhunter_score": 92, "iterations": 3, "premium_model_used": False},
                    "comparison": {"cost_savings_pct": 38.89, "headhunter_score_delta": -1, "machine_gate_pass": True},
                    "agent_audit": {"pass_1_winner_variant": "optimized", "pass_2_winner_variant": "optimized", "consensus": "optimized"},
                }],
            })
            site = Path(temp) / "site"
            build_ab_showcase(experiment_root=root, site_dir=site)
            text = (site / "index.html").read_text(encoding="utf-8")
            self.assertIn("Blind A/B Cost Lab", text)
            self.assertIn("CV LEFT", text)
            self.assertIn("CV RIGHT", text)
            self.assertIn("body.revealed .reveal-panel", text)
            self.assertIn("allVoted()", text)
            self.assertIn("Process identity, cost and agent preference remain hidden", text)

    def test_restore_adds_navigation_to_existing_showcase(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            persisted = base / "persisted"
            (persisted / "site").mkdir(parents=True)
            (persisted / "site" / "index.html").write_text("<html>ab</html>", encoding="utf-8")
            site = base / "site"
            site.mkdir()
            (site / "index.html").write_text(
                '<html><head></head><body><header><div class="top-stats"></div></header></body></html>',
                encoding="utf-8",
            )
            self.assertTrue(restore_persisted(persisted_dir=persisted, site_dir=site))
            self.assertTrue((site / "ab-testing" / "index.html").exists())
            self.assertIn("cvfit-ab-nav", (site / "index.html").read_text(encoding="utf-8"))
            self.assertFalse(attach_navigation(site))


if __name__ == "__main__":
    unittest.main()
