from __future__ import annotations

import sys

from cv_auto.runner import main
from cv_observability import EventLogger


def _arg_value(name: str) -> str | None:
    try:
        index = sys.argv.index(name)
    except ValueError:
        return None
    return sys.argv[index + 1] if index + 1 < len(sys.argv) else None


if __name__ == "__main__":
    logger = EventLogger("cv_generation", run_id=_arg_value("--run-id"))
    try:
        with logger.span("generation_batch"):
            exit_code = main()
    except Exception:
        raise
    logger.emit("INFO" if exit_code == 0 else "ERROR", "process_finished", exit_code=exit_code)
    raise SystemExit(exit_code)
