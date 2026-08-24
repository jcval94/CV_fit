from __future__ import annotations

import argparse
import html
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from cv_observability.application_state import summarize_entry

MARKER = 'id="decision-grade-economics"'


def _read(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _num(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _money(value: Any) -> str:
    parsed = _num(value)
    return f"${parsed:,.4f}" if parsed is not None else "n/a"


def _pct(value: Any) -> str:
    parsed = _num(value)
    return f"{parsed:.1f}%" if parsed is not None else "n/a"


def _safe(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def _iso(value: str) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _application_economics(base: dict[str, Any], application_state: dict[str, Any]) -> dict[str, Any]:
    events = [item for item in base.get("events", []) if isinstance(item, dict)]
    paid_ids = sorted({
        str(item.get("vacancy_id")) for item in events
        if item.get("stage") == "generation" and (_num(item.get("cost_usd")) or 0.0) > 0 and item.get("vacancy_id")
    })
    cohort_set = set(paid_ids)
    cohort_spend = round(sum(
        _num(item.get("cost_usd")) or 0.0
        for item in events if str(item.get("vacancy_id") or "") in cohort_set
    ), 8)
    app_catalog = {str(row.get("vacancy_id")): row for row in base.get("applications", []) if isinstance(row, dict) and row.get("vacancy_id")}
    state_entries = application_state.get("entries", {}) if isinstance(application_state, dict) else {}

    rows: list[dict[str, Any]] = []
    applied_count = interviewed_count = offered_count = accepted_count = dispositioned_count = final_count = 0
    for vacancy_id in paid_ids:
        raw = state_entries.get(vacancy_id, {}) if isinstance(state_entries.get(vacancy_id), dict) else {}
        summary = summarize_entry(raw) if raw else {
            "current_status": None, "applied": False, "interviewed": False, "offered": False,
            "accepted": False, "explicitly_not_applied": False, "terminal": False, "event_count": 0,
        }
        dispositioned = bool(summary["applied"] or summary["explicitly_not_applied"])
        if dispositioned:
            dispositioned_count += 1
        if summary["applied"]:
            applied_count += 1
            if summary["terminal"]:
                final_count += 1
        interviewed_count += int(summary["interviewed"])
        offered_count += int(summary["offered"])
        accepted_count += int(summary["accepted"])
        identity = app_catalog.get(vacancy_id, {})
        rows.append({
            "vacancy_id": vacancy_id,
            "company": identity.get("company") or vacancy_id,
            "role_title": identity.get("role_title") or "",
            "known_cost_usd": identity.get("recorded_cost_usd"),
            "current_status": summary["current_status"],
            "applied": summary["applied"],
            "interviewed": summary["interviewed"],
            "offered": summary["offered"],
            "terminal": summary["terminal"],
            "dispositioned": dispositioned,
            "event_count": summary["event_count"],
        })

    cohort_count = len(paid_ids)
    disposition_coverage = round(dispositioned_count / cohort_count * 100.0, 2) if cohort_count else 100.0
    final_coverage = round(final_count / applied_count * 100.0, 2) if applied_count else (100.0 if disposition_coverage == 100.0 else 0.0)
    cost_per_application = round(cohort_spend / applied_count, 8) if disposition_coverage == 100.0 and applied_count else None
    final_metrics_ready = disposition_coverage == 100.0 and final_coverage == 100.0
    cost_per_interview = round(cohort_spend / interviewed_count, 8) if final_metrics_ready and interviewed_count else None
    cost_per_offer = round(cohort_spend / offered_count, 8) if final_metrics_ready and offered_count else None
    interview_rate = round(interviewed_count / applied_count * 100.0, 2) if final_metrics_ready and applied_count else None
    offer_rate = round(offered_count / applied_count * 100.0, 2) if final_metrics_ready and applied_count else None

    return {
        "scope": "ledger-era paid generation cohort only; pre-ledger lower-bound history is excluded from ROI denominators",
        "cohort_vacancy_count": cohort_count,
        "cohort_known_spend_usd": cohort_spend,
        "explicit_disposition_count": dispositioned_count,
        "application_disposition_coverage_pct": disposition_coverage,
        "confirmed_application_count": applied_count,
        "confirmed_interview_count": interviewed_count,
        "confirmed_offer_count": offered_count,
        "confirmed_acceptance_count": accepted_count,
        "final_applied_outcome_count": final_count,
        "final_applied_outcome_coverage_pct": final_coverage,
        "cost_per_application_usd": cost_per_application,
        "cost_per_interview_usd": cost_per_interview,
        "cost_per_offer_usd": cost_per_offer,
        "interview_rate_pct": interview_rate,
        "offer_rate_pct": offer_rate,
        "cost_per_application_ready": disposition_coverage == 100.0,
        "final_funnel_metrics_ready": final_metrics_ready,
        "rows": rows,
        "truth_note": "No READY CV is treated as an application. Only explicit append-only application events count. Final interview/offer economics are withheld while applied outcomes remain open.",
    }


def _spend_reasons(base: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    attribution = {}
    for row in (evidence.get("spend_attribution") or {}).values():
        if isinstance(row, dict):
            attribution[(str(row.get("batch_run_id") or ""), str(row.get("vacancy_id") or ""))] = row
    groups: dict[str, float] = defaultdict(float)
    classified = exact = total = 0.0
    for event in base.get("events", []):
        if not isinstance(event, dict):
            continue
        cost = _num(event.get("cost_usd")) or 0.0
        total += cost
        row = attribution.get((str(event.get("batch_run_id") or ""), str(event.get("vacancy_id") or "")))
        reason = str((row or {}).get("spend_reason") or "UNCLASSIFIED")
        groups[reason] += cost
        if reason != "UNCLASSIFIED":
            classified += cost
        if row and row.get("attribution_precision") == "candidate_plan_exact":
            exact += cost
    rows = [{"name": name, "known_cost_usd": round(cost, 8)} for name, cost in sorted(groups.items(), key=lambda item: (-item[1], item[0]))]
    return {
        "rows": rows,
        "classified_spend_pct": round(classified / total * 100.0, 2) if total else 100.0,
        "candidate_plan_exact_spend_pct": round(exact / total * 100.0, 2) if total else 100.0,
        "truth_note": "UNCLASSIFIED is retained whenever the persisted candidate plan cannot prove why a paid vacancy entered the queue. Ambiguous backlog/stale cases are never silently guessed.",
    }


def _marginal_reviews(base: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    app_catalog = {str(row.get("vacancy_id")): row for row in base.get("applications", []) if isinstance(row, dict)}
    cycles = [dict(row) for row in (evidence.get("review_cycles") or {}).values() if isinstance(row, dict)]
    cycles.sort(key=lambda row: (str(row.get("batch_run_id") or ""), str(row.get("vacancy_id") or ""), int(row.get("iteration") or 0)))
    improving_spend = non_improving_spend = incomplete_spend = initial_spend = positive_points = 0.0
    complete_followup_count = 0
    for row in cycles:
        identity = app_catalog.get(str(row.get("vacancy_id") or ""), {})
        row["company"] = identity.get("company") or row.get("vacancy_id")
        row["role_title"] = identity.get("role_title") or ""
        cost = _num(row.get("cycle_known_cost_usd")) or 0.0
        if int(row.get("iteration") or 0) == 1:
            initial_spend += cost
            continue
        delta = _num(row.get("score_delta"))
        if not row.get("cycle_cost_complete") or delta is None:
            incomplete_spend += cost
            continue
        complete_followup_count += 1
        if delta > 0:
            improving_spend += cost
            positive_points += delta
        else:
            non_improving_spend += cost
    unpaired = [dict(row) for row in (evidence.get("unpaired_revisions") or {}).values() if isinstance(row, dict)]
    unpaired_spend = round(sum(_num(row.get("known_cost_usd")) or 0.0 for row in unpaired), 8)
    measured_followup = improving_spend + non_improving_spend
    return {
        "cycles": cycles,
        "initial_evaluation_spend_usd": round(initial_spend, 8),
        "improving_followup_spend_usd": round(improving_spend, 8),
        "non_improving_followup_spend_usd": round(non_improving_spend, 8),
        "incomplete_marginal_attribution_spend_usd": round(incomplete_spend, 8),
        "unpaired_revision_spend_usd": unpaired_spend,
        "positive_score_points": round(positive_points, 4),
        "weighted_cost_per_positive_score_point_usd": round(improving_spend / positive_points, 8) if positive_points else None,
        "non_improving_share_of_measured_followup_pct": round(non_improving_spend / measured_followup * 100.0, 2) if measured_followup else None,
        "complete_followup_cycle_count": complete_followup_count,
        "truth_note": "For iteration N>1, score delta is attributed only to cv_reviser_(N-1) plus senior_headhunter_N. Initial review has no prior score. Reviser spend without a subsequent score is reported separately, never assigned an invented quality delta.",
    }


def _provider_reconciliation(base: dict[str, Any], ledger: dict[str, Any], reconciliation: dict[str, Any]) -> dict[str, Any]:
    runs = {str(row.get("run_id")): row for row in (ledger.get("runs") or {}).values() if isinstance(row, dict) and row.get("run_id")}
    events = [row for row in (ledger.get("events") or {}).values() if isinstance(row, dict)]
    rows: list[dict[str, Any]] = []
    covered_run_ids: set[str] = set()
    for statement in (reconciliation.get("entries") or {}).values():
        if not isinstance(statement, dict):
            continue
        start, end = _iso(statement["period_start"]), _iso(statement["period_end"])
        run_ids = {
            run_id for run_id, run in runs.items()
            if run.get("recorded_at") and start <= _iso(str(run["recorded_at"])) < end
        }
        covered_run_ids.update(run_ids)
        period_events = [event for event in events if str(event.get("batch_run_id") or "") in run_ids]
        telemetry = round(sum(_num(event.get("cost_usd")) or 0.0 for event in period_events), 8)
        unpriced = sum(event.get("precision") == "call_telemetry" and event.get("cost_usd") is None for event in period_events)
        actual = _num(statement.get("actual_cost_usd"))
        variance = round(actual - telemetry, 8) if actual is not None else None
        variance_pct = round(variance / actual * 100.0, 2) if actual not in (None, 0) and variance is not None else None
        rows.append({
            "entry_id": statement.get("entry_id"),
            "period_start": statement.get("period_start"),
            "period_end": statement.get("period_end"),
            "actual_cost_usd": actual,
            "telemetry_known_cost_usd": telemetry,
            "variance_actual_minus_telemetry_usd": variance,
            "variance_pct_of_actual": variance_pct,
            "run_count": len(run_ids),
            "unpriced_call_count": unpriced,
            "telemetry_complete": unpriced == 0,
            "source_kind": statement.get("source_kind"),
        })
    paid_run_ids = {run_id for run_id, run in runs.items() if (_num(run.get("known_spend_usd")) or 0.0) > 0}
    coverage = round(len(paid_run_ids & covered_run_ids) / len(paid_run_ids) * 100.0, 2) if paid_run_ids else 100.0
    return {
        "rows": sorted(rows, key=lambda row: str(row.get("period_end") or ""), reverse=True),
        "paid_run_coverage_pct": coverage,
        "fully_reconciled": bool(rows) and coverage == 100.0 and all(row["telemetry_complete"] for row in rows),
        "truth_note": "Provider statements are user-recorded evidence. Telemetry comparison uses ledger run recorded_at timestamps; it does not claim direct access to the provider billing account.",
    }


def build_decision_payload(*, base: dict[str, Any], ledger: dict[str, Any], application_state: dict[str, Any], decision_evidence: dict[str, Any], reconciliation: dict[str, Any]) -> dict[str, Any]:
    applications = _application_economics(base, application_state)
    reasons = _spend_reasons(base, decision_evidence)
    marginal = _marginal_reviews(base, decision_evidence)
    provider = _provider_reconciliation(base, ledger, reconciliation)
    telemetry_coverage = _num((base.get("summary") or {}).get("since_ledger_telemetry_coverage_pct")) or 0.0
    if telemetry_coverage < 100.0:
        status = "PARTIAL_COST_ATTRIBUTION"
    elif applications["application_disposition_coverage_pct"] < 100.0:
        status = "WAITING_APPLICATION_DISPOSITIONS"
    elif applications["final_applied_outcome_coverage_pct"] < 100.0:
        status = "OUTCOMES_STILL_OPEN"
    elif not provider["fully_reconciled"]:
        status = "TELEMETRY_ROI_READY_PROVIDER_UNRECONCILED"
    else:
        status = "DECISION_GRADE_RECONCILED"
    return {
        "schema_version": 1,
        "readiness": {
            "status": status,
            "ledger_call_cost_coverage_pct": telemetry_coverage,
            "application_disposition_coverage_pct": applications["application_disposition_coverage_pct"],
            "final_applied_outcome_coverage_pct": applications["final_applied_outcome_coverage_pct"],
            "spend_reason_classified_pct": reasons["classified_spend_pct"],
            "spend_reason_candidate_plan_exact_pct": reasons["candidate_plan_exact_spend_pct"],
            "provider_paid_run_reconciliation_coverage_pct": provider["paid_run_coverage_pct"],
            "provider_fully_reconciled": provider["fully_reconciled"],
            "truth_rule": "Missing, ambiguous, open or unreconciled evidence disables the corresponding decision metric instead of being imputed.",
        },
        "application_economics": applications,
        "spend_reasons": reasons,
        "marginal_reviews": marginal,
        "provider_reconciliation": provider,
    }


def _app_rows(rows: list[dict[str, Any]]) -> str:
    out = []
    for row in rows:
        out.append(f'<tr><td>{_safe(row.get("company"))}<small>{_safe(row.get("role_title"))}</small></td><td>{_safe(row.get("current_status") or "UNKNOWN")}</td><td>{"yes" if row.get("dispositioned") else "no"}</td><td>{"yes" if row.get("interviewed") else "no"}</td><td>{"yes" if row.get("offered") else "no"}</td><td>{_money(row.get("known_cost_usd"))}</td></tr>')
    return "".join(out) or '<tr><td colspan="6">No ledger-era paid applications yet.</td></tr>'


def _reason_rows(rows: list[dict[str, Any]]) -> str:
    return "".join(f'<tr><td>{_safe(row.get("name"))}</td><td><strong>{_money(row.get("known_cost_usd"))}</strong></td></tr>' for row in rows) or '<tr><td colspan="2">No classified spend yet.</td></tr>'


def _cycle_rows(rows: list[dict[str, Any]]) -> str:
    out = []
    for row in rows:
        delta = row.get("score_delta")
        out.append(f'<tr><td>{_safe(row.get("company"))}<small>{_safe(row.get("role_title"))}</small></td><td>{_safe(row.get("iteration"))}</td><td>{_safe(row.get("previous_score") if row.get("previous_score") is not None else "—")}</td><td>{_safe(row.get("score") if row.get("score") is not None else "—")}</td><td>{_safe(f"{delta:+.1f}" if isinstance(delta,(int,float)) else "—")}</td><td>{_money(row.get("cycle_known_cost_usd"))}</td><td>{_money(row.get("cost_per_positive_score_point_usd"))}</td><td>{"complete" if row.get("cycle_cost_complete") else "partial"}</td><td>{"PASS" if row.get("quality_gate_passed") else "not pass"}</td></tr>')
    return "".join(out) or '<tr><td colspan="9">No persisted review-cycle evidence yet.</td></tr>'


def _reconciliation_rows(rows: list[dict[str, Any]]) -> str:
    out = []
    for row in rows:
        out.append(f'<tr><td>{_safe(row.get("period_start"))}<small>to {_safe(row.get("period_end"))}</small></td><td>{_money(row.get("actual_cost_usd"))}</td><td>{_money(row.get("telemetry_known_cost_usd"))}</td><td>{_money(row.get("variance_actual_minus_telemetry_usd"))}</td><td>{_pct(row.get("variance_pct_of_actual"))}</td><td>{_safe(row.get("run_count"))}</td><td>{"complete" if row.get("telemetry_complete") else "unpriced calls"}</td></tr>')
    return "".join(out) or '<tr><td colspan="7">No provider statement has been recorded. Telemetry remains an estimate, not an invoice.</td></tr>'


def render_section(payload: dict[str, Any]) -> str:
    r = payload["readiness"]
    a = payload["application_economics"]
    s = payload["spend_reasons"]
    m = payload["marginal_reviews"]
    p = payload["provider_reconciliation"]
    return f'''<section class="panel section" id="decision-grade-economics"><h2>Decision-grade economics</h2><p class="muted"><strong>Readiness: {_safe(r["status"])}</strong>. Missing evidence stays missing; the dashboard never converts READY into APPLIED, open outcomes into final outcomes, or telemetry estimates into invoices.</p><div class="decision-cards"><div><span>Ledger cohort spend</span><strong>{_money(a["cohort_known_spend_usd"])}</strong></div><div><span>Disposition coverage</span><strong>{_pct(a["application_disposition_coverage_pct"])}</strong></div><div><span>Confirmed applied</span><strong>{a["confirmed_application_count"]}</strong></div><div><span>Interviews</span><strong>{a["confirmed_interview_count"]}</strong></div><div><span>Offers</span><strong>{a["confirmed_offer_count"]}</strong></div><div><span>Cost / application</span><strong>{_money(a["cost_per_application_usd"])}</strong></div><div><span>Cost / interview</span><strong>{_money(a["cost_per_interview_usd"])}</strong></div><div><span>Cost / offer</span><strong>{_money(a["cost_per_offer_usd"])}</strong></div></div><div class="truth-grid"><div><b>Call cost coverage</b><span>{_pct(r["ledger_call_cost_coverage_pct"])}</span></div><div><b>Spend reason classified</b><span>{_pct(r["spend_reason_classified_pct"])}</span></div><div><b>Final outcome coverage</b><span>{_pct(r["final_applied_outcome_coverage_pct"])}</span></div><div><b>Provider run reconciliation</b><span>{_pct(r["provider_paid_run_reconciliation_coverage_pct"])}</span></div></div><p class="muted">{_safe(a["truth_note"])}</p></section>
<section class="grid"><article class="panel"><h2>Why money was spent</h2><p class="muted">Candidate-plan exact attribution: {_pct(s["candidate_plan_exact_spend_pct"])}. Classified: {_pct(s["classified_spend_pct"])}.</p><div class="wrap"><table><thead><tr><th>Reason</th><th>Known cost</th></tr></thead><tbody>{_reason_rows(s["rows"])}</tbody></table></div><small>{_safe(s["truth_note"])}</small></article><article class="panel"><h2>Marginal review economics</h2><div class="callouts"><div><span>Improving follow-up</span><strong>{_money(m["improving_followup_spend_usd"])}</strong></div><div><span>Non-improving</span><strong>{_money(m["non_improving_followup_spend_usd"])}</strong></div><div><span>Unpaired revisions</span><strong>{_money(m["unpaired_revision_spend_usd"])}</strong></div><div><span>$/positive score point</span><strong>{_money(m["weighted_cost_per_positive_score_point_usd"])}</strong></div></div><small>{_safe(m["truth_note"])}</small></article></section>
<section class="panel section"><h2>Marginal cost by review cycle</h2><div class="wrap"><table><thead><tr><th>Application</th><th>Iteration</th><th>Previous score</th><th>Score</th><th>Delta</th><th>Cycle cost</th><th>$/positive point</th><th>Cost precision</th><th>Gate</th></tr></thead><tbody>{_cycle_rows(m["cycles"])}</tbody></table></div></section>
<section class="panel section"><h2>Observed application outcomes</h2><p class="muted">Only explicit append-only outcome events appear here. An absent event means UNKNOWN, not NOT_APPLIED.</p><div class="wrap"><table><thead><tr><th>Company / role</th><th>Current outcome</th><th>Disposition known</th><th>Interview</th><th>Offer</th><th>Ledger-era cost</th></tr></thead><tbody>{_app_rows(a["rows"])}</tbody></table></div></section>
<section class="panel section"><h2>Provider reconciliation</h2><p class="muted">Paid-run coverage: {_pct(p["paid_run_coverage_pct"])}. {_safe(p["truth_note"])}</p><div class="wrap"><table><thead><tr><th>Statement period</th><th>Provider actual</th><th>Telemetry</th><th>Actual − telemetry</th><th>Variance</th><th>Runs</th><th>Telemetry</th></tr></thead><tbody>{_reconciliation_rows(p["rows"])}</tbody></table></div></section>'''


def enrich_dashboard(*, site_dir: Path, ledger_path: Path, application_state_path: Path, decision_evidence_path: Path, reconciliation_path: Path) -> dict[str, Any]:
    public_path = site_dir / "budget" / "cost_ledger_public.json"
    html_path = site_dir / "budget" / "index.html"
    if not public_path.exists() or not html_path.exists():
        raise FileNotFoundError("base Budget & Cost dashboard must be built first")
    base = _read(public_path, {})
    ledger = _read(ledger_path, {"events": {}, "runs": {}})
    application_state = _read(application_state_path, {"schema_version": 1, "entries": {}})
    decision_evidence = _read(decision_evidence_path, {"schema_version": 1, "spend_attribution": {}, "review_cycles": {}, "unpaired_revisions": {}})
    reconciliation = _read(reconciliation_path, {"schema_version": 1, "entries": {}})
    payload = build_decision_payload(base=base, ledger=ledger, application_state=application_state, decision_evidence=decision_evidence, reconciliation=reconciliation)
    base["decision_grade"] = payload
    _write(public_path, base)

    source = html_path.read_text(encoding="utf-8")
    if MARKER not in source:
        extra_css = '<style id="decision-grade-style">.decision-cards{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:12px 0}.decision-cards>div,.truth-grid>div{border:1px solid var(--line);border-radius:9px;padding:9px}.decision-cards span,.truth-grid b{display:block;font-size:10px;color:var(--muted);text-transform:uppercase}.decision-cards strong{display:block;font-size:17px;margin-top:3px}.truth-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:10px}.truth-grid span{display:block;font-weight:800;margin-top:3px}@media(max-width:900px){.decision-cards,.truth-grid{grid-template-columns:repeat(2,1fr)}}</style>'
        source = source.replace("</head>", extra_css + "</head>", 1)
        source = source.replace("</main>", render_section(payload) + "</main>", 1)
        html_path.write_text(source, encoding="utf-8")
    return {
        "readiness": payload["readiness"]["status"],
        "application_disposition_coverage_pct": payload["application_economics"]["application_disposition_coverage_pct"],
        "final_applied_outcome_coverage_pct": payload["application_economics"]["final_applied_outcome_coverage_pct"],
        "spend_reason_classified_pct": payload["spend_reasons"]["classified_spend_pct"],
        "provider_reconciliation_coverage_pct": payload["provider_reconciliation"]["paid_run_coverage_pct"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Add decision-grade ROI, spend reason, marginal-review and reconciliation metrics to Budget & Cost.")
    parser.add_argument("--site-dir", default="_site")
    parser.add_argument("--ledger", default="generation_state/cost_ledger.json")
    parser.add_argument("--application-state", default="generation_state/application_state.json")
    parser.add_argument("--decision-evidence", default="generation_state/decision_evidence.json")
    parser.add_argument("--provider-reconciliation", default="generation_state/provider_reconciliation.json")
    args = parser.parse_args()
    result = enrich_dashboard(
        site_dir=Path(args.site_dir),
        ledger_path=Path(args.ledger),
        application_state_path=Path(args.application_state),
        decision_evidence_path=Path(args.decision_evidence),
        reconciliation_path=Path(args.provider_reconciliation),
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
