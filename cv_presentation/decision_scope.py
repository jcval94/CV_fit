from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from cv_presentation.decision_dashboard import MARKER, build_decision_payload, render_section


def _read(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _num(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _iso(value: str) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _scope_run_ids(evidence: dict[str, Any], ledger: dict[str, Any]) -> list[str]:
    ledger_runs = ledger.get("runs") or {}
    rows = []
    for run_id, row in (evidence.get("runs") or {}).items():
        if not isinstance(row, dict) or not row.get("candidate_plan_available"):
            continue
        ledger_run = ledger_runs.get(run_id)
        if not isinstance(ledger_run, dict):
            continue
        rows.append((str(ledger_run.get("recorded_at") or ""), str(run_id)))
    return [run_id for _, run_id in sorted(rows)]


def _scoped_base(base: dict[str, Any], run_ids: set[str]) -> dict[str, Any]:
    scoped = dict(base)
    events = [
        dict(event) for event in base.get("events", [])
        if isinstance(event, dict) and str(event.get("batch_run_id") or "") in run_ids
    ]
    scoped["events"] = events
    vacancy_ids = {str(event.get("vacancy_id") or "") for event in events if event.get("vacancy_id")}
    cost_by_vacancy: dict[str, float] = {}
    for event in events:
        vacancy_id = str(event.get("vacancy_id") or "")
        if vacancy_id:
            cost_by_vacancy[vacancy_id] = cost_by_vacancy.get(vacancy_id, 0.0) + (_num(event.get("cost_usd")) or 0.0)
    applications = []
    for row in base.get("applications", []):
        if not isinstance(row, dict) or str(row.get("vacancy_id") or "") not in vacancy_ids:
            continue
        item = dict(row)
        item["legacy_cost_usd"] = 0.0
        item["recorded_cost_usd"] = round(cost_by_vacancy.get(str(item.get("vacancy_id")), 0.0), 8)
        item["known_cost_usd"] = item["recorded_cost_usd"]
        applications.append(item)
    scoped["applications"] = applications
    recorded = sum(_num(event.get("cost_usd")) or 0.0 for event in events)
    exact = sum(
        _num(event.get("cost_usd")) or 0.0
        for event in events if event.get("precision") == "call_telemetry"
    )
    summary = dict(base.get("summary") or {})
    summary["recorded_known_spend_usd"] = round(recorded, 8)
    summary["call_level_known_spend_usd"] = round(exact, 8)
    summary["since_ledger_telemetry_coverage_pct"] = round(exact / recorded * 100.0, 2) if recorded else 100.0
    scoped["summary"] = summary
    review_loop = sum(
        _num(event.get("cost_usd")) or 0.0
        for event in events
        if str(event.get("agent") or "").startswith(("senior_headhunter_", "cv_reviser_"))
    )
    concentrations = dict(base.get("cost_concentrations") or {})
    concentrations["review_loop_spend_usd"] = round(review_loop, 8)
    scoped["cost_concentrations"] = concentrations
    return scoped


def _scoped_ledger(ledger: dict[str, Any], run_ids: set[str]) -> dict[str, Any]:
    return {
        **ledger,
        "runs": {
            run_id: row for run_id, row in (ledger.get("runs") or {}).items()
            if run_id in run_ids and isinstance(row, dict)
        },
        "events": {
            event_id: row for event_id, row in (ledger.get("events") or {}).items()
            if isinstance(row, dict) and str(row.get("batch_run_id") or "") in run_ids
        },
        "legacy_baseline": None,
    }


def _eligible_reconciliation(
    reconciliation: dict[str, Any],
    *,
    full_ledger: dict[str, Any],
    scoped_run_ids: set[str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    paid_runs = {
        str(run_id): row for run_id, row in (full_ledger.get("runs") or {}).items()
        if isinstance(row, dict) and (_num(row.get("known_spend_usd")) or 0.0) > 0 and row.get("recorded_at")
    }
    eligible: dict[str, Any] = {}
    excluded: list[dict[str, Any]] = []
    for entry_id, statement in (reconciliation.get("entries") or {}).items():
        if not isinstance(statement, dict):
            continue
        start, end = _iso(statement["period_start"]), _iso(statement["period_end"])
        full_period_runs = {
            run_id for run_id, row in paid_runs.items()
            if start <= _iso(str(row["recorded_at"])) < end
        }
        outside_scope = sorted(full_period_runs - scoped_run_ids)
        if outside_scope:
            excluded.append({
                "entry_id": entry_id,
                "reason": "statement period contains paid CV_fit runs outside the decision-grade cohort",
                "outside_scope_run_count": len(outside_scope),
            })
            continue
        eligible[str(entry_id)] = statement
    return {"schema_version": 1, "entries": eligible}, excluded


def build_scoped_decision_grade(
    *,
    base: dict[str, Any],
    ledger: dict[str, Any],
    application_state: dict[str, Any],
    decision_evidence: dict[str, Any],
    reconciliation: dict[str, Any],
) -> dict[str, Any]:
    ordered_run_ids = _scope_run_ids(decision_evidence, ledger)
    run_ids = set(ordered_run_ids)
    scoped_base = _scoped_base(base, run_ids)
    scoped_ledger = _scoped_ledger(ledger, run_ids)
    eligible_recon, excluded_recon = _eligible_reconciliation(
        reconciliation,
        full_ledger=ledger,
        scoped_run_ids=run_ids,
    )
    payload = build_decision_payload(
        base=scoped_base,
        ledger=scoped_ledger,
        application_state=application_state,
        decision_evidence=decision_evidence,
        reconciliation=eligible_recon,
    )
    runs = scoped_ledger.get("runs") or {}
    started_at = min(
        (str(row.get("recorded_at")) for row in runs.values() if isinstance(row, dict) and row.get("recorded_at")),
        default=None,
    )
    payload["scope"] = {
        "scope_kind": "FULLY_OBSERVABLE_DECISION_GRADE_RUNS",
        "started_at": started_at,
        "run_count": len(run_ids),
        "run_ids": ordered_run_ids,
        "provider_statements_excluded_count": len(excluded_recon),
        "provider_statement_exclusions": excluded_recon,
        "note": (
            "All-history Budget & Cost totals remain visible above. ROI, spend-origin and marginal-review decisions use only runs "
            "whose candidate plan was persisted, so missing pre-feature evidence is never reconstructed as fact."
        ),
    }
    return payload


def enrich_scoped_dashboard(
    *,
    site_dir: Path,
    ledger_path: Path,
    application_state_path: Path,
    decision_evidence_path: Path,
    reconciliation_path: Path,
) -> dict[str, Any]:
    public_path = site_dir / "budget" / "cost_ledger_public.json"
    html_path = site_dir / "budget" / "index.html"
    if not public_path.exists() or not html_path.exists():
        raise FileNotFoundError("base Budget & Cost dashboard must be built first")
    base = _read(public_path, {})
    ledger = _read(ledger_path, {"events": {}, "runs": {}})
    application_state = _read(application_state_path, {"schema_version": 1, "entries": {}})
    decision_evidence = _read(decision_evidence_path, {"schema_version": 1, "runs": {}, "spend_attribution": {}, "review_cycles": {}, "unpaired_revisions": {}})
    reconciliation = _read(reconciliation_path, {"schema_version": 1, "entries": {}})
    payload = build_scoped_decision_grade(
        base=base,
        ledger=ledger,
        application_state=application_state,
        decision_evidence=decision_evidence,
        reconciliation=reconciliation,
    )
    base["decision_grade"] = payload
    _write(public_path, base)

    source = html_path.read_text(encoding="utf-8")
    if MARKER not in source:
        extra_css = '<style id="decision-grade-style">.decision-cards{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:12px 0}.decision-cards>div,.truth-grid>div{border:1px solid var(--line);border-radius:9px;padding:9px}.decision-cards span,.truth-grid b{display:block;font-size:10px;color:var(--muted);text-transform:uppercase}.decision-cards strong{display:block;font-size:17px;margin-top:3px}.truth-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:10px}.truth-grid span{display:block;font-weight:800;margin-top:3px}@media(max-width:900px){.decision-cards,.truth-grid{grid-template-columns:repeat(2,1fr)}}</style>'
        source = source.replace("</head>", extra_css + "</head>", 1)
        scope_note = payload.get("scope") or {}
        section = render_section(payload).replace(
            '<section class="panel section" id="decision-grade-economics">',
            '<section class="panel section" id="decision-grade-economics"><div class="notice"><strong>Decision cohort:</strong> '
            + str(scope_note.get("run_count") or 0)
            + ' fully observable run(s). '
            + str(scope_note.get("note") or "")
            + '</div>',
            1,
        )
        source = source.replace("</main>", section + "</main>", 1)
        html_path.write_text(source, encoding="utf-8")
    return {
        "scope_run_count": payload["scope"]["run_count"],
        "scope_started_at": payload["scope"]["started_at"],
        "readiness": payload["readiness"]["status"],
        "application_disposition_coverage_pct": payload["application_economics"]["application_disposition_coverage_pct"],
        "spend_reason_classified_pct": payload["spend_reasons"]["classified_spend_pct"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build decision-grade economics only from fully observable CV_fit runs.")
    parser.add_argument("--site-dir", default="_site")
    parser.add_argument("--ledger", default="generation_state/cost_ledger.json")
    parser.add_argument("--application-state", default="generation_state/application_state.json")
    parser.add_argument("--decision-evidence", default="generation_state/decision_evidence.json")
    parser.add_argument("--provider-reconciliation", default="generation_state/provider_reconciliation.json")
    args = parser.parse_args()
    result = enrich_scoped_dashboard(
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
