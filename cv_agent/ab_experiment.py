from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from cv_agent.adk_runtime import AdkStructuredClient
from cv_agent.cost_optimized import OPTIMIZATION_PROFILE, run_cost_optimized_cv
from cv_agent.model_policy import model_ids
from cv_agent.schemas import CVDocument


MIN_TARGET_SAVINGS_PCT = 25.0
MAX_ACCEPTABLE_HEADHUNTER_LOSS = 2

BLIND_AUDITOR_INSTRUCTION = """
You are an independent senior recruiting auditor comparing two CVs for the same vacancy.
The two candidates are in fact two anonymous versions of the same person's CV. You must not infer
which generation process produced either version. Do not consider cost, model choice, iteration count,
file names, or implementation details; they are intentionally withheld.

Judge only employer-facing quality:
1. vacancy alignment
2. opening impact
3. evidence credibility
4. specificity and technical ownership
5. seniority signal without exaggeration
6. ATS clarity
7. language quality
8. conciseness and prioritization

Choose left, right, or tie. A tie is correct when differences are too small to matter in a hiring decision.
Penalize unsupported or inflated claims heavily. Return concise, concrete differences rather than generic praise.
""".strip()


class BlindAuditScores(BaseModel):
    overall: int = Field(ge=0, le=100)
    vacancy_alignment: int = Field(ge=0, le=100)
    evidence_credibility: int = Field(ge=0, le=100)
    seniority_signal: int = Field(ge=0, le=100)
    ats_clarity: int = Field(ge=0, le=100)
    conciseness: int = Field(ge=0, le=100)


class BlindAudit(BaseModel):
    preferred: Literal["left", "right", "tie"]
    confidence: int = Field(ge=0, le=100)
    left: BlindAuditScores
    right: BlindAuditScores
    decisive_differences: list[str] = Field(default_factory=list)
    rationale: str


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _cv_from_file(path: Path) -> CVDocument:
    payload = _read_json(path)
    return CVDocument.model_validate(payload.get("cv", payload))


def _known_cost(usage: dict[str, Any]) -> float | None:
    value = usage.get("estimated_cost_usd")
    if value is None:
        value = usage.get("known_estimated_cost_usd")
    return float(value) if value is not None else None


def _validators_pass(report: dict[str, Any]) -> bool:
    validation = report.get("final_validation", {})
    return all(validation.get(name, {}).get("status") == "PASS" for name in ("factual", "language", "structure", "editorial"))


def _baseline_runs(root: Path, vacancy_state: Path) -> list[dict[str, Any]]:
    records_dir = vacancy_state / "records"
    candidates: list[dict[str, Any]] = []
    for cv_path in sorted(root.glob("*/**/cv_final.json")):
        run_dir = cv_path.parent
        report_path = run_dir / "run_report.json"
        usage_path = run_dir / "usage_report.json"
        if not report_path.exists() or not usage_path.exists():
            continue
        report = _read_json(report_path)
        vacancy_id = str(report.get("vacancy_id") or run_dir.parent.name)
        record_path = records_dir / f"{vacancy_id}.json"
        if not record_path.exists():
            continue
        record = _read_json(record_path)
        if not record.get("jd_generation_eligible"):
            continue

        trace_path = run_dir / "evidence_trace.json"
        if trace_path.exists():
            baseline_hash = _read_json(trace_path).get("vacancy_content_hash")
            current_hash = record.get("content_hash")
            if baseline_hash and current_hash and baseline_hash != current_hash:
                continue

        usage = _read_json(usage_path)
        cost = _known_cost(usage)
        if cost is None or cost <= 0:
            continue
        candidates.append({
            "vacancy_id": vacancy_id,
            "run_dir": run_dir,
            "report": report,
            "usage": usage,
            "record": record,
            "coverage": float(report.get("match_coverage_score") or 0.0),
            "cost": cost,
        })
    return candidates


