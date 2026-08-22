from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


ARTIFACT_FIELDS = {
    "generation_status",
    "ready_to_send",
    "rag_coverage",
    "headhunter_score",
    "primary_label",
    "alternate_label",
    "primary_html_file",
    "primary_pdf_file",
    "primary_screenshot_file",
    "alternate_html_file",
    "alternate_pdf_file",
    "alternate_screenshot_file",
    "primary_physical_status",
    "primary_visual_status",
    "primary_presentation_review_status",
    "alternate_physical_status",
    "alternate_visual_status",
    "alternate_presentation_review_status",
    "page_utilization",
    "section_area_ratios",
    "section_item_counts",
}

CURRENT_VACANCY_FIELDS = {
    "company",
    "role_title",
    "url",
    "fit_score",
    "fit_summary",
    "jd_fidelity",
    "work_model",
    "location",
}


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _has_cv_assets(site_dir: Path, vacancy_id: str) -> bool:
    root = site_dir / "vacancies" / vacancy_id
    return any((root / name).exists() for name in ("cv_primary.html", "cv_alternate.html", "cv_primary.pdf", "cv_alternate.pdf"))


def inherit_previous_public_bundles(*, current_site: Path, previous_site: Path) -> dict[str, Any]:
    """Carry forward public-safe CV bundles when the current generation run is a no-op.

    The generation manifest is intentionally idempotent, but GitHub Actions workspaces
    are ephemeral. A later successful ingest run can therefore have no new CV files
    even though prior public bundles are still the latest valid artifacts. This helper
    copies only the already-public vacancy bundle directories from the previous
    showcase snapshot and preserves current vacancy metadata from the new run.
    """
    current_payload = _read_json(current_site / "showcase.json", {"date": None, "vacancies": []})
    previous_payload = _read_json(previous_site / "showcase.json", {"date": None, "vacancies": []})
    previous_by_id = {
        str(row.get("vacancy_id")): row
        for row in previous_payload.get("vacancies", [])
        if row.get("vacancy_id")
    }

    inherited: list[str] = []
    current_rows: list[dict[str, Any]] = []
    for current in current_payload.get("vacancies", []):
        vacancy_id = str(current.get("vacancy_id") or "")
        if not vacancy_id:
            current_rows.append(current)
            continue
        previous = previous_by_id.get(vacancy_id)
        if _has_cv_assets(current_site, vacancy_id) or previous is None or not _has_cv_assets(previous_site, vacancy_id):
            current_rows.append(current)
            continue

        src = previous_site / "vacancies" / vacancy_id
        dst = current_site / "vacancies" / vacancy_id
        dst.mkdir(parents=True, exist_ok=True)
        for path in src.iterdir():
            if path.is_file():
                shutil.copy2(path, dst / path.name)

        merged = dict(previous)
        for key in CURRENT_VACANCY_FIELDS:
            if key in current and current.get(key) not in (None, ""):
                merged[key] = current[key]
        merged["vacancy_id"] = vacancy_id
        merged["artifact_source"] = "inherited_previous_showcase"
        current_rows.append(merged)
        inherited.append(vacancy_id)

    current_payload["vacancies"] = current_rows
    current_payload["inherited_vacancy_ids"] = inherited
    current_payload["previous_showcase_date"] = previous_payload.get("date")
    _write_json(current_site / "showcase.json", current_payload)
    return {
        "current_date": current_payload.get("date"),
        "previous_date": previous_payload.get("date"),
        "inherited_count": len(inherited),
        "inherited_vacancy_ids": inherited,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Carry forward the latest public CV bundle snapshot into a no-op showcase run.")
    parser.add_argument("--current-site", default="_site")
    parser.add_argument("--previous-site", required=True)
    args = parser.parse_args()
    report = inherit_previous_public_bundles(
        current_site=Path(args.current_site),
        previous_site=Path(args.previous_site),
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
