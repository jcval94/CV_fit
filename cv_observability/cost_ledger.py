from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cv_agent.telemetry import PRICING_BASIS, PRICING_SNAPSHOT_DATE, PRICING_SOURCE

LEDGER_SCHEMA_VERSION = 1


def _read(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _num(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return max(float(value), 0.0)
    except (TypeError, ValueError):
        return None


def _first(*values: Any) -> float | None:
    for value in values:
        parsed = _num(value)
        if parsed is not None:
            return parsed
    return None


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _empty() -> dict[str, Any]:
    return {
        "schema_version": LEDGER_SCHEMA_VERSION,
        "pricing_snapshot_date": PRICING_SNAPSHOT_DATE,
        "pricing_basis": PRICING_BASIS,
        "pricing_source": PRICING_SOURCE,
        "legacy_baseline": None,
        "runs": {},
        "events": {},
    }


def _load(path: Path) -> dict[str, Any]:
    ledger = _read(path, _empty())
    if ledger.get("schema_version") != LEDGER_SCHEMA_VERSION:
        raise RuntimeError("cost ledger schema changed; migrate explicitly")
    for key, value in _empty().items():
        ledger.setdefault(key, value)
    return ledger


def _legacy_generation(entry: dict[str, Any], recovered: dict[str, Any]) -> float | None:
    last = entry.get("last_known_metrics") if isinstance(entry.get("last_known_metrics"), dict) else {}
    return _first(
        entry.get("cumulative_known_cost_usd"), entry.get("known_estimated_cost_usd"),
        entry.get("estimated_cost_usd"), entry.get("attempt_known_cost_usd"),
        last.get("cumulative_known_cost_usd"), last.get("known_estimated_cost_usd"),
        last.get("estimated_cost_usd"), recovered.get("generation_cost_usd"),
        recovered.get("estimated_cost_usd"),
    )


def capture_legacy_baseline(*, manifest_path: Path, recovered_metrics_path: Path,
                            ledger_path: Path, source_commit: str | None) -> dict[str, Any]:
    """Freeze known pre-ledger aggregate once; never invent historical call detail."""
    ledger = _load(ledger_path)
    if isinstance(ledger.get("legacy_baseline"), dict):
        return ledger["legacy_baseline"]
    manifest = _read(manifest_path, {"entries": {}})
    recovered = _read(recovered_metrics_path, {"entries": {}})
    recovered_entries = recovered.get("entries", {}) if isinstance(recovered, dict) else {}
    rows: dict[str, Any] = {}
    total = 0.0
    for vacancy_id, raw in sorted((manifest.get("entries") or {}).items()):
        entry = dict(raw or {})
        rec = recovered_entries.get(vacancy_id, {})
        rec = rec if isinstance(rec, dict) else {}
        stages = {
            "generation": _legacy_generation(entry, rec),
            "cover_letter": _num(entry.get("cover_letter_cost_usd")),
            "presentation": _num(entry.get("presentation_cost_usd")),
        }
        known = {k: v for k, v in stages.items() if v is not None}
        if not known:
            continue
        cost = round(sum(known.values()), 8)
        total += cost
        rows[str(vacancy_id)] = {
            "stages": known, "known_cost_usd": cost,
            "current_status": entry.get("status"),
            "ready_to_send": bool(entry.get("ready_to_send")),
            "agent_detail_available": False, "historical_cost_complete": False,
        }
    baseline = {
        "captured_at": _now(), "source_commit": source_commit,
        "known_cost_usd": round(total, 8), "vacancy_count": len(rows), "entries": rows,
        "agent_detail_available": False, "historical_cost_complete": False,
        "note": "Known pre-ledger aggregate reconstructed from versioned state. Old per-call telemetry and repeated downstream costs are not fully recoverable; this is a lower-bound estimate, not fabricated precision.",
    }
    ledger["legacy_baseline"] = baseline
    _write(ledger_path, ledger)
    return baseline


def _event_id(*parts: Any) -> str:
    return hashlib.sha256("|".join(str(x or "") for x in parts).encode()).hexdigest()[:24]


def _error_type(value: Any) -> str | None:
    text = str(value or "").strip()
    return text.split(":", 1)[0][:120] if text else None


def _events(*, batch_run_id: str, vacancy_id: str, vacancy_run_id: str,
            stage: str, status: str | None, usage: dict[str, Any],
            fallback_cost: float | None, source_commit: str | None) -> list[dict[str, Any]]:
    calls = usage.get("calls") if isinstance(usage, dict) else []
    calls = calls if isinstance(calls, list) else []
    out: list[dict[str, Any]] = []
    call_cost = 0.0
    for index, raw in enumerate(calls, 1):
        call = raw if isinstance(raw, dict) else {}
        cost = _num(call.get("estimated_cost_usd"))
        call_cost += cost or 0.0
        out.append({
            "event_id": _event_id(batch_run_id, vacancy_id, vacancy_run_id, stage, index, call.get("name"), call.get("model")),
            "batch_run_id": batch_run_id, "vacancy_id": vacancy_id, "vacancy_run_id": vacancy_run_id,
            "stage": stage, "agent": call.get("name") or f"{stage}_unknown_call",
            "model": call.get("model"), "call_index": index,
            "prompt_tokens": int(call.get("prompt_tokens") or 0),
            "cached_input_tokens": int(call.get("cached_input_tokens") or 0),
            "candidate_tokens": int(call.get("candidate_tokens") or 0),
            "reasoning_tokens": int(call.get("reasoning_tokens") or 0),
            "total_tokens": int(call.get("total_tokens") or 0),
            "duration_ms": int(call.get("duration_ms") or 0),
            "cost_usd": cost, "status": status, "error_type": _error_type(call.get("error")),
            "precision": "call_telemetry", "source_commit": source_commit,
        })
    stage_known = _first(
        usage.get("estimated_cost_usd") if isinstance(usage, dict) else None,
        usage.get("known_estimated_cost_usd") if isinstance(usage, dict) else None,
        fallback_cost,
    )
    residual = None if stage_known is None else round(max(stage_known - call_cost, 0.0), 8)
    if not calls and stage_known is not None:
        residual = stage_known
    if residual is not None and residual > 0.0000001:
        precision = "stage_aggregate" if not calls else "stage_aggregate_residual"
        out.append({
            "event_id": _event_id(batch_run_id, vacancy_id, vacancy_run_id, stage, precision),
            "batch_run_id": batch_run_id, "vacancy_id": vacancy_id, "vacancy_run_id": vacancy_run_id,
            "stage": stage, "agent": f"{stage}_{'aggregate' if not calls else 'unattributed_residual'}",
            "model": None, "call_index": None,
            "prompt_tokens": int(usage.get("prompt_tokens") or 0) if not calls else 0,
            "cached_input_tokens": int(usage.get("cached_input_tokens") or 0) if not calls else 0,
            "candidate_tokens": int(usage.get("candidate_tokens") or 0) if not calls else 0,
            "reasoning_tokens": int(usage.get("reasoning_tokens") or 0) if not calls else 0,
            "total_tokens": int(usage.get("total_tokens") or 0) if not calls else 0,
            "duration_ms": 0, "cost_usd": residual, "status": status, "error_type": None,
            "precision": precision, "source_commit": source_commit,
        })
    return out


def _by_vacancy(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(x.get("vacancy_id")): x for x in report.get("results", []) if isinstance(x, dict) and x.get("vacancy_id")}


def record_run(*, generation_report_path: Path, cover_report_path: Path,
               bundle_report_path: Path, outputs: Path, ledger_path: Path,
               source_commit: str | None, batch_budget_usd: float | None) -> dict[str, Any]:
    generation = _read(generation_report_path, {})
    cover = _read(cover_report_path, {})
    bundle = _read(bundle_report_path, {})
    run_id = str(generation.get("run_id") or "").strip()
    if not run_id:
        raise ValueError(f"generation report has no run_id: {generation_report_path}")
    ledger = _load(ledger_path)
    if isinstance(ledger["runs"].get(run_id), dict):
        return ledger["runs"][run_id]

    cover_by, bundle_by = _by_vacancy(cover), _by_vacancy(bundle)
    events: list[dict[str, Any]] = []
    for item in generation.get("results", []):
        if not isinstance(item, dict):
            continue
        vacancy_id, vacancy_run_id = str(item.get("vacancy_id") or ""), str(item.get("run_id") or "")
        if not vacancy_id or not vacancy_run_id:
            continue
        run_dir = outputs / vacancy_id / vacancy_run_id
        gen_usage = _read(run_dir / "usage_report.json", {})
        events += _events(
            batch_run_id=run_id, vacancy_id=vacancy_id, vacancy_run_id=vacancy_run_id,
            stage="generation", status=str(item.get("status") or "UNKNOWN"), usage=gen_usage,
            fallback_cost=_first(item.get("attempt_known_cost_usd"), item.get("known_estimated_cost_usd"), item.get("estimated_cost_usd")),
            source_commit=source_commit,
        )
        run_report = _read(run_dir / "run_report.json", {})
        stage_usage = run_report.get("stage_usage") if isinstance(run_report.get("stage_usage"), dict) else {}
        cov, cov_usage = cover_by.get(vacancy_id, {}), stage_usage.get("cover_letter", {})
        if cov or cov_usage:
            events += _events(
                batch_run_id=run_id, vacancy_id=vacancy_id, vacancy_run_id=vacancy_run_id,
                stage="cover_letter", status=str(cov.get("status") or run_report.get("cover_letter_status") or "UNKNOWN"),
                usage=cov_usage if isinstance(cov_usage, dict) else {},
                fallback_cost=_first(cov.get("known_estimated_cost_usd"), cov.get("estimated_cost_usd"), run_report.get("cover_letter_cost_usd")),
                source_commit=source_commit,
            )
        bun, pres_usage = bundle_by.get(vacancy_id, {}), stage_usage.get("presentation", {})
        if bun or pres_usage:
            events += _events(
                batch_run_id=run_id, vacancy_id=vacancy_id, vacancy_run_id=vacancy_run_id,
                stage="presentation", status=str(bun.get("status") or "UNKNOWN"),
                usage=pres_usage if isinstance(pres_usage, dict) else {},
                fallback_cost=_first(bun.get("presentation_cost_usd"), run_report.get("presentation_cost_usd")),
                source_commit=source_commit,
            )

    for event in events:
        ledger["events"][event["event_id"]] = event
    total_spend = round(sum(_num(e.get("cost_usd")) or 0.0 for e in events), 8)
    generation_spend = round(sum(_num(e.get("cost_usd")) or 0.0 for e in events if e.get("stage") == "generation"), 8)
    downstream_spend = round(max(total_spend - generation_spend, 0.0), 8)
    call_spend = round(sum(_num(e.get("cost_usd")) or 0.0 for e in events if e.get("precision") == "call_telemetry"), 8)
    unpriced = sum(e.get("precision") == "call_telemetry" and e.get("cost_usd") is None for e in events)
    bundles = [x for x in bundle.get("results", []) if isinstance(x, dict)]
    summary = {
        "run_id": run_id, "source_commit": source_commit or generation.get("source_commit"), "recorded_at": _now(),
        "generation_budget_usd": batch_budget_usd, "budget_usd": batch_budget_usd,
        "known_spend_usd": total_spend, "generation_known_spend_usd": generation_spend,
        "downstream_known_spend_usd": downstream_spend, "call_level_known_spend_usd": call_spend,
        "telemetry_coverage_pct": round(call_spend / total_spend * 100.0, 2) if total_spend else 100.0,
        "event_count": len(events), "call_count": sum(e.get("precision") == "call_telemetry" for e in events),
        "unpriced_call_count": unpriced, "candidate_count": generation.get("candidate_count"),
        "source_candidate_count": generation.get("source_candidate_count"), "generation_attempts": generation.get("generation_attempts"),
        "generation_result_counts": generation.get("result_counts", {}), "bundle_result_counts": bundle.get("result_counts", {}),
        "ready_count": sum(bool(x.get("ready_to_send")) for x in bundles), "event_ids": [e["event_id"] for e in events],
    }
    ledger["runs"][run_id] = summary
    _write(ledger_path, ledger)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Persist append-only call-aware CV_fit cost ledger.")
    sub = parser.add_subparsers(dest="command", required=True)
    baseline = sub.add_parser("baseline")
    baseline.add_argument("--manifest", default="generation_state/manifest.json")
    baseline.add_argument("--recovered-metrics", default="generation_state/recovered_metrics.json")
    baseline.add_argument("--ledger", default="generation_state/cost_ledger.json")
    baseline.add_argument("--source-commit", default=None)
    record = sub.add_parser("record-run")
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
            manifest_path=Path(args.manifest), recovered_metrics_path=Path(args.recovered_metrics),
            ledger_path=Path(args.ledger), source_commit=args.source_commit,
        )
        print(json.dumps({"known_cost_usd": result.get("known_cost_usd"), "vacancy_count": result.get("vacancy_count"), "historical_cost_complete": result.get("historical_cost_complete")}, sort_keys=True))
        return 0
    result = record_run(
        generation_report_path=Path(args.generation_report), cover_report_path=Path(args.cover_report),
        bundle_report_path=Path(args.bundle_report), outputs=Path(args.outputs), ledger_path=Path(args.ledger),
        source_commit=args.source_commit, batch_budget_usd=args.batch_budget_usd,
    )
    print(json.dumps({"run_id": result.get("run_id"), "known_spend_usd": result.get("known_spend_usd"), "generation_known_spend_usd": result.get("generation_known_spend_usd"), "telemetry_coverage_pct": result.get("telemetry_coverage_pct"), "call_count": result.get("call_count")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
