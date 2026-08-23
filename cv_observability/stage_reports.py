from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from cv_observability import EventLogger


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _cost(item: dict[str, Any]) -> Any:
    for key in (
        "total_pipeline_known_cost_usd",
        "known_estimated_cost_usd",
        "estimated_cost_usd",
        "attempt_known_cost_usd",
    ):
        if item.get(key) is not None:
            return item.get(key)
    return None


def log_generation(report_path: Path, outputs: Path, logger: EventLogger) -> None:
    report = _read_json(report_path, {})
    logger.info(
        "generation_batch_summary",
        batch_run_id=report.get("run_id"),
        candidate_count=report.get("candidate_count"),
        generation_attempts=report.get("generation_attempts"),
        stale_logic_candidate_count=report.get("stale_logic_candidate_count"),
        retrieval_mode=report.get("retrieval_mode"),
        result_counts=report.get("result_counts", {}),
    )
    for item in report.get("results", []):
        vacancy_id = str(item.get("vacancy_id") or "")
        bound = logger.bind(run_id=str(item.get("run_id") or report.get("run_id") or ""), vacancy_id=vacancy_id)
        status = str(item.get("status") or "UNKNOWN")
        level = "ERROR" if status.startswith("FAILED") else ("WARNING" if status in {"COMPLETED_BELOW_TARGET", "DEFERRED_CAP", "SKIPPED_NOT_ELIGIBLE"} else "INFO")
        bound.emit(
            level,
            "generation_result",
            status=status,
            ready_to_send=item.get("ready_to_send"),
            estimated_cost_usd=item.get("estimated_cost_usd"),
            known_estimated_cost_usd=item.get("known_estimated_cost_usd"),
            attempt_known_cost_usd=item.get("attempt_known_cost_usd"),
            cumulative_known_cost_usd=item.get("cumulative_known_cost_usd"),
            prior_status=item.get("prior_status"),
            error=item.get("error"),
            reason=item.get("reason"),
        )
        run_id = item.get("run_id")
        if not vacancy_id or not run_id:
            continue
        review_dir = outputs / vacancy_id / str(run_id) / "reviews"
        for review_path in sorted(review_dir.glob("iteration_*.json")) if review_dir.exists() else []:
            record = _read_json(review_path, {})
            review = record.get("review", {}) or {}
            validation = record.get("validation", {}) or {}
            gate = validation.get("quality_gate", {}) or {}
            policy = record.get("model_policy", {}) or {}
            bound.emit(
                "INFO" if gate.get("passed") else "WARNING",
                "headhunter_iteration",
                iteration=record.get("iteration"),
                overall_score=review.get("overall_score"),
                decision=review.get("decision"),
                evidence_strength=(review.get("scores") or {}).get("evidence_strength"),
                quality_gate_passed=gate.get("passed"),
                gate_reasons=gate.get("reasons", []),
                factual=(validation.get("factual") or {}).get("status"),
                language=(validation.get("language") or {}).get("status"),
                structure=(validation.get("structure") or {}).get("status"),
                editorial=(validation.get("editorial") or {}).get("status"),
                reviewer_model=policy.get("reviewer_model"),
                reviser_model=policy.get("reviser_model"),
                premium=policy.get("premium"),
            )


def log_cover(report_path: Path, logger: EventLogger) -> None:
    report = _read_json(report_path, {})
    logger.info(
        "cover_letter_batch_summary",
        generated=report.get("generated"),
        failed=report.get("failed"),
        total_cost_usd=_cost(report.get("usage", {}) or {}),
        call_count=(report.get("usage", {}) or {}).get("call_count"),
    )
    for item in report.get("results", []):
        status = str(item.get("status") or "UNKNOWN")
        logger.bind(run_id=str(item.get("run_id") or ""), vacancy_id=str(item.get("vacancy_id") or "")).emit(
            "ERROR" if status == "FAILED" else "INFO",
            "cover_letter_result",
            status=status,
            estimated_cost_usd=item.get("estimated_cost_usd"),
            known_estimated_cost_usd=item.get("known_estimated_cost_usd"),
            error=item.get("error"),
        )


