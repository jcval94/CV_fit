from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from cv_agent.ab_experiment import (
    MAX_ACCEPTABLE_HEADHUNTER_LOSS,
    MIN_TARGET_SAVINGS_PCT,
    _baseline_runs,
    _blind_audit,
    _cv_from_file,
    _known_cost,
    _left_is_baseline,
    _validators_pass,
    _variant_from_preference,
    _write_json,
)
from cv_agent.adk_runtime import AdkStructuredClient
from cv_agent.cost_optimized import OPTIMIZATION_PROFILE, run_cost_optimized_cv


EARLY_POSITIVE_MIN_SAVINGS_PCT = 30.0
EARLY_POSITIVE_MIN_SCORE_DELTA = -1
DECISIVE_POSITIVE_AUDIT_CONFIDENCE = 82
DECISIVE_NEGATIVE_AUDIT_CONFIDENCE = 86
EARLY_NEGATIVE_SCORE_DELTA = -4
EARLY_NEGATIVE_MAX_SAVINGS_PCT = 10.0
BASELINE_RELATIVE_COST_CEILING = 0.90


def _representative_sequence(candidates: list[dict[str, Any]], max_cases: int) -> list[dict[str, Any]]:
    """Pick a median case first, then coverage extremes, then fill center-out.

    The first result should answer the most likely question cheaply. Extremes are
    only paid for when the median case is not decisive enough.
    """

    if max_cases <= 0 or not candidates:
        return []
    ordered = sorted(candidates, key=lambda item: (item["coverage"], item["vacancy_id"]))
    middle = len(ordered) // 2
    indexes: list[int] = [middle]
    for index in (0, len(ordered) - 1):
        if index not in indexes:
            indexes.append(index)
    remaining = [index for index in range(len(ordered)) if index not in indexes]
    remaining.sort(key=lambda index: (abs(index - middle), index))
    indexes.extend(remaining)
    return [ordered[index] for index in indexes[:max_cases]]


def _strong_deterministic_positive(
    *,
    savings_pct: float | None,
    score_delta: int,
    optimized_safe: bool,
) -> bool:
    return (
        optimized_safe
        and savings_pct is not None
        and savings_pct >= EARLY_POSITIVE_MIN_SAVINGS_PCT
        and score_delta >= EARLY_POSITIVE_MIN_SCORE_DELTA
    )


def _strong_deterministic_negative(
    *,
    savings_pct: float | None,
    score_delta: int,
    optimized_safe: bool,
) -> bool:
    return (
        not optimized_safe
        or score_delta <= EARLY_NEGATIVE_SCORE_DELTA
        or (savings_pct is not None and savings_pct <= EARLY_NEGATIVE_MAX_SAVINGS_PCT)
    )


def _should_run_second_audit(
    *,
    first_winner: str,
    first_confidence: int,
    savings_pct: float | None,
    score_delta: int,
    optimized_safe: bool,
) -> bool:
    """Use a second swapped audit only when the first result is not decisive.

    Human review remains the final promotion gate, so a high-confidence first
    audit that agrees with strong deterministic evidence does not need a second
    paid judge call merely to rediscover the same conclusion.
    """

    if (
        first_confidence >= DECISIVE_POSITIVE_AUDIT_CONFIDENCE
        and first_winner in {"optimized", "tie"}
        and _strong_deterministic_positive(
            savings_pct=savings_pct,
            score_delta=score_delta,
            optimized_safe=optimized_safe,
        )
    ):
        return False
    if (
        first_confidence >= DECISIVE_NEGATIVE_AUDIT_CONFIDENCE
        and first_winner == "baseline"
        and _strong_deterministic_negative(
            savings_pct=savings_pct,
            score_delta=score_delta,
            optimized_safe=optimized_safe,
        )
    ):
        return False
    return True


def _case_is_decisive_negative(case: dict[str, Any]) -> bool:
    comparison = case["comparison"]
    optimized = case["optimized"]
    audit = case["agent_audit"]
    savings = comparison.get("cost_savings_pct")
    return (
        not optimized.get("validators_pass", False)
        or comparison.get("headhunter_score_delta", 0) <= -3
        or (savings is not None and savings < MIN_TARGET_SAVINGS_PCT)
        or audit.get("consensus") == "baseline"
    )


