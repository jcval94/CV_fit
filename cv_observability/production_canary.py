from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

_GENERATION_OK = {"PASS", "COMPLETED_BELOW_TARGET"}
_PRESENTATION_OK = {"PASS", "REVIEW_REQUIRED"}
_REQUIRED_ARTIFACTS = (
    "cv_final.json",
    "cover_letter_final.md",
    "cv_primary.html",
    "cv_primary.pdf",
    "application_bundle_report.json",
)


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # diagnostic code must survive malformed partial output
        if isinstance(default, dict):
            return {**default, "_read_error": f"{type(exc).__name__}: {exc}"}
        return default


def _process(value: str | None) -> str:
    normalized = str(value or "skipped").strip().lower()
    if normalized in {"success", "failure", "cancelled", "skipped"}:
        return normalized
    return normalized or "skipped"


def _semantic_retrieval(process_outcome: str) -> str:
    if process_outcome == "success":
        return "PASS"
    if process_outcome == "skipped":
        return "NOT_REACHED"
    return "PROCESS_FAILED"


def build_summary(
    *,
    outputs_root: Path,
    generation_state: Path,
    vacancy_id: str,
    canary_run_id: str,
    process_outcomes: dict[str, str],
    run_url: str = "",
) -> dict[str, Any]:
    process = {name: _process(process_outcomes.get(name)) for name in ("retrieval", "generation", "cover", "presentation")}

    batch_path = outputs_root / "_batch" / canary_run_id / "generation_run_report.json"
    bundle_path = outputs_root / "_batch" / canary_run_id / "application_bundle_batch_report.json"
    manifest_path = generation_state / "manifest.json"

    batch = _load_json(batch_path, {"results": []})
    bundle_batch = _load_json(bundle_path, {"results": []})
    manifest = _load_json(manifest_path, {"entries": {}})

    generated = next(
        (item for item in batch.get("results", []) if isinstance(item, dict) and item.get("vacancy_id") == vacancy_id),
        {},
    )
    presentation_result = next(
        (item for item in bundle_batch.get("results", []) if isinstance(item, dict) and item.get("vacancy_id") == vacancy_id),
        {},
    )
    entry = (manifest.get("entries") or {}).get(vacancy_id, {}) if isinstance(manifest, dict) else {}

    generated_run_id = generated.get("run_id") or entry.get("run_id")
    run_dir = outputs_root / vacancy_id / str(generated_run_id or "")
    missing = [name for name in _REQUIRED_ARTIFACTS if not (run_dir / name).is_file()]

    generation_status = str(generated.get("status") or entry.get("status") or "NOT_REACHED")
    presentation_status = str(presentation_result.get("status") or "NOT_REACHED")

    semantic_retrieval = _semantic_retrieval(process["retrieval"])
    if semantic_retrieval != "PASS":
        semantic_generation = "NOT_REACHED"
    elif process["generation"] != "success":
        semantic_generation = "PROCESS_FAILED"
    else:
        semantic_generation = generation_status

    generation_ok = semantic_generation in _GENERATION_OK
    if not generation_ok:
        semantic_cover = "NOT_REACHED"
    elif process["cover"] != "success":
        semantic_cover = "PROCESS_FAILED"
    elif (run_dir / "cover_letter_final.md").is_file():
        semantic_cover = "PASS"
    else:
        semantic_cover = "MISSING_ARTIFACT"

    cover_ok = semantic_cover == "PASS"
    if not cover_ok:
        semantic_presentation = "NOT_REACHED"
    elif process["presentation"] != "success":
        semantic_presentation = "PROCESS_FAILED"
    else:
        semantic_presentation = presentation_status

    presentation_ok = semantic_presentation in _PRESENTATION_OK
    canary_healthy = (
        semantic_retrieval == "PASS"
        and generation_ok
        and cover_ok
        and presentation_ok
        and not missing
    )

    stage_outcomes = {
        "retrieval": semantic_retrieval,
        "generation": semantic_generation,
        "cover": semantic_cover,
        "presentation": semantic_presentation,
    }

    return {
        "vacancy_id": vacancy_id,
        "run_url": run_url,
        "canary_healthy": canary_healthy,
        "process_outcomes": process,
        "stage_outcomes": stage_outcomes,
        "generation_status": generation_status,
        "generation_error": generated.get("error") or entry.get("error"),
        "presentation_status": presentation_status,
        "presentation_error": presentation_result.get("error") or presentation_result.get("reason"),
        "ready_to_send": bool(presentation_result.get("ready_to_send")),
        "missing_artifacts": missing,
        "headhunter_score": entry.get("headhunter_score"),
        "coverage_score": entry.get("coverage_score"),
        "generation_cost_usd": presentation_result.get("generation_cost_usd", entry.get("known_estimated_cost_usd")),
        "cover_letter_cost_usd": presentation_result.get("cover_letter_cost_usd", entry.get("cover_letter_cost_usd")),
        "presentation_cost_usd": presentation_result.get("presentation_cost_usd", entry.get("presentation_cost_usd")),
        "total_pipeline_known_cost_usd": presentation_result.get("total_pipeline_known_cost_usd", entry.get("total_pipeline_known_cost_usd")),
        "total_pipeline_cost_complete": presentation_result.get("total_pipeline_cost_complete", entry.get("total_pipeline_cost_complete")),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a semantic production-canary diagnostic")
    parser.add_argument("--outputs-root", default="outputs/auto")
    parser.add_argument("--generation-state", default="/tmp/generation_state")
    parser.add_argument("--vacancy-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-url", default="")
    parser.add_argument("--retrieval-process", default="skipped")
    parser.add_argument("--generation-process", default="skipped")
    parser.add_argument("--cover-process", default="skipped")
    parser.add_argument("--presentation-process", default="skipped")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    summary = build_summary(
        outputs_root=Path(args.outputs_root),
        generation_state=Path(args.generation_state),
        vacancy_id=args.vacancy_id,
        canary_run_id=args.run_id,
        run_url=args.run_url,
        process_outcomes={
            "retrieval": args.retrieval_process,
            "generation": args.generation_process,
            "cover": args.cover_process,
            "presentation": args.presentation_process,
        },
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
