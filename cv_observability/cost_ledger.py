from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cv_agent.telemetry import PRICING_BASIS, PRICING_SNAPSHOT_DATE, PRICING_SOURCE


LEDGER_SCHEMA_VERSION = 1


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return max(float(value), 0.0)
    except (TypeError, ValueError):
        return None


def _first_cost(*values: Any) -> float | None:
    for value in values:
        parsed = _number(value)
        if parsed is not None:
            return parsed
    return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _empty_ledger() -> dict[str, Any]:
    return {
        "schema_version": LEDGER_SCHEMA_VERSION,
        "pricing_snapshot_date": PRICING_SNAPSHOT_DATE,
        "pricing_basis": PRICING_BASIS,
        "pricing_source": PRICING_SOURCE,
        "legacy_baseline": None,
        "runs": {},
        "events": {},
    }


def _load_ledger(path: Path) -> dict[str, Any]:
    ledger = _read_json(path, _empty_ledger())
    if ledger.get("schema_version") != LEDGER_SCHEMA_VERSION:
        raise RuntimeError("cost ledger schema changed; migrate explicitly instead of silently rewriting history")
    ledger.setdefault("legacy_baseline", None)
    ledger.setdefault("runs", {})
    ledger.setdefault("events", {})
    ledger.setdefault("pricing_snapshot_date", PRICING_SNAPSHOT_DATE)
    ledger.setdefault("pricing_basis", PRICING_BASIS)
    ledger.setdefault("pricing_source", PRICING_SOURCE)
    return ledger


def _legacy_generation_cost(entry: dict[str, Any], recovered: dict[str, Any]) -> float | None:
    last = entry.get("last_known_metrics") if isinstance(entry.get("last_known_metrics"), dict) else {}
    return _first_cost(
        entry.get("cumulative_known_cost_usd"),
        entry.get("known_estimated_cost_usd"),
        entry.get("estimated_cost_usd"),
        entry.get("attempt_known_cost_usd"),
        last.get("cumulative_known_cost_usd"),
        last.get("known_estimated_cost_usd"),
        last.get("estimated_cost_usd"),
        recovered.get("generation_cost_usd"),
        recovered.get("estimated_cost_usd"),
    )


def capture_legacy_baseline(
    *,
    manifest_path: Path,
    recovered_metrics_path: Path,
    ledger_path: Path,
    source_commit: str | None,
) -> dict[str, Any]:
    """Freeze the known pre-ledger spend once, without inventing call-level history.

    Historical generation state predates the append-only ledger. The manifest can
    prove known aggregate spend, but it cannot reconstruct every old model call,
    especially repeated cover/presentation work. That limitation is persisted as
    metadata so the dashboard never presents false precision.
    """
    ledger = _load_ledger(ledger_path)
    if isinstance(ledger.get("legacy_baseline"), dict):
        return ledger["legacy_baseline"]

    manifest = _read_json(manifest_path, {"entries": {}})
    recovered_payload = _read_json(recovered_metrics_path, {"entries": {}})
    recovered_entries = recovered_payload.get("entries", {}) if isinstance(recovered_payload, dict) else {}
    rows: dict[str, Any] = {}
    known_total = 0.0

    for vacancy_id, raw in sorted((manifest.get("entries") or {}).items()):
        entry = dict(raw or {})
        recovered = recovered_entries.get(vacancy_id, {})
        recovered = recovered if isinstance(recovered, dict) else {}
        generation = _legacy_generation_cost(entry, recovered)
        cover = _number(entry.get("cover_letter_cost_usd"))
        presentation = _number(entry.get("presentation_cost_usd"))
        stages = {
            "generation": generation,
            "cover_letter": cover,
            "presentation": presentation,
        }
        stage_known = {key: value for key, value in stages.items() if value is not None}
        if not stage_known:
            continue
        total = round(sum(stage_known.values()), 8)
        known_total += total
        rows[str(vacancy_id)] = {
            "stages": stage_known,
            "known_cost_usd": total,
            "current_status": entry.get("status"),
            "ready_to_send": bool(entry.get("ready_to_send")),
            "agent_detail_available": False,
            "historical_cost_complete": False,
        }

    baseline = {
        "captured_at": _utc_now(),
        "source_commit": source_commit,
        "known_cost_usd": round(known_total, 8),
        "vacancy_count": len(rows),
        "entries": rows,
        "agent_detail_available": False,
        "historical_cost_complete": False,
        "note": (
            "Known pre-ledger aggregate reconstructed from versioned generation state. "
            "Old per-call telemetry and repeated downstream stage costs are not recoverable, "
            "so this is a documented lower-bound estimate rather than fabricated detail."
        ),
    }
    ledger["legacy_baseline"] = baseline
    _write_json(ledger_path, ledger)
    return baseline


