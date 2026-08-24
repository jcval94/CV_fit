from __future__ import annotations

import argparse
import html
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


NAV_MARKER = 'id="cvfit-budget-nav"'


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return max(float(value), 0.0)
    except (TypeError, ValueError):
        return None


def _money(value: Any) -> str:
    parsed = _number(value)
    return f"${parsed:,.4f}" if parsed is not None else "n/a"


def _safe(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def _pct(value: Any) -> str:
    parsed = _number(value)
    return f"{parsed:.1f}%" if parsed is not None else "n/a"


def _vacancy_catalog(vacancy_state: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for path in sorted((vacancy_state / "records").glob("*.json")):
        record = _read_json(path, {})
        if not isinstance(record, dict):
            continue
        vacancy_id = str(record.get("vacancy_id") or path.stem)
        rows[vacancy_id] = {
            "company": record.get("company") or "Unknown company",
            "role_title": record.get("role_title") or "Unknown role",
            "url": record.get("url") or "",
            "fit_score": record.get("fit_score"),
        }
    return rows


def _legacy_stage_totals(baseline: dict[str, Any]) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for row in (baseline.get("entries") or {}).values():
        if not isinstance(row, dict):
            continue
        for stage, value in (row.get("stages") or {}).items():
            parsed = _number(value)
            if parsed is not None:
                totals[str(stage)] += parsed
    return {key: round(value, 8) for key, value in totals.items()}


def _event_cost(event: dict[str, Any]) -> float:
    return _number(event.get("cost_usd")) or 0.0


def _aggregate_events(events: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for event in events:
        label = str(event.get(key) or "Unattributed")
        row = groups.setdefault(label, {
            "name": label,
            "calls": 0,
            "prompt_tokens": 0,
            "cached_input_tokens": 0,
            "candidate_tokens": 0,
            "reasoning_tokens": 0,
            "total_tokens": 0,
            "known_cost_usd": 0.0,
            "unpriced_calls": 0,
        })
        if event.get("precision") == "call_telemetry":
            row["calls"] += 1
            if event.get("cost_usd") is None:
                row["unpriced_calls"] += 1
        for token_key in ("prompt_tokens", "cached_input_tokens", "candidate_tokens", "reasoning_tokens", "total_tokens"):
            row[token_key] += int(event.get(token_key) or 0)
        row["known_cost_usd"] += _event_cost(event)
    for row in groups.values():
        row["known_cost_usd"] = round(row["known_cost_usd"], 8)
    return sorted(groups.values(), key=lambda row: (-row["known_cost_usd"], row["name"]))


def build_payload(*, ledger: dict[str, Any], manifest: dict[str, Any], vacancy_state: Path) -> dict[str, Any]:
    catalog = _vacancy_catalog(vacancy_state)
    baseline = ledger.get("legacy_baseline") if isinstance(ledger.get("legacy_baseline"), dict) else {}
    events = [dict(value) for value in (ledger.get("events") or {}).values() if isinstance(value, dict)]
    runs = [dict(value) for value in (ledger.get("runs") or {}).values() if isinstance(value, dict)]
    runs.sort(key=lambda row: str(row.get("recorded_at") or ""), reverse=True)
    run_meta = {str(row.get("run_id")): row for row in runs}

    legacy_known = _number(baseline.get("known_cost_usd")) or 0.0
    recorded_known = round(sum(_event_cost(event) for event in events), 8)
    total_known = round(legacy_known + recorded_known, 8)
    call_known = round(sum(
        _event_cost(event) for event in events if event.get("precision") == "call_telemetry"
    ), 8)
    current_coverage = round(call_known / recorded_known * 100.0, 2) if recorded_known else 100.0
    all_history_coverage = round(call_known / total_known * 100.0, 2) if total_known else 100.0

    stage_totals: dict[str, float] = defaultdict(float)
    for stage, value in _legacy_stage_totals(baseline).items():
        stage_totals[stage] += value
    for event in events:
        stage_totals[str(event.get("stage") or "unknown")] += _event_cost(event)
    stage_rows = [
        {"name": stage, "known_cost_usd": round(cost, 8)}
        for stage, cost in sorted(stage_totals.items(), key=lambda item: (-item[1], item[0]))
    ]

    agent_rows = _aggregate_events(events, "agent")
    model_rows = _aggregate_events(events, "model")
    if legacy_known:
        legacy_row = {
            "name": "Historical pre-ledger — agent/model unavailable",
            "calls": 0,
            "prompt_tokens": 0,
            "cached_input_tokens": 0,
            "candidate_tokens": 0,
            "reasoning_tokens": 0,
            "total_tokens": 0,
            "known_cost_usd": round(legacy_known, 8),
            "unpriced_calls": 0,
        }
        agent_rows.append(dict(legacy_row))
        model_rows.append(dict(legacy_row))

    manifest_entries = manifest.get("entries") or {}
    application_bundles = sum(
        isinstance(entry, dict) and bool(entry.get("application_bundle_file") or entry.get("presentation_gate"))
        for entry in manifest_entries.values()
    )
    ready_count = sum(isinstance(entry, dict) and bool(entry.get("ready_to_send")) for entry in manifest_entries.values())
    paid_generation_runs = {
        str(event.get("vacancy_run_id"))
        for event in events
        if event.get("stage") == "generation" and _event_cost(event) > 0 and event.get("vacancy_run_id")
    }

    cost_by_vacancy: dict[str, dict[str, Any]] = {}
    for vacancy_id, row in (baseline.get("entries") or {}).items():
        if not isinstance(row, dict):
            continue
        target = cost_by_vacancy.setdefault(str(vacancy_id), {"legacy_cost_usd": 0.0, "recorded_cost_usd": 0.0, "stages": defaultdict(float), "calls": 0})
        target["legacy_cost_usd"] += _number(row.get("known_cost_usd")) or 0.0
        for stage, value in (row.get("stages") or {}).items():
            target["stages"][str(stage)] += _number(value) or 0.0
    for event in events:
        vacancy_id = str(event.get("vacancy_id") or "")
        if not vacancy_id:
            continue
        target = cost_by_vacancy.setdefault(vacancy_id, {"legacy_cost_usd": 0.0, "recorded_cost_usd": 0.0, "stages": defaultdict(float), "calls": 0})
        cost = _event_cost(event)
        target["recorded_cost_usd"] += cost
        target["stages"][str(event.get("stage") or "unknown")] += cost
        if event.get("precision") == "call_telemetry":
            target["calls"] += 1

    application_rows: list[dict[str, Any]] = []
    for vacancy_id, cost in cost_by_vacancy.items():
        identity = catalog.get(vacancy_id, {})
        current = manifest_entries.get(vacancy_id, {}) if isinstance(manifest_entries.get(vacancy_id), dict) else {}
        total = round(cost["legacy_cost_usd"] + cost["recorded_cost_usd"], 8)
        application_rows.append({
            "vacancy_id": vacancy_id,
            "company": identity.get("company") or vacancy_id,
            "role_title": identity.get("role_title") or "",
            "url": identity.get("url") or "",
            "fit_score": identity.get("fit_score"),
            "status": current.get("status"),
            "ready_to_send": bool(current.get("ready_to_send")),
            "calls": cost["calls"],
            "legacy_cost_usd": round(cost["legacy_cost_usd"], 8),
            "recorded_cost_usd": round(cost["recorded_cost_usd"], 8),
            "known_cost_usd": total,
            "stages": {key: round(value, 8) for key, value in cost["stages"].items()},
        })
    application_rows.sort(key=lambda row: (-row["known_cost_usd"], row["company"], row["role_title"]))

    enriched_events: list[dict[str, Any]] = []
    for event in events:
        row = dict(event)
        identity = catalog.get(str(event.get("vacancy_id") or ""), {})
        meta = run_meta.get(str(event.get("batch_run_id") or ""), {})
        row["company"] = identity.get("company") or row.get("vacancy_id")
        row["role_title"] = identity.get("role_title") or ""
        row["recorded_at"] = meta.get("recorded_at")
        enriched_events.append(row)
    enriched_events.sort(key=lambda row: (str(row.get("recorded_at") or ""), str(row.get("vacancy_run_id") or ""), str(row.get("stage") or ""), int(row.get("call_index") or 0)), reverse=True)

    failed_call_spend = round(sum(_event_cost(event) for event in events if event.get("error_type")), 8)
    review_loop_spend = round(sum(
        _event_cost(event) for event in events
        if str(event.get("agent") or "").startswith(("senior_headhunter_", "cv_reviser_"))
    ), 8)
    premium_spend = round(sum(
        _event_cost(event) for event in events if "sol" in str(event.get("model") or "").casefold()
    ), 8)
    below_target_spend = round(sum(
        _event_cost(event) for event in events
        if event.get("stage") == "generation" and event.get("status") == "COMPLETED_BELOW_TARGET"
    ), 8)
    failed_generation_spend = round(sum(
        _event_cost(event) for event in events
        if event.get("stage") == "generation" and str(event.get("status") or "").startswith("FAILED")
    ), 8)

    latest = runs[0] if runs else {}
    latest_budget = _number(latest.get("budget_usd"))
    latest_spend = _number(latest.get("known_spend_usd")) or 0.0
    latest_budget_pct = round(latest_spend / latest_budget * 100.0, 2) if latest_budget else None

    return {
        "schema_version": 1,
        "pricing": {
            "snapshot_date": ledger.get("pricing_snapshot_date"),
            "basis": ledger.get("pricing_basis"),
            "source": ledger.get("pricing_source"),
            "note": "Repository telemetry estimate from token usage and pinned public pricing; not an OpenAI invoice or account balance.",
        },
        "summary": {
            "known_spend_usd": total_known,
            "legacy_known_spend_usd": round(legacy_known, 8),
            "recorded_known_spend_usd": recorded_known,
            "call_level_known_spend_usd": call_known,
            "since_ledger_telemetry_coverage_pct": current_coverage,
            "all_history_agent_detail_coverage_pct": all_history_coverage,
            "tracked_vacancies": len(manifest_entries),
            "application_bundles": application_bundles,
            "ready_applications": ready_count,
            "recorded_paid_generation_attempts": len(paid_generation_runs),
            "known_cost_per_current_bundle_usd": round(total_known / application_bundles, 8) if application_bundles else None,
            "known_cost_per_ready_usd": round(total_known / ready_count, 8) if ready_count else None,
        },
        "latest_run": {
            **latest,
            "budget_consumed_pct": latest_budget_pct,
        } if latest else {},
        "cost_concentrations": {
            "review_loop_spend_usd": review_loop_spend,
            "premium_model_spend_usd": premium_spend,
            "failed_call_spend_usd": failed_call_spend,
            "below_target_generation_spend_usd": below_target_spend,
            "failed_generation_spend_usd": failed_generation_spend,
            "note": "These categories can overlap; do not sum them as savings.",
        },
        "stages": stage_rows,
        "agents": agent_rows,
        "models": model_rows,
        "applications": application_rows,
        "runs": runs,
        "events": enriched_events,
        "legacy_baseline": {
            "known_cost_usd": baseline.get("known_cost_usd"),
            "vacancy_count": baseline.get("vacancy_count"),
            "historical_cost_complete": baseline.get("historical_cost_complete"),
            "note": baseline.get("note"),
        } if baseline else {},
    }


def _bar_rows(rows: list[dict[str, Any]], *, total: float, name_key: str = "name") -> str:
    html_rows: list[str] = []
    for row in rows:
        cost = _number(row.get("known_cost_usd")) or 0.0
        width = min(cost / total * 100.0, 100.0) if total else 0.0
        html_rows.append(
            f'<div class="bar-row"><div class="bar-label"><strong>{_safe(row.get(name_key))}</strong><span>{_money(cost)}</span></div>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{width:.2f}%"></div></div></div>'
        )
    return "".join(html_rows) or '<div class="empty">No cost data yet.</div>'


def _agent_table(rows: list[dict[str, Any]], total: float) -> str:
    output: list[str] = []
    for row in rows:
        cost = _number(row.get("known_cost_usd")) or 0.0
        share = cost / total * 100.0 if total else 0.0
        output.append(
            "<tr>" + "".join([
                f"<td><strong>{_safe(row.get('name'))}</strong></td>",
                f"<td>{int(row.get('calls') or 0)}</td>",
                f"<td>{int(row.get('prompt_tokens') or 0):,}</td>",
                f"<td>{int(row.get('cached_input_tokens') or 0):,}</td>",
                f"<td>{int(row.get('candidate_tokens') or 0):,}</td>",
                f"<td>{int(row.get('reasoning_tokens') or 0):,}</td>",
                f"<td>{_money(cost)}</td>",
                f"<td>{share:.1f}%</td>",
                f"<td>{int(row.get('unpriced_calls') or 0)}</td>",
            ]) + "</tr>"
        )
    return "".join(output) or '<tr><td colspan="9">No detailed calls recorded yet.</td></tr>'


def _application_table(rows: list[dict[str, Any]]) -> str:
    output: list[str] = []
    for row in rows:
        stages = row.get("stages") or {}
        company = _safe(row.get("company"))
        if row.get("url"):
            company = f'<a href="{_safe(row.get("url"))}" target="_blank" rel="noopener">{company}</a>'
        output.append(
            "<tr>" + "".join([
                f"<td>{company}<div class=small>{_safe(row.get('role_title'))}</div></td>",
                f"<td>{_safe(row.get('status') or 'n/a')}</td>",
                f"<td>{'READY' if row.get('ready_to_send') else 'review'}</td>",
                f"<td>{_money(stages.get('generation'))}</td>",
                f"<td>{_money(stages.get('cover_letter'))}</td>",
                f"<td>{_money(stages.get('presentation'))}</td>",
                f"<td><strong>{_money(row.get('known_cost_usd'))}</strong></td>",
                f"<td>{int(row.get('calls') or 0)}</td>",
            ]) + "</tr>"
        )
    return "".join(output) or '<tr><td colspan="8">No application cost data yet.</td></tr>'


def _run_table(rows: list[dict[str, Any]]) -> str:
    output: list[str] = []
    for row in rows:
        budget = _number(row.get("budget_usd"))
        spend = _number(row.get("known_spend_usd")) or 0.0
        ratio = spend / budget * 100 if budget else None
        output.append(
            "<tr>" + "".join([
                f"<td><code>{_safe(row.get('run_id'))}</code><div class=small>{_safe(row.get('recorded_at'))}</div></td>",
                f"<td>{_safe(row.get('source_candidate_count') if row.get('source_candidate_count') is not None else row.get('candidate_count'))}</td>",
                f"<td>{_safe(row.get('generation_attempts'))}</td>",
                f"<td>{_safe(row.get('ready_count'))}</td>",
                f"<td>{_money(spend)}</td>",
                f"<td>{_money(budget)}</td>",
                f"<td>{f'{ratio:.1f}%' if ratio is not None else 'n/a'}</td>",
                f"<td>{_pct(row.get('telemetry_coverage_pct'))}</td>",
            ]) + "</tr>"
        )
    return "".join(output) or '<tr><td colspan="8">No ledger-era runs recorded yet.</td></tr>'


def _event_table(rows: list[dict[str, Any]]) -> str:
    output: list[str] = []
    for row in rows:
        output.append(
            f'<tr data-search="{_safe(" ".join(str(row.get(key) or "") for key in ("company", "role_title", "stage", "agent", "model", "status", "error_type")))}">' + "".join([
                f"<td>{_safe(row.get('recorded_at') or '')}<div class=small><code>{_safe(row.get('vacancy_run_id'))}</code></div></td>",
                f"<td>{_safe(row.get('company'))}<div class=small>{_safe(row.get('role_title'))}</div></td>",
                f"<td>{_safe(row.get('stage'))}</td>",
                f"<td><strong>{_safe(row.get('agent'))}</strong></td>",
                f"<td>{_safe(row.get('model') or 'unattributed')}</td>",
                f"<td>{int(row.get('prompt_tokens') or 0):,}</td>",
                f"<td>{int(row.get('cached_input_tokens') or 0):,}</td>",
                f"<td>{int(row.get('candidate_tokens') or 0):,}</td>",
                f"<td>{int(row.get('reasoning_tokens') or 0):,}</td>",
                f"<td><strong>{_money(row.get('cost_usd'))}</strong></td>",
                f"<td>{_safe(row.get('status') or '')}{('<div class=small>error: '+_safe(row.get('error_type'))+'</div>') if row.get('error_type') else ''}</td>",
                f"<td>{_safe(row.get('precision'))}</td>",
            ]) + "</tr>"
        )
    return "".join(output) or '<tr><td colspan="12">No call-level events recorded yet.</td></tr>'


def render_html(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    total = _number(summary.get("known_spend_usd")) or 0.0
    latest = payload.get("latest_run") or {}
    concentrations = payload.get("cost_concentrations") or {}
    baseline = payload.get("legacy_baseline") or {}
    latest_budget = _number(latest.get("budget_usd"))
    latest_spend = _number(latest.get("known_spend_usd")) or 0.0
    latest_pct = _number(latest.get("budget_consumed_pct")) or 0.0
    meter_width = min(latest_pct, 100.0)
    pricing = payload.get("pricing") or {}

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CV_fit — Budget & Cost</title>
<style>
:root{{--bg:#f0f2f5;--panel:#fff;--ink:#1c1e21;--muted:#65676b;--line:#dfe3e8;--blue:#1769aa;--blue-soft:#e7f3ff;--ok:#1f7a3f;--warn:#9a5a00;--danger:#b42318;--shadow:0 1px 2px rgba(0,0,0,.12)}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 Arial,Helvetica,sans-serif}}a{{color:var(--blue)}}code{{font:11px/1.3 ui-monospace,SFMono-Regular,Consolas,monospace}}.top{{position:sticky;top:0;z-index:20;background:rgba(255,255,255,.97);border-bottom:1px solid var(--line)}}.top-inner{{max-width:1440px;margin:auto;padding:12px 20px;display:flex;justify-content:space-between;align-items:center;gap:16px}}.brand{{font-weight:850;font-size:18px}}.tabs{{display:flex;gap:7px;flex-wrap:wrap}}.tabs a{{text-decoration:none;padding:7px 10px;border-radius:8px;font-weight:750}}.tabs .active{{background:var(--blue-soft)}}main{{max-width:1440px;margin:20px auto 70px;padding:0 20px}}.hero,.panel{{background:var(--panel);border:1px solid var(--line);border-radius:13px;box-shadow:var(--shadow)}}.hero{{padding:20px;margin-bottom:14px}}h1{{margin:0 0 5px;font-size:26px}}h2{{margin:0 0 12px;font-size:18px}}h3{{margin:0 0 9px;font-size:14px}}.muted,.small{{color:var(--muted)}}.small{{font-size:11px}}.cards{{display:grid;grid-template-columns:repeat(6,minmax(130px,1fr));gap:10px;margin:14px 0}}.card{{background:#fff;border:1px solid var(--line);border-radius:11px;padding:12px}}.card span{{display:block;color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.5px}}.card strong{{display:block;margin-top:4px;font-size:20px}}.grid-2{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:14px 0}}.panel{{padding:16px;overflow:hidden}}.meter{{height:13px;background:#e8edf2;border-radius:999px;overflow:hidden;margin:9px 0}}.meter>div{{height:100%;background:var(--blue)}}.bar-row{{margin:10px 0}}.bar-label{{display:flex;justify-content:space-between;gap:12px;font-size:12px}}.bar-track{{height:8px;background:#eef1f4;border-radius:999px;overflow:hidden;margin-top:4px}}.bar-fill{{height:100%;background:#7aaed6}}.callouts{{display:grid;grid-template-columns:repeat(5,1fr);gap:8px}}.callout{{border:1px solid var(--line);border-radius:10px;padding:10px;background:#fafbfc}}.callout strong{{font-size:17px;display:block}}.callout span{{font-size:10px;color:var(--muted)}}.notice{{padding:11px 13px;border-radius:9px;background:#fff7db;border:1px solid #efd98c;color:#6b5200;margin:10px 0}}.ok-note{{background:#eaf7ef;border-color:#a8d7b8;color:#245f39}}.table-wrap{{overflow:auto;border:1px solid var(--line);border-radius:10px}}table{{border-collapse:collapse;width:100%;min-width:850px;background:#fff}}th,td{{padding:8px 9px;border-bottom:1px solid #edf0f2;text-align:left;vertical-align:top;font-size:11px}}th{{position:sticky;top:0;background:#f7f8fa;color:#475569;font-size:10px;text-transform:uppercase;letter-spacing:.35px;z-index:2}}tbody tr:hover{{background:#fbfdff}}.search{{width:100%;padding:9px 11px;border:1px solid #ccd0d5;border-radius:8px;margin:0 0 10px;font:inherit}}.section{{margin-top:14px}}.empty{{color:var(--muted);padding:14px}}.foot{{margin-top:14px;padding:13px;color:var(--muted);font-size:11px}}@media(max-width:1100px){{.cards{{grid-template-columns:repeat(3,1fr)}}.callouts{{grid-template-columns:repeat(3,1fr)}}}}@media(max-width:760px){{main{{padding:0 10px}}.top-inner{{align-items:flex-start;flex-direction:column}}.cards{{grid-template-columns:repeat(2,1fr)}}.grid-2{{grid-template-columns:1fr}}.callouts{{grid-template-columns:1fr 1fr}}}}
</style></head><body>
<header class="top"><div class="top-inner"><div class="brand">CV_fit</div><nav class="tabs"><a href="../index.html">Vacancies</a><a class="active" href="index.html">Budget & Cost</a><a href="../ab-testing/index.html">A/B Cost Lab</a></nav></div></header>
<main>
<section class="hero"><h1>Budget & Cost</h1><p class="muted">Every known OpenAI dollar in the production CV pipeline, with call-level detail whenever telemetry exists. No prompts, credentials or generated private payloads are published.</p>
<div class="cards"><div class="card"><span>Known spend</span><strong>{_money(total)}</strong></div><div class="card"><span>Application bundles</span><strong>{summary.get('application_bundles')}</strong></div><div class="card"><span>READY now</span><strong>{summary.get('ready_applications')}</strong></div><div class="card"><span>Cost / bundle</span><strong>{_money(summary.get('known_cost_per_current_bundle_usd'))}</strong></div><div class="card"><span>Cost / READY</span><strong>{_money(summary.get('known_cost_per_ready_usd'))}</strong></div><div class="card"><span>Recorded paid attempts</span><strong>{summary.get('recorded_paid_generation_attempts')}</strong></div></div>
<div class="notice"><strong>Precision boundary:</strong> {_money(summary.get('legacy_known_spend_usd'))} predates the append-only ledger. It is a versioned aggregate lower bound, not fabricated agent detail. Since the ledger started, {_pct(summary.get('since_ledger_telemetry_coverage_pct'))} of known spend is attributable at call level. Full-history agent-detail coverage is {_pct(summary.get('all_history_agent_detail_coverage_pct'))}.</div></section>

<section class="grid-2"><article class="panel"><h2>Latest production budget</h2><div class="bar-label"><strong>{_safe(latest.get('run_id') or 'No recorded run')}</strong><span>{_money(latest_spend)} / {_money(latest_budget)}</span></div><div class="meter"><div style="width:{meter_width:.2f}%"></div></div><p class="muted">{_pct(latest.get('budget_consumed_pct'))} consumed · {latest.get('generation_attempts','n/a')} generation attempt(s) · {latest.get('ready_count','n/a')} READY bundle(s).</p><p class="small">The batch cap controls generation spend; cover-letter and presentation have their own much smaller shared stage caps.</p></article><article class="panel"><h2>Cost concentration</h2><div class="callouts"><div class="callout"><span>Review loop</span><strong>{_money(concentrations.get('review_loop_spend_usd'))}</strong></div><div class="callout"><span>Premium model</span><strong>{_money(concentrations.get('premium_model_spend_usd'))}</strong></div><div class="callout"><span>Failed calls</span><strong>{_money(concentrations.get('failed_call_spend_usd'))}</strong></div><div class="callout"><span>Below-target generation</span><strong>{_money(concentrations.get('below_target_generation_spend_usd'))}</strong></div><div class="callout"><span>Failed generation</span><strong>{_money(concentrations.get('failed_generation_spend_usd'))}</strong></div></div><p class="small">Categories overlap intentionally. They diagnose where spend concentrates; they must not be added together as a savings estimate.</p></article></section>

<section class="grid-2"><article class="panel"><h2>Cost by stage</h2>{_bar_rows(payload.get('stages',[]),total=total)}</article><article class="panel"><h2>Cost by model</h2>{_bar_rows(payload.get('models',[]),total=total)}</article></section>

<section class="panel section"><h2>Cost by agent</h2><div class="table-wrap"><table><thead><tr><th>Agent</th><th>Calls</th><th>Input</th><th>Cached</th><th>Output</th><th>Reasoning</th><th>Known cost</th><th>% total</th><th>Unpriced</th></tr></thead><tbody>{_agent_table(payload.get('agents',[]),total)}</tbody></table></div></section>

<section class="panel section"><h2>Application cost ledger</h2><p class="muted">“Application bundle” means a generated CV/application package. Employer submission is not currently persisted, so this page does not pretend a bundle was actually submitted.</p><div class="table-wrap"><table><thead><tr><th>Company / role</th><th>Generation status</th><th>Current gate</th><th>Generation</th><th>Cover</th><th>Presentation</th><th>Total known</th><th>Exact calls</th></tr></thead><tbody>{_application_table(payload.get('applications',[]))}</tbody></table></div></section>

<section class="panel section"><h2>Run history</h2><div class="table-wrap"><table><thead><tr><th>Run</th><th>New candidates</th><th>Attempts</th><th>READY</th><th>Known spend</th><th>Batch budget</th><th>Budget used</th><th>Call coverage</th></tr></thead><tbody>{_run_table(payload.get('runs',[]))}</tbody></table></div></section>

<section class="panel section"><h2>Exact call ledger</h2><p class="muted">Search by company, role, stage, agent, model or status. This is the auditable drill-down behind the totals above.</p><input id="call-search" class="search" type="search" placeholder="Filter calls…"><div class="table-wrap"><table id="call-table"><thead><tr><th>Run / time</th><th>Application</th><th>Stage</th><th>Agent</th><th>Model</th><th>Input</th><th>Cached</th><th>Output</th><th>Reasoning</th><th>Cost</th><th>Status</th><th>Precision</th></tr></thead><tbody>{_event_table(payload.get('events',[]))}</tbody></table></div><p><a href="cost_ledger_public.json" target="_blank" rel="noopener">Open raw public cost JSON ↗</a></p></section>

<section class="foot">Pricing snapshot: <strong>{_safe(pricing.get('snapshot_date'))}</strong> · {_safe(pricing.get('basis'))}. {_safe(pricing.get('note'))}<br>{_safe(baseline.get('note') or '')}</section>
</main>
<script>(()=>{{const input=document.getElementById('call-search');const rows=[...document.querySelectorAll('#call-table tbody tr')];if(!input)return;input.addEventListener('input',()=>{{const q=input.value.trim().toLowerCase();rows.forEach(row=>row.style.display=!q||String(row.dataset.search||'').toLowerCase().includes(q)?'':'none');}});}})();</script>
</body></html>"""


def attach_navigation(site_dir: Path) -> bool:
    index_path = site_dir / "index.html"
    if not index_path.exists():
        return False
    source = index_path.read_text(encoding="utf-8")
    if NAV_MARKER in source:
        return False
    style = '<style id="cvfit-budget-nav-style">.cvfit-budget-nav a{display:inline-block;text-decoration:none;background:#e7f3ff;color:#1769aa;border-radius:9px;padding:7px 10px;font-weight:800;white-space:nowrap}</style>'
    if "</head>" in source:
        source = source.replace("</head>", style + "</head>", 1)
    nav = '<nav id="cvfit-budget-nav" class="cvfit-budget-nav"><a href="budget/index.html">Budget & Cost</a></nav>'
    if '<div class="top-stats">' in source:
        source = source.replace('<div class="top-stats">', nav + '<div class="top-stats">', 1)
    elif "<body>" in source:
        source = source.replace("<body>", "<body>" + nav, 1)
    else:
        return False
    index_path.write_text(source, encoding="utf-8")
    return True


def build_budget_dashboard(
    *,
    ledger_path: Path,
    manifest_path: Path,
    vacancy_state: Path,
    site_dir: Path,
) -> dict[str, Any]:
    ledger = _read_json(ledger_path, {"schema_version": 1, "events": {}, "runs": {}, "legacy_baseline": {}})
    manifest = _read_json(manifest_path, {"entries": {}})
    payload = build_payload(ledger=ledger, manifest=manifest, vacancy_state=vacancy_state)
    target = site_dir / "budget"
    target.mkdir(parents=True, exist_ok=True)
    (target / "cost_ledger_public.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (target / "index.html").write_text(render_html(payload), encoding="utf-8")
    attached = attach_navigation(site_dir)
    return {
        "known_spend_usd": payload["summary"]["known_spend_usd"],
        "application_bundles": payload["summary"]["application_bundles"],
        "ready_applications": payload["summary"]["ready_applications"],
        "event_count": len(payload.get("events", [])),
        "navigation_attached": attached,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the static GitHub Pages Budget & Cost dashboard without model calls.")
    parser.add_argument("--ledger", default="generation_state/cost_ledger.json")
    parser.add_argument("--manifest", default="generation_state/manifest.json")
    parser.add_argument("--vacancy-state", default="vacancy_state")
    parser.add_argument("--site-dir", default="_site")
    args = parser.parse_args()
    report = build_budget_dashboard(
        ledger_path=Path(args.ledger),
        manifest_path=Path(args.manifest),
        vacancy_state=Path(args.vacancy_state),
        site_dir=Path(args.site_dir),
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
