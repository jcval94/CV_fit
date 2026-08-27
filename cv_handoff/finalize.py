from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from cv_handoff.builder import _read_json, _write_json, rebuild_index


def render_final(
    html_path: Path,
    *,
    repository: str = "jcval94/CV_fit",
) -> dict[str, Any]:
    if not html_path.exists():
        raise FileNotFoundError(html_path)
    package_dir = html_path.parent
    vacancy_id = package_dir.name
    pdf_path = package_dir / "final.pdf"
    screenshot_path = package_dir / "final.png"

    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1000, "height": 1400})
        page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
        page.emulate_media(media="print")
        page.pdf(
            path=str(pdf_path),
            format="Letter",
            print_background=True,
            prefer_css_page_size=True,
        )
        page.emulate_media(media="screen")
        page.screenshot(path=str(screenshot_path), full_page=True)
        browser.close()

    pdf_pages = len(PdfReader(str(pdf_path)).pages)
    warnings: list[str] = []
    if pdf_pages > 2:
        warnings.append(f"final_pdf_has_{pdf_pages}_pages")

    raw_base = f"https://raw.githubusercontent.com/{repository}/main/handoff/{vacancy_id}"
    report = {
        "schema_version": 1,
        "vacancy_id": vacancy_id,
        "html_file": html_path.name,
        "pdf_file": pdf_path.name,
        "screenshot_file": screenshot_path.name,
        "pdf_pages": pdf_pages,
        "status": "PASS" if not warnings else "REVIEW",
        "warnings": warnings,
        "links": {
            "html": f"{raw_base}/final.html",
            "pdf": f"{raw_base}/final.pdf",
            "screenshot": f"{raw_base}/final.png",
        },
    }
    _write_json(package_dir / "final_report.json", report)

    manifest_path = package_dir / "handoff.json"
    manifest = _read_json(manifest_path, {})
    if isinstance(manifest, dict):
        manifest["status"] = "finalized"
        files = manifest.setdefault("files", {})
        files["final_html"] = "final.html"
        files["final_pdf"] = "final.pdf"
        files["final_screenshot"] = "final.png"
        if (package_dir / "review_notes.md").exists():
            files["review_notes"] = "review_notes.md"
        if (package_dir / "cover_letter_final.md").exists():
            files["cover_letter_final"] = "cover_letter_final.md"
        links = manifest.setdefault("links", {})
        links.update(report["links"])
        if (package_dir / "cover_letter_final.md").exists():
            links["cover_letter_final"] = f"{raw_base}/cover_letter_final.md"
        manifest["final_render"] = {
            "status": report["status"],
            "pdf_pages": pdf_pages,
            "warnings": warnings,
        }
        _write_json(manifest_path, manifest)

    rebuild_index(package_dir.parent, repository=repository)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a Work-refined final.html to PDF and PNG.")
    parser.add_argument("--html", required=True)
    parser.add_argument("--repository", default="jcval94/CV_fit")
    args = parser.parse_args()
    report = render_final(Path(args.html), repository=args.repository)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
