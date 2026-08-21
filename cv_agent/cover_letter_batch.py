from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from cv_agent.adk_runtime import AdkStructuredClient
from cv_agent.cover_letter import generate_cover_letter
from cv_agent.schemas import CVDocument


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _final_cv(path: Path) -> CVDocument:
    payload = _read_json(path)
    return CVDocument.model_validate(payload.get("cv", payload))


async def generate_batch(
    *,
    batch_report: Path,
    outputs: Path,
    vacancy_state: Path,
    max_estimated_cost_usd: float,
) -> dict:
    report = _read_json(batch_report)
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
        await generate_cover_letter(client=client, vacancy=vacancy, final_cv=cv, output_dir=output_dir)
        run_report_path = output_dir / "run_report.json"
        run_report = _read_json(run_report_path)
        run_report["cover_letter_status"] = "PASS"
        run_report["cover_letter_file"] = "cover_letter_final.md"
        _write_json(run_report_path, run_report)
        results.append({"vacancy_id": vacancy_id, "run_id": run_id, "status": "PASS"})

    usage = client.telemetry_snapshot()
    summary = {
        "generated": len(results),
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
    parser.add_argument("--max-estimated-cost-usd", type=float, default=1.0)
    args = parser.parse_args()
    if args.max_estimated_cost_usd <= 0:
        parser.error("--max-estimated-cost-usd must be > 0")
    result = asyncio.run(generate_batch(
        batch_report=Path(args.batch_report),
        outputs=Path(args.outputs),
        vacancy_state=Path(args.vacancy_state),
        max_estimated_cost_usd=args.max_estimated_cost_usd,
    ))
    print(json.dumps({"generated": result["generated"], "estimated_cost_usd": result["usage"].get("estimated_cost_usd")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