def _sequential_stop_reason(cases: list[dict[str, Any]]) -> str | None:
    """Stop paying for more cases once the evidence is already actionable."""

    if not cases:
        return None
    if len(cases) == 1:
        case = cases[0]
        comparison = case["comparison"]
        if (
            comparison.get("machine_gate_pass")
            and _strong_deterministic_positive(
                savings_pct=comparison.get("cost_savings_pct"),
                score_delta=int(comparison.get("headhunter_score_delta") or 0),
                optimized_safe=bool(case["optimized"].get("validators_pass")),
            )
            and case["agent_audit"].get("consensus") in {"optimized", "tie"}
        ):
            return "strong_positive_after_one_representative_case"
        return None

    first_two = cases[:2]
    if all(case["comparison"].get("machine_gate_pass") for case in first_two):
        savings = [float(case["comparison"]["cost_savings_pct"]) for case in first_two]
        deltas = [int(case["comparison"]["headhunter_score_delta"]) for case in first_two]
        if sum(savings) / len(savings) >= MIN_TARGET_SAVINGS_PCT and min(deltas) >= -MAX_ACCEPTABLE_HEADHUNTER_LOSS:
            return "confirmed_positive_after_two_cases"

    if all(_case_is_decisive_negative(case) for case in first_two):
        return "confirmed_not_promising_after_two_cases"
    return None


def _case_cost_ceiling(*, baseline_cost: float, configured_ceiling: float) -> float:
    relative = baseline_cost * BASELINE_RELATIVE_COST_CEILING
    return round(max(0.05, min(configured_ceiling, relative)), 4)


