from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cv_agent.adk_runtime import AdkStructuredClient
from cv_agent.cost_optimized import OPTIMIZATION_PROFILE, run_cost_optimized_cv
from cv_auto.runner import (
    GenerationAttemptError,
    _ordered_unique,
    _write_json,
    candidate_ids_from_ingest_report,
    run_generation_batch,
)


def _generate_cost_v1(
    *,
    vacancy_id: str,
    vacancy_state: Path,
    evidence_state: Path,
    output_dir: Path,
    run_id: str,
    retrieval_mode: str,
    max_estimated_cost_usd: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Production adapter for the already-tested cost_v1 workflow.

    cost_v1 preserves deterministic factual/editorial/style gates while reducing
    reviewer context, stopping genuinely stagnant review loops, and avoiding a
    premium fifth review unless the candidate is already close to passing.
    """
    client = AdkStructuredClient(max_estimated_cost_usd=max_estimated_cost_usd)
    try:
        report = asyncio.run(
            run_cost_optimized_cv(
                vacancy_id=vacancy_id,
                client=client,
                output_dir=output_dir,
                vacancy_state=vacancy_state,
                evidence_state=evidence_state,
                run_id=run_id,
                retrieval_mode=retrieval_mode,
            )
        )
    except Exception as exc:
        usage = client.telemetry_snapshot()
        _write_json(output_dir / "usage_report.json", usage)
        _write_json(output_dir / "run_report.json", {
            "schema_version": 1,
            "run_id": run_id,
            "vacancy_id": vacancy_id,
            "optimization_profile": OPTIMIZATION_PROFILE,
            "status": "FAILED_REVIEW_REQUIRED",
            "error": f"{type(exc).__name__}: {exc}"[:2000],
            "usage_report_file": "usage_report.json",
            "usage_summary": {key: value for key, value in usage.items() if key != "calls"},
        })
        raise GenerationAttemptError(exc, usage) from exc

    usage = client.telemetry_snapshot()
    _write_json(output_dir / "usage_report.json", usage)
    report["usage_report_file"] = "usage_report.json"
    report["usage_summary"] = {key: value for key, value in usage.items() if key != "calls"}
    _write_json(output_dir / "run_report.json", report)
    return report, usage


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the governed cost_v1 automatic CV generation profile.")
    parser.add_argument("--vacancy-id", action="append", default=[])
    parser.add_argument("--ingest-report", default=None)
    parser.add_argument("--vacancy-state", default="vacancy_state")
    parser.add_argument("--evidence-state", default="rag_state")
    parser.add_argument("--generation-state", default="generation_state")
    parser.add_argument("--outputs", default="outputs/auto")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--source-commit", default=None)
    parser.add_argument("--retrieval-mode", default="hybrid-rerank", choices=["lexical", "hybrid", "hybrid-rerank"])
    parser.add_argument("--max-vacancies-per-run", type=int, default=6)
    parser.add_argument("--max-estimated-cost-usd", type=float, default=1.0)
    parser.add_argument("--max-batch-estimated-cost-usd", type=float, default=2.0)
    parser.add_argument("--min-batch-remaining-usd", type=float, default=0.25)
    args = parser.parse_args()

    candidate_ids = list(args.vacancy_id)
    if args.ingest_report:
        candidate_ids.extend(candidate_ids_from_ingest_report(Path(args.ingest_report)))
    candidate_ids = _ordered_unique(candidate_ids)
    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    source_commit = args.source_commit or os.getenv("GITHUB_SHA")

    report = run_generation_batch(
        candidate_ids=candidate_ids,
        vacancy_state=Path(args.vacancy_state),
        evidence_state=Path(args.evidence_state),
        generation_state=Path(args.generation_state),
        outputs=Path(args.outputs),
        run_id=run_id,
        source_commit=source_commit,
        retrieval_mode=args.retrieval_mode,
        max_vacancies_per_run=args.max_vacancies_per_run,
        max_estimated_cost_usd=args.max_estimated_cost_usd,
        max_batch_estimated_cost_usd=args.max_batch_estimated_cost_usd,
        min_batch_remaining_usd=args.min_batch_remaining_usd,
        retry_failed=False,
        include_stale_logic=False,
        process_deferred_without_candidates=False,
        generator=_generate_cost_v1,
    )
    report["generation_profile"] = OPTIMIZATION_PROFILE
    report_path = Path(args.outputs) / "_batch" / run_id / "generation_run_report.json"
    _write_json(report_path, report)
    print(json.dumps({
        "run_id": run_id,
        "generation_profile": OPTIMIZATION_PROFILE,
        "source_candidate_count": report.get("source_candidate_count"),
        "generation_attempts": report.get("generation_attempts"),
        "batch_known_spend_usd": report.get("batch_known_spend_usd"),
        "max_batch_estimated_cost_usd": report.get("max_batch_estimated_cost_usd"),
        "result_counts": report.get("result_counts"),
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
