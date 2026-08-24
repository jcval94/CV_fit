from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


def _read(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _num(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _empty() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "runs": {}, "spend_attribution": {}, "review_cycles": {}, "unpaired_revisions": {}}


def _load(path: Path) -> dict[str, Any]:
    state = _read(path, _empty())
    if state.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeError("decision evidence schema changed; migrate explicitly")
    for key, value in _empty().items():
        state.setdefault(key, value)
    return state


def _stable_id(*parts: Any) -> str:
    raw = "|".join(str(part if part is not None else "") for part in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _reason_for(
    vacancy_id: str,
    *,
    original: set[str],
    retries: set[str],
    deferred_count: int,
    stale_count: int,
    plan_available: bool,
) -> tuple[str, str]:
    if vacancy_id in original:
        return "NEW_OR_MODIFIED_VACANCY", "candidate_plan_exact"
    if vacancy_id in retries:
        return "AUTO_RETRY_TRANSIENT", "candidate_plan_exact"
    if not plan_available:
        return "UNCLASSIFIED", "missing_candidate_plan"
    if deferred_count > 0 and stale_count > 0:
        return "BACKLOG_OR_STALE_UNRESOLVED", "run_level_ambiguous"
    if deferred_count > 0:
        return "DEFERRED_BACKLOG", "run_level_inferred_from_queue_counts"
    if stale_count > 0:
        return "STALE_LOGIC_BACKFILL", "run_level_inferred_from_queue_counts"
    return "UNCLASSIFIED", "candidate_plan_no_matching_origin"


def _event_cost(events: list[dict[str, Any]], agent: str, *, residual_present: bool) -> tuple[float | None, bool]:
    matches = [event for event in events if str(event.get("agent") or "") == agent]
    if not matches:
        return None, False
    values = [_num(event.get("cost_usd")) for event in matches]
    known = [value for value in values if value is not None]
    cost = round(sum(known), 8) if known else None
    complete = len(known) == len(matches) and not residual_present
    return cost, complete


def _review_cycles(
    *,
    batch_run_id: str,
    vacancy_id: str,
    vacancy_run_id: str,
    run_dir: Path,
    generation_events: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    review_dir = run_dir / "reviews"
    if not review_dir.exists():
        return [], []
    residual_present = any(str(event.get("precision") or "").startswith("stage_aggregate") for event in generation_events)
    cycles: list[dict[str, Any]] = []
    previous_score: float | None = None
    previous_gate: bool | None = None
    seen_followup_reviser: set[str] = set()

    for path in sorted(review_dir.glob("iteration_*.json")):
        record = _read(path, {})
        iteration = int(record.get("iteration") or 0)
        if iteration <= 0:
            continue
        review = record.get("review") if isinstance(record.get("review"), dict) else {}
        validation = record.get("validation") if isinstance(record.get("validation"), dict) else {}
        gate = validation.get("quality_gate") if isinstance(validation.get("quality_gate"), dict) else {}
        score = _num(review.get("overall_score"))
        headhunter_agent = f"senior_headhunter_{iteration}"
        headhunter_cost, hh_complete = _event_cost(generation_events, headhunter_agent, residual_present=residual_present)
        reviser_agent = f"cv_reviser_{iteration - 1}" if iteration > 1 else None
        reviser_cost: float | None = None
        reviser_complete = True
        if reviser_agent:
            reviser_cost, reviser_complete = _event_cost(generation_events, reviser_agent, residual_present=residual_present)
            seen_followup_reviser.add(reviser_agent)
        known_parts = [value for value in (headhunter_cost, reviser_cost) if value is not None]
        cycle_cost = round(sum(known_parts), 8) if known_parts else None
        cost_complete = hh_complete and reviser_complete and headhunter_cost is not None and (iteration == 1 or reviser_cost is not None)
        delta = round(score - previous_score, 4) if score is not None and previous_score is not None else None
        cost_per_point = None
        if cost_complete and cycle_cost is not None and delta is not None and delta > 0:
            cost_per_point = round(cycle_cost / delta, 8)
        gate_passed = bool(gate.get("passed")) if "passed" in gate else None
        cycle = {
            "cycle_id": _stable_id(batch_run_id, vacancy_id, vacancy_run_id, "review", iteration),
            "batch_run_id": batch_run_id,
            "vacancy_id": vacancy_id,
            "vacancy_run_id": vacancy_run_id,
            "iteration": iteration,
            "cycle_type": "INITIAL_EVALUATION" if iteration == 1 else "REVISION_AND_REVIEW",
            "previous_score": previous_score,
            "score": score,
            "score_delta": delta,
            "decision": review.get("decision"),
            "quality_gate_passed": gate_passed,
            "previous_quality_gate_passed": previous_gate,
            "became_quality_gate_pass": bool(gate_passed is True and previous_gate is not True),
            "headhunter_agent": headhunter_agent,
            "headhunter_known_cost_usd": headhunter_cost,
            "preceding_reviser_agent": reviser_agent,
            "preceding_reviser_known_cost_usd": reviser_cost,
            "cycle_known_cost_usd": cycle_cost,
            "cycle_cost_complete": cost_complete,
            "cost_per_positive_score_point_usd": cost_per_point,
            "source_review_file": str(path.relative_to(run_dir)),
            "precision": "review_artifact_join_call_ledger" if cost_complete else "review_artifact_partial_cost_join",
        }
        cycles.append(cycle)
        previous_score = score
        previous_gate = gate_passed

    unpaired: list[dict[str, Any]] = []
    reviser_agents = sorted({str(event.get("agent") or "") for event in generation_events if str(event.get("agent") or "").startswith("cv_reviser_")})
    for agent in reviser_agents:
        if agent in seen_followup_reviser:
            continue
        cost, complete = _event_cost(generation_events, agent, residual_present=residual_present)
        unpaired.append({
            "record_id": _stable_id(batch_run_id, vacancy_id, vacancy_run_id, "unpaired", agent),
            "batch_run_id": batch_run_id,
            "vacancy_id": vacancy_id,
            "vacancy_run_id": vacancy_run_id,
            "agent": agent,
            "known_cost_usd": cost,
            "cost_complete": complete,
            "reason": "reviser call has no subsequent persisted headhunter score; no quality delta is attributed",
        })
    return cycles, unpaired


def enrich_from_outputs(*, outputs_root: Path, ledger_path: Path, state_path: Path) -> dict[str, Any]:
    ledger = _read(ledger_path, {"events": {}, "runs": {}})
    ledger_events = [event for event in (ledger.get("events") or {}).values() if isinstance(event, dict)]
    state = _load(state_path)
    processed = 0
    skipped = 0

    for generation_report_path in sorted(outputs_root.glob("**/generation_run_report.json")):
        report = _read(generation_report_path, {})
        batch_run_id = str(report.get("run_id") or "").strip()
        if not batch_run_id:
            continue
        report_sha = _sha_file(generation_report_path)
        existing_run = state["runs"].get(batch_run_id)
        if isinstance(existing_run, dict) and existing_run.get("source_generation_report_sha256") == report_sha:
            skipped += 1
            continue
        output_root = generation_report_path.parents[2]
        candidate_plan_path = generation_report_path.parent / "candidate_plan.json"
        plan_available = candidate_plan_path.exists()
        plan = _read(candidate_plan_path, {}) if plan_available else {}
        original = {str(value) for value in plan.get("original_reindexed_vacancy_ids", []) if value}
        retries = {str(value) for value in plan.get("auto_retry_vacancy_ids", []) if value}
        deferred_count = int(report.get("deferred_candidate_count") or 0)
        stale_count = int(report.get("stale_logic_included_count") or 0)
        attribution_ids: list[str] = []
        cycle_ids: list[str] = []
        unpaired_ids: list[str] = []

        for result in report.get("results", []):
            if not isinstance(result, dict):
                continue
            vacancy_id = str(result.get("vacancy_id") or "")
            vacancy_run_id = str(result.get("run_id") or "")
            if not vacancy_id:
                continue
            reason, precision = _reason_for(
                vacancy_id,
                original=original,
                retries=retries,
                deferred_count=deferred_count,
                stale_count=stale_count,
                plan_available=plan_available,
            )
            attribution_id = _stable_id(batch_run_id, vacancy_id, "spend_reason")
            attribution = {
                "attribution_id": attribution_id,
                "batch_run_id": batch_run_id,
                "vacancy_id": vacancy_id,
                "vacancy_run_id": vacancy_run_id or None,
                "spend_reason": reason,
                "attribution_precision": precision,
                "generation_status": result.get("status"),
                "source_candidate_plan_present": plan_available,
            }
            state["spend_attribution"][attribution_id] = attribution
            attribution_ids.append(attribution_id)

            if not vacancy_run_id:
                continue
            run_dir = output_root / vacancy_id / vacancy_run_id
            generation_events = [
                event for event in ledger_events
                if str(event.get("batch_run_id") or "") == batch_run_id
                and str(event.get("vacancy_id") or "") == vacancy_id
                and str(event.get("stage") or "") == "generation"
            ]
            cycles, unpaired = _review_cycles(
                batch_run_id=batch_run_id,
                vacancy_id=vacancy_id,
                vacancy_run_id=vacancy_run_id,
                run_dir=run_dir,
                generation_events=generation_events,
            )
            for cycle in cycles:
                state["review_cycles"][cycle["cycle_id"]] = cycle
                cycle_ids.append(cycle["cycle_id"])
            for row in unpaired:
                state["unpaired_revisions"][row["record_id"]] = row
                unpaired_ids.append(row["record_id"])

        state["runs"][batch_run_id] = {
            "run_id": batch_run_id,
            "source_generation_report_sha256": report_sha,
            "source_commit": report.get("source_commit"),
            "candidate_plan_available": plan_available,
            "spend_attribution_ids": attribution_ids,
            "review_cycle_ids": cycle_ids,
            "unpaired_revision_ids": unpaired_ids,
        }
        processed += 1

    if processed:
        _write(state_path, state)
    return {
        "processed_runs": processed,
        "skipped_idempotent_runs": skipped,
        "spend_attribution_count": len(state.get("spend_attribution", {})),
        "review_cycle_count": len(state.get("review_cycles", {})),
        "unpaired_revision_count": len(state.get("unpaired_revisions", {})),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Persist truthful spend-origin and marginal-review evidence from generated artifacts.")
    parser.add_argument("--outputs", required=True)
    parser.add_argument("--ledger", default="generation_state/cost_ledger.json")
    parser.add_argument("--state", default="generation_state/decision_evidence.json")
    args = parser.parse_args()
    result = enrich_from_outputs(outputs_root=Path(args.outputs), ledger_path=Path(args.ledger), state_path=Path(args.state))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