def _representative_sample(candidates: list[dict[str, Any]], max_cases: int) -> list[dict[str, Any]]:
    if max_cases <= 0:
        return []
    ordered = sorted(candidates, key=lambda item: (item["coverage"], item["vacancy_id"]))
    if len(ordered) <= max_cases:
        return ordered
    if max_cases == 1:
        return [ordered[len(ordered) // 2]]
    indexes = [round(i * (len(ordered) - 1) / (max_cases - 1)) for i in range(max_cases)]
    return [ordered[index] for index in dict.fromkeys(indexes)]


def _left_is_baseline(experiment_id: str, vacancy_id: str) -> bool:
    digest = hashlib.sha256(f"{experiment_id}:{vacancy_id}".encode("utf-8")).digest()
    return digest[0] % 2 == 0


def _variant_from_preference(preferred: str, *, left_variant: str) -> str:
    if preferred == "tie":
        return "tie"
    if preferred == "left":
        return left_variant
    return "optimized" if left_variant == "baseline" else "baseline"


async def _blind_audit(
    *,
    client: AdkStructuredClient,
    vacancy: dict[str, Any],
    left: CVDocument,
    right: CVDocument,
    name: str,
) -> BlindAudit:
    models = model_ids()
    result = await client.call(
        name=name,
        model=models["balanced"],
        instruction=BLIND_AUDITOR_INSTRUCTION,
        payload={
            "vacancy": {
                "company": vacancy.get("company"),
                "role_title": vacancy.get("role_title"),
                "application_language": vacancy.get("application_language"),
                "requirements": vacancy.get("requirements", []),
                "responsibilities": vacancy.get("responsibilities", []),
            },
            "left_cv": left.model_dump(),
            "right_cv": right.model_dump(),
        },
        output_schema=BlindAudit,
        max_output_tokens=2600,
    )
    assert isinstance(result, BlindAudit)
    return result


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
    optimized_client = AdkStructuredClient(max_estimated_cost_usd=max_optimized_cost_usd)
    optimized_report = await run_cost_optimized_cv(
        vacancy_id=vacancy_id,
        client=optimized_client,
        output_dir=optimized_dir,
        vacancy_state=vacancy_state,
        evidence_state=evidence_state,
        run_id=f"{experiment_id}-{vacancy_id}-cost-v1",
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

    # Two independent blinded passes with reversed order reduce positional bias.
    audit_client = AdkStructuredClient(max_estimated_cost_usd=max_audit_cost_usd)
    audit_1 = await _blind_audit(
        client=audit_client,
        vacancy=baseline["record"],
        left=left_cv,
        right=right_cv,
        name=f"blind_cv_auditor_1_{vacancy_id[-6:]}",
    )
    audit_2_raw = await _blind_audit(
        client=audit_client,
        vacancy=baseline["record"],
        left=right_cv,
        right=left_cv,
        name=f"blind_cv_auditor_2_{vacancy_id[-6:]}",
    )
    audit_usage = audit_client.telemetry_snapshot()

    audit_1_winner = _variant_from_preference(audit_1.preferred, left_variant=left_variant)
    swapped_left_variant = "optimized" if left_variant == "baseline" else "baseline"
    audit_2_winner = _variant_from_preference(audit_2_raw.preferred, left_variant=swapped_left_variant)
    consensus = audit_1_winner if audit_1_winner == audit_2_winner else "disagreement"

    baseline_cost = float(baseline["cost"])
    optimized_cost = _known_cost(optimized_usage)
    savings_pct = None
    if optimized_cost is not None and baseline_cost > 0:
        savings_pct = round((baseline_cost - optimized_cost) / baseline_cost * 100.0, 2)

    baseline_score = int(baseline["report"].get("final_review", {}).get("overall_score") or 0)
    optimized_score = int(optimized_report.get("final_review", {}).get("overall_score") or 0)
    score_delta = optimized_score - baseline_score
    optimized_safe = _validators_pass(optimized_report)
    baseline_safe = _validators_pass(baseline["report"])
    machine_gate = (
        optimized_safe
        and (not baseline_safe or optimized_safe)
        and score_delta >= -MAX_ACCEPTABLE_HEADHUNTER_LOSS
        and savings_pct is not None
        and savings_pct >= MIN_TARGET_SAVINGS_PCT
        and consensus in {"optimized", "tie"}
    )

    # Candidate files are deliberately process-neutral for human review.
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
            "pass_1": audit_1.model_dump(),
            "pass_1_winner_variant": audit_1_winner,
            "pass_2_swapped": audit_2_raw.model_dump(),
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
    selected = _representative_sample(candidates, max_cases)
    if not selected:
        raise RuntimeError("no compatible baseline CV runs with complete usage telemetry were found")

    cases: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for baseline in selected:
        try:
            cases.append(await _run_case(
                baseline=baseline,
                vacancy_state=vacancy_state,
                evidence_state=evidence_state,
                output_root=output_root,
                experiment_id=experiment_id,
                max_optimized_cost_usd=max_optimized_cost_usd,
                max_audit_cost_usd=max_audit_cost_usd,
            ))
        except Exception as exc:
            failures.append({
                "vacancy_id": baseline["vacancy_id"],
                "error": f"{type(exc).__name__}: {exc}",
            })

    successful_savings = [case["comparison"]["cost_savings_pct"] for case in cases if case["comparison"]["cost_savings_pct"] is not None]
    score_deltas = [case["comparison"]["headhunter_score_delta"] for case in cases]
    summary = {
        "schema_version": 1,
        "experiment_id": experiment_id,
        "design": "existing production baseline vs cost_v1; two order-reversed blinded agent audits; human vote remains blinded until selection",
        "selected_case_count": len(selected),
        "completed_case_count": len(cases),
        "failed_case_count": len(failures),
        "mean_cost_savings_pct": round(sum(successful_savings) / len(successful_savings), 2) if successful_savings else None,
        "mean_headhunter_score_delta": round(sum(score_deltas) / len(score_deltas), 2) if score_deltas else None,
        "machine_gate_pass_count": sum(1 for case in cases if case["comparison"]["machine_gate_pass"]),
        "human_review_required": True,
        "cases": cases,
        "failures": failures,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    _write_json(output_root / "ab_report.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run blind A/B comparison between existing CV_fit baseline outputs and cost_v1.")
    parser.add_argument("--baseline-outputs", required=True)
    parser.add_argument("--vacancy-state", default="vacancy_state")
    parser.add_argument("--evidence-state", default="rag_state")
    parser.add_argument("--output", default="outputs/ab")
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--max-cases", type=int, default=3)
    parser.add_argument("--max-optimized-cost-usd", type=float, default=1.10)
    parser.add_argument("--max-audit-cost-usd", type=float, default=0.80)
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
        "failed": summary["failed_case_count"],
        "mean_cost_savings_pct": summary["mean_cost_savings_pct"],
        "mean_headhunter_score_delta": summary["mean_headhunter_score_delta"],
        "machine_gate_pass_count": summary["machine_gate_pass_count"],
    }, ensure_ascii=False, sort_keys=True))
    return 0 if summary["completed_case_count"] > 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