async def _run_case(
    *,
    baseline: dict[str, Any],
    vacancy_state: Path,
    evidence_state: Path,
    output_root: Path,
    experiment_id: str,
    max_optimized_cost_usd: float,
    max_audit_cost_usd: float,
) -> dict[str, Any]:
    vacancy_id = baseline["vacancy_id"]
    case_dir = output_root / "cases" / vacancy_id
    optimized_dir = case_dir / "optimized_internal"
    baseline_cost = float(baseline["cost"])
    optimized_cost_ceiling = _case_cost_ceiling(
        baseline_cost=baseline_cost,
        configured_ceiling=max_optimized_cost_usd,
    )
    optimized_client = AdkStructuredClient(max_estimated_cost_usd=optimized_cost_ceiling)
    optimized_report = await run_cost_optimized_cv(
        vacancy_id=vacancy_id,
        client=optimized_client,
        output_dir=optimized_dir,
        vacancy_state=vacancy_state,
        evidence_state=evidence_state,
        run_id=f"{experiment_id}-{vacancy_id}-cost-v1-sequential",
        retrieval_mode="hybrid-rerank",
    )
    optimized_usage = optimized_client.telemetry_snapshot()
    _write_json(optimized_dir / "usage_report.json", optimized_usage)
    _write_json(optimized_dir / "run_report.json", optimized_report)

    baseline_cv = _cv_from_file(baseline["run_dir"] / "cv_final.json")
    optimized_cv = _cv_from_file(optimized_dir / "cv_final.json")
    left_baseline = _left_is_baseline(experiment_id, vacancy_id)
    left_variant = "baseline" if left_baseline else "optimized"
    left_cv = baseline_cv if left_baseline else optimized_cv
    right_cv = optimized_cv if left_baseline else baseline_cv

    optimized_cost = _known_cost(optimized_usage)
    savings_pct = None
    if optimized_cost is not None and baseline_cost > 0:
        savings_pct = round((baseline_cost - optimized_cost) / baseline_cost * 100.0, 2)

    baseline_score = int(baseline["report"].get("final_review", {}).get("overall_score") or 0)
    optimized_score = int(optimized_report.get("final_review", {}).get("overall_score") or 0)
    score_delta = optimized_score - baseline_score
    optimized_safe = _validators_pass(optimized_report)
    baseline_safe = _validators_pass(baseline["report"])

    audit_client = AdkStructuredClient(max_estimated_cost_usd=max_audit_cost_usd)
    audit_1 = await _blind_audit(
        client=audit_client,
        vacancy=baseline["record"],
        left=left_cv,
        right=right_cv,
        name=f"blind_cv_auditor_1_{vacancy_id[-6:]}",
    )
    audit_1_winner = _variant_from_preference(audit_1.preferred, left_variant=left_variant)

    audit_2_raw = None
    audit_2_winner = None
    if _should_run_second_audit(
        first_winner=audit_1_winner,
        first_confidence=audit_1.confidence,
        savings_pct=savings_pct,
        score_delta=score_delta,
        optimized_safe=optimized_safe,
    ):
        audit_2_raw = await _blind_audit(
            client=audit_client,
            vacancy=baseline["record"],
            left=right_cv,
            right=left_cv,
            name=f"blind_cv_auditor_2_{vacancy_id[-6:]}",
        )
        swapped_left_variant = "optimized" if left_variant == "baseline" else "baseline"
        audit_2_winner = _variant_from_preference(audit_2_raw.preferred, left_variant=swapped_left_variant)
        consensus = audit_1_winner if audit_1_winner == audit_2_winner else "disagreement"
        audit_mode = "dual_order_reversed"
    else:
        consensus = audit_1_winner
        audit_mode = "single_decisive"

    audit_usage = audit_client.telemetry_snapshot()
    machine_gate = (
        optimized_safe
        and (not baseline_safe or optimized_safe)
        and score_delta >= -MAX_ACCEPTABLE_HEADHUNTER_LOSS
        and savings_pct is not None
        and savings_pct >= MIN_TARGET_SAVINGS_PCT
        and consensus in {"optimized", "tie"}
    )

    _write_json(case_dir / "candidate_left.json", left_cv.model_dump())
    _write_json(case_dir / "candidate_right.json", right_cv.model_dump())
    case = {
        "vacancy_id": vacancy_id,
        "company": baseline["record"].get("company"),
        "role_title": baseline["record"].get("role_title"),
        "url": baseline["record"].get("url"),
        "application_language": baseline["record"].get("application_language"),
        "coverage_score": baseline["coverage"],
        "blind_mapping": {
            "left": left_variant,
            "right": "optimized" if left_variant == "baseline" else "baseline",
        },
        "baseline": {
            "cost_usd": baseline_cost,
            "call_count": baseline["usage"].get("call_count"),
            "total_tokens": baseline["usage"].get("total_tokens"),
            "headhunter_score": baseline_score,
            "quality_target_reached": baseline["report"].get("quality_target_reached"),
            "iterations": baseline["report"].get("iterations_executed"),
            "premium_model_used": baseline["report"].get("premium_model_used"),
            "validators_pass": baseline_safe,
        },
        "optimized": {
            "profile": OPTIMIZATION_PROFILE,
            "cost_usd": optimized_cost,
            "cost_ceiling_usd": optimized_cost_ceiling,
            "call_count": optimized_usage.get("call_count"),
            "total_tokens": optimized_usage.get("total_tokens"),
            "headhunter_score": optimized_score,
            "quality_target_reached": optimized_report.get("quality_target_reached"),
            "iterations": optimized_report.get("iterations_executed"),
            "premium_model_used": optimized_report.get("premium_model_used"),
            "early_stop_reason": optimized_report.get("early_stop_reason"),
            "validators_pass": optimized_safe,
        },
        "comparison": {
            "cost_savings_pct": savings_pct,
            "headhunter_score_delta": score_delta,
            "minimum_target_savings_pct": MIN_TARGET_SAVINGS_PCT,
            "maximum_acceptable_headhunter_loss": MAX_ACCEPTABLE_HEADHUNTER_LOSS,
            "machine_gate_pass": machine_gate,
            "human_status": "PENDING_BLIND_VOTE",
        },
        "agent_audit": {
            "mode": audit_mode,
            "pass_1": audit_1.model_dump(),
            "pass_1_winner_variant": audit_1_winner,
            "pass_2_swapped": audit_2_raw.model_dump() if audit_2_raw else None,
            "pass_2_winner_variant": audit_2_winner,
            "consensus": consensus,
            "audit_cost_usd": _known_cost(audit_usage),
            "audit_call_count": audit_usage.get("call_count"),
        },
        "candidate_left_file": f"cases/{vacancy_id}/candidate_left.json",
        "candidate_right_file": f"cases/{vacancy_id}/candidate_right.json",
    }
    _write_json(case_dir / "case_report.json", case)
    return case


