from __future__ import annotations

import argparse
import json
from pathlib import Path

from cv_presentation.feed_enhancements import enhance_feed_index
from cv_presentation.showcase import refresh_existing_showcase


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refresh and enhance the GitHub Pages vacancy feed from an existing daily-showcase artifact without regenerating CVs."
    )
    parser.add_argument("--site-dir", default="_site")
    parser.add_argument("--generation-manifest", default="generation_state/manifest.json")
    args = parser.parse_args()
    site_dir = Path(args.site_dir)
    report = refresh_existing_showcase(site_dir)
    report["feed_enhancements"] = enhance_feed_index(
        site_dir,
        generation_manifest_path=Path(args.generation_manifest),
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
