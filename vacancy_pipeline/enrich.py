from __future__ import annotations

import argparse
import hashlib
import html as html_lib
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from vacancy_pipeline.contract import detect_source_format, extract_url


USER_AGENT = "CV_fit/1.0 (+https://github.com/jcval94/CV_fit; employer-JD retrieval)"
AUTO_DIR_PARTS = ("enriched", "auto")


class _JsonLdParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._capture = False
        self._parts: list[str] = []
        self.scripts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() != "script":
            return
        attrs_map = {str(key).casefold(): str(value or "") for key, value in attrs}
        if attrs_map.get("type", "").casefold().split(";")[0].strip() == "application/ld+json":
            self._capture = True
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == "script" and self._capture:
            self.scripts.append("".join(self._parts).strip())
            self._capture = False
            self._parts = []


class _TextParser(HTMLParser):
    BLOCK_TAGS = {"p", "div", "li", "br", "tr", "section", "h1", "h2", "h3", "h4"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() in self.BLOCK_TAGS:
            self.parts.append("\n")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    if "<" in text and ">" in text:
        parser = _TextParser()
        try:
            parser.feed(text)
            text = " ".join(parser.parts)
        except Exception:
            text = re.sub(r"<[^>]+>", " ", text)
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _split_items(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        raw = value
    else:
        text = str(value)
        text = re.sub(r"</?(?:li|p|div|br|tr|h\d)[^>]*>", "\n", text, flags=re.IGNORECASE)
        raw = re.split(r"[\n\r•]+", text)
    result: list[str] = []
    seen: set[str] = set()
    for item in raw:
        if isinstance(item, dict):
            item = item.get("name") or item.get("value") or ""
        cleaned = _clean_text(item)
        if len(cleaned) < 24:
            continue
        key = cleaned.casefold()
        if key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result[:20]


def _walk_jsonld(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_jsonld(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_jsonld(child)


def _is_job_posting(node: dict[str, Any]) -> bool:
    node_type = node.get("@type")
    types = node_type if isinstance(node_type, list) else [node_type]
    return any(str(item).casefold() == "jobposting" for item in types if item)


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.casefold()) if len(token) > 1}


def _overlap(a: str, b: str) -> float:
    left, right = _tokens(a), _tokens(b)
    if not left or not right:
        return 0.0
    return len(left & right) / min(len(left), len(right))


def _organization_name(node: dict[str, Any]) -> str:
    org = node.get("hiringOrganization")
    if isinstance(org, dict):
        return _clean_text(org.get("name"))
    return _clean_text(org)


def extract_matching_job_posting(html_text: str, *, role_title: str, company: str) -> dict[str, Any] | None:
    parser = _JsonLdParser()
    parser.feed(html_text)
    candidates: list[tuple[float, dict[str, Any]]] = []
    for raw in parser.scripts:
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for node in _walk_jsonld(payload):
            if not _is_job_posting(node):
                continue
            title = _clean_text(node.get("title"))
            employer = _organization_name(node)
            title_score = _overlap(role_title, title)
            company_score = _overlap(company, employer)
            score = title_score * 0.75 + company_score * 0.25
            if title_score >= 0.5 or score >= 0.45:
                candidates.append((score, node))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def job_posting_fields(node: dict[str, Any]) -> dict[str, Any]:
    description = _clean_text(node.get("description"))
    requirements: list[str] = []
    for key in ("qualifications", "experienceRequirements", "educationRequirements", "skills"):
        requirements.extend(_split_items(node.get(key)))
    responsibilities = _split_items(node.get("responsibilities"))
    return {
        "description": description or None,
        "requirements": list(dict.fromkeys(requirements))[:20],
        "responsibilities": responsibilities[:20],
    }


def fetch_html(url: str, *, timeout: float = 15.0) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
    with urlopen(request, timeout=timeout) as response:
        content_type = str(response.headers.get("Content-Type") or "")
        if "html" not in content_type.casefold():
            raise ValueError(f"unexpected content type: {content_type}")
        return response.read(2_500_000).decode("utf-8", errors="replace")


def _entry_values(source_format: str, item: dict[str, Any]) -> tuple[str, str, str | None]:
    if source_format == "gptw_v1":
        return (
            _clean_text(item.get("company")),
            _clean_text(item.get("role_title")),
            extract_url(item.get("url")),
        )
    return (
        _clean_text(item.get("empresa")),
        _clean_text(item.get("puesto")),
        extract_url(item.get("url_postulacion")),
    )


def _already_has_jd(item: dict[str, Any]) -> bool:
    description = _clean_text(item.get("description"))
    details = _split_items(item.get("requirements")) + _split_items(item.get("responsibilities"))
    return len(description) >= 300 or len(details) >= 3


def _auto_output_path(repo: Path, source_root: str, *, company: str, role: str, url: str) -> Path:
    slug = re.sub(r"[^a-z0-9]+", "-", f"{company}-{role}".casefold()).strip("-")[:90] or "vacancy"
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10]
    return repo / source_root / "enriched" / "auto" / f"{slug}-{digest}.json"


def _build_enriched_document(
    *,
    source_format: str,
    original: dict[str, Any],
    item: dict[str, Any],
    fields: dict[str, Any],
    url: str,
    retrieved_at: str,
) -> dict[str, Any]:
    enriched_item = dict(item)
    enriched_item.update({key: value for key, value in fields.items() if value})
    if source_format == "gptw_v1":
        enriched_item["url"] = url
        return {
            "last_updated": retrieved_at,
            "total_results": 1,
            "jd_source_url": url,
            "jd_retrieved_at": retrieved_at,
            "jd_capture_mode": "official_source_jsonld_jobposting_auto",
            "vacancies": [enriched_item],
        }
    metadata = dict(original.get("metadata") or {})
    metadata["total_vacantes_encontradas"] = 1
    metadata["criterio_temporal"] = "Preservación automática de JD oficial para generación CV"
    enriched_item["url_postulacion"] = url
    return {
        "metadata": metadata,
        "jd_source_url": url,
        "jd_retrieved_at": retrieved_at,
        "jd_capture_mode": "official_source_jsonld_jobposting_auto",
        "vacantes": [enriched_item],
    }


def _same_enrichment(existing: dict[str, Any], candidate: dict[str, Any]) -> bool:
    def stable(value: dict[str, Any]) -> dict[str, Any]:
        value = json.loads(json.dumps(value))
        value.pop("jd_retrieved_at", None)
        value.pop("last_updated", None)
        return value
    return stable(existing) == stable(candidate)


def enrich_repo(
    *,
    repo: Path,
    report_path: Path,
    max_fetches: int = 12,
    fetcher: Callable[[str], str] = fetch_html,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    fetches = 0
    written = 0
    unchanged = 0
    roots = ("GPTW", "Vacantes")
    for source_root in roots:
        root = repo / source_root
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.json")):
            relative_parts = path.relative_to(root).parts
            if len(relative_parts) >= 2 and tuple(part.casefold() for part in relative_parts[:2]) == AUTO_DIR_PARTS:
                continue
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                results.append({"source": str(path.relative_to(repo)), "status": "SKIPPED_INVALID_JSON", "error": type(exc).__name__})
                continue
            source_format = detect_source_format(document)
            if source_format == "unknown":
                continue
            entries = document.get("vacancies" if source_format == "gptw_v1" else "vacantes") or []
            for item in entries:
                if not isinstance(item, dict) or _already_has_jd(item):
                    continue
                company, role, url = _entry_values(source_format, item)
                if not company or not role or not url:
                    results.append({"source": str(path.relative_to(repo)), "company": company, "role": role, "status": "NEEDS_FULL_JD", "reason": "missing_specific_application_url"})
                    continue
                output_path = _auto_output_path(repo, source_root, company=company, role=role, url=url)
                if output_path.exists():
                    try:
                        existing = json.loads(output_path.read_text(encoding="utf-8"))
                        existing_entries = existing.get("vacancies" if source_format == "gptw_v1" else "vacantes") or []
                        if existing_entries and _already_has_jd(existing_entries[0]):
                            results.append({"source": str(path.relative_to(repo)), "company": company, "role": role, "status": "ALREADY_ENRICHED", "output": str(output_path.relative_to(repo))})
                            continue
                    except Exception:
                        pass
                if fetches >= max_fetches:
                    results.append({"source": str(path.relative_to(repo)), "company": company, "role": role, "status": "DEFERRED_FETCH_CAP"})
                    continue
                fetches += 1
                try:
                    html_text = fetcher(url)
                    node = extract_matching_job_posting(html_text, role_title=role, company=company)
                    if node is None:
                        results.append({"source": str(path.relative_to(repo)), "company": company, "role": role, "url": url, "status": "NEEDS_FULL_JD", "reason": "no_matching_jobposting_jsonld"})
                        continue
                    fields = job_posting_fields(node)
                    if len(_clean_text(fields.get("description"))) < 300 and len(fields.get("requirements") or []) + len(fields.get("responsibilities") or []) < 3:
                        results.append({"source": str(path.relative_to(repo)), "company": company, "role": role, "url": url, "status": "NEEDS_FULL_JD", "reason": "retrieved_jobposting_still_sparse"})
                        continue
                    retrieved_at = _utc_now()
                    candidate = _build_enriched_document(
                        source_format=source_format,
                        original=document,
                        item=item,
                        fields=fields,
                        url=url,
                        retrieved_at=retrieved_at,
                    )
                    if output_path.exists():
                        existing = json.loads(output_path.read_text(encoding="utf-8"))
                        if _same_enrichment(existing, candidate):
                            unchanged += 1
                            results.append({"source": str(path.relative_to(repo)), "company": company, "role": role, "status": "UNCHANGED", "output": str(output_path.relative_to(repo))})
                            continue
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_text(json.dumps(candidate, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                    written += 1
                    results.append({"source": str(path.relative_to(repo)), "company": company, "role": role, "url": url, "status": "ENRICHED", "output": str(output_path.relative_to(repo))})
                except (HTTPError, URLError, TimeoutError, ValueError) as exc:
                    results.append({"source": str(path.relative_to(repo)), "company": company, "role": role, "url": url, "status": "NEEDS_FULL_JD", "reason": f"{type(exc).__name__}: {exc}"[:300]})
                except Exception as exc:
                    results.append({"source": str(path.relative_to(repo)), "company": company, "role": role, "url": url, "status": "NEEDS_FULL_JD", "reason": f"unexpected_{type(exc).__name__}"})

    report = {
        "schema_version": 1,
        "run_at": _utc_now(),
        "fetches": fetches,
        "written": written,
        "unchanged": unchanged,
        "needs_full_jd": sum(item.get("status") == "NEEDS_FULL_JD" for item in results),
        "results": results,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Retrieve employer-authored JobPosting JSON-LD for sparse daily vacancies.")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--report", default="/tmp/vacancy-enrichment-report.json")
    parser.add_argument("--max-fetches", type=int, default=12)
    args = parser.parse_args()
    report = enrich_repo(repo=Path(args.repo), report_path=Path(args.report), max_fetches=max(args.max_fetches, 0))
    print(json.dumps({key: report[key] for key in ("fetches", "written", "unchanged", "needs_full_jd")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