async def run_experiment(
    *,
    baseline_outputs: Path,
    vacancy_state: Path,
    evidence_state: Path,
    output_root: Path,
    experiment_id: str,
    max_cases: int,
    max_optimized_cost_usd: float,
    max_audit_cost_usd: float,
) -> dict[str, Any]:
    candidates = _baseline_runs(baseline_outputs, vacancy_state)
    selected = _representative_sequence(candidates, max_cases)
    if not selected:
        raise RuntimeError("no compatible baseline CV runs with complete usage telemetry were found")

    cases: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    early_stop_reason: str | None = None
    for baseline in selected:
        try:
            case = await _run_case(
                baseline=baseline,
                vacancy_state=vacancy_state,
                evidence_state=evidence_state,
                output_root=output_root,
                experiment_id=experiment_id,
                max_optimized_cost_usd=max_optimized_cost_usd,
                max_audit_cost_usd=max_audit_cost_usd,
            )
            cases.append(case)
            early_stop_reason = _sequential_stop_reason(cases)
            if early_stop_reason:
                break
        except Exception as exc:
            failures.append({
                "vacancy_id": baseline["vacancy_id"],
                "error": f"{type(exc).__name__}: {exc}",
            })

    successful_savings = [
        float(case["comparison"]["cost_savings_pct"])
        for case in cases
        if case["comparison"]["cost_savings_pct"] is not None
    ]
    score_deltas = [int(case["comparison"]["headhunter_score_delta"]) for case in cases]
    optimized_costs = [float(case["optimized"]["cost_usd"] or 0.0) for case in cases]
    audit_costs = [float(case["agent_audit"]["audit_cost_usd"] or 0.0) for case in cases]
    if early_stop_reason is None and len(cases) >= len(selected):
        early_stop_reason = "max_planned_cases_reached"

    summary = {
        "schema_version": 2,
        "experiment_id": experiment_id,
        "design": (
            "adaptive sequential existing production baseline vs cost_v1; median coverage first; "
            "1-3 cases only as needed; second blinded swapped audit only when the first pass is not decisive; "
            "human vote remains blinded until selection"
        ),
        "planned_case_count": len(selected),
        "selected_case_count": len(selected),
        "completed_case_count": len(cases),
        "avoided_case_count": max(0, len(selected) - len(cases)),
        "failed_case_count": len(failures),
        "early_stop_reason": early_stop_reason,
        "mean_cost_savings_pct": round(sum(successful_savings) / len(successful_savings), 2) if successful_savings else None,
        "mean_headhunter_score_delta": round(sum(score_deltas) / len(score_deltas), 2) if score_deltas else None,
        "machine_gate_pass_count": sum(1 for case in cases if case["comparison"]["machine_gate_pass"]),
        "optimized_generation_cost_usd": round(sum(optimized_costs), 4),
        "agent_audit_cost_usd": round(sum(audit_costs), 4),
        "experiment_incremental_cost_usd": round(sum(optimized_costs) + sum(audit_costs), 4),
        "human_review_required": True,
        "cases": cases,
        "failures": failures,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    _write_json(output_root / "ab_report.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run adaptive blind A/B comparison between CV_fit baseline outputs and cost_v1.")
    parser.add_argument("--baseline-outputs", required=True)
    parser.add_argument("--vacancy-state", default="vacancy_state")
    parser.add_argument("--evidence-state", default="rag_state")
    parser.add_argument("--output", default="outputs/ab")
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--max-cases", type=int, default=3)
    parser.add_argument("--max-optimized-cost-usd", type=float, default=0.85)
    parser.add_argument("--max-audit-cost-usd", type=float, default=0.25)
    args = parser.parse_args()
    if args.max_cases <= 0:
        parser.error("--max-cases must be greater than zero")
    if args.max_optimized_cost_usd <= 0 or args.max_audit_cost_usd <= 0:
        parser.error("cost budgets must be greater than zero")

    summary = asyncio.run(run_experiment(
        baseline_outputs=Path(args.baseline_outputs),
        vacancy_state=Path(args.vacancy_state),
        evidence_state=Path(args.evidence_state),
        output_root=Path(args.output),
        experiment_id=args.experiment_id,
        max_cases=args.max_cases,
        max_optimized_cost_usd=args.max_optimized_cost_usd,
        max_audit_cost_usd=args.max_audit_cost_usd,
    ))
    print(json.dumps({
        "completed": summary["completed_case_count"],
        "avoided": summary["avoided_case_count"],
        "early_stop_reason": summary["early_stop_reason"],
        "mean_cost_savings_pct": summary["mean_cost_savings_pct"],
        "mean_headhunter_score_delta": summary["mean_headhunter_score_delta"],
        "machine_gate_pass_count": summary["machine_gate_pass_count"],
        "experiment_incremental_cost_usd": summary["experiment_incremental_cost_usd"],
    }, ensure_ascii=False, sort_keys=True))
    return 0 if summary["completed_case_count"] > 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
