from __future__ import annotations

import json
import os
import re
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, TextIO


_SENSITIVE_KEY_FRAGMENTS = (
    "access_token",
    "api_key",
    "authorization",
    "bearer",
    "email",
    "instruction",
    "password",
    "phone",
    "prompt",
    "recipient",
    "secret",
    "token",
)

_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_BEARER_RE = re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{8,}")
_OPENAI_KEY_RE = re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b")
_LONG_DIGITS_RE = re.compile(r"(?<!\d)\+?\d{10,15}(?!\d)")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _sensitive_key(key: str) -> bool:
    normalized = key.lower()
    return any(fragment in normalized for fragment in _SENSITIVE_KEY_FRAGMENTS)


def _sanitize_text(value: str, *, limit: int = 1200) -> str:
    text = value.replace("\r", " ").replace("\n", " ")
    text = _BEARER_RE.sub("Bearer [REDACTED]", text)
    text = _OPENAI_KEY_RE.sub("[REDACTED_KEY]", text)
    text = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    text = _LONG_DIGITS_RE.sub("[REDACTED_NUMBER]", text)
    return text[:limit]


def sanitize(value: Any, *, key: str | None = None) -> Any:
    """Return a log-safe representation without leaking common secret/PII fields."""
    if key is not None and _sensitive_key(key):
        return "[REDACTED]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _sanitize_text(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): sanitize(v, key=str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [sanitize(item) for item in value]
    return _sanitize_text(str(value))


def _compact(value: Any) -> str:
    safe = sanitize(value)
    if isinstance(safe, (dict, list)):
        return json.dumps(safe, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if safe is None:
        return "null"
    if isinstance(safe, bool):
        return "true" if safe else "false"
    return str(safe)


class EventLogger:
    """Small structured logger optimized for GitHub Actions and local CLI runs.

    Every line is human-scannable and machine-parseable enough for grep. When
    `event_log_path` (or CVFIT_EVENT_LOG) is set, the same event is appended as
    JSONL for later E2E diagnosis.
    """

    def __init__(
        self,
        component: str,
        *,
        run_id: str | None = None,
        vacancy_id: str | None = None,
        event_log_path: str | Path | None = None,
        stream: TextIO | None = None,
    ) -> None:
        self.component = component
        self.run_id = run_id or os.getenv("CVFIT_RUN_ID") or os.getenv("GITHUB_RUN_ID")
        self.vacancy_id = vacancy_id
        configured_path = event_log_path or os.getenv("CVFIT_EVENT_LOG")
        self.event_log_path = Path(configured_path) if configured_path else None
        self.stream = stream or sys.stdout

    def bind(self, *, run_id: str | None = None, vacancy_id: str | None = None) -> "EventLogger":
        return EventLogger(
            self.component,
            run_id=run_id if run_id is not None else self.run_id,
            vacancy_id=vacancy_id if vacancy_id is not None else self.vacancy_id,
            event_log_path=self.event_log_path,
            stream=self.stream,
        )

    def emit(self, level: str, event: str, **fields: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "ts": _utc_now(),
            "level": level.upper(),
            "component": self.component,
            "event": event,
        }
        if self.run_id:
            payload["run_id"] = self.run_id
        if self.vacancy_id:
            payload["vacancy_id"] = self.vacancy_id
        for key, value in fields.items():
            if value is not None:
                payload[key] = sanitize(value, key=key)

        ordered_keys = ["ts", "level", "component", "event", "run_id", "vacancy_id"]
        extras = sorted(key for key in payload if key not in ordered_keys)
        parts = ["CVFIT"]
        for key in ordered_keys + extras:
            if key in payload:
                parts.append(f"{key}={_compact(payload[key])}")
        print(" | ".join(parts), file=self.stream, flush=True)

        if self.event_log_path:
            self.event_log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.event_log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        return payload

    def info(self, event: str, **fields: Any) -> dict[str, Any]:
        return self.emit("INFO", event, **fields)

    def warning(self, event: str, **fields: Any) -> dict[str, Any]:
        return self.emit("WARNING", event, **fields)

    def error(self, event: str, **fields: Any) -> dict[str, Any]:
        return self.emit("ERROR", event, **fields)

    @contextmanager
    def span(self, stage: str, **fields: Any) -> Iterator[None]:
        started = time.perf_counter()
        self.info("stage_started", stage=stage, **fields)
        try:
            yield
        except Exception as exc:
            duration_ms = round((time.perf_counter() - started) * 1000, 1)
            self.error(
                "stage_failed",
                stage=stage,
                duration_ms=duration_ms,
                error_type=type(exc).__name__,
                error=str(exc),
                **fields,
            )
            raise
        else:
            duration_ms = round((time.perf_counter() - started) * 1000, 1)
            self.info("stage_completed", stage=stage, duration_ms=duration_ms, **fields)
