from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from cv_agent.adk_runtime import AdkStructuredClient
from cv_agent.cover_letter import generate_cover_letter
from cv_agent.schemas import CVDocument


def _read_json(path: Path, default: Any | None = None):
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _final_cv(path: Path) -> CVDocument:
    payload = _read_json(path)
    return CVDocument.model_validate(payload.get("cv", payload))


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _usage_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Return only the usage generated since the previous snapshot."""
    before_calls = int(before.get("call_count") or 0)
    after_calls = int(after.get("call_count") or 0)
    before_known = _number(before.get("known_estimated_cost_usd")) or 0.0
    after_known = _number(after.get("known_estimated_cost_usd")) or 0.0
    before_exact = _number(before.get("estimated_cost_usd"))
    after_exact = _number(after.get("estimated_cost_usd"))
    exact = None
    if before_exact is not None and after_exact is not None:
        exact = round(max(after_exact - before_exact, 0.0), 8)
    return {
        "call_count": max(after_calls - before_calls, 0),
        "estimated_cost_usd": exact,
        "known_estimated_cost_usd": round(max(after_known - before_known, 0.0), 8),
        "prompt_tokens": max(int(after.get("prompt_tokens") or 0) - int(before.get("prompt_tokens") or 0), 0),
        "cached_input_tokens": max(int(after.get("cached_input_tokens") or 0) - int(before.get("cached_input_tokens") or 0), 0),
        "candidate_tokens": max(int(after.get("candidate_tokens") or 0) - int(before.get("candidate_tokens") or 0), 0),
        "reasoning_tokens": max(int(after.get("reasoning_tokens") or 0) - int(before.get("reasoning_tokens") or 0), 0),
        "total_tokens": max(int(after.get("total_tokens") or 0) - int(before.get("total_tokens") or 0), 0),
    }


def _stage_cost(usage: dict[str, Any]) -> float | None:
    exact = _number(usage.get("estimated_cost_usd"))
    if exact is not None:
        return exact
    return _number(usage.get("known_estimated_cost_usd"))


async def generate_batch(
    *,
    batch_report: Path,
    outputs: Path,
    vacancy_state: Path,
    max_estimated_cost_usd: float,
    generation_state: Path = Path("generation_state"),
) -> dict:
    report = _read_json(batch_report)
    manifest_path = generation_state / "manifest.json"
    manifest = _read_json(manifest_path, {"entries": {}})
    entries = manifest.setdefault("entries", {})
    client = AdkStructuredClient(max_estimated_cost_usd=max_estimated_cost_usd)
    results = []

    for item in report.get("results", []):
        vacancy_id = item.get("vacancy_id")
        run_id = item.get("run_id")
        status = item.get("status")
        if not vacancy_id or not run_id or status not in {"PASS", "COMPLETED_BELOW_TARGET"}:
            continue
        output_dir = outputs / vacancy_id / run_id
        vacancy = _read_json(vacancy_state / "records" / f"{vacancy_id}.json")
        cv = _final_cv(output_dir / "cv_final.json")
        before = client.telemetry_snapshot()
        error: str | None = None
        try:
            await generate_cover_letter(client=client, vacancy=vacancy, final_cv=cv, output_dir=output_dir)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"[:2000]
        after = client.telemetry_snapshot()
        usage = _usage_delta(before, after)
        stage_cost = _stage_cost(usage)

        run_report_path = output_dir / "run_report.json"
        run_report = _read_json(run_report_path, {})
        stage_usage = run_report.setdefault("stage_usage", {})
        stage_usage["cover_letter"] = usage
        run_report["cover_letter_status"] = "PASS" if error is None else "FAILED"
        run_report["cover_letter_cost_usd"] = stage_cost
        if error is None:
            run_report["cover_letter_file"] = "cover_letter_final.md"
        else:
            run_report["cover_letter_error"] = error
        _write_json(run_report_path, run_report)

        entry = entries.setdefault(str(vacancy_id), {})
        entry["cover_letter_usage"] = usage
        entry["cover_letter_cost_usd"] = stage_cost
        entry["cover_letter_status"] = "PASS" if error is None else "FAILED"
        if error is not None:
            entry["cover_letter_error"] = error

        result = {
            "vacancy_id": vacancy_id,
            "run_id": run_id,
            "status": "PASS" if error is None else "FAILED",
            "estimated_cost_usd": usage.get("estimated_cost_usd"),
            "known_estimated_cost_usd": usage.get("known_estimated_cost_usd"),
        }
        if error is not None:
            result["error"] = error
        results.append(result)

    _write_json(manifest_path, manifest)
    usage = client.telemetry_snapshot()
    summary = {
        "generated": sum(item["status"] == "PASS" for item in results),
        "failed": sum(item["status"] == "FAILED" for item in results),
        "results": results,
        "usage": usage,
    }
    _write_json(batch_report.parent / "cover_letter_batch_report.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate concise grounded cover letters for a cv_auto batch.")
    parser.add_argument("--batch-report", required=True)
    parser.add_argument("--outputs", default="outputs/auto")
    parser.add_argument("--vacancy-state", default="vacancy_state")
    parser.add_argument("--generation-state", default="generation_state")
    parser.add_argument("--max-estimated-cost-usd", type=float, default=1.0)
    args = parser.parse_args()
    if args.max_estimated_cost_usd <= 0:
        parser.error("--max-estimated-cost-usd must be > 0")
    result = asyncio.run(generate_batch(
        batch_report=Path(args.batch_report),
        outputs=Path(args.outputs),
        vacancy_state=Path(args.vacancy_state),
        generation_state=Path(args.generation_state),
        max_estimated_cost_usd=args.max_estimated_cost_usd,
    ))
    print(json.dumps({
        "generated": result["generated"],
        "failed": result["failed"],
        "estimated_cost_usd": result["usage"].get("estimated_cost_usd"),
        "known_estimated_cost_usd": result["usage"].get("known_estimated_cost_usd"),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
