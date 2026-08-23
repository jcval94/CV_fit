from __future__ import annotations

import sys

from cv_observability import EventLogger
from vacancy_pipeline.pipeline import main


def _arg_value(name: str) -> str | None:
    try:
        index = sys.argv.index(name)
    except ValueError:
        return None
    return sys.argv[index + 1] if index + 1 < len(sys.argv) else None


logger = EventLogger("vacancy_ingest", run_id=_arg_value("--run-id"))
try:
    with logger.span("vacancy_ingest"):
        exit_code = main()
except Exception:
    raise
logger.emit("INFO" if exit_code == 0 else "ERROR", "process_finished", exit_code=exit_code)
raise SystemExit(exit_code)
