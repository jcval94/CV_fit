from __future__ import annotations

import argparse
import json
from pathlib import Path

from cv_observability import EventLogger
from cv_presentation.feed_enhancements import enhance_feed_index
from cv_presentation.p0_decision_ux import apply_p0_decision_ux
from cv_presentation.showcase import refresh_existing_showcase


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refresh and enhance the GitHub Pages vacancy feed from an existing daily-showcase artifact without regenerating CVs."
    )
    parser.add_argument("--site-dir", default="_site")
    parser.add_argument("--generation-manifest", default="generation_state/manifest.json")
    args = parser.parse_args()
    site_dir = Path(args.site_dir)
    logger = EventLogger("pages_refresh")

    with logger.span("refresh_showcase", site_dir=site_dir):
        report = refresh_existing_showcase(site_dir)
    logger.info(
        "showcase_refreshed",
        vacancy_count=report.get("vacancy_count"),
        generated_count=report.get("generated_count"),
        ready_count=report.get("ready_count"),
    )

    with logger.span("feed_enhancements"):
        report["feed_enhancements"] = enhance_feed_index(
            site_dir,
            generation_manifest_path=Path(args.generation_manifest),
        )
    logger.info("feed_enhancements_applied", result=report["feed_enhancements"])

    with logger.span("decision_ux"):
        report["p0_decision_ux"] = apply_p0_decision_ux(site_dir)
    logger.info("decision_ux_applied", result=report["p0_decision_ux"])

    logger.info("pages_refresh_completed", result=report)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
