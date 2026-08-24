from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _num(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _pct(part: float, total: float) -> float:
    if total <= 0:
        return 100.0
    return round(min(max(part / total * 100.0, 0.0), 100.0), 2)


def enforce_readiness(*, public_payload_path: Path, html_path: Path | None = None) -> dict[str, Any]:
    payload = _read(public_payload_path)
    decision = payload.get("decision_grade")
    if not isinstance(decision, dict):
        raise ValueError("decision_grade payload must exist before readiness enforcement")
    readiness = decision.get("readiness")
    applications = decision.get("application_economics")
    reasons = decision.get("spend_reasons")
    marginal = decision.get("marginal_reviews")
    provider = decision.get("provider_reconciliation")
    if not all(isinstance(x, dict) for x in (readiness, applications, reasons, marginal, provider)):
        raise ValueError("decision_grade payload is missing required evidence sections")

    review_loop_total = _num((payload.get("cost_concentrations") or {}).get("review_loop_spend_usd")) or 0.0
    accounted_review = sum(
        _num(marginal.get(key)) or 0.0
        for key in (
            "initial_evaluation_spend_usd",
            "improving_followup_spend_usd",
            "non_improving_followup_spend_usd",
            "incomplete_marginal_attribution_spend_usd",
            "unpaired_revision_spend_usd",
        )
    )
    review_coverage = _pct(accounted_review, review_loop_total)
    # Never report >100% due to overlap/rounding. A material over-attribution is a data-quality failure.
    if review_loop_total > 0 and accounted_review > review_loop_total + 0.000001:
        raise ValueError(
            f"marginal-review evidence over-attributes spend: accounted={accounted_review:.8f}, ledger={review_loop_total:.8f}"
        )

    telemetry = _num(readiness.get("ledger_call_cost_coverage_pct")) or 0.0
    spend_reason = _num(reasons.get("classified_spend_pct")) or 0.0
    disposition = _num(applications.get("application_disposition_coverage_pct")) or 0.0
    final_outcomes = _num(applications.get("final_applied_outcome_coverage_pct")) or 0.0
    provider_reconciled = bool(provider.get("fully_reconciled"))

    if telemetry < 100.0:
        status = "PARTIAL_COST_ATTRIBUTION"
    elif spend_reason < 100.0:
        status = "PARTIAL_SPEND_ORIGIN"
    elif review_coverage < 100.0:
        status = "PARTIAL_REVIEW_ATTRIBUTION"
    elif disposition < 100.0:
        status = "WAITING_APPLICATION_DISPOSITIONS"
    elif final_outcomes < 100.0:
        status = "OUTCOMES_STILL_OPEN"
    elif not provider_reconciled:
        status = "TELEMETRY_ROI_READY_PROVIDER_UNRECONCILED"
    else:
        status = "DECISION_GRADE_RECONCILED"

    old_status = str(readiness.get("status") or "")
    readiness["status"] = status
    readiness["marginal_review_spend_coverage_pct"] = review_coverage
    readiness["review_loop_known_spend_usd"] = round(review_loop_total, 8)
    readiness["review_loop_accounted_spend_usd"] = round(accounted_review, 8)
    readiness["completely_informed"] = status == "DECISION_GRADE_RECONCILED"
    readiness["complete_decision_rule"] = (
        "DECISION_GRADE_RECONCILED requires 100% ledger call-cost attribution, 100% classified spend origin, "
        "100% accounted review-loop spend, 100% paid-vacancy application disposition, 100% final outcomes for "
        "confirmed applications, and provider reconciliation from a CV_fit-dedicated billing scope."
    )
    _write(public_payload_path, payload)

    if html_path is not None and html_path.exists():
        source = html_path.read_text(encoding="utf-8")
        if old_status:
            source = source.replace(f"Readiness: {old_status}", f"Readiness: {status}", 1)
        marker = '<section class="panel section" id="decision-grade-economics">'
        if marker in source and "decision-readiness-completeness" not in source:
            notice = (
                '<div id="decision-readiness-completeness" class="notice"><strong>Completeness gate:</strong> '
                f'cost attribution {telemetry:.1f}% · spend origin {spend_reason:.1f}% · review attribution {review_coverage:.1f}% · '
                f'application dispositions {disposition:.1f}% · final outcomes {final_outcomes:.1f}% · '
                f'provider reconciliation {"complete" if provider_reconciled else "pending"}. '
                'The green decision-grade state is unavailable until every required dimension is complete.</div>'
            )
            source = source.replace(marker, marker + notice, 1)
        html_path.write_text(source, encoding="utf-8")

    return {
        "status": status,
        "completely_informed": status == "DECISION_GRADE_RECONCILED",
        "ledger_call_cost_coverage_pct": telemetry,
        "spend_reason_classified_pct": spend_reason,
        "marginal_review_spend_coverage_pct": review_coverage,
        "application_disposition_coverage_pct": disposition,
        "final_applied_outcome_coverage_pct": final_outcomes,
        "provider_fully_reconciled": provider_reconciled,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail conservative: only label Budget & Cost decision-grade when every evidence dimension is complete.")
    parser.add_argument("--public-payload", default="_site/budget/cost_ledger_public.json")
    parser.add_argument("--html", default="_site/budget/index.html")
    args = parser.parse_args()
    result = enforce_readiness(public_payload_path=Path(args.public_payload), html_path=Path(args.html))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
