from __future__ import annotations

import argparse
import html
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

NAV_MARKER = 'id="cvfit-budget-nav"'


def _read(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _num(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return max(float(value), 0.0)
    except (TypeError, ValueError):
        return None


def _money(value: Any) -> str:
    value = _num(value)
    return f"${value:,.4f}" if value is not None else "n/a"


def _safe(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def _pct(value: Any) -> str:
    value = _num(value)
    return f"{value:.1f}%" if value is not None else "n/a"


def _catalog(vacancy_state: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for path in sorted((vacancy_state / "records").glob("*.json")):
        row = _read(path, {})
        if not isinstance(row, dict):
            continue
        vacancy_id = str(row.get("vacancy_id") or path.stem)
        out[vacancy_id] = {
            "company": row.get("company") or "Unknown company",
            "role_title": row.get("role_title") or "Unknown role",
            "url": row.get("url") or "",
            "fit_score": row.get("fit_score"),
        }
    return out


def _aggregate(events: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for event in events:
        name = str(event.get(key) or "Unattributed")
        row = groups.setdefault(name, {
            "name": name, "calls": 0, "prompt_tokens": 0, "cached_input_tokens": 0,
            "candidate_tokens": 0, "reasoning_tokens": 0, "total_tokens": 0,
            "known_cost_usd": 0.0, "unpriced_calls": 0,
        })
        if event.get("precision") == "call_telemetry":
            row["calls"] += 1
            if event.get("cost_usd") is None:
                row["unpriced_calls"] += 1
        for field in ("prompt_tokens", "cached_input_tokens", "candidate_tokens", "reasoning_tokens", "total_tokens"):
            row[field] += int(event.get(field) or 0)
        row["known_cost_usd"] += _num(event.get("cost_usd")) or 0.0
    for row in groups.values():
        row["known_cost_usd"] = round(row["known_cost_usd"], 8)
    return sorted(groups.values(), key=lambda x: (-x["known_cost_usd"], x["name"]))


def build_payload(*, ledger: dict[str, Any], manifest: dict[str, Any], vacancy_state: Path) -> dict[str, Any]:
    catalog = _catalog(vacancy_state)
    baseline = ledger.get("legacy_baseline") if isinstance(ledger.get("legacy_baseline"), dict) else {}
    events = [dict(x) for x in (ledger.get("events") or {}).values() if isinstance(x, dict)]
    runs = [dict(x) for x in (ledger.get("runs") or {}).values() if isinstance(x, dict)]
    runs.sort(key=lambda x: str(x.get("recorded_at") or ""), reverse=True)
    run_meta = {str(x.get("run_id")): x for x in runs}

    legacy = _num(baseline.get("known_cost_usd")) or 0.0
    recorded = round(sum(_num(x.get("cost_usd")) or 0.0 for x in events), 8)
    exact = round(sum(_num(x.get("cost_usd")) or 0.0 for x in events if x.get("precision") == "call_telemetry"), 8)
    total = round(legacy + recorded, 8)

    stages: dict[str, float] = defaultdict(float)
    for row in (baseline.get("entries") or {}).values():
        if isinstance(row, dict):
            for stage, value in (row.get("stages") or {}).items():
                stages[str(stage)] += _num(value) or 0.0
    for event in events:
        stages[str(event.get("stage") or "unknown")] += _num(event.get("cost_usd")) or 0.0
    stage_rows = [{"name": k, "known_cost_usd": round(v, 8)} for k, v in sorted(stages.items(), key=lambda x: (-x[1], x[0]))]

    agents = _aggregate(events, "agent")
    models = _aggregate(events, "model")
    if legacy:
        legacy_row = {"name": "Historical pre-ledger — detail unavailable", "calls": 0,
                      "prompt_tokens": 0, "cached_input_tokens": 0, "candidate_tokens": 0,
                      "reasoning_tokens": 0, "total_tokens": 0, "known_cost_usd": round(legacy, 8),
                      "unpriced_calls": 0}
        agents.append(dict(legacy_row)); models.append(dict(legacy_row))

    entries = manifest.get("entries") or {}
    bundles = sum(isinstance(x, dict) and bool(x.get("application_bundle_file") or x.get("presentation_gate")) for x in entries.values())
    ready = sum(isinstance(x, dict) and bool(x.get("ready_to_send")) for x in entries.values())
    paid_attempts = len({str(x.get("vacancy_run_id")) for x in events if x.get("stage") == "generation" and (_num(x.get("cost_usd")) or 0) > 0 and x.get("vacancy_run_id")})

    by_vacancy: dict[str, dict[str, Any]] = {}
    for vacancy_id, row in (baseline.get("entries") or {}).items():
        if not isinstance(row, dict): continue
        dst = by_vacancy.setdefault(str(vacancy_id), {"legacy": 0.0, "recorded": 0.0, "stages": defaultdict(float), "calls": 0})
        dst["legacy"] += _num(row.get("known_cost_usd")) or 0.0
        for stage, value in (row.get("stages") or {}).items(): dst["stages"][str(stage)] += _num(value) or 0.0
    for event in events:
        vacancy_id = str(event.get("vacancy_id") or "")
        if not vacancy_id: continue
        dst = by_vacancy.setdefault(vacancy_id, {"legacy": 0.0, "recorded": 0.0, "stages": defaultdict(float), "calls": 0})
        cost = _num(event.get("cost_usd")) or 0.0
        dst["recorded"] += cost; dst["stages"][str(event.get("stage") or "unknown")] += cost
        if event.get("precision") == "call_telemetry": dst["calls"] += 1

    applications = []
    for vacancy_id, cost in by_vacancy.items():
        identity = catalog.get(vacancy_id, {})
        state = entries.get(vacancy_id, {}) if isinstance(entries.get(vacancy_id), dict) else {}
        applications.append({
            "vacancy_id": vacancy_id, "company": identity.get("company") or vacancy_id,
            "role_title": identity.get("role_title") or "", "url": identity.get("url") or "",
            "fit_score": identity.get("fit_score"), "status": state.get("status"),
            "ready_to_send": bool(state.get("ready_to_send")), "calls": cost["calls"],
            "legacy_cost_usd": round(cost["legacy"], 8), "recorded_cost_usd": round(cost["recorded"], 8),
            "known_cost_usd": round(cost["legacy"] + cost["recorded"], 8),
            "stages": {k: round(v, 8) for k, v in cost["stages"].items()},
        })
    applications.sort(key=lambda x: (-x["known_cost_usd"], x["company"]))

    enriched_events = []
    for event in events:
        row = dict(event); identity = catalog.get(str(event.get("vacancy_id") or ""), {})
        row["company"] = identity.get("company") or row.get("vacancy_id")
        row["role_title"] = identity.get("role_title") or ""
        row["recorded_at"] = run_meta.get(str(event.get("batch_run_id") or ""), {}).get("recorded_at")
        enriched_events.append(row)
    enriched_events.sort(key=lambda x: (str(x.get("recorded_at") or ""), str(x.get("vacancy_run_id") or ""), int(x.get("call_index") or 0)), reverse=True)

    concentrations = {
        "review_loop_spend_usd": round(sum((_num(x.get("cost_usd")) or 0) for x in events if str(x.get("agent") or "").startswith(("senior_headhunter_", "cv_reviser_"))), 8),
        "premium_model_spend_usd": round(sum((_num(x.get("cost_usd")) or 0) for x in events if "sol" in str(x.get("model") or "").casefold()), 8),
        "failed_call_spend_usd": round(sum((_num(x.get("cost_usd")) or 0) for x in events if x.get("error_type")), 8),
        "below_target_generation_spend_usd": round(sum((_num(x.get("cost_usd")) or 0) for x in events if x.get("stage") == "generation" and x.get("status") == "COMPLETED_BELOW_TARGET"), 8),
        "failed_generation_spend_usd": round(sum((_num(x.get("cost_usd")) or 0) for x in events if x.get("stage") == "generation" and str(x.get("status") or "").startswith("FAILED")), 8),
        "note": "Categories overlap; never add them together as savings.",
    }
    latest = runs[0] if runs else {}
    generation_budget = _num(latest.get("generation_budget_usd") if latest else None)
    generation_spend = _num(latest.get("generation_known_spend_usd") if latest else None) or 0.0
    latest_view = dict(latest)
    latest_view["generation_budget_consumed_pct"] = round(generation_spend / generation_budget * 100, 2) if generation_budget else None

    return {
        "schema_version": 1,
        "pricing": {"snapshot_date": ledger.get("pricing_snapshot_date"), "basis": ledger.get("pricing_basis"), "source": ledger.get("pricing_source"), "note": "Token-usage estimate from pinned public pricing; not an OpenAI invoice or live account balance."},
        "summary": {
            "known_spend_usd": total, "legacy_known_spend_usd": round(legacy, 8),
            "recorded_known_spend_usd": recorded, "call_level_known_spend_usd": exact,
            "since_ledger_telemetry_coverage_pct": round(exact / recorded * 100, 2) if recorded else 100.0,
            "all_history_agent_detail_coverage_pct": round(exact / total * 100, 2) if total else 100.0,
            "tracked_vacancies": len(entries), "application_bundles": bundles, "ready_applications": ready,
            "recorded_paid_generation_attempts": paid_attempts,
            "known_cost_per_current_bundle_usd": round(total / bundles, 8) if bundles else None,
            "known_cost_per_ready_usd": round(total / ready, 8) if ready else None,
        },
        "latest_run": latest_view, "cost_concentrations": concentrations, "stages": stage_rows,
        "agents": agents, "models": models, "applications": applications, "runs": runs,
        "events": enriched_events,
        "legacy_baseline": {"known_cost_usd": baseline.get("known_cost_usd"), "vacancy_count": baseline.get("vacancy_count"), "historical_cost_complete": baseline.get("historical_cost_complete"), "note": baseline.get("note")} if baseline else {},
    }


def _bars(rows: list[dict[str, Any]], total: float) -> str:
    if not rows: return '<div class="empty">No cost data yet.</div>'
    out = []
    for row in rows:
        cost = _num(row.get("known_cost_usd")) or 0.0; width = min(cost / total * 100, 100) if total else 0
        out.append(f'<div class="bar"><div><strong>{_safe(row.get("name"))}</strong><span>{_money(cost)}</span></div><i><b style="width:{width:.2f}%"></b></i></div>')
    return "".join(out)


def _agents(rows: list[dict[str, Any]], total: float) -> str:
    out = []
    for row in rows:
        cost = _num(row.get("known_cost_usd")) or 0.0; share = cost / total * 100 if total else 0
        out.append(f'<tr><td><strong>{_safe(row.get("name"))}</strong></td><td>{int(row.get("calls") or 0)}</td><td>{int(row.get("prompt_tokens") or 0):,}</td><td>{int(row.get("cached_input_tokens") or 0):,}</td><td>{int(row.get("candidate_tokens") or 0):,}</td><td>{int(row.get("reasoning_tokens") or 0):,}</td><td>{_money(cost)}</td><td>{share:.1f}%</td><td>{int(row.get("unpriced_calls") or 0)}</td></tr>')
    return "".join(out) or '<tr><td colspan="9">No detailed calls yet.</td></tr>'


def _apps(rows: list[dict[str, Any]]) -> str:
    out = []
    for row in rows:
        stages = row.get("stages") or {}; company = _safe(row.get("company"))
        if row.get("url"): company = f'<a href="{_safe(row.get("url"))}" target="_blank" rel="noopener">{company}</a>'
        out.append(f'<tr><td>{company}<small>{_safe(row.get("role_title"))}</small></td><td>{_safe(row.get("status") or "n/a")}</td><td>{"READY" if row.get("ready_to_send") else "review"}</td><td>{_money(stages.get("generation"))}</td><td>{_money(stages.get("cover_letter"))}</td><td>{_money(stages.get("presentation"))}</td><td><strong>{_money(row.get("known_cost_usd"))}</strong></td><td>{int(row.get("calls") or 0)}</td></tr>')
    return "".join(out) or '<tr><td colspan="8">No application cost data yet.</td></tr>'


def _runs(rows: list[dict[str, Any]]) -> str:
    out = []
    for row in rows:
        budget = _num(row.get("generation_budget_usd")); generation = _num(row.get("generation_known_spend_usd")) or 0; total = _num(row.get("known_spend_usd")) or 0
        used = generation / budget * 100 if budget else None
        out.append(f'<tr><td><code>{_safe(row.get("run_id"))}</code><small>{_safe(row.get("recorded_at"))}</small></td><td>{_safe(row.get("source_candidate_count") if row.get("source_candidate_count") is not None else row.get("candidate_count"))}</td><td>{_safe(row.get("generation_attempts"))}</td><td>{_safe(row.get("ready_count"))}</td><td>{_money(generation)}</td><td>{_money(row.get("downstream_known_spend_usd"))}</td><td><strong>{_money(total)}</strong></td><td>{_money(budget)}</td><td>{f"{used:.1f}%" if used is not None else "n/a"}</td><td>{_pct(row.get("telemetry_coverage_pct"))}</td></tr>')
    return "".join(out) or '<tr><td colspan="10">No ledger-era runs yet.</td></tr>'


def _events(rows: list[dict[str, Any]]) -> str:
    out = []
    for row in rows:
        search = " ".join(str(row.get(k) or "") for k in ("company", "role_title", "stage", "agent", "model", "status", "error_type"))
        error = f'<small>error: {_safe(row.get("error_type"))}</small>' if row.get("error_type") else ""
        out.append(f'<tr data-search="{_safe(search)}"><td>{_safe(row.get("recorded_at") or "")}<small><code>{_safe(row.get("vacancy_run_id"))}</code></small></td><td>{_safe(row.get("company"))}<small>{_safe(row.get("role_title"))}</small></td><td>{_safe(row.get("stage"))}</td><td><strong>{_safe(row.get("agent"))}</strong></td><td>{_safe(row.get("model") or "unattributed")}</td><td>{int(row.get("prompt_tokens") or 0):,}</td><td>{int(row.get("cached_input_tokens") or 0):,}</td><td>{int(row.get("candidate_tokens") or 0):,}</td><td>{int(row.get("reasoning_tokens") or 0):,}</td><td><strong>{_money(row.get("cost_usd"))}</strong></td><td>{_safe(row.get("status") or "")}{error}</td><td>{_safe(row.get("precision"))}</td></tr>')
    return "".join(out) or '<tr><td colspan="12">No call events yet.</td></tr>'


def render_html(payload: dict[str, Any]) -> str:
    s, latest, c, pricing, baseline = payload["summary"], payload.get("latest_run") or {}, payload.get("cost_concentrations") or {}, payload.get("pricing") or {}, payload.get("legacy_baseline") or {}
    total = _num(s.get("known_spend_usd")) or 0.0
    gen_budget = _num(latest.get("generation_budget_usd")); gen_spend = _num(latest.get("generation_known_spend_usd")) or 0; gen_pct = _num(latest.get("generation_budget_consumed_pct")) or 0
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CV_fit — Budget & Cost</title><style>
:root{{--bg:#f0f2f5;--panel:#fff;--ink:#1c1e21;--muted:#65676b;--line:#dfe3e8;--blue:#1769aa;--soft:#e7f3ff;--shadow:0 1px 2px rgba(0,0,0,.12)}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 Arial,sans-serif}}a{{color:var(--blue)}}.top{{position:sticky;top:0;z-index:10;background:#fffffff5;border-bottom:1px solid var(--line)}}.top>div{{max-width:1440px;margin:auto;padding:12px 20px;display:flex;justify-content:space-between;gap:14px;align-items:center}}nav a{{text-decoration:none;padding:7px 10px;border-radius:8px;font-weight:750}}nav .active{{background:var(--soft)}}main{{max-width:1440px;margin:20px auto 70px;padding:0 20px}}.hero,.panel{{background:var(--panel);border:1px solid var(--line);border-radius:13px;box-shadow:var(--shadow)}}.hero,.panel{{padding:16px}}h1{{margin:0 0 5px}}h2{{margin:0 0 11px;font-size:18px}}.muted,small{{color:var(--muted)}}small{{display:block;font-size:10px}}.cards{{display:grid;grid-template-columns:repeat(6,1fr);gap:9px;margin:14px 0}}.card{{border:1px solid var(--line);border-radius:10px;padding:10px;background:#fff}}.card span{{font-size:10px;color:var(--muted);text-transform:uppercase}}.card strong{{display:block;font-size:19px;margin-top:3px}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:14px 0}}.notice{{background:#fff7db;border:1px solid #efd98c;border-radius:9px;padding:10px;margin-top:10px}}.meter{{height:13px;background:#e8edf2;border-radius:999px;overflow:hidden;margin:9px 0}}.meter b{{display:block;height:100%;background:var(--blue)}}.bar{{margin:9px 0}}.bar>div{{display:flex;justify-content:space-between;gap:10px;font-size:12px}}.bar i{{display:block;height:8px;background:#eef1f4;border-radius:999px;overflow:hidden;margin-top:4px}}.bar b{{display:block;height:100%;background:#7aaed6}}.callouts{{display:grid;grid-template-columns:repeat(5,1fr);gap:7px}}.callouts div{{border:1px solid var(--line);border-radius:9px;padding:9px}}.callouts strong{{display:block;font-size:16px}}.callouts span{{font-size:10px;color:var(--muted)}}.section{{margin-top:14px}}.wrap{{overflow:auto;border:1px solid var(--line);border-radius:9px}}table{{border-collapse:collapse;width:100%;min-width:900px}}th,td{{padding:8px;border-bottom:1px solid #edf0f2;text-align:left;vertical-align:top;font-size:11px}}th{{background:#f7f8fa;position:sticky;top:0;font-size:10px;text-transform:uppercase}}input{{width:100%;padding:9px;border:1px solid #ccd0d5;border-radius:8px;margin-bottom:9px}}code{{font-size:10px}}@media(max-width:1000px){{.cards{{grid-template-columns:repeat(3,1fr)}}.callouts{{grid-template-columns:repeat(3,1fr)}}}}@media(max-width:700px){{main{{padding:0 10px}}.top>div{{align-items:flex-start;flex-direction:column}}.cards{{grid-template-columns:repeat(2,1fr)}}.grid{{grid-template-columns:1fr}}.callouts{{grid-template-columns:1fr 1fr}}}}
</style></head><body><header class="top"><div><strong>CV_fit</strong><nav><a href="../index.html">Vacancies</a><a class="active" href="index.html">Budget & Cost</a></nav></div></header><main>
<section class="hero"><h1>Budget & Cost</h1><p class="muted">Auditable OpenAI spend by application, stage, agent, model and call. No prompts, credentials or generated private payloads are published.</p><div class="cards"><div class="card"><span>Known spend</span><strong>{_money(total)}</strong></div><div class="card"><span>Application bundles</span><strong>{s.get("application_bundles")}</strong></div><div class="card"><span>READY now</span><strong>{s.get("ready_applications")}</strong></div><div class="card"><span>Cost / bundle</span><strong>{_money(s.get("known_cost_per_current_bundle_usd"))}</strong></div><div class="card"><span>Cost / READY</span><strong>{_money(s.get("known_cost_per_ready_usd"))}</strong></div><div class="card"><span>Paid attempts recorded</span><strong>{s.get("recorded_paid_generation_attempts")}</strong></div></div><div class="notice"><strong>Precision boundary:</strong> {_money(s.get("legacy_known_spend_usd"))} predates the append-only ledger and is a documented lower bound. Since the ledger started, {_pct(s.get("since_ledger_telemetry_coverage_pct"))} of known spend has call-level attribution; full-history agent-detail coverage is {_pct(s.get("all_history_agent_detail_coverage_pct"))}.</div></section>
<section class="grid"><article class="panel"><h2>Latest generation budget</h2><div><strong>{_safe(latest.get("run_id") or "No recorded run")}</strong><span style="float:right">{_money(gen_spend)} / {_money(gen_budget)}</span></div><div class="meter"><b style="width:{min(gen_pct,100):.2f}%"></b></div><p class="muted">{_pct(latest.get("generation_budget_consumed_pct"))} of the generation cap. Total pipeline spend in this run is {_money(latest.get("known_spend_usd"))}, including {_money(latest.get("downstream_known_spend_usd"))} downstream.</p></article><article class="panel"><h2>Cost concentration</h2><div class="callouts"><div><span>Review loop</span><strong>{_money(c.get("review_loop_spend_usd"))}</strong></div><div><span>Premium model</span><strong>{_money(c.get("premium_model_spend_usd"))}</strong></div><div><span>Failed calls</span><strong>{_money(c.get("failed_call_spend_usd"))}</strong></div><div><span>Below target</span><strong>{_money(c.get("below_target_generation_spend_usd"))}</strong></div><div><span>Failed generation</span><strong>{_money(c.get("failed_generation_spend_usd"))}</strong></div></div><small>Diagnostic categories overlap; do not sum them as savings.</small></article></section>
<section class="grid"><article class="panel"><h2>Cost by stage</h2>{_bars(payload.get("stages",[]),total)}</article><article class="panel"><h2>Cost by model</h2>{_bars(payload.get("models",[]),total)}</article></section>
<section class="panel section"><h2>Cost by agent</h2><div class="wrap"><table><thead><tr><th>Agent</th><th>Calls</th><th>Input</th><th>Cached</th><th>Output</th><th>Reasoning</th><th>Known cost</th><th>% total</th><th>Unpriced</th></tr></thead><tbody>{_agents(payload.get("agents",[]),total)}</tbody></table></div></section>
<section class="panel section"><h2>Application cost ledger</h2><p class="muted">A bundle is a generated application package, not proof that an employer submission occurred.</p><div class="wrap"><table><thead><tr><th>Company / role</th><th>Generation</th><th>Gate</th><th>Generation cost</th><th>Cover</th><th>Presentation</th><th>Total known</th><th>Exact calls</th></tr></thead><tbody>{_apps(payload.get("applications",[]))}</tbody></table></div></section>
<section class="panel section"><h2>Run history</h2><div class="wrap"><table><thead><tr><th>Run</th><th>New candidates</th><th>Attempts</th><th>READY</th><th>Generation</th><th>Downstream</th><th>Total</th><th>Gen budget</th><th>Budget used</th><th>Call coverage</th></tr></thead><tbody>{_runs(payload.get("runs",[]))}</tbody></table></div></section>
<section class="panel section"><h2>Exact call ledger</h2><p class="muted">Filter by company, role, stage, agent, model, status or error.</p><input id="q" type="search" placeholder="Filter calls…"><div class="wrap"><table id="calls"><thead><tr><th>Run / time</th><th>Application</th><th>Stage</th><th>Agent</th><th>Model</th><th>Input</th><th>Cached</th><th>Output</th><th>Reasoning</th><th>Cost</th><th>Status</th><th>Precision</th></tr></thead><tbody>{_events(payload.get("events",[]))}</tbody></table></div><p><a href="cost_ledger_public.json" target="_blank">Open raw cost JSON ↗</a></p></section>
<p class="muted">Pricing snapshot: <strong>{_safe(pricing.get("snapshot_date"))}</strong> · {_safe(pricing.get("basis"))}. {_safe(pricing.get("note"))}<br>{_safe(baseline.get("note") or "")}</p></main><script>(()=>{{const q=document.getElementById('q'),rows=[...document.querySelectorAll('#calls tbody tr')];q?.addEventListener('input',()=>{{const s=q.value.toLowerCase();rows.forEach(r=>r.style.display=!s||String(r.dataset.search||'').toLowerCase().includes(s)?'':'none')}})}})();</script></body></html>'''


def attach_navigation(site_dir: Path) -> bool:
    path = site_dir / "index.html"
    if not path.exists(): return False
    source = path.read_text(encoding="utf-8")
    if NAV_MARKER in source: return False
    style = '<style id="cvfit-budget-nav-style">.cvfit-budget-nav a{display:inline-block;text-decoration:none;background:#e7f3ff;color:#1769aa;border-radius:9px;padding:7px 10px;font-weight:800;white-space:nowrap}</style>'
    if "</head>" in source: source = source.replace("</head>", style + "</head>", 1)
    nav = '<nav id="cvfit-budget-nav" class="cvfit-budget-nav"><a href="budget/index.html">Budget & Cost</a></nav>'
    if '<div class="top-stats">' in source: source = source.replace('<div class="top-stats">', nav + '<div class="top-stats">', 1)
    elif "<body>" in source: source = source.replace("<body>", "<body>" + nav, 1)
    else: return False
    path.write_text(source, encoding="utf-8"); return True


def build_budget_dashboard(*, ledger_path: Path, manifest_path: Path, vacancy_state: Path, site_dir: Path) -> dict[str, Any]:
    ledger = _read(ledger_path, {"schema_version": 1, "events": {}, "runs": {}, "legacy_baseline": {}})
    manifest = _read(manifest_path, {"entries": {}})
    payload = build_payload(ledger=ledger, manifest=manifest, vacancy_state=vacancy_state)
    target = site_dir / "budget"; target.mkdir(parents=True, exist_ok=True)
    (target / "cost_ledger_public.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (target / "index.html").write_text(render_html(payload), encoding="utf-8")
    attached = attach_navigation(site_dir)
    return {"known_spend_usd": payload["summary"]["known_spend_usd"], "application_bundles": payload["summary"]["application_bundles"], "ready_applications": payload["summary"]["ready_applications"], "event_count": len(payload.get("events", [])), "navigation_attached": attached}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build static Budget & Cost dashboard without model calls.")
    parser.add_argument("--ledger", default="generation_state/cost_ledger.json")
    parser.add_argument("--manifest", default="generation_state/manifest.json")
    parser.add_argument("--vacancy-state", default="vacancy_state")
    parser.add_argument("--site-dir", default="_site")
    args = parser.parse_args()
    print(json.dumps(build_budget_dashboard(ledger_path=Path(args.ledger), manifest_path=Path(args.manifest), vacancy_state=Path(args.vacancy_state), site_dir=Path(args.site_dir)), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
