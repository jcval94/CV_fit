from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
ALLOWED_STATUSES = {
    "NOT_APPLIED",
    "APPLIED",
    "INTERVIEW",
    "REJECTED",
    "OFFER",
    "WITHDRAWN",
    "ACCEPTED",
}
APPLIED_STATUSES = {"APPLIED", "INTERVIEW", "REJECTED", "OFFER", "WITHDRAWN", "ACCEPTED"}
TERMINAL_STATUSES = {"NOT_APPLIED", "REJECTED", "WITHDRAWN", "ACCEPTED"}
ALLOWED_EVIDENCE_KINDS = {"USER_CONFIRMED", "EXTERNAL_RECORD", "SYSTEM_OBSERVED"}


def _read(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalize_time(value: str | None, *, fallback: str) -> tuple[str, str]:
    text = str(value or "").strip()
    if not text:
        return fallback, "recorded_at_fallback"
    normalized = text.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("occurred_at must include a timezone offset or Z")
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat(), "explicit_event_time"


def _sha(value: str | None) -> str | None:
    text = str(value or "").strip()
    return hashlib.sha256(text.encode("utf-8")).hexdigest() if text else None


def _empty() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "entries": {}}


def _load(path: Path) -> dict[str, Any]:
    state = _read(path, _empty())
    if state.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeError("application state schema changed; migrate explicitly")
    state.setdefault("entries", {})
    return state


def _event_id(*, vacancy_id: str, status: str, occurred_at: str, evidence_kind: str, evidence_ref_sha256: str | None) -> str:
    raw = "|".join((vacancy_id, status, occurred_at, evidence_kind, evidence_ref_sha256 or ""))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def record_application_event(
    *,
    state_path: Path,
    vacancy_state: Path,
    vacancy_id: str,
    status: str,
    occurred_at: str | None = None,
    evidence_kind: str = "USER_CONFIRMED",
    evidence_ref: str | None = None,
    recorded_by: str | None = None,
) -> dict[str, Any]:
    vacancy_id = str(vacancy_id or "").strip()
    status = str(status or "").strip().upper()
    evidence_kind = str(evidence_kind or "").strip().upper()
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"unsupported application status: {status}")
    if evidence_kind not in ALLOWED_EVIDENCE_KINDS:
        raise ValueError(f"unsupported evidence kind: {evidence_kind}")
    if not (vacancy_state / "records" / f"{vacancy_id}.json").exists():
        raise ValueError(f"unknown vacancy_id: {vacancy_id}")

    recorded_at = _now()
    event_time, time_basis = _normalize_time(occurred_at, fallback=recorded_at)
    ref_hash = _sha(evidence_ref)
    event_id = _event_id(
        vacancy_id=vacancy_id,
        status=status,
        occurred_at=event_time,
        evidence_kind=evidence_kind,
        evidence_ref_sha256=ref_hash,
    )
    state = _load(state_path)
    entry = state["entries"].setdefault(vacancy_id, {"vacancy_id": vacancy_id, "events": []})
    events = entry.setdefault("events", [])
    existing = next((item for item in events if item.get("event_id") == event_id), None)
    if existing:
        return existing

    event = {
        "event_id": event_id,
        "status": status,
        "occurred_at": event_time,
        "occurred_at_basis": time_basis,
        "recorded_at": recorded_at,
        "evidence_kind": evidence_kind,
        "evidence_ref_sha256": ref_hash,
        "recorded_by": str(recorded_by or "").strip() or None,
    }
    events.append(event)
    events.sort(key=lambda item: (str(item.get("occurred_at") or ""), str(item.get("recorded_at") or ""), str(item.get("event_id") or "")))
    latest = events[-1]
    entry["current_status"] = latest["status"]
    entry["current_status_event_id"] = latest["event_id"]
    entry["updated_at"] = recorded_at
    _write(state_path, state)
    return event


def summarize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    events = [item for item in entry.get("events", []) if isinstance(item, dict)]
    statuses = {str(item.get("status") or "") for item in events}
    current = str(entry.get("current_status") or "") or None
    return {
        "current_status": current,
        "applied": bool(statuses & APPLIED_STATUSES),
        "interviewed": "INTERVIEW" in statuses,
        "offered": bool(statuses & {"OFFER", "ACCEPTED"}),
        "accepted": "ACCEPTED" in statuses,
        "explicitly_not_applied": current == "NOT_APPLIED",
        "terminal": current in TERMINAL_STATUSES,
        "event_count": len(events),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Record explicit, append-only job-application outcome evidence.")
    parser.add_argument("--state", default="generation_state/application_state.json")
    parser.add_argument("--vacancy-state", default="vacancy_state")
    parser.add_argument("--vacancy-id", required=True)
    parser.add_argument("--status", required=True, choices=sorted(ALLOWED_STATUSES))
    parser.add_argument("--occurred-at", default=None)
    parser.add_argument("--evidence-kind", default="USER_CONFIRMED", choices=sorted(ALLOWED_EVIDENCE_KINDS))
    parser.add_argument("--evidence-ref", default=None)
    parser.add_argument("--recorded-by", default=None)
    args = parser.parse_args()
    event = record_application_event(
        state_path=Path(args.state),
        vacancy_state=Path(args.vacancy_state),
        vacancy_id=args.vacancy_id,
        status=args.status,
        occurred_at=args.occurred_at,
        evidence_kind=args.evidence_kind,
        evidence_ref=args.evidence_ref,
        recorded_by=args.recorded_by,
    )
    print(json.dumps({"event_id": event["event_id"], "status": event["status"], "occurred_at": event["occurred_at"], "occurred_at_basis": event["occurred_at_basis"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
