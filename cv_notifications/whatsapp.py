from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


STATE_SCHEMA_VERSION = 1
PLAN_SCHEMA_VERSION = 1
DEFAULT_GRAPH_VERSION = "v23.0"
DEFAULT_TEMPLATE_NAME = "cv_fit_opportunity_ready"
DEFAULT_TEMPLATE_LANGUAGE = "es_MX"
FINAL_STATUSES = {"ACCEPTED", "RESERVED", "UNKNOWN_DELIVERY", "FAILED"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _recipient_hash(recipient: str) -> str:
    return _sha256_bytes(recipient.strip().encode("utf-8"))[:16]


def _base_url(value: str) -> str:
    value = value.strip()
    if not value.startswith(("https://", "http://")):
        raise ValueError("page_url must be an absolute http(s) URL")
    return value.rstrip("/")


def _text(value: Any, *, fallback: str = "n/a", limit: int = 1024) -> str:
    if value is None or value == "":
        return fallback
    return str(value).strip()[:limit]


def _score(value: Any) -> str:
    if value is None or value == "":
        return "n/a"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return _text(value, limit=32)
    if numeric.is_integer():
        return str(int(numeric))
    return f"{numeric:.1f}"


def _primary_html_file(site_dir: Path, vacancy_id: str) -> str | None:
    bundle_path = site_dir / "vacancies" / vacancy_id / "application_bundle_report.json"
    bundle = _read_json(bundle_path, {})
    for item in bundle.get("templates", []):
        if item.get("role") == "primary" and item.get("html_file"):
            return str(item["html_file"])
    fallback = site_dir / "vacancies" / vacancy_id / "cv_primary.html"
    return fallback.name if fallback.exists() else None


def _fingerprint(
    *,
    vacancy_id: str,
    cv_sha256: str,
    vacancy_url: str,
    recipient_hash: str,
    template_name: str,
    template_language: str,
) -> str:
    payload = {
        "vacancy_id": vacancy_id,
        "cv_sha256": cv_sha256,
        "vacancy_url": vacancy_url,
        "recipient_hash": recipient_hash,
        "template_name": template_name,
        "template_language": template_language,
    }
    stable = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha256_bytes(stable)


def reserve_notifications(
    *,
    site_dir: Path,
    state_path: Path,
    plan_path: Path,
    page_url: str,
    recipient: str,
    template_name: str = DEFAULT_TEMPLATE_NAME,
    template_language: str = DEFAULT_TEMPLATE_LANGUAGE,
) -> dict[str, Any]:
    """Reserve READY notifications before any outbound send.

    A reservation is persisted before delivery so reruns cannot send the same
    CV artifact twice. If delivery becomes ambiguous, automatic retries stay
    disabled; the state is left for explicit human reconciliation.
    """
    page_url = _base_url(page_url)
    recipient = recipient.strip()
    if not recipient:
        raise ValueError("recipient is required")
    showcase = _read_json(site_dir / "showcase.json", {"vacancies": []})
    process = _read_json(site_dir / "process_metrics.json", {"entries": {}})
    state = _read_json(
        state_path,
        {"schema_version": STATE_SCHEMA_VERSION, "entries": {}},
    )
    if state.get("schema_version") != STATE_SCHEMA_VERSION:
        raise RuntimeError("unsupported WhatsApp notification state schema")
    entries = state.setdefault("entries", {})
    recipient_digest = _recipient_hash(recipient)
    reserved: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []

    for row in showcase.get("vacancies", []):
        vacancy_id = str(row.get("vacancy_id") or "").strip()
        if not vacancy_id:
            continue
        if not bool(row.get("ready_to_send")):
            skipped.append({"vacancy_id": vacancy_id, "reason": "not_ready_to_send"})
            continue
        vacancy_url = str(row.get("url") or "").strip()
        if not vacancy_url:
            skipped.append({"vacancy_id": vacancy_id, "reason": "missing_vacancy_url"})
            continue
        primary_html = _primary_html_file(site_dir, vacancy_id)
        if not primary_html:
            skipped.append({"vacancy_id": vacancy_id, "reason": "missing_primary_html"})
            continue
        cv_path = site_dir / "vacancies" / vacancy_id / primary_html
        if not cv_path.exists():
            skipped.append({"vacancy_id": vacancy_id, "reason": "primary_html_not_published"})
            continue

        cv_sha256 = _sha256_file(cv_path)
        fingerprint = _fingerprint(
            vacancy_id=vacancy_id,
            cv_sha256=cv_sha256,
            vacancy_url=vacancy_url,
            recipient_hash=recipient_digest,
            template_name=template_name,
            template_language=template_language,
        )
        existing = entries.get(fingerprint)
        if isinstance(existing, dict) and existing.get("status") in FINAL_STATUSES:
            skipped.append({"vacancy_id": vacancy_id, "reason": f"already_{str(existing.get('status')).lower()}"})
            continue

        metric = (process.get("entries") or {}).get(vacancy_id, {})
        cv_url = f"{page_url}/vacancies/{vacancy_id}/{primary_html}"
        detail_url = f"{page_url}/vacancies/{vacancy_id}/index.html"
        item = {
            "fingerprint": fingerprint,
            "vacancy_id": vacancy_id,
            "company": _text(row.get("company"), limit=120),
            "role_title": _text(row.get("role_title"), limit=180),
            "source_fit": _score(row.get("fit_score")),
            "headhunter_score": _score(metric.get("headhunter_score")),
            "rag_coverage": _score(metric.get("coverage_score")),
            "cv_url": cv_url,
            "review_url": detail_url,
            "vacancy_url": vacancy_url,
            "cv_sha256": cv_sha256,
            "template_name": template_name,
            "template_language": template_language,
        }
        entries[fingerprint] = {
            **item,
            "status": "RESERVED",
            "reserved_at": _utc_now(),
            "recipient_hash": recipient_digest,
        }
        reserved.append(item)

    plan = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "created_at": _utc_now(),
        "page_url": page_url,
        "recipient_hash": recipient_digest,
        "count": len(reserved),
        "notifications": reserved,
        "skipped": skipped,
    }
    _write_json(state_path, state)
    _write_json(plan_path, plan)
    return plan


