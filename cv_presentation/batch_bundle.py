from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from cv_agent.adk_runtime import AdkStructuredClient
from cv_presentation.application_bundle import PresentationGateBlocked, build_application_bundle


def _read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _usage_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_calls = int(before.get("call_count") or 0)
    after_calls = int(after.get("call_count") or 0)
    before_known = _number(before.get("known_estimated_cost_usd")) or 0.0
    after_known = _number(after.get("known_estimated_cost_usd")) or 0.0
    before_exact = _number(before.get("estimated_cost_usd"))
    after_exact = _number(after.get("estimated_cost_usd"))
    exact = None
    if before_exact is not None and after_exact is not None:
        exact = round(max(after_exact - before_exact, 0.0), 8)
    return {
        "call_count": max(after_calls - before_calls, 0),
        "estimated_cost_usd": exact,
        "known_estimated_cost_usd": round(max(after_known - before_known, 0.0), 8),
        "prompt_tokens": max(int(after.get("prompt_tokens") or 0) - int(before.get("prompt_tokens") or 0), 0),
        "cached_input_tokens": max(int(after.get("cached_input_tokens") or 0) - int(before.get("cached_input_tokens") or 0), 0),
        "candidate_tokens": max(int(after.get("candidate_tokens") or 0) - int(before.get("candidate_tokens") or 0), 0),
        "reasoning_tokens": max(int(after.get("reasoning_tokens") or 0) - int(before.get("reasoning_tokens") or 0), 0),
        "total_tokens": max(int(after.get("total_tokens") or 0) - int(before.get("total_tokens") or 0), 0),
    }


def _stage_cost(usage: dict[str, Any]) -> float | None:
    exact = _number(usage.get("estimated_cost_usd"))
    if exact is not None:
        return exact
    return _number(usage.get("known_estimated_cost_usd"))


def _generation_cost(entry: dict[str, Any]) -> float | None:
    for key in ("known_estimated_cost_usd", "estimated_cost_usd", "attempt_known_cost_usd"):
        value = _number(entry.get(key))
        if value is not None:
            return value
    return None


def _pipeline_cost(entry: dict[str, Any]) -> tuple[float | None, bool]:
    stages = (
        _generation_cost(entry),
        _number(entry.get("cover_letter_cost_usd")),
        _number(entry.get("presentation_cost_usd")),
    )
    known = [value for value in stages if value is not None]
    return (round(sum(known), 8) if known else None, len(known) == len(stages))


def _persist_run_costs(run_dir: Path, entry: dict[str, Any], presentation_usage: dict[str, Any]) -> None:
    run_report_path = run_dir / "run_report.json"
    run_report = _read_json(run_report_path, {})
    stage_usage = run_report.setdefault("stage_usage", {})
    stage_usage["presentation"] = presentation_usage
    run_report["generation_cost_usd"] = _generation_cost(entry)
    run_report["cover_letter_cost_usd"] = _number(entry.get("cover_letter_cost_usd"))
    run_report["presentation_cost_usd"] = _number(entry.get("presentation_cost_usd"))
    run_report["total_pipeline_known_cost_usd"] = entry.get("total_pipeline_known_cost_usd")
    run_report["total_pipeline_cost_complete"] = entry.get("total_pipeline_cost_complete")
    _write_json(run_report_path, run_report)


