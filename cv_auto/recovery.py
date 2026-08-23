from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


RECOVERABLE_ERROR_PATTERNS = (
    r"insufficient_quota",
    r"credit_balance_exhausted",
    r"rate\s*limit",
    r"\b429\b",
    r"timeout",
    r"timed out",
    r"connection(?:error| reset| refused)?",
    r"temporar(?:y|ily) unavailable",
    r"server[_ ]error",
    r"\b50[234]\b",
)


def _read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def is_recoverable_failure(entry: dict[str, Any]) -> bool:
    if entry.get("status") != "FAILED_REVIEW_REQUIRED":
        return False
    text = str(entry.get("error") or "").casefold()
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in RECOVERABLE_ERROR_PATTERNS)


def build_generation_candidate_report(
    *,
    ingest_report: Path,
    generation_manifest: Path,
    vacancy_state: Path,
    output: Path,
    max_vacancies_per_run: int,
    max_recovery_candidates: int = 3,
) -> dict[str, Any]:
    report = _read_json(ingest_report)
    manifest = _read_json(generation_manifest, {"entries": {}})
    entries = manifest.get("entries") or {}
    original = [str(value) for value in report.get("reindexed_vacancy_ids", []) if value]

    capacity = max(max_vacancies_per_run - len(original), 0)
    recovery_limit = min(capacity, max(max_recovery_candidates, 0))
    recovery: list[str] = []
    for vacancy_id in sorted(entries):
        if len(recovery) >= recovery_limit:
            break
        if vacancy_id in original:
            continue
        entry = entries.get(vacancy_id)
        if not isinstance(entry, dict) or not is_recoverable_failure(entry):
            continue
        record_path = vacancy_state / "records" / f"{vacancy_id}.json"
        if not record_path.exists():
            continue
        record = _read_json(record_path, {})
        if not bool(record.get("jd_generation_eligible")):
            continue
        recovery.append(vacancy_id)

    enriched = dict(report)
    enriched["reindexed_vacancy_ids"] = original + recovery
    enriched["original_reindexed_vacancy_ids"] = original
    enriched["auto_retry_vacancy_ids"] = recovery
    enriched["auto_retry_count"] = len(recovery)
    enriched["candidate_capacity"] = max_vacancies_per_run
    _write_json(output, enriched)
    return enriched


def main() -> int:
    parser = argparse.ArgumentParser(description="Append only clearly recoverable prior CV failures after today's new candidates.")
    parser.add_argument("--ingest-report", required=True)
    parser.add_argument("--generation-manifest", default="generation_state/manifest.json")
    parser.add_argument("--vacancy-state", default="vacancy_state")
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-vacancies-per-run", type=int, default=6)
    parser.add_argument("--max-recovery-candidates", type=int, default=3)
    args = parser.parse_args()

    report = build_generation_candidate_report(
        ingest_report=Path(args.ingest_report),
        generation_manifest=Path(args.generation_manifest),
        vacancy_state=Path(args.vacancy_state),
        output=Path(args.output),
        max_vacancies_per_run=args.max_vacancies_per_run,
        max_recovery_candidates=args.max_recovery_candidates,
    )
    print(json.dumps({
        "new_candidates": len(report.get("original_reindexed_vacancy_ids", [])),
        "auto_retry_candidates": report.get("auto_retry_vacancy_ids", []),
        "total_candidates": len(report.get("reindexed_vacancy_ids", [])),
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
