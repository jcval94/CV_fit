from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def _read(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _stable_id(*parts: Any) -> str:
    raw = "|".join(str(part if part is not None else "") for part in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def classify_manual_request(
    *,
    generation_report: Path,
    decision_state: Path,
    request_id: str,
    vacancy_ids: set[str],
) -> dict[str, Any]:
    """Mark spend origin as an explicit user-requested policy test.

    This runs only after decision_evidence has joined the call ledger and review
    artifacts. It changes spend-origin metadata, never cost, score, gate, or CV
    content. The explicit request id is persisted so the classification is
    auditable rather than inferred from queue position.
    """
    report = _read(generation_report, {})
    batch_run_id = str(report.get("run_id") or "").strip()
    if not batch_run_id:
        raise ValueError("generation report has no run_id")
    state = _read(decision_state, {"schema_version": 1, "runs": {}, "spend_attribution": {}, "review_cycles": {}, "unpaired_revisions": {}})
    state.setdefault("runs", {})
    state.setdefault("spend_attribution", {})

    result_by_id = {
        str(item.get("vacancy_id")): item
        for item in report.get("results", [])
        if isinstance(item, dict) and item.get("vacancy_id")
    }
    changed = 0
    attribution_ids: list[str] = []
    for vacancy_id in sorted(vacancy_ids):
        item = result_by_id.get(vacancy_id)
        if item is None:
            continue
        attribution_id = _stable_id(batch_run_id, vacancy_id, "spend_reason")
        row = dict(state["spend_attribution"].get(attribution_id) or {})
        row.update({
            "attribution_id": attribution_id,
            "batch_run_id": batch_run_id,
            "vacancy_id": vacancy_id,
            "vacancy_run_id": item.get("run_id"),
            "spend_reason": "MANUAL_POLICY_TEST",
            "attribution_precision": "explicit_manual_request",
            "generation_status": item.get("status"),
            "source_candidate_plan_present": True,
            "manual_request_id": request_id,
        })
        state["spend_attribution"][attribution_id] = row
        attribution_ids.append(attribution_id)
        changed += 1

    run = dict(state["runs"].get(batch_run_id) or {})
    existing = list(run.get("spend_attribution_ids") or [])
    run["spend_attribution_ids"] = list(dict.fromkeys(existing + attribution_ids))
    run["manual_request_id"] = request_id
    run["spend_origin_override"] = "explicit_manual_request"
    state["runs"][batch_run_id] = run
    _write(decision_state, state)
    return {"batch_run_id": batch_run_id, "request_id": request_id, "classified_vacancies": changed}


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify an explicit user-requested CV generation run without altering costs or outcomes.")
    parser.add_argument("--generation-report", required=True)
    parser.add_argument("--decision-state", default="generation_state/decision_evidence.json")
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--vacancy-id", action="append", required=True)
    args = parser.parse_args()
    result = classify_manual_request(
        generation_report=Path(args.generation_report),
        decision_state=Path(args.decision_state),
        request_id=args.request_id,
        vacancy_ids=set(args.vacancy_id),
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