def _event_id(*parts: Any) -> str:
    payload = "|".join(str(part if part is not None else "") for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def _error_type(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return text.split(":", 1)[0][:120]


def _call_events(
    *,
    batch_run_id: str,
    vacancy_id: str,
    vacancy_run_id: str,
    stage: str,
    status: str | None,
    usage: dict[str, Any],
    fallback_cost: float | None,
    source_commit: str | None,
) -> list[dict[str, Any]]:
    calls = usage.get("calls") if isinstance(usage, dict) else None
    calls = calls if isinstance(calls, list) else []
    events: list[dict[str, Any]] = []
    known_from_calls = 0.0

    for index, raw in enumerate(calls, start=1):
        call = raw if isinstance(raw, dict) else {}
        cost = _number(call.get("estimated_cost_usd"))
        if cost is not None:
            known_from_calls += cost
        event_id = _event_id(batch_run_id, vacancy_id, vacancy_run_id, stage, index, call.get("name"), call.get("model"))
        events.append({
            "event_id": event_id,
            "batch_run_id": batch_run_id,
            "vacancy_id": vacancy_id,
            "vacancy_run_id": vacancy_run_id,
            "stage": stage,
            "agent": call.get("name") or f"{stage}_unknown_call",
            "model": call.get("model"),
            "call_index": index,
            "prompt_tokens": int(call.get("prompt_tokens") or 0),
            "cached_input_tokens": int(call.get("cached_input_tokens") or 0),
            "candidate_tokens": int(call.get("candidate_tokens") or 0),
            "reasoning_tokens": int(call.get("reasoning_tokens") or 0),
            "total_tokens": int(call.get("total_tokens") or 0),
            "duration_ms": int(call.get("duration_ms") or 0),
            "cost_usd": cost,
            "status": status,
            "error_type": _error_type(call.get("error")),
            "precision": "call_telemetry",
            "source_commit": source_commit,
        })

    stage_known = _first_cost(
        usage.get("estimated_cost_usd") if isinstance(usage, dict) else None,
        usage.get("known_estimated_cost_usd") if isinstance(usage, dict) else None,
        fallback_cost,
    )
    if not calls and stage_known is not None:
        event_id = _event_id(batch_run_id, vacancy_id, vacancy_run_id, stage, "aggregate")
        events.append({
            "event_id": event_id,
            "batch_run_id": batch_run_id,
            "vacancy_id": vacancy_id,
            "vacancy_run_id": vacancy_run_id,
            "stage": stage,
            "agent": f"{stage}_aggregate",
            "model": None,
            "call_index": None,
            "prompt_tokens": int(usage.get("prompt_tokens") or 0) if isinstance(usage, dict) else 0,
            "cached_input_tokens": int(usage.get("cached_input_tokens") or 0) if isinstance(usage, dict) else 0,
            "candidate_tokens": int(usage.get("candidate_tokens") or 0) if isinstance(usage, dict) else 0,
            "reasoning_tokens": int(usage.get("reasoning_tokens") or 0) if isinstance(usage, dict) else 0,
            "total_tokens": int(usage.get("total_tokens") or 0) if isinstance(usage, dict) else 0,
            "duration_ms": 0,
            "cost_usd": stage_known,
            "status": status,
            "error_type": None,
            "precision": "stage_aggregate",
            "source_commit": source_commit,
        })
    elif calls and stage_known is not None:
        residual = round(max(stage_known - known_from_calls, 0.0), 8)
        if residual > 0.0000001:
            event_id = _event_id(batch_run_id, vacancy_id, vacancy_run_id, stage, "residual")
            events.append({
                "event_id": event_id,
                "batch_run_id": batch_run_id,
                "vacancy_id": vacancy_id,
                "vacancy_run_id": vacancy_run_id,
                "stage": stage,
                "agent": f"{stage}_unattributed_residual",
                "model": None,
                "call_index": None,
                "prompt_tokens": 0,
                "cached_input_tokens": 0,
                "candidate_tokens": 0,
                "reasoning_tokens": 0,
                "total_tokens": 0,
                "duration_ms": 0,
                "cost_usd": residual,
                "status": status,
                "error_type": None,
                "precision": "stage_aggregate_residual",
                "source_commit": source_commit,
            })
    return events


def _results_by_vacancy(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("vacancy_id")): item
        for item in report.get("results", [])
        if isinstance(item, dict) and item.get("vacancy_id")
    }


def record_run(
    *,
    generation_report_path: Path,
    cover_report_path: Path,
    bundle_report_path: Path,
    outputs: Path,
    ledger_path: Path,
    source_commit: str | None,
    batch_budget_usd: float | None,
) -> dict[str, Any]:
    generation = _read_json(generation_report_path, {})
    cover = _read_json(cover_report_path, {})
    bundle = _read_json(bundle_report_path, {})
    batch_run_id = str(generation.get("run_id") or "").strip()
    if not batch_run_id:
        raise ValueError(f"generation report has no run_id: {generation_report_path}")

    ledger = _load_ledger(ledger_path)
    existing = ledger["runs"].get(batch_run_id)
    if isinstance(existing, dict):
        return existing

    cover_by = _results_by_vacancy(cover)
    bundle_by = _results_by_vacancy(bundle)
    events: list[dict[str, Any]] = []

    for item in generation.get("results", []):
        if not isinstance(item, dict):
            continue
        vacancy_id = str(item.get("vacancy_id") or "")
        vacancy_run_id = str(item.get("run_id") or "")
        if not vacancy_id or not vacancy_run_id:
            continue
        run_dir = outputs / vacancy_id / vacancy_run_id
        generation_usage = _read_json(run_dir / "usage_report.json", {})
        events.extend(_call_events(
            batch_run_id=batch_run_id,
            vacancy_id=vacancy_id,
            vacancy_run_id=vacancy_run_id,
            stage="generation",
            status=str(item.get("status") or "UNKNOWN"),
            usage=generation_usage,
            fallback_cost=_first_cost(item.get("attempt_known_cost_usd"), item.get("known_estimated_cost_usd"), item.get("estimated_cost_usd")),
            source_commit=source_commit,
        ))

        run_report = _read_json(run_dir / "run_report.json", {})
        stage_usage = run_report.get("stage_usage") if isinstance(run_report, dict) else {}
        stage_usage = stage_usage if isinstance(stage_usage, dict) else {}

        cover_item = cover_by.get(vacancy_id, {})
        cover_usage = stage_usage.get("cover_letter") if isinstance(stage_usage.get("cover_letter"), dict) else {}
        if cover_item or cover_usage:
            events.extend(_call_events(
                batch_run_id=batch_run_id,
                vacancy_id=vacancy_id,
                vacancy_run_id=vacancy_run_id,
                stage="cover_letter",
                status=str(cover_item.get("status") or run_report.get("cover_letter_status") or "UNKNOWN"),
                usage=cover_usage,
                fallback_cost=_first_cost(cover_item.get("known_estimated_cost_usd"), cover_item.get("estimated_cost_usd"), run_report.get("cover_letter_cost_usd")),
                source_commit=source_commit,
            ))

        bundle_item = bundle_by.get(vacancy_id, {})
        presentation_usage = stage_usage.get("presentation") if isinstance(stage_usage.get("presentation"), dict) else {}
        if bundle_item or presentation_usage:
            events.extend(_call_events(
                batch_run_id=batch_run_id,
                vacancy_id=vacancy_id,
                vacancy_run_id=vacancy_run_id,
                stage="presentation",
                status=str(bundle_item.get("status") or "UNKNOWN"),
                usage=presentation_usage,
                fallback_cost=_first_cost(bundle_item.get("presentation_cost_usd"), run_report.get("presentation_cost_usd")),
                source_commit=source_commit,
            ))

    for event in events:
        ledger["events"][event["event_id"]] = event

    known_spend = round(sum(_number(event.get("cost_usd")) or 0.0 for event in events), 8)
    precise_spend = round(sum(
        _number(event.get("cost_usd")) or 0.0
        for event in events
        if event.get("precision") == "call_telemetry"
    ), 8)
    unpriced_calls = sum(event.get("precision") == "call_telemetry" and event.get("cost_usd") is None for event in events)
    bundle_results = [item for item in bundle.get("results", []) if isinstance(item, dict)]
    summary = {
        "run_id": batch_run_id,
        "source_commit": source_commit or generation.get("source_commit"),
        "recorded_at": _utc_now(),
        "budget_usd": batch_budget_usd,
        "known_spend_usd": known_spend,
        "call_level_known_spend_usd": precise_spend,
        "telemetry_coverage_pct": round((precise_spend / known_spend * 100.0), 2) if known_spend else 100.0,
        "event_count": len(events),
        "call_count": sum(event.get("precision") == "call_telemetry" for event in events),
        "unpriced_call_count": unpriced_calls,
        "candidate_count": generation.get("candidate_count"),
        "source_candidate_count": generation.get("source_candidate_count"),
        "generation_attempts": generation.get("generation_attempts"),
        "generation_result_counts": generation.get("result_counts", {}),
        "bundle_result_counts": bundle.get("result_counts", {}),
        "ready_count": sum(bool(item.get("ready_to_send")) for item in bundle_results),
        "event_ids": [event["event_id"] for event in events],
    }
    ledger["runs"][batch_run_id] = summary
    _write_json(ledger_path, ledger)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Persist CV_fit OpenAI spend as an append-only, call-aware cost ledger.")
    sub = parser.add_subparsers(dest="command", required=True)

    baseline = sub.add_parser("baseline", help="Freeze known pre-ledger aggregate spend exactly once.")
    baseline.add_argument("--manifest", default="generation_state/manifest.json")
    baseline.add_argument("--recovered-metrics", default="generation_state/recovered_metrics.json")
    baseline.add_argument("--ledger", default="generation_state/cost_ledger.json")
    baseline.add_argument("--source-commit", default=None)

    record = sub.add_parser("record-run", help="Append one completed generation batch without double counting retries.")
    record.add_argument("--generation-report", required=True)
    record.add_argument("--cover-report", required=True)
    record.add_argument("--bundle-report", required=True)
    record.add_argument("--outputs", default="outputs/auto")
    record.add_argument("--ledger", default="generation_state/cost_ledger.json")
    record.add_argument("--source-commit", default=None)
    record.add_argument("--batch-budget-usd", type=float, default=None)

    args = parser.parse_args()
    if args.command == "baseline":
        result = capture_legacy_baseline(
            manifest_path=Path(args.manifest),
            recovered_metrics_path=Path(args.recovered_metrics),
            ledger_path=Path(args.ledger),
            source_commit=args.source_commit,
        )
        print(json.dumps({
            "known_cost_usd": result.get("known_cost_usd"),
            "vacancy_count": result.get("vacancy_count"),
            "historical_cost_complete": result.get("historical_cost_complete"),
        }, sort_keys=True))
        return 0

    result = record_run(
        generation_report_path=Path(args.generation_report),
        cover_report_path=Path(args.cover_report),
        bundle_report_path=Path(args.bundle_report),
        outputs=Path(args.outputs),
        ledger_path=Path(args.ledger),
        source_commit=args.source_commit,
        batch_budget_usd=args.batch_budget_usd,
    )
    print(json.dumps({
        "run_id": result.get("run_id"),
        "known_spend_usd": result.get("known_spend_usd"),
        "telemetry_coverage_pct": result.get("telemetry_coverage_pct"),
        "call_count": result.get("call_count"),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
