from __future__ import annotations

import argparse
import hashlib
import json
import logging
import posixpath
import re
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from rag.normalize import NormalizedRecord, normalize_file, resolve_source_commit, slugify


EVIDENCE_PIPELINE_VERSION = 1
EVIDENCE_CHUNK_SCHEMA_VERSION = 1
INDEX_SCHEMA_VERSION = 1
FIELD_RE = re.compile(r"^- \*\*([^*]+):\*\*\s*(.*)$")
TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+#.-]*")
APPROVED_METRIC_STATUSES = {"validated_public", "validated_public_technical"}

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EvidenceChunk:
    schema_version: int
    chunk_id: str
    record_id: str
    record_type: str
    chunk_type: str
    title: str
    heading_path: list[str]
    text: str
    source_path: str
    source_commit: str | None
    source_refs: list[str]
    metric_refs: list[str]
    constraints: list[str]
    retrieval_class: str
    public_safe: bool
    cv_eligible: bool
    confidence: str
    proficiency: str | None
    attributes: dict[str, Any]
    content_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _fields(content: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in content.splitlines():
        match = FIELD_RE.match(line.strip())
        if match:
            result[match.group(1).strip().casefold()] = match.group(2).strip().strip("`")
    return result


def _truthy(value: str | None) -> bool:
    return (value or "").strip().casefold() in {"true", "yes", "approved"}


def _normalized_tokenize(text: str) -> list[str]:
    value = unicodedata.normalize("NFKD", text)
    value = "".join(ch for ch in value if not unicodedata.combining(ch)).casefold()
    return [token for token in TOKEN_RE.findall(value) if len(token) > 1]


def _chunk_hash(payload: dict[str, Any]) -> str:
    stable = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _sha256(stable)


def _record_constraints(record: NormalizedRecord) -> list[str]:
    constraints = []
    for section in record.sections:
        if section.semantic_type == "boundary" and section.content.strip():
            constraints.append(section.content.strip())
    return constraints


def _chunk(
    record: NormalizedRecord,
    *,
    chunk_id: str,
    chunk_type: str,
    title: str,
    heading_path: list[str],
    text: str,
    constraints: list[str],
    cv_eligible: bool,
    proficiency: str | None = None,
    attributes: dict[str, Any] | None = None,
    metric_refs: list[str] | None = None,
) -> EvidenceChunk:
    attrs = attributes or {}
    refs = sorted(set(metric_refs if metric_refs is not None else record.metric_refs))
    hash_payload = {
        "record_id": record.record_id,
        "chunk_id": chunk_id,
        "text": text,
        "constraints": constraints,
        "proficiency": proficiency,
        "attributes": attrs,
        "metric_refs": refs,
        "source_refs": record.source_refs,
    }
    return EvidenceChunk(
        schema_version=EVIDENCE_CHUNK_SCHEMA_VERSION,
        chunk_id=chunk_id,
        record_id=record.record_id,
        record_type=record.record_type,
        chunk_type=chunk_type,
        title=title,
        heading_path=heading_path,
        text=text.strip(),
        source_path=record.source_path,
        source_commit=record.source_commit,
        source_refs=list(record.source_refs),
        metric_refs=refs,
        constraints=list(constraints),
        retrieval_class=record.retrieval_class,
        public_safe=record.public_safe,
        cv_eligible=bool(cv_eligible),
        confidence=record.confidence,
        proficiency=proficiency,
        attributes=attrs,
        content_hash=_chunk_hash(hash_payload),
    )


def _metric_chunk(record: NormalizedRecord, section: Any) -> EvidenceChunk:
    fields = _fields(section.content)
    metric_id = section.title.split("—", 1)[0].strip().split()[0]
    status = fields.get("status", "").casefold()
    public_safe = _truthy(fields.get("public safe"))
    cv_usage = fields.get("cv usage", "").casefold()
    approved = status in APPROVED_METRIC_STATUSES and public_safe and cv_usage == "approved"
    attrs = {
        "metric_id": metric_id,
        "status": fields.get("status"),
        "public_safe_entry": public_safe,
        "cv_usage": fields.get("cv usage"),
        "result": fields.get("result"),
        "approved_cv_wording": fields.get("approved cv wording") or fields.get("approved wording"),
    }
    constraints = []
    if fields.get("usage constraint"):
        constraints.append(fields["usage constraint"])
    text = f"{section.title}\n{section.content}".strip()
    return _chunk(
        record,
        chunk_id=f"{record.record_id}::{metric_id}",
        chunk_type="achievement_metric",
        title=section.title,
        heading_path=section.heading_path,
        text=text,
        constraints=constraints,
        cv_eligible=record.automatic_reuse_eligible and approved,
        attributes=attrs,
        metric_refs=[metric_id],
    )


def _skill_chunk(record: NormalizedRecord, section: Any) -> EvidenceChunk:
    fields = _fields(section.content)
    level = (fields.get("level") or "").casefold() or None
    proficiency = fields.get("proficiency") or level
    attrs = {
        "level": level,
        "proficiency": proficiency,
        "evidence": fields.get("evidence"),
        "coverage": fields.get("coverage"),
        "usage_note": fields.get("usage note"),
        "boundary": fields.get("boundary"),
    }
    constraints = [value for value in (fields.get("usage note"), fields.get("boundary")) if value]
    return _chunk(
        record,
        chunk_id=f"{record.record_id}::{slugify(section.title)}",
        chunk_type="skill" if level else "language",
        title=section.title,
        heading_path=section.heading_path,
        text=f"{section.title}\n{section.content}".strip(),
        constraints=constraints,
        cv_eligible=record.automatic_reuse_eligible,
        proficiency=proficiency,
        attributes=attrs,
        metric_refs=[],
    )


def _credential_chunk(record: NormalizedRecord, section: Any) -> EvidenceChunk:
    fields = _fields(section.content)
    status = (fields.get("status") or "").casefold()
    cv_usage = (fields.get("cv usage") or "").casefold()
    inactive = any(term in status for term in ("expired", "inactive", "revoked"))
    explicitly_blocked = cv_usage in {"blocked", "do_not_use", "do not use"}
    attrs = {"status": fields.get("status"), "cv_usage": fields.get("cv usage")}
    return _chunk(
        record,
        chunk_id=f"{record.record_id}::{slugify(section.title)}",
        chunk_type="credential",
        title=section.title,
        heading_path=section.heading_path,
        text=f"{section.title}\n{section.content}".strip(),
        constraints=[],
        cv_eligible=record.automatic_reuse_eligible and not inactive and not explicitly_blocked,
        attributes=attrs,
        metric_refs=[],
    )


def chunk_record(record: NormalizedRecord) -> list[EvidenceChunk]:
    """Create semantic, stable chunks while preserving source constraints."""
    if record.retrieval_class == "router":
        return []

    constraints = _record_constraints(record)
    chunks: list[EvidenceChunk] = []

    if record.record_id == "achievement-metrics":
        return [_metric_chunk(record, section) for section in record.sections if section.semantic_type == "metric"]

    if record.record_id == "skills":
        for section in record.sections:
            fields = _fields(section.content)
            if fields.get("level") or fields.get("proficiency"):
                chunks.append(_skill_chunk(record, section))
        return chunks

    for section in record.sections:
        if not section.content.strip():
            continue
        if section.semantic_type == "credential" or section.title.upper().startswith("CERT-"):
            chunks.append(_credential_chunk(record, section))
            continue

        chunk_type = section.semantic_type
        if record.retrieval_class == "policy":
            chunk_type = "policy_" + chunk_type
        elif record.record_type == "project" and chunk_type == "section":
            chunk_type = "project_detail"
        elif record.record_type == "role" and chunk_type == "section":
            chunk_type = "role_detail"

        section_constraints = list(constraints)
        if section.semantic_type == "boundary" and section.content.strip() not in section_constraints:
            section_constraints.append(section.content.strip())

        chunks.append(_chunk(
            record,
            chunk_id=section.section_id,
            chunk_type=chunk_type,
            title=section.title,
            heading_path=section.heading_path,
            text=f"{section.title}\n{section.content}".strip(),
            constraints=section_constraints,
            cv_eligible=record.automatic_reuse_eligible and record.retrieval_class == "evidence",
        ))
    return chunks


def empty_index() -> dict[str, Any]:
    return {"schema_version": INDEX_SCHEMA_VERSION, "chunks": {}, "postings": {}, "record_chunks": {}}


def remove_record_from_index(index: dict[str, Any], record_id: str) -> None:
    for chunk_id in list(index.get("record_chunks", {}).pop(record_id, [])):
        meta = index.get("chunks", {}).pop(chunk_id, None)
        if not meta:
            continue
        for term in meta.get("terms", {}):
            posting = index.get("postings", {}).get(term, [])
            if chunk_id in posting:
                posting.remove(chunk_id)
            if not posting:
                index.get("postings", {}).pop(term, None)


def add_record_chunks(index: dict[str, Any], chunks: list[EvidenceChunk]) -> None:
    if not chunks:
        return
    record_id = chunks[0].record_id
    remove_record_from_index(index, record_id)
    eligible = [chunk for chunk in chunks if chunk.cv_eligible and chunk.retrieval_class == "evidence"]
    index.setdefault("record_chunks", {})[record_id] = []
    for chunk in eligible:
        terms = dict(sorted(Counter(_normalized_tokenize(chunk.text)).items()))
        index["chunks"][chunk.chunk_id] = {
            "record_id": chunk.record_id,
            "chunk_type": chunk.chunk_type,
            "source_path": chunk.source_path,
            "content_hash": chunk.content_hash,
            "proficiency": chunk.proficiency,
            "constraints": chunk.constraints,
            "metric_refs": chunk.metric_refs,
            "terms": terms,
            "text": chunk.text,
        }
        index["record_chunks"][record_id].append(chunk.chunk_id)
        for term in terms:
            posting = index["postings"].setdefault(term, [])
            if chunk.chunk_id not in posting:
                posting.append(chunk.chunk_id)
                posting.sort()


def retrieve_evidence(index: dict[str, Any], query: str, top_k: int = 8) -> list[dict[str, Any]]:
    query_terms = Counter(_normalized_tokenize(query))
    if not query_terms:
        return []
    candidate_ids: set[str] = set()
    for term in query_terms:
        candidate_ids.update(index.get("postings", {}).get(term, []))
    hits: list[dict[str, Any]] = []
    for chunk_id in candidate_ids:
        meta = index["chunks"][chunk_id]
        score = 0.0
        for term, qtf in query_terms.items():
            tf = meta.get("terms", {}).get(term, 0)
            if tf:
                score += (1.0 + tf) * qtf
        if score:
            hits.append({
                "chunk_id": chunk_id,
                "record_id": meta["record_id"],
                "score": score,
                "chunk_type": meta["chunk_type"],
                "source_path": meta["source_path"],
                "proficiency": meta.get("proficiency"),
                "constraints": meta.get("constraints", []),
                "metric_refs": meta.get("metric_refs", []),
                "text": meta["text"],
            })
    hits.sort(key=lambda item: (-item["score"], item["chunk_id"]))
    return hits[:top_k]


def _resolve_relations(records: list[dict[str, Any]]) -> list[dict[str, str]]:
    by_path = {record["source_path"]: record["record_id"] for record in records}
    edges: set[tuple[str, str, str]] = set()
    for record in records:
        source_id = record["record_id"]
        for metric_id in record.get("metric_refs", []):
            edges.add((source_id, "references_metric", metric_id))
        source_dir = posixpath.dirname(record["source_path"])
        for link in record.get("linked_markdown_paths", []):
            target_path = posixpath.normpath(posixpath.join(source_dir, link))
            target_id = by_path.get(target_path)
            if target_id:
                edges.add((source_id, "links_to", target_id))
    return [
        {"source": source, "relation": relation, "target": target}
        for source, relation, target in sorted(edges)
    ]


def _record_file(state_dir: Path, record_id: str) -> Path:
    return state_dir / "records" / f"{record_id}.json"


def _chunk_file(state_dir: Path, record_id: str) -> Path:
    return state_dir / "chunks" / f"{record_id}.json"


def run_evidence_pipeline(
    repo_root: Path,
    state_dir: Path,
    *,
    run_id: str,
    source_commit: str | None = None,
    full_rebuild: bool = False,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    state_dir = state_dir.resolve()
    source_commit = source_commit or resolve_source_commit(repo_root)
    previous = _read_json(state_dir / "manifest.json", {"pipeline_version": None, "sources": {}})
    if previous.get("pipeline_version") != EVIDENCE_PIPELINE_VERSION:
        full_rebuild = True

    discovered = {
        path.relative_to(repo_root).as_posix(): path
        for path in sorted((repo_root / "experience").rglob("*.md"))
    }
    current_hashes = {rel: _sha256(path.read_text(encoding="utf-8")) for rel, path in discovered.items()}
    previous_sources: dict[str, Any] = previous.get("sources", {})

    if full_rebuild:
        new_paths = sorted(discovered)
        modified_paths: list[str] = []
        unchanged_paths: list[str] = []
        deleted_paths = sorted(set(previous_sources) - set(discovered))
    else:
        new_paths = sorted(path for path in discovered if path not in previous_sources)
        modified_paths = sorted(path for path in discovered if path in previous_sources and previous_sources[path].get("source_hash") != current_hashes[path])
        unchanged_paths = sorted(path for path in discovered if path in previous_sources and previous_sources[path].get("source_hash") == current_hashes[path])
        deleted_paths = sorted(set(previous_sources) - set(discovered))

    impacted_record_ids: set[str] = set()
    for path in deleted_paths + modified_paths:
        previous_id = previous_sources.get(path, {}).get("record_id")
        if previous_id:
            impacted_record_ids.add(previous_id)

    manifest_sources = {} if full_rebuild else dict(previous_sources)
    index = empty_index() if full_rebuild else _read_json(state_dir / "lexical_index.json", empty_index())

    for path in deleted_paths:
        old_id = previous_sources.get(path, {}).get("record_id")
        if old_id:
            remove_record_from_index(index, old_id)
            _record_file(state_dir, old_id).unlink(missing_ok=True)
            _chunk_file(state_dir, old_id).unlink(missing_ok=True)
        manifest_sources.pop(path, None)

    process_paths = sorted(set(new_paths + modified_paths))
    reindexed: list[str] = []
    for rel in process_paths:
        record = normalize_file(discovered[rel], repo_root, source_commit=source_commit)
        impacted_record_ids.add(record.record_id)
        chunks = chunk_record(record)
        _write_json(_record_file(state_dir, record.record_id), record.to_dict())
        _write_json(_chunk_file(state_dir, record.record_id), {
            "schema_version": EVIDENCE_CHUNK_SCHEMA_VERSION,
            "record_id": record.record_id,
            "chunks": [chunk.to_dict() for chunk in chunks],
        })
        add_record_chunks(index, chunks)
        reindexed.append(record.record_id)
        manifest_sources[rel] = {
            "source_hash": current_hashes[rel],
            "record_id": record.record_id,
            "record_hash": record.content_hash,
            "chunk_ids": [chunk.chunk_id for chunk in chunks],
        }

    active_records = []
    for entry in manifest_sources.values():
        record_id = entry.get("record_id")
        if record_id and _record_file(state_dir, record_id).exists():
            active_records.append(_read_json(_record_file(state_dir, record_id), {}))
    active_records.sort(key=lambda item: item.get("record_id", ""))
    relations = _resolve_relations(active_records)

    _write_json(state_dir / "lexical_index.json", index)
    _write_json(state_dir / "relations.json", {"schema_version": 1, "relations": relations})
    manifest = {
        "pipeline_version": EVIDENCE_PIPELINE_VERSION,
        "source_commit": source_commit,
        "sources": dict(sorted(manifest_sources.items())),
    }
    _write_json(state_dir / "manifest.json", manifest)

    report = {
        "schema_version": 1,
        "run_id": run_id,
        "source_commit": source_commit,
        "status": "success",
        "source_counts": {
            "discovered": len(discovered),
            "new": len(new_paths),
            "modified": len(modified_paths),
            "deleted": len(deleted_paths),
            "unchanged": len(unchanged_paths),
        },
        "record_counts": {
            "active": len(manifest_sources),
            "impacted": len(impacted_record_ids),
            "reindexed": len(reindexed),
        },
        "paths": {
            "new": new_paths,
            "modified": modified_paths,
            "deleted": deleted_paths,
            "unchanged": unchanged_paths,
        },
        "reindexed_record_ids": sorted(reindexed),
    }
    _write_json(state_dir / "runs" / f"{slugify(run_id)}.json", report)
    _write_json(state_dir / "latest_run.json", report)
    logger.info(
        "evidence run=%s active=%s impacted=%s reindexed=%s",
        run_id,
        report["record_counts"]["active"],
        report["record_counts"]["impacted"],
        report["record_counts"]["reindexed"],
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Incrementally normalize, chunk, and index professional evidence.")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--state-dir", default="rag_state")
    parser.add_argument("--run-id", default="local")
    parser.add_argument("--source-commit", default=None)
    parser.add_argument("--full-rebuild", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    report = run_evidence_pipeline(
        Path(args.repo),
        Path(args.state_dir),
        run_id=args.run_id,
        source_commit=args.source_commit,
        full_rebuild=args.full_rebuild,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
