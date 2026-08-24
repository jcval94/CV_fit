from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from cv_observability.application_state import ALLOWED_EVIDENCE_KINDS, ALLOWED_STATUSES
from cv_observability.provider_reconciliation import DEDICATED_SCOPE


def _read(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def validate_decision_sources(
    *,
    application_state_path: Path,
    provider_reconciliation_path: Path,
    decision_evidence_path: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    application_state = _read(application_state_path, {"schema_version": 1, "entries": {}})
    provider = _read(provider_reconciliation_path, {"schema_version": 1, "entries": {}})
    evidence = _read(decision_evidence_path, {"schema_version": 1, "spend_attribution": {}, "review_cycles": {}, "unpaired_revisions": {}})

    if application_state.get("schema_version") != 1:
        errors.append("application_state schema_version must be 1")
    for vacancy_id, entry in (application_state.get("entries") or {}).items():
        if not isinstance(entry, dict):
            errors.append(f"application_state {vacancy_id}: entry must be an object")
            continue
        events = entry.get("events") or []
        if not isinstance(events, list):
            errors.append(f"application_state {vacancy_id}: events must be a list")
            continue
        for event in events:
            if not isinstance(event, dict):
                errors.append(f"application_state {vacancy_id}: event must be an object")
                continue
            status = str(event.get("status") or "")
            kind = str(event.get("evidence_kind") or "")
            if status not in ALLOWED_STATUSES:
                errors.append(f"application_state {vacancy_id}: invalid status {status!r}")
            if kind not in ALLOWED_EVIDENCE_KINDS:
                errors.append(f"application_state {vacancy_id}: invalid evidence_kind {kind!r}")
            if "evidence_ref" in event:
                errors.append(f"application_state {vacancy_id}: raw evidence_ref must never be persisted")

    if provider.get("schema_version") != 1:
        errors.append("provider_reconciliation schema_version must be 1")
    for entry_id, entry in (provider.get("entries") or {}).items():
        if not isinstance(entry, dict):
            errors.append(f"provider_reconciliation {entry_id}: entry must be an object")
            continue
        if entry.get("scope_kind") != DEDICATED_SCOPE:
            errors.append(
                f"provider_reconciliation {entry_id}: only {DEDICATED_SCOPE} can be used for CV_fit reconciliation"
            )
        if entry.get("source_kind") != "PROVIDER_STATEMENT_USER_RECORDED":
            errors.append(f"provider_reconciliation {entry_id}: unsupported source_kind")
        if "evidence_ref" in entry:
            errors.append(f"provider_reconciliation {entry_id}: raw evidence_ref must never be persisted")

    if evidence.get("schema_version") != 1:
        errors.append("decision_evidence schema_version must be 1")
    for attribution_id, row in (evidence.get("spend_attribution") or {}).items():
        if not isinstance(row, dict):
            errors.append(f"spend_attribution {attribution_id}: row must be an object")
            continue
        precision = str(row.get("attribution_precision") or "")
        reason = str(row.get("spend_reason") or "")
        if precision == "candidate_plan_exact" and reason not in {"NEW_OR_MODIFIED_VACANCY", "AUTO_RETRY_TRANSIENT"}:
            errors.append(f"spend_attribution {attribution_id}: exact precision is inconsistent with reason {reason!r}")

    result = {
        "valid": not errors,
        "error_count": len(errors),
        "errors": errors,
        "application_entry_count": len(application_state.get("entries") or {}),
        "provider_statement_count": len(provider.get("entries") or {}),
        "spend_attribution_count": len(evidence.get("spend_attribution") or {}),
        "review_cycle_count": len(evidence.get("review_cycles") or {}),
    }
    if errors:
        raise ValueError("decision evidence truth validation failed: " + "; ".join(errors[:10]))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail closed if decision-grade evidence violates truthfulness contracts.")
    parser.add_argument("--application-state", default="generation_state/application_state.json")
    parser.add_argument("--provider-reconciliation", default="generation_state/provider_reconciliation.json")
    parser.add_argument("--decision-evidence", default="generation_state/decision_evidence.json")
    args = parser.parse_args()
    result = validate_decision_sources(
        application_state_path=Path(args.application_state),
        provider_reconciliation_path=Path(args.provider_reconciliation),
        decision_evidence_path=Path(args.decision_evidence),
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
