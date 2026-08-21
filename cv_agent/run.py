from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
from pathlib import Path

from cv_agent.adk_runtime import AdkStructuredClient
from cv_agent.workflow import run_agentic_cv


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate and iteratively review one evidence-grounded vacancy-specific CV with OpenAI-backed ADK.")
    parser.add_argument("--vacancy-id", required=True)
    parser.add_argument("--vacancy-state", default="vacancy_state")
    parser.add_argument("--evidence-state", default="rag_state")
    parser.add_argument("--outputs", default="outputs")
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()

    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = Path(args.outputs) / args.vacancy_id / run_id
    report = asyncio.run(run_agentic_cv(
        vacancy_id=args.vacancy_id,
        client=AdkStructuredClient(),
        output_dir=output_dir,
        vacancy_state=Path(args.vacancy_state),
        evidence_state=Path(args.evidence_state),
        run_id=run_id,
    ))
    print(f"status={report['status']} quality_target_reached={report['quality_target_reached']} iterations={report['iterations_executed']}")
    print(f"output={output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
