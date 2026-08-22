from __future__ import annotations

import argparse
import json
from pathlib import Path

from cv_presentation.showcase import refresh_existing_showcase


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh the GitHub Pages feed from an existing daily-showcase artifact without regenerating CVs.")
    parser.add_argument("--site-dir", default="_site")
    args = parser.parse_args()
    report = refresh_existing_showcase(Path(args.site_dir))
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
