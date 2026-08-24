from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


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


def _parse_time(value: str) -> str:
    normalized = str(value).strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("period timestamps must include timezone offset or Z")
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _sha(value: str | None) -> str | None:
    text = str(value or "").strip()
    return hashlib.sha256(text.encode("utf-8")).hexdigest() if text else None


def _empty() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "entries": {}}


def _load(path: Path) -> dict[str, Any]:
    state = _read(path, _empty())
    if state.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeError("provider reconciliation schema changed; migrate explicitly")
    state.setdefault("entries", {})
    return state


def record_provider_statement(
    *,
    state_path: Path,
    period_start: str,
    period_end: str,
    actual_cost_usd: float,
    evidence_ref: str | None = None,
    recorded_by: str | None = None,
) -> dict[str, Any]:
    start = _parse_time(period_start)
    end = _parse_time(period_end)
    if start >= end:
        raise ValueError("period_start must be before period_end")
    cost = float(actual_cost_usd)
    if cost < 0:
        raise ValueError("actual_cost_usd must be >= 0")
    ref_hash = _sha(evidence_ref)
    raw = "|".join((start, end, f"{cost:.8f}", ref_hash or ""))
    entry_id = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    state = _load(state_path)
    if entry_id in state["entries"]:
        return state["entries"][entry_id]
    entry = {
        "entry_id": entry_id,
        "period_start": start,
        "period_end": end,
        "actual_cost_usd": round(cost, 8),
        "currency": "USD",
        "source_kind": "PROVIDER_STATEMENT_USER_RECORDED",
        "evidence_ref_sha256": ref_hash,
        "recorded_at": _now(),
        "recorded_by": str(recorded_by or "").strip() or None,
    }
    state["entries"][entry_id] = entry
    _write(state_path, state)
    return entry


def main() -> int:
    parser = argparse.ArgumentParser(description="Record a provider billing/usage statement for telemetry reconciliation.")
    parser.add_argument("--state", default="generation_state/provider_reconciliation.json")
    parser.add_argument("--period-start", required=True)
    parser.add_argument("--period-end", required=True)
    parser.add_argument("--actual-cost-usd", required=True, type=float)
    parser.add_argument("--evidence-ref", default=None)
    parser.add_argument("--recorded-by", default=None)
    args = parser.parse_args()
    entry = record_provider_statement(
        state_path=Path(args.state),
        period_start=args.period_start,
        period_end=args.period_end,
        actual_cost_usd=args.actual_cost_usd,
        evidence_ref=args.evidence_ref,
        recorded_by=args.recorded_by,
    )
    print(json.dumps({"entry_id": entry["entry_id"], "period_start": entry["period_start"], "period_end": entry["period_end"], "actual_cost_usd": entry["actual_cost_usd"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
