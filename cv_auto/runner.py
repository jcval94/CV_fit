from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from cv_agent.preflight import assert_vacancy_generation_ready
from cv_auto import AUTO_GENERATION_LOGIC_VERSION, AUTO_GENERATION_PIPELINE_VERSION, AUTO_GENERATION_SCHEMA_VERSION


TERMINAL_STATUSES = {
    "PASS",
    "COMPLETED_BELOW_TARGET",
    "SKIPPED_NOT_ELIGIBLE",
    "FAILED_REVIEW_REQUIRED",
}
DEFERRED_STATUS = "DEFERRED_CAP"
GenerationCallable = Callable[..., tuple[dict[str, Any], dict[str, Any]]]


class GenerationAttemptError(RuntimeError):
    """Generation failed after a live client existed; keep its partial usage."""

    def __init__(self, cause: Exception, usage: dict[str, Any]) -> None:
        self.cause = cause
        self.usage = usage
        super().__init__(f"{type(cause).__name__}: {cause}")


def _read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _numeric_cost(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return max(float(value), 0.0)
    except (TypeError, ValueError):
        return None


def _known_usage_cost(usage: dict[str, Any]) -> float | None:
    exact = _numeric_cost(usage.get("estimated_cost_usd"))
    if exact is not None:
        return exact
    return _numeric_cost(usage.get("known_estimated_cost_usd"))


def _prior_cumulative_cost(previous: dict[str, Any] | None) -> float:
    if not previous:
        return 0.0
    for key in ("cumulative_known_cost_usd", "known_estimated_cost_usd", "estimated_cost_usd"):
        value = _numeric_cost(previous.get(key))
        if value is not None:
            return value
    last_known = previous.get("last_known_metrics")
    if isinstance(last_known, dict):
        for key in ("cumulative_known_cost_usd", "known_estimated_cost_usd", "estimated_cost_usd"):
            value = _numeric_cost(last_known.get(key))
            if value is not None:
                return value
    return 0.0


def _last_known_metrics(previous: dict[str, Any] | None) -> dict[str, Any]:
    """Keep observability from the last evaluated artifact without marking it current."""
    if not previous:
        return {}
    source = previous.get("last_known_metrics") if previous.get("status") == "FAILED_REVIEW_REQUIRED" else previous
    if not isinstance(source, dict):
        return {}
    keys = (
        "run_id",
        "coverage_score",
        "unsupported_requirements",
        "estimated_cost_usd",
        "known_estimated_cost_usd",
        "cumulative_known_cost_usd",
        "content_quality_target_reached",
        "headhunter_iterations",
        "best_review_iteration",
        "headhunter_score",
        "headhunter_decision",
        "premium_model_used",
        "presentation_gate",
        "application_bundle_file",
    )
    return {key: source[key] for key in keys if key in source and source[key] is not None}


def evidence_fingerprint(evidence_state: Path) -> str:
    """Fingerprint the versioned retrieval state used by automatic generation."""
    required = ["manifest.json", "lexical_index.json", "dense_index.json", "relations.json"]
    parts: list[dict[str, str]] = []
    for name in required:
        path = evidence_state / name
        if not path.exists() or path.stat().st_size == 0:
            raise FileNotFoundError(f"required professional retrieval state missing or empty: {path}")
        parts.append({"name": name, "sha256": _sha256_file(path)})
    stable = json.dumps(parts, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha256_bytes(stable)


def generation_fingerprint(
    vacancy: dict[str, Any],
    *,
    evidence_hash: str,
    retrieval_mode: str,
) -> str:
    payload = {
        "pipeline_version": AUTO_GENERATION_PIPELINE_VERSION,
        "generation_logic_version": AUTO_GENERATION_LOGIC_VERSION,
        "vacancy_id": vacancy.get("vacancy_id"),
        "vacancy_content_hash": vacancy.get("content_hash"),
        "evidence_fingerprint": evidence_hash,
        "retrieval_mode": retrieval_mode,
    }
    return _sha256_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def candidate_ids_from_ingest_report(path: Path) -> list[str]:
    report = _read_json(path)
    return [str(value) for value in report.get("reindexed_vacancy_ids", []) if value]


def _load_manifest(state_dir: Path) -> dict[str, Any]:
    manifest = _read_json(
        state_dir / "manifest.json",
        {
            "schema_version": AUTO_GENERATION_SCHEMA_VERSION,
            "pipeline_version": AUTO_GENERATION_PIPELINE_VERSION,
            "entries": {},
        },
    )
    if manifest.get("pipeline_version") != AUTO_GENERATION_PIPELINE_VERSION:
        raise RuntimeError(
            "automatic generation manifest pipeline version changed; migrate/reset it explicitly rather than regenerating silently"
        )
    manifest.setdefault("schema_version", AUTO_GENERATION_SCHEMA_VERSION)
    manifest.setdefault("entries", {})
    return manifest


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def stale_generation_logic_ids(entries: dict[str, Any], vacancy_state: Path) -> list[str]:
    """Return active vacancies generated with older code semantics.

    A code-only correction (for example the canonical chronology backbone) must
    trigger one controlled regeneration even when the vacancy JSON and RAG state
    are unchanged. Once an entry is persisted with the current logic version it
    becomes idempotent again.
    """
    stale: list[str] = []
    for vacancy_id, entry in entries.items():
        if entry.get("generation_logic_version") == AUTO_GENERATION_LOGIC_VERSION:
            continue
        if (vacancy_state / "records" / f"{vacancy_id}.json").exists():
            stale.append(vacancy_id)
    return sorted(stale)


def _default_generate_one(
    *,
    vacancy_id: str,
    vacancy_state: Path,
    evidence_state: Path,
    output_dir: Path,
    run_id: str,
    retrieval_mode: str,
    max_estimated_cost_usd: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    from cv_agent.adk_runtime import AdkStructuredClient
    from cv_agent.workflow import run_agentic_cv

    client = AdkStructuredClient(max_estimated_cost_usd=max_estimated_cost_usd)
    try:
        report = asyncio.run(
            run_agentic_cv(
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
        # ADK records every attempted call, including calls that raise. Persist
        # that snapshot before bubbling the failure up so paid/partial work is
        # never silently lost from observability.
        usage = client.telemetry_snapshot()
        _write_json(output_dir / "usage_report.json", usage)
        _write_json(output_dir / "run_report.json", {
            "schema_version": 1,
            "run_id": run_id,
            "vacancy_id": vacancy_id,
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


def _base_entry(
    *,
    fingerprint: str,
    vacancy: dict[str, Any],
    evidence_hash: str,
    retrieval_mode: str,
    source_commit: str | None,
) -> dict[str, Any]:
    return {
        "fingerprint": fingerprint,
        "generation_logic_version": AUTO_GENERATION_LOGIC_VERSION,
        "vacancy_content_hash": vacancy.get("content_hash"),
        "evidence_fingerprint": evidence_hash,
        "retrieval_mode": retrieval_mode,
        "source_commit": source_commit,
    }


def run_generation_batch(
    *,
    candidate_ids: list[str],
    vacancy_state: Path,
    evidence_state: Path,
    generation_state: Path,
    outputs: Path,
    run_id: str,
    source_commit: str | None,
    retrieval_mode: str = "hybrid-rerank",
    max_vacancies_per_run: int = 5,
    max_estimated_cost_usd: float = 2.0,
    retry_failed: bool = False,
    generator: GenerationCallable | None = None,
) -> dict[str, Any]:
    if max_vacancies_per_run < 1:
        raise ValueError("max_vacancies_per_run must be >= 1")
    if max_estimated_cost_usd <= 0:
        raise ValueError("max_estimated_cost_usd must be > 0")

    manifest = _load_manifest(generation_state)
    entries: dict[str, Any] = manifest["entries"]
    evidence_hash = evidence_fingerprint(evidence_state)
    deferred = sorted(vacancy_id for vacancy_id, entry in entries.items() if entry.get("status") == DEFERRED_STATUS)
    stale_logic = stale_generation_logic_ids(entries, vacancy_state)
    queue = _ordered_unique(deferred + stale_logic + candidate_ids)
    generate_one = generator or _default_generate_one

    generated_attempts = 0
    results: list[dict[str, Any]] = []
    manifest_changed = False

    for vacancy_id in queue:
        vacancy_path = vacancy_state / "records" / f"{vacancy_id}.json"
        if not vacancy_path.exists():
            results.append({"vacancy_id": vacancy_id, "status": "SKIPPED_MISSING"})
            continue

        vacancy = _read_json(vacancy_path)
        fingerprint = generation_fingerprint(vacancy, evidence_hash=evidence_hash, retrieval_mode=retrieval_mode)
        previous = entries.get(vacancy_id)
        previous_status = previous.get("status") if previous else None
        same_fingerprint = bool(previous and previous.get("fingerprint") == fingerprint)
        if same_fingerprint and previous_status in TERMINAL_STATUSES and not (
            retry_failed and previous_status == "FAILED_REVIEW_REQUIRED"
        ):
            results.append({"vacancy_id": vacancy_id, "status": "SKIPPED_IDEMPOTENT", "prior_status": previous_status})
            continue

        base_entry = _base_entry(
            fingerprint=fingerprint,
            vacancy=vacancy,
            evidence_hash=evidence_hash,
            retrieval_mode=retrieval_mode,
            source_commit=source_commit,
        )
        try:
            assert_vacancy_generation_ready(vacancy)
        except ValueError as exc:
            entry = {
                **base_entry,
                "status": "SKIPPED_NOT_ELIGIBLE",
                "ready_to_send": False,
                "reason": str(exc)[:1500],
            }
            if previous != entry:
                entries[vacancy_id] = entry
                manifest_changed = True
            results.append({"vacancy_id": vacancy_id, "status": entry["status"], "reason": entry["reason"]})
            continue

        if generated_attempts >= max_vacancies_per_run:
            entry = {
                **base_entry,
                "status": DEFERRED_STATUS,
                "ready_to_send": False,
            }
            if previous != entry:
                entries[vacancy_id] = entry
                manifest_changed = True
            results.append({"vacancy_id": vacancy_id, "status": DEFERRED_STATUS})
            continue

        generated_attempts += 1
        vacancy_run_id = f"{run_id}-{vacancy_id}"
        output_dir = outputs / vacancy_id / vacancy_run_id
        prior_cumulative = _prior_cumulative_cost(previous)
        try:
            report, usage = generate_one(
                vacancy_id=vacancy_id,
                vacancy_state=vacancy_state,
                evidence_state=evidence_state,
                output_dir=output_dir,
                run_id=vacancy_run_id,
                retrieval_mode=retrieval_mode,
                max_estimated_cost_usd=max_estimated_cost_usd,
            )
            attempt_known_cost = _known_usage_cost(usage)
            cumulative_known_cost = round(prior_cumulative + (attempt_known_cost or 0.0), 8)
            final_review = dict(report.get("final_review") or {})
            entry = {
                **base_entry,
                "status": report.get("status", "UNKNOWN"),
                "ready_to_send": bool(report.get("quality_target_reached")),
                "review_required": not bool(report.get("quality_target_reached")),
                "coverage_score": report.get("match_coverage_score"),
                "unsupported_requirements": report.get("unsupported_requirements", []),
                "content_quality_target_reached": report.get("quality_target_reached"),
                "headhunter_iterations": report.get("iterations_executed"),
                "best_review_iteration": report.get("best_review_iteration"),
                "headhunter_score": final_review.get("overall_score"),
                "headhunter_decision": final_review.get("decision"),
                "premium_model_used": report.get("premium_model_used"),
                "estimated_cost_usd": usage.get("estimated_cost_usd"),
                "known_estimated_cost_usd": usage.get("known_estimated_cost_usd"),
                "attempt_known_cost_usd": attempt_known_cost,
                "cumulative_known_cost_usd": cumulative_known_cost,
                "usage_report_file": "usage_report.json",
                "run_id": vacancy_run_id,
            }
            entries[vacancy_id] = entry
            manifest_changed = True
            results.append({
                "vacancy_id": vacancy_id,
                "status": entry["status"],
                "ready_to_send": entry["ready_to_send"],
                "estimated_cost_usd": entry["estimated_cost_usd"],
                "known_estimated_cost_usd": entry["known_estimated_cost_usd"],
                "cumulative_known_cost_usd": entry["cumulative_known_cost_usd"],
                "run_id": vacancy_run_id,
            })
        except Exception as exc:
            usage: dict[str, Any] = {}
            cause = exc
            if isinstance(exc, GenerationAttemptError):
                usage = exc.usage
                cause = exc.cause
            attempt_known_cost = _known_usage_cost(usage)
            cumulative_known_cost = round(prior_cumulative + (attempt_known_cost or 0.0), 8)
            last_known = _last_known_metrics(previous)
            entry = {
                **base_entry,
                "status": "FAILED_REVIEW_REQUIRED",
                "ready_to_send": False,
                "review_required": True,
                "error": f"{type(cause).__name__}: {cause}"[:2000],
                "attempt_estimated_cost_usd": usage.get("estimated_cost_usd") if usage else None,
                "attempt_known_cost_usd": attempt_known_cost,
                "cumulative_known_cost_usd": cumulative_known_cost,
                "run_id": vacancy_run_id,
            }
            if usage:
                entry["usage_report_file"] = "usage_report.json"
            if last_known:
                entry["last_known_metrics"] = last_known
            entries[vacancy_id] = entry
            manifest_changed = True
            results.append({
                "vacancy_id": vacancy_id,
                "status": entry["status"],
                "error": entry["error"],
                "attempt_known_cost_usd": attempt_known_cost,
                "cumulative_known_cost_usd": cumulative_known_cost,
                "run_id": vacancy_run_id,
            })

    if manifest_changed:
        _write_json(generation_state / "manifest.json", manifest)

    summary = {
        "schema_version": AUTO_GENERATION_SCHEMA_VERSION,
        "pipeline_version": AUTO_GENERATION_PIPELINE_VERSION,
        "generation_logic_version": AUTO_GENERATION_LOGIC_VERSION,
        "run_id": run_id,
        "source_commit": source_commit,
        "retrieval_mode": retrieval_mode,
        "evidence_fingerprint": evidence_hash,
        "stale_logic_candidate_count": len(stale_logic),
        "candidate_count": len(queue),
        "generation_attempts": generated_attempts,
        "result_counts": {
            status: sum(item["status"] == status for item in results)
            for status in sorted({item["status"] for item in results})
        },
        "results": results,
    }
    _write_json(outputs / "_batch" / run_id / "generation_run_report.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate vacancy-specific CV artifacts incrementally and idempotently.")
    parser.add_argument("--vacancy-id", action="append", default=[])
    parser.add_argument("--ingest-report", default=None)
    parser.add_argument("--vacancy-state", default="vacancy_state")
    parser.add_argument("--evidence-state", default="rag_state")
    parser.add_argument("--generation-state", default="generation_state")
    parser.add_argument("--outputs", default="outputs/auto")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--source-commit", default=None)
    parser.add_argument("--retrieval-mode", default="hybrid-rerank", choices=["lexical", "hybrid", "hybrid-rerank"])
    parser.add_argument("--max-vacancies-per-run", type=int, default=5)
    parser.add_argument("--max-estimated-cost-usd", type=float, default=2.0)
    parser.add_argument("--retry-failed", action="store_true")
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
        retry_failed=args.retry_failed,
    )
    print(json.dumps({
        "run_id": report["run_id"],
        "generation_logic_version": report["generation_logic_version"],
        "stale_logic_candidate_count": report["stale_logic_candidate_count"],
        "candidate_count": report["candidate_count"],
        "generation_attempts": report["generation_attempts"],
        "result_counts": report["result_counts"],
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
