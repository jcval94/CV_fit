from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from cv_agent.adk_runtime import AdkStructuredClient
from cv_agent.workflow import run_agentic_cv


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate and iteratively review one evidence-grounded vacancy-specific CV with OpenAI-backed ADK.")
    parser.add_argument("--vacancy-id", required=True)
    parser.add_argument("--vacancy-state", default="vacancy_state")
    parser.add_argument("--evidence-state", default="rag_state")
    parser.add_argument("--outputs", default="outputs")
    parser.add_argument("--run-id", default=None)
    parser.add_argument(
        "--max-estimated-cost-usd",
        type=float,
        default=None,
        help="Stop before starting another OpenAI call once the cumulative estimated cost reaches this budget.",
    )
    args = parser.parse_args()

    if args.max_estimated_cost_usd is not None and args.max_estimated_cost_usd <= 0:
        parser.error("--max-estimated-cost-usd must be greater than zero")

    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = Path(args.outputs) / args.vacancy_id / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    client = AdkStructuredClient(max_estimated_cost_usd=args.max_estimated_cost_usd)

    try:
        report = asyncio.run(run_agentic_cv(
            vacancy_id=args.vacancy_id,
            client=client,
            output_dir=output_dir,
            vacancy_state=Path(args.vacancy_state),
            evidence_state=Path(args.evidence_state),
            run_id=run_id,
        ))
    except Exception:
        _write_json(output_dir / "usage_report.json", client.telemetry_snapshot())
        raise

    usage = client.telemetry_snapshot()
    _write_json(output_dir / "usage_report.json", usage)
    report["usage_report_file"] = "usage_report.json"
    report["usage_summary"] = {
        key: value
        for key, value in usage.items()
        if key not in {"calls"}
    }
    _write_json(output_dir / "run_report.json", report)

    print(f"status={report['status']} quality_target_reached={report['quality_target_reached']} iterations={report['iterations_executed']}")
    print(
        "usage="
        f"calls:{usage['call_count']} "
        f"tokens:{usage['total_tokens']} "
        f"estimated_cost_usd:{usage['estimated_cost_usd']} "
        f"budget_usd:{usage['max_estimated_cost_usd']}"
    )
    print(f"output={output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