def log_presentation(report_path: Path, logger: EventLogger) -> None:
    report = _read_json(report_path, {})
    usage = report.get("presentation_usage", {}) or {}
    logger.info(
        "presentation_batch_summary",
        source_batch_run_id=report.get("source_batch_run_id"),
        result_counts=report.get("result_counts", {}),
        total_cost_usd=_cost(usage),
        call_count=usage.get("call_count"),
    )
    for item in report.get("results", []):
        status = str(item.get("status") or "UNKNOWN")
        level = "ERROR" if status.startswith("FAILED") else ("WARNING" if status == "REVIEW_REQUIRED" else "INFO")
        logger.bind(run_id=str(item.get("run_id") or ""), vacancy_id=str(item.get("vacancy_id") or "")).emit(
            level,
            "presentation_result",
            status=status,
            ready_to_send=item.get("ready_to_send"),
            primary_visual_status=item.get("primary_visual_status"),
            primary_presentation_review_status=item.get("primary_presentation_review_status"),
            generation_cost_usd=item.get("generation_cost_usd"),
            cover_letter_cost_usd=item.get("cover_letter_cost_usd"),
            presentation_cost_usd=item.get("presentation_cost_usd"),
            total_pipeline_known_cost_usd=item.get("total_pipeline_known_cost_usd"),
            total_pipeline_cost_complete=item.get("total_pipeline_cost_complete"),
            presentation_blocked=item.get("presentation_blocked"),
            error=item.get("error"),
            reason=item.get("reason"),
        )


def log_pages(site_dir: Path, logger: EventLogger) -> None:
    showcase = _read_json(site_dir / "showcase.json", {})
    process = _read_json(site_dir / "process_metrics.json", {})
    vacancies = showcase.get("vacancies", []) or []
    logger.info(
        "pages_snapshot_summary",
        date=showcase.get("date"),
        vacancy_count=len(vacancies),
        metrics_entry_count=len(process.get("entries", {}) or {}),
        ready_count=sum(bool(item.get("ready_to_send")) for item in vacancies),
    )
    for row in vacancies:
        vacancy_id = str(row.get("vacancy_id") or "")
        metric = (process.get("entries", {}) or {}).get(vacancy_id, {}) or {}
        logger.bind(vacancy_id=vacancy_id).info(
            "pages_vacancy_published",
            company=row.get("company"),
            role_title=row.get("role_title"),
            ready_to_send=row.get("ready_to_send"),
            source_fit=row.get("fit_score"),
            headhunter_score=metric.get("headhunter_score"),
            rag_coverage=metric.get("coverage_score"),
            pipeline_cost_usd=metric.get("total_pipeline_known_cost_usd"),
            cost_complete=metric.get("total_pipeline_cost_complete"),
        )


def log_whatsapp(state_path: Path, plan_path: Path | None, logger: EventLogger) -> None:
    state = _read_json(state_path, {"entries": {}})
    plan = _read_json(plan_path, {}) if plan_path else {}
    entries = list((state.get("entries", {}) or {}).values())
    counts: dict[str, int] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        status = str(entry.get("status") or "UNKNOWN")
        counts[status] = counts.get(status, 0) + 1
    logger.info(
        "whatsapp_state_summary",
        reserved_in_plan=plan.get("count"),
        persisted_entry_count=len(entries),
        status_counts=counts,
    )
    planned = {str(item.get("fingerprint")): item for item in plan.get("notifications", []) if item.get("fingerprint")}
    for fingerprint, item in planned.items():
        state_entry = (state.get("entries", {}) or {}).get(fingerprint, {}) or {}
        status = str(state_entry.get("status") or "UNKNOWN")
        level = "ERROR" if status in {"FAILED", "UNKNOWN_DELIVERY"} else ("WARNING" if status == "RESERVED" else "INFO")
        logger.bind(vacancy_id=str(item.get("vacancy_id") or state_entry.get("vacancy_id") or "")).emit(
            level,
            "whatsapp_notification_result",
            status=status,
            provider_message_id=state_entry.get("provider_message_id"),
            error=state_entry.get("error"),
            template_name=state_entry.get("template_name"),
            template_language=state_entry.get("template_language"),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit detailed redacted logs from persisted CV_fit stage reports.")
    sub = parser.add_subparsers(dest="command", required=True)

    generation = sub.add_parser("generation")
    generation.add_argument("--report", required=True)
    generation.add_argument("--outputs", default="outputs/auto")

    cover = sub.add_parser("cover")
    cover.add_argument("--report", required=True)

    presentation = sub.add_parser("presentation")
    presentation.add_argument("--report", required=True)

    pages = sub.add_parser("pages")
    pages.add_argument("--site-dir", default="_site")

    whatsapp = sub.add_parser("whatsapp")
    whatsapp.add_argument("--state", default="generation_state/whatsapp_notifications.json")
    whatsapp.add_argument("--plan", default=None)

    args = parser.parse_args()
    logger = EventLogger(f"stage_report.{args.command}")
    if args.command == "generation":
        log_generation(Path(args.report), Path(args.outputs), logger)
    elif args.command == "cover":
        log_cover(Path(args.report), logger)
    elif args.command == "presentation":
        log_presentation(Path(args.report), logger)
    elif args.command == "pages":
        log_pages(Path(args.site_dir), logger)
    else:
        log_whatsapp(Path(args.state), Path(args.plan) if args.plan else None, logger)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
