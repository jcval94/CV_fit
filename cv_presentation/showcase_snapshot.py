from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from cv_presentation.showcase import _detail_page

_TEMPLATE_ARTIFACT_FIELDS = (
    "html_file",
    "pdf_file",
    "screenshot_file",
    "fit_report_file",
    "design_report_file",
    "physical_report_file",
    "visual_eval_file",
    "presentation_review_file",
)
_ROW_ARTIFACT_FIELDS = (
    "primary_html_file",
    "primary_pdf_file",
    "primary_screenshot_file",
    "alternate_html_file",
    "alternate_pdf_file",
    "alternate_screenshot_file",
)
_CURRENT_METADATA_FIELDS = (
    "vacancy_id",
    "company",
    "role_title",
    "url",
    "location",
    "fit_score",
    "jd_fidelity",
    "source_date",
)


def _read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _has_cv_assets(site_dir: Path, row: dict[str, Any]) -> bool:
    vacancy_id = str(row.get("vacancy_id") or "")
    if not vacancy_id:
        return False
    vacancy_dir = site_dir / "vacancies" / vacancy_id
    names = [str(row.get(field) or "") for field in _ROW_ARTIFACT_FIELDS]
    names.extend(("cv_primary.html", "cv_alternate.html"))
    return any(name and (vacancy_dir / name).is_file() for name in names)


def _bundle_and_allowed_files(source_dir: Path, row: dict[str, Any]) -> tuple[dict[str, Any] | None, set[str]]:
    allowed = {"application_bundle_report.json", "cover_letter_final.md"}
    bundle_path = source_dir / "application_bundle_report.json"
    bundle: dict[str, Any] | None = None
    if bundle_path.is_file():
        payload = _read_json(bundle_path)
        if isinstance(payload, dict):
            bundle = payload
            for template in bundle.get("templates", []):
                if not isinstance(template, dict):
                    continue
                for field in _TEMPLATE_ARTIFACT_FIELDS:
                    value = template.get(field)
                    if value:
                        allowed.add(Path(str(value)).name)
    for field in _ROW_ARTIFACT_FIELDS:
        value = row.get(field)
        if value:
            allowed.add(Path(str(value)).name)
    return bundle, allowed


def inherit_missing_bundles(*, site_dir: Path, previous_site_dir: Path) -> dict[str, Any]:
    current_path = site_dir / "showcase.json"
    previous_path = previous_site_dir / "showcase.json"
    current = _read_json(current_path)
    previous = _read_json(previous_path, default={})
    current_rows = current.get("vacancies", [])
    previous_by_id = {
        str(row.get("vacancy_id")): row
        for row in previous.get("vacancies", [])
        if isinstance(row, dict) and row.get("vacancy_id")
    }

    inherited: list[str] = []
    for index, current_row in enumerate(current_rows):
        if not isinstance(current_row, dict) or _has_cv_assets(site_dir, current_row):
            continue
        vacancy_id = str(current_row.get("vacancy_id") or "")
        previous_row = previous_by_id.get(vacancy_id)
        if not previous_row or not _has_cv_assets(previous_site_dir, previous_row):
            continue

        source_dir = previous_site_dir / "vacancies" / vacancy_id
        destination_dir = site_dir / "vacancies" / vacancy_id
        bundle, allowed = _bundle_and_allowed_files(source_dir, previous_row)
        destination_dir.mkdir(parents=True, exist_ok=True)
        copied = 0
        for name in sorted(allowed):
            source = source_dir / name
            if source.is_file():
                shutil.copy2(source, destination_dir / name)
                copied += 1
        if copied == 0:
            continue

        merged = dict(previous_row)
        for field in _CURRENT_METADATA_FIELDS:
            if field in current_row:
                merged[field] = current_row[field]
        merged["artifact_source"] = "inherited_previous_showcase"
        current_rows[index] = merged

        if bundle is None:
            bundle_path = destination_dir / "application_bundle_report.json"
            if bundle_path.is_file():
                payload = _read_json(bundle_path)
                bundle = payload if isinstance(payload, dict) else None
        coverage = merged.get("rag_coverage")
        run_report = {"match_coverage_score": coverage} if coverage is not None else None
        (destination_dir / "index.html").write_text(
            _detail_page(merged, bundle, run_report),
            encoding="utf-8",
        )
        inherited.append(vacancy_id)

    current["vacancies"] = current_rows
    current["generated_count"] = sum(_has_cv_assets(site_dir, row) for row in current_rows if isinstance(row, dict))
    current["ready_count"] = sum(
        bool(row.get("ready_to_send")) and _has_cv_assets(site_dir, row)
        for row in current_rows
        if isinstance(row, dict)
    )
    _write_json(current_path, current)
    return {"inherited_count": len(inherited), "vacancy_ids": inherited}


def main() -> int:
    parser = argparse.ArgumentParser(description="Carry forward missing public CV bundles from a previous showcase")
    parser.add_argument("--site-dir", default="_site")
    parser.add_argument("--previous-site-dir", required=True)
    args = parser.parse_args()
    result = inherit_missing_bundles(
        site_dir=Path(args.site_dir),
        previous_site_dir=Path(args.previous_site_dir),
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
