from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from cv_observability.logging import EventLogger, sanitize


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _by_vacancy(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("vacancy_id")): item
        for item in report.get("results", [])
        if item.get("vacancy_id")
    }


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None


def _fmt(value: Any) -> str:
    if value is None or value == "":
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(sanitize(value)).replace("|", "\\|").replace("\n", " ")[:180]


def _error(item: dict[str, Any] | None) -> str:
    if not item:
        return ""
    return _fmt(item.get("error") or item.get("reason") or "")


def _latest_whatsapp_status(entries: list[dict[str, Any]]) -> str | None:
    if not entries:
        return None
    ordered = sorted(
        entries,
        key=lambda entry: str(
            entry.get("accepted_at")
            or entry.get("failed_at")
            or entry.get("reserved_at")
            or ""
        ),
    )
    return ordered[-1].get("status")


def build_summary(
    *,
    ingest_report: Path,
    generation_report: Path,
    cover_report: Path,
    bundle_report: Path,
    generation_manifest: Path,
    whatsapp_state: Path | None = None,
) -> dict[str, Any]:
    ingest = _read_json(ingest_report, {})
    generation = _read_json(generation_report, {})
    cover = _read_json(cover_report, {})
    bundle = _read_json(bundle_report, {})
    manifest = _read_json(generation_manifest, {"entries": {}})
    whatsapp = _read_json(whatsapp_state, {"entries": {}}) if whatsapp_state else {"entries": {}}

    generation_by = _by_vacancy(generation)
    cover_by = _by_vacancy(cover)
    bundle_by = _by_vacancy(bundle)
    manifest_entries = manifest.get("entries", {}) or {}

    ids = set(generation_by) | set(cover_by) | set(bundle_by) | set(manifest_entries)
    rows: list[dict[str, Any]] = []
    for vacancy_id in sorted(ids):
        gen = generation_by.get(vacancy_id, {})
        cov = cover_by.get(vacancy_id, {})
        bun = bundle_by.get(vacancy_id, {})
        state = manifest_entries.get(vacancy_id, {}) or {}
        wa_entries = [
            value for value in (whatsapp.get("entries", {}) or {}).values()
            if isinstance(value, dict) and value.get("vacancy_id") == vacancy_id
        ]
        rows.append({
            "vacancy_id": vacancy_id,
            "generation": gen.get("status") or state.get("status"),
            "headhunter": state.get("headhunter_score"),
            "coverage": state.get("coverage_score"),
            "cover_letter": cov.get("status") or state.get("cover_letter_status"),
            "presentation": bun.get("status") or (state.get("presentation_gate") or {}).get("status"),
            "ready": bun.get("ready_to_send") if "ready_to_send" in bun else state.get("ready_to_send"),
            "generation_cost_usd": _first_present(
                bun.get("generation_cost_usd"),
                state.get("known_estimated_cost_usd"),
                state.get("estimated_cost_usd"),
            ),
            "cover_cost_usd": _first_present(
                bun.get("cover_letter_cost_usd"),
                state.get("cover_letter_cost_usd"),
            ),
            "presentation_cost_usd": _first_present(
                bun.get("presentation_cost_usd"),
                state.get("presentation_cost_usd"),
            ),
            "pipeline_cost_usd": _first_present(
                bun.get("total_pipeline_known_cost_usd"),
                state.get("total_pipeline_known_cost_usd"),
            ),
            "cost_complete": bun.get("total_pipeline_cost_complete") if "total_pipeline_cost_complete" in bun else state.get("total_pipeline_cost_complete"),
            "whatsapp": _latest_whatsapp_status(wa_entries),
            "error": _error(bun) or _error(cov) or _error(gen),
        })

    return {
        "ingest": {
            "status": ingest.get("status"),
            "sources": ingest.get("source_counts", {}),
            "vacancies": ingest.get("vacancy_counts", {}),
        },
        "generation_counts": generation.get("result_counts", {}),
        "cover_generated": cover.get("generated"),
        "cover_failed": cover.get("failed"),
        "presentation_counts": bundle.get("result_counts", {}),
        "rows": rows,
    }


def render_markdown(summary: dict[str, Any]) -> str:
    ingest = summary.get("ingest", {})
    lines = [
        "## CV_fit E2E observability",
        "",
        f"**Ingest:** `{_fmt(ingest.get('status'))}` · sources `{_fmt(ingest.get('sources'))}` · vacancies `{_fmt(ingest.get('vacancies'))}`",
        "",
        "| Vacancy | Generation | Headhunter | RAG | Cover | Presentation | Ready | Pipeline cost | Cost coverage | WhatsApp | Error |",
        "|---|---|---:|---:|---|---|---|---:|---|---|---|",
    ]
    for row in summary.get("rows", []):
        lines.append(
            "| " + " | ".join([
                _fmt(row.get("vacancy_id")),
                _fmt(row.get("generation")),
                _fmt(row.get("headhunter")),
                _fmt(row.get("coverage")),
                _fmt(row.get("cover_letter")),
                _fmt(row.get("presentation")),
                _fmt(row.get("ready")),
                _fmt(row.get("pipeline_cost_usd")),
                "complete" if row.get("cost_complete") is True else ("partial" if row.get("cost_complete") is False else "n/a"),
                _fmt(row.get("whatsapp")),
                _fmt(row.get("error")),
            ]) + " |"
        )
    return "\n".join(lines) + "\n"


def emit_summary(summary: dict[str, Any], *, logger: EventLogger) -> None:
    logger.info(
        "pipeline_summary",
        ingest_status=summary.get("ingest", {}).get("status"),
        vacancy_count=len(summary.get("rows", [])),
        generation_counts=summary.get("generation_counts", {}),
        presentation_counts=summary.get("presentation_counts", {}),
        cover_generated=summary.get("cover_generated"),
        cover_failed=summary.get("cover_failed"),
    )
    for row in summary.get("rows", []):
        bound = logger.bind(vacancy_id=str(row.get("vacancy_id") or ""))
        level = "ERROR" if row.get("error") else "INFO"
        bound.emit(
            level,
            "vacancy_e2e_summary",
            generation=row.get("generation"),
            headhunter=row.get("headhunter"),
            rag_coverage=row.get("coverage"),
            cover_letter=row.get("cover_letter"),
            presentation=row.get("presentation"),
            ready_to_send=row.get("ready"),
            pipeline_cost_usd=row.get("pipeline_cost_usd"),
            cost_complete=row.get("cost_complete"),
            whatsapp=row.get("whatsapp"),
            error=row.get("error") or None,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit a consolidated redacted CV_fit E2E summary.")
    parser.add_argument("--ingest-report", required=True)
    parser.add_argument("--generation-report", required=True)
    parser.add_argument("--cover-report", required=True)
    parser.add_argument("--bundle-report", required=True)
    parser.add_argument("--generation-manifest", default="generation_state/manifest.json")
    parser.add_argument("--whatsapp-state", default="generation_state/whatsapp_notifications.json")
    parser.add_argument("--markdown-out", default=None)
    args = parser.parse_args()

    logger = EventLogger("pipeline_summary")
    summary = build_summary(
        ingest_report=Path(args.ingest_report),
        generation_report=Path(args.generation_report),
        cover_report=Path(args.cover_report),
        bundle_report=Path(args.bundle_report),
        generation_manifest=Path(args.generation_manifest),
        whatsapp_state=Path(args.whatsapp_state),
    )
    emit_summary(summary, logger=logger)
    markdown = render_markdown(summary)

    target = args.markdown_out or os.getenv("GITHUB_STEP_SUMMARY")
    if target:
        path = Path(target)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(markdown)
    else:
        print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