def finalize_batch(
    *,
    batch_report: Path,
    outputs: Path,
    vacancy_state: Path,
    generation_state: Path,
    identity_public: Path,
    brand_profiles_dir: Path,
    max_design_cost_usd: float,
) -> dict[str, Any]:
    batch = _read_json(batch_report)
    manifest_path = generation_state / "manifest.json"
    manifest = _read_json(manifest_path, {"entries": {}})
    entries = manifest.setdefault("entries", {})
    client = AdkStructuredClient(max_estimated_cost_usd=max_design_cost_usd)
    results: list[dict[str, Any]] = []

    for item in batch.get("results", []):
        vacancy_id = str(item.get("vacancy_id") or "")
        run_id = item.get("run_id")
        if not vacancy_id or not run_id:
            results.append({"vacancy_id": vacancy_id, "status": "SKIPPED_NO_FRESH_OUTPUT"})
            continue
        vacancy_path = vacancy_state / "records" / f"{vacancy_id}.json"
        run_dir = outputs / vacancy_id / str(run_id)
        if not vacancy_path.exists() or not (run_dir / "cv_final.json").exists():
            results.append({"vacancy_id": vacancy_id, "status": "SKIPPED_MISSING_OUTPUT"})
            continue

        vacancy = _read_json(vacancy_path)
        entry = entries.setdefault(vacancy_id, {})
        before = client.telemetry_snapshot()
        try:
            report = build_application_bundle(
                vacancy=vacancy,
                run_dir=run_dir,
                identity_public_path=identity_public,
                brand_profiles_dir=brand_profiles_dir,
                design_client=client,
            )
            status = "PASS" if report.ready_to_send else "REVIEW_REQUIRED"
            primary = next(x for x in report.templates if x.role == "primary")
            alternate = next(x for x in report.templates if x.role == "alternate")
            results.append({
                "vacancy_id": vacancy_id,
                "run_id": run_id,
                "status": status,
                "ready_to_send": report.ready_to_send,
                "primary_visual_status": primary.visual_status,
                "primary_presentation_review_status": primary.presentation_review_status,
                "application_bundle_file": str(run_dir / "application_bundle_report.json"),
            })
            entry["content_quality_target_reached"] = report.content_quality_target_reached
            entry["presentation_gate"] = {
                "status": "PASS" if report.ready_to_send else "REVIEW_REQUIRED",
                "primary_template": report.primary_template,
                "primary_physical_status": primary.physical_status,
                "primary_visual_status": primary.visual_status,
                "primary_presentation_review_status": primary.presentation_review_status,
                "primary_page_utilization": primary.page_utilization,
                "primary_section_area_ratios": primary.section_area_ratios,
                "primary_section_item_counts": primary.section_item_counts,
                "alternate_template": report.alternate_template,
                "alternate_physical_status": alternate.physical_status,
                "alternate_visual_status": alternate.visual_status,
                "alternate_presentation_review_status": alternate.presentation_review_status,
                "cover_letter_ready": report.cover_letter_ready,
                "reasons": report.reasons,
            }
            entry["ready_to_send"] = report.ready_to_send
            entry["review_required"] = not report.ready_to_send
            entry["application_bundle_file"] = "application_bundle_report.json"
        except PresentationGateBlocked as exc:
            reason = str(exc)[:2000]
            results.append({
                "vacancy_id": vacancy_id,
                "run_id": run_id,
                "status": "REVIEW_REQUIRED",
                "ready_to_send": False,
                "presentation_blocked": True,
                "reason": reason,
            })
            entry["ready_to_send"] = False
            entry["review_required"] = True
            entry["presentation_gate"] = {"status": "BLOCKED", "reason": reason}
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"[:2000]
            results.append({
                "vacancy_id": vacancy_id,
                "run_id": run_id,
                "status": "FAILED_PRESENTATION_GATE",
                "ready_to_send": False,
                "error": error,
            })
            entry["ready_to_send"] = False
            entry["review_required"] = True
            entry["presentation_gate"] = {"status": "ERROR", "error": error}

        after = client.telemetry_snapshot()
        presentation_usage = _usage_delta(before, after)
        entry["presentation_usage"] = presentation_usage
        entry["presentation_cost_usd"] = _stage_cost(presentation_usage)
        total_known, complete = _pipeline_cost(entry)
        entry["total_pipeline_known_cost_usd"] = total_known
        entry["total_pipeline_cost_complete"] = complete
        _persist_run_costs(run_dir, entry, presentation_usage)

        result = results[-1]
        if result.get("vacancy_id") == vacancy_id:
            result["generation_cost_usd"] = _generation_cost(entry)
            result["cover_letter_cost_usd"] = _number(entry.get("cover_letter_cost_usd"))
            result["presentation_cost_usd"] = entry.get("presentation_cost_usd")
            result["total_pipeline_known_cost_usd"] = total_known
            result["total_pipeline_cost_complete"] = complete

    _write_json(manifest_path, manifest)
    summary = {
        "schema_version": 3,
        "source_batch_run_id": batch.get("run_id"),
        "result_counts": {
            status: sum(x["status"] == status for x in results)
            for status in sorted({x["status"] for x in results})
        },
        "presentation_usage": client.telemetry_snapshot(),
        "results": results,
    }
    output_path = batch_report.parent / "application_bundle_batch_report.json"
    _write_json(output_path, summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Technical Modern + Harvard bundles and finalize ready_to_send with physical and visual gates.")
    parser.add_argument("--batch-report", required=True)
    parser.add_argument("--outputs", default="outputs/auto")
    parser.add_argument("--vacancy-state", default="vacancy_state")
    parser.add_argument("--generation-state", default="generation_state")
    parser.add_argument("--identity-public", default="cv_presentation/identity.public.yaml")
    parser.add_argument("--brand-profiles-dir", default="cv_presentation/brands")
    parser.add_argument("--max-design-cost-usd", type=float, default=2.0)
    args = parser.parse_args()
    if args.max_design_cost_usd <= 0:
        parser.error("--max-design-cost-usd must be > 0")

    report = finalize_batch(
        batch_report=Path(args.batch_report),
        outputs=Path(args.outputs),
        vacancy_state=Path(args.vacancy_state),
        generation_state=Path(args.generation_state),
        identity_public=Path(args.identity_public),
        brand_profiles_dir=Path(args.brand_profiles_dir),
        max_design_cost_usd=args.max_design_cost_usd,
    )
    print(json.dumps({"result_counts": report["result_counts"]}, ensure_ascii=False, sort_keys=True))
    return 0 if not report["result_counts"].get("FAILED_PRESENTATION_GATE") else 2


if __name__ == "__main__":
    raise SystemExit(main())
