from __future__ import annotations

import argparse
import json
from pathlib import Path

from cv_presentation.physical_layout import validate_html_and_export_pdf


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate rendered CV HTML in Chromium and export a verified US-Letter PDF.")
    parser.add_argument("--html", required=True)
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--expected-pages", required=True, type=int, choices=[1, 2])
    parser.add_argument("--screenshot", default=None)
    args = parser.parse_args()

    report = validate_html_and_export_pdf(
        Path(args.html),
        Path(args.pdf),
        expected_pages=args.expected_pages,
        screenshot_path=Path(args.screenshot) if args.screenshot else None,
    )
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report.status,
        "dom_pages": report.dom_pages,
        "pdf_pages": report.pdf_pages,
        "reasons": report.reasons,
    }, ensure_ascii=False, sort_keys=True))
    return 0 if report.status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
