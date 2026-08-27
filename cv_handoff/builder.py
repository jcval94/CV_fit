from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


REDACTED_KEYS = {
    "email",
    "phone",
    "phone_number",
    "mobile",
    "address",
    "private_contact",
    "personal_email",
}


FINAL_REVIEW_PROMPT = """# Final CV review

Act as the final editor before this application is sent.

Your goal is not to regenerate the CV from scratch. Improve the existing proposal into the strongest accurate, credible and concise version for this vacancy.

## Sources of truth
1. `vacancy.md` / `vacancy.json`: what the employer actually asks for.
2. `cv_proposed.json`: the current content proposal.
3. `cv_proposed.html`: the current rendered CV.
4. `html_base.html.j2`: the visual/template baseline.
5. The repository `experience/` evidence: the candidate's factual professional history.

## Rules
- Use the vacancy to decide what deserves emphasis.
- Use real candidate evidence as the factual boundary.
- Never invent technologies, responsibilities, metrics, employers, titles, dates or achievements.
- Transferable experience may be reframed when the connection is defensible, but never presented as direct experience when it is not.
- Prefer quantified evidence and concrete outcomes over adjectives.
- Remove true-but-distracting material when it weakens the application.
- Preserve the base HTML system unless there is a clear usability, ATS, pagination or visual reason to change it.
- Keep the document self-contained, print-safe, Letter sized and ideally no more than two pages.
- Match the language of the vacancy.
- Do not add years of experience to the headline.
- Optimize for a senior recruiter reading the first 10–20 seconds.

## Deliverables
Create:
- `final.html`: the final self-contained CV ready to render and send.
- `review_notes.md`: a concise explanation of the most important changes, remaining gaps and any claim that was deliberately not made.

The automated quality KPI is advisory. A below-target proposal can still become the final sendable CV.
"""


def _read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            if str(key).lower() in REDACTED_KEYS:
                continue
            cleaned[str(key)] = _redact(item)
        return cleaned
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _quality_score(run_report: dict[str, Any]) -> float | int | None:
    raw = ((run_report.get("final_review") or {}).get("overall_score"))
    if raw is None or isinstance(raw, bool):
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return int(value) if value.is_integer() else round(value, 1)


def _source_date(vacancy: dict[str, Any]) -> str | None:
    candidates: list[str] = []
    for row in vacancy.get("provenance", []):
        for key in ("source_search_date", "source_updated_at"):
            value = str(row.get(key) or "")
            if len(value) >= 10 and value[:10].count("-") == 2:
                candidates.append(value[:10])
    return max(candidates) if candidates else None


def _vacancy_markdown(vacancy: dict[str, Any]) -> str:
    def bullets(values: Any) -> str:
        if not isinstance(values, list) or not values:
            return "_Not explicitly provided._"
        return "\n".join(f"- {item}" for item in values if str(item).strip())

    parts = [
        f"# {vacancy.get('company', '')} — {vacancy.get('role_title', '')}",
        "",
        f"- Vacancy ID: `{vacancy.get('vacancy_id', '')}`",
        f"- Location: {vacancy.get('location_raw') or vacancy.get('city') or 'Not specified'}",
        f"- Work model: {vacancy.get('work_model') or 'Not specified'}",
        f"- Source fit: {vacancy.get('fit_score') if vacancy.get('fit_score') is not None else 'n/a'}",
        f"- JD fidelity: {vacancy.get('jd_fidelity') or 'n/a'}",
        f"- Original vacancy: {vacancy.get('url') or ''}",
        "",
        "## Description",
        "",
        str(vacancy.get("description") or vacancy.get("fit_summary") or "_Not provided._"),
        "",
        "## Responsibilities",
        "",
        bullets(vacancy.get("responsibilities")),
        "",
        "## Requirements",
        "",
        bullets(vacancy.get("requirements")),
        "",
    ]
    return "\n".join(parts)


