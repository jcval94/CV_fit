from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from cv_auto.recovery import build_generation_candidate_report
from cv_auto.runner import main
from cv_observability import EventLogger


def _arg_value(name: str) -> str | None:
    try:
        index = sys.argv.index(name)
    except ValueError:
        return None
    return sys.argv[index + 1] if index + 1 < len(sys.argv) else None


def _prepare_recoverable_candidates(logger: EventLogger) -> Path | None:
    ingest_value = _arg_value("--ingest-report")
    if not ingest_value:
        return None

    recover_enabled = os.getenv("CVFIT_AUTO_RECOVER_TRANSIENT", "true").casefold() == "true"
    ingest = Path(ingest_value)
    generation_manifest = Path(_arg_value("--generation-state") or "generation_state") / "manifest.json"
    vacancy_state = Path(_arg_value("--vacancy-state") or "vacancy_state")
    outputs = Path(_arg_value("--outputs") or "outputs/auto")
    max_vacancies = int(_arg_value("--max-vacancies-per-run") or "5")
    max_recovery = int(os.getenv("CVFIT_MAX_RECOVERY_CANDIDATES", "3")) if recover_enabled else 0
    run_id = _arg_value("--run-id") or "current"
    output = Path("/tmp") / f"cvfit-generation-candidates-{run_id}.json"

    report = build_generation_candidate_report(
        ingest_report=ingest,
        generation_manifest=generation_manifest,
        vacancy_state=vacancy_state,
        output=output,
        max_vacancies_per_run=max_vacancies,
        max_recovery_candidates=max_recovery,
    )
    # Persist the exact queue-origin evidence inside the uploaded auto-cv artifact.
    # This is intentionally public-safe metadata: vacancy ids and origin classes only.
    persisted_plan = outputs / "_batch" / run_id / "candidate_plan.json"
    persisted_plan.parent.mkdir(parents=True, exist_ok=True)
    persisted_plan.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    retry_ids = report.get("auto_retry_vacancy_ids", [])
    if retry_ids and recover_enabled:
        index = sys.argv.index("--ingest-report")
        sys.argv[index + 1] = str(output)
        if "--retry-failed" not in sys.argv:
            sys.argv.append("--retry-failed")
    logger.info(
        "generation_candidates_planned",
        new_candidate_count=len(report.get("original_reindexed_vacancy_ids", [])),
        recoverable_retry_count=len(retry_ids),
        total_candidate_count=len(report.get("reindexed_vacancy_ids", [])),
        max_vacancies_per_run=max_vacancies,
        candidate_plan_file=str(persisted_plan),
    )
    return persisted_plan


if __name__ == "__main__":
    logger = EventLogger("cv_generation", run_id=_arg_value("--run-id"))
    try:
        _prepare_recoverable_candidates(logger)
        with logger.span("generation_batch"):
            exit_code = main()
    except Exception:
        raise
    logger.emit("INFO" if exit_code == 0 else "ERROR", "process_finished", exit_code=exit_code)
    raise SystemExit(exit_code)