def build_template_payload(*, notification: dict[str, Any], recipient: str) -> dict[str, Any]:
    """Build the seven-variable Meta template payload used by CV_fit."""
    values = [
        _text(notification.get("company"), limit=120),
        _text(notification.get("role_title"), limit=180),
        _text(notification.get("source_fit"), limit=32),
        _text(notification.get("headhunter_score"), limit=32),
        _text(notification.get("rag_coverage"), limit=32),
        _text(notification.get("cv_url"), limit=1024),
        _text(notification.get("vacancy_url"), limit=1024),
    ]
    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "template",
        "template": {
            "name": notification.get("template_name") or DEFAULT_TEMPLATE_NAME,
            "language": {"code": notification.get("template_language") or DEFAULT_TEMPLATE_LANGUAGE},
            "components": [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": value} for value in values],
                }
            ],
        },
    }


def _post_json(*, url: str, token: str, payload: dict[str, Any], timeout: float = 20.0) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        return json.loads(body or "{}")


def send_reserved_notifications(
    *,
    state_path: Path,
    plan_path: Path,
    access_token: str,
    phone_number_id: str,
    recipient: str,
    graph_version: str = DEFAULT_GRAPH_VERSION,
) -> dict[str, Any]:
    access_token = access_token.strip()
    phone_number_id = phone_number_id.strip()
    recipient = recipient.strip()
    graph_version = graph_version.strip() or DEFAULT_GRAPH_VERSION
    if not access_token or not phone_number_id or not recipient:
        raise ValueError("WhatsApp access token, phone number id and recipient are required")

    plan = _read_json(plan_path, {"notifications": []})
    state = _read_json(state_path, {"schema_version": STATE_SCHEMA_VERSION, "entries": {}})
    entries = state.setdefault("entries", {})
    endpoint = f"https://graph.facebook.com/{graph_version}/{phone_number_id}/messages"
    results: list[dict[str, Any]] = []

    for notification in plan.get("notifications", []):
        fingerprint = str(notification.get("fingerprint") or "")
        state_entry = entries.get(fingerprint)
        if not fingerprint or not isinstance(state_entry, dict):
            results.append({"fingerprint": fingerprint, "status": "SKIPPED_MISSING_RESERVATION"})
            continue
        if state_entry.get("status") != "RESERVED":
            results.append({"fingerprint": fingerprint, "status": f"SKIPPED_{state_entry.get('status', 'UNKNOWN')}"})
            continue

        payload = build_template_payload(notification=notification, recipient=recipient)
        try:
            response = _post_json(url=endpoint, token=access_token, payload=payload)
            messages = response.get("messages") or []
            message_id = messages[0].get("id") if messages and isinstance(messages[0], dict) else None
            state_entry.update(
                {
                    "status": "ACCEPTED",
                    "accepted_at": _utc_now(),
                    "provider_message_id": message_id,
                    "graph_version": graph_version,
                }
            )
            results.append({"fingerprint": fingerprint, "status": "ACCEPTED", "message_id": message_id})
        except HTTPError as exc:
            try:
                error_body = exc.read().decode("utf-8")
            except Exception:
                error_body = ""
            state_entry.update(
                {
                    "status": "FAILED",
                    "failed_at": _utc_now(),
                    "error": f"HTTP {exc.code}: {error_body}"[:1500],
                    "graph_version": graph_version,
                }
            )
            results.append({"fingerprint": fingerprint, "status": "FAILED", "http_status": exc.code})
        except (URLError, TimeoutError, socket.timeout) as exc:
            state_entry.update(
                {
                    "status": "UNKNOWN_DELIVERY",
                    "failed_at": _utc_now(),
                    "error": f"{type(exc).__name__}: {exc}"[:1500],
                    "graph_version": graph_version,
                }
            )
            results.append({"fingerprint": fingerprint, "status": "UNKNOWN_DELIVERY"})
        except Exception as exc:
            state_entry.update(
                {
                    "status": "FAILED",
                    "failed_at": _utc_now(),
                    "error": f"{type(exc).__name__}: {exc}"[:1500],
                    "graph_version": graph_version,
                }
            )
            results.append({"fingerprint": fingerprint, "status": "FAILED"})
        finally:
            _write_json(state_path, state)

    counts = {
        status: sum(item.get("status") == status for item in results)
        for status in sorted({str(item.get("status")) for item in results})
    }
    return {"count": len(results), "result_counts": counts, "results": results}


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"required environment variable is missing: {name}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Reserve and send idempotent CV_fit WhatsApp notifications.")
    sub = parser.add_subparsers(dest="command", required=True)

    reserve = sub.add_parser("reserve")
    reserve.add_argument("--site-dir", default="_site")
    reserve.add_argument("--state", default="generation_state/whatsapp_notifications.json")
    reserve.add_argument("--plan", default="/tmp/cvfit_whatsapp_plan.json")
    reserve.add_argument("--page-url", required=True)

    send = sub.add_parser("send")
    send.add_argument("--state", default="generation_state/whatsapp_notifications.json")
    send.add_argument("--plan", default="/tmp/cvfit_whatsapp_plan.json")

    args = parser.parse_args()
    if args.command == "reserve":
        plan = reserve_notifications(
            site_dir=Path(args.site_dir),
            state_path=Path(args.state),
            plan_path=Path(args.plan),
            page_url=args.page_url,
            recipient=_required_env("WHATSAPP_RECIPIENT"),
            template_name=os.getenv("WHATSAPP_TEMPLATE_NAME", DEFAULT_TEMPLATE_NAME).strip() or DEFAULT_TEMPLATE_NAME,
            template_language=os.getenv("WHATSAPP_TEMPLATE_LANGUAGE", DEFAULT_TEMPLATE_LANGUAGE).strip() or DEFAULT_TEMPLATE_LANGUAGE,
        )
        print(json.dumps({"count": plan["count"], "skipped": len(plan["skipped"])}, sort_keys=True))
        return 0

    report = send_reserved_notifications(
        state_path=Path(args.state),
        plan_path=Path(args.plan),
        access_token=_required_env("WHATSAPP_ACCESS_TOKEN"),
        phone_number_id=_required_env("WHATSAPP_PHONE_NUMBER_ID"),
        recipient=_required_env("WHATSAPP_RECIPIENT"),
        graph_version=os.getenv("WHATSAPP_GRAPH_VERSION", DEFAULT_GRAPH_VERSION),
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    bad = report["result_counts"].get("FAILED", 0) + report["result_counts"].get("UNKNOWN_DELIVERY", 0)
    return 2 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