def rebuild_index(
    handoff_dir: Path,
    *,
    repository: str = "jcval94/CV_fit",
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for manifest_path in sorted(handoff_dir.glob("*/handoff.json")):
        row = _read_json(manifest_path, {})
        if isinstance(row, dict) and row.get("vacancy_id"):
            rows.append(row)
    rows.sort(
        key=lambda row: (
            row.get("status") == "finalized",
            -(float(row.get("source_fit") or 0)),
            str(row.get("source_date") or ""),
            str(row.get("company") or ""),
        )
    )
    payload = {
        "schema_version": 1,
        "repository": repository,
        "selection_policy": "pending first; then source_fit descending; recency available as source_date",
        "pending_count": sum(row.get("status") != "finalized" for row in rows),
        "finalized_count": sum(row.get("status") == "finalized" for row in rows),
        "candidates": rows,
    }
    _write_json(handoff_dir / "index.json", payload)
    return payload


def build_handoffs(
    *,
    batch_report: Path,
    outputs: Path,
    vacancy_state: Path,
    template_file: Path,
    handoff_dir: Path,
    repository: str = "jcval94/CV_fit",
) -> dict[str, Any]:
    batch = _read_json(batch_report, {"results": []})
    handoff_dir.mkdir(parents=True, exist_ok=True)
    built: list[str] = []
    skipped: list[dict[str, str]] = []

    for item in batch.get("results", []):
        vacancy_id = str(item.get("vacancy_id") or "")
        run_id = str(item.get("run_id") or "")
        if not vacancy_id or not run_id:
            continue

        vacancy_path = vacancy_state / "records" / f"{vacancy_id}.json"
        run_dir = outputs / vacancy_id / run_id
        cv_json = run_dir / "cv_final.json"
        if not vacancy_path.exists() or not cv_json.exists():
            skipped.append({"vacancy_id": vacancy_id, "reason": "missing_vacancy_or_cv"})
            continue

        vacancy = _read_json(vacancy_path)
        run_report = _read_json(run_dir / "run_report.json", {})
        bundle = _read_json(run_dir / "application_bundle_report.json", {})
        package_dir = handoff_dir / vacancy_id
        package_dir.mkdir(parents=True, exist_ok=True)

        primary = next(
            (
                row
                for row in bundle.get("templates", [])
                if isinstance(row, dict) and row.get("role") == "primary"
            ),
            {},
        )
        proposed_html = run_dir / str(primary.get("html_file") or "cv_primary.html")

        (package_dir / "vacancy.md").write_text(_vacancy_markdown(vacancy), encoding="utf-8")
        _write_json(package_dir / "vacancy.json", _redact(vacancy))
        _write_json(package_dir / "cv_proposed.json", _redact(_read_json(cv_json)))
        if proposed_html.exists():
            shutil.copy2(proposed_html, package_dir / "cv_proposed.html")
        if template_file.exists():
            shutil.copy2(template_file, package_dir / "html_base.html.j2")
        (package_dir / "prompt.md").write_text(FINAL_REVIEW_PROMPT, encoding="utf-8")

        quality = _quality_score(run_report)
        final_exists = (package_dir / "final.html").exists()
        base_url = f"https://github.com/{repository}/tree/main/handoff/{vacancy_id}"
        raw_base = f"https://raw.githubusercontent.com/{repository}/main/handoff/{vacancy_id}"
        manifest = {
            "schema_version": 1,
            "vacancy_id": vacancy_id,
            "company": vacancy.get("company"),
            "role_title": vacancy.get("role_title"),
            "source_date": _source_date(vacancy),
            "source_fit": vacancy.get("fit_score"),
            "quality_kpi": quality,
            "pipeline_status": item.get("status"),
            "ready_to_send": bool(bundle.get("ready_to_send")),
            "status": "finalized" if final_exists else "pending_final_review",
            "run_id": run_id,
            "vacancy_url": vacancy.get("url"),
            "repo_folder_url": base_url,
            "files": {
                "vacancy": "vacancy.md",
                "vacancy_json": "vacancy.json",
                "cv_proposed": "cv_proposed.json",
                "cv_proposed_html": "cv_proposed.html" if proposed_html.exists() else None,
                "html_base": "html_base.html.j2" if template_file.exists() else None,
                "prompt": "prompt.md",
                "final_html": "final.html" if final_exists else None,
                "final_pdf": "final.pdf" if (package_dir / "final.pdf").exists() else None,
                "review_notes": "review_notes.md" if (package_dir / "review_notes.md").exists() else None,
            },
            "links": {
                "proposed_html": f"{raw_base}/cv_proposed.html" if proposed_html.exists() else None,
                "final_html": f"{raw_base}/final.html" if final_exists else None,
                "final_pdf": f"{raw_base}/final.pdf" if (package_dir / "final.pdf").exists() else None,
            },
        }
        _write_json(package_dir / "handoff.json", manifest)
        built.append(vacancy_id)

    index = rebuild_index(handoff_dir, repository=repository)
    return {"built": built, "skipped": skipped, "index": index}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build versioned ChatGPT Work final-review packages.")
    parser.add_argument("--batch-report", required=True)
    parser.add_argument("--outputs", default="outputs/auto")
    parser.add_argument("--vacancy-state", default="vacancy_state")
    parser.add_argument("--template-file", default="cv_presentation/templates/technical_modern_v1.html.j2")
    parser.add_argument("--handoff-dir", default="handoff")
    parser.add_argument("--repository", default="jcval94/CV_fit")
    args = parser.parse_args()

    report = build_handoffs(
        batch_report=Path(args.batch_report),
        outputs=Path(args.outputs),
        vacancy_state=Path(args.vacancy_state),
        template_file=Path(args.template_file),
        handoff_dir=Path(args.handoff_dir),
        repository=args.repository,
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
