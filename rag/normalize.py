#!/usr/bin/env python3
"""Normalize canonical Markdown evidence into deterministic JSON-ready records.

This module is deliberately provider-agnostic. It does not chunk, embed, index,
retrieve, rerank, or generate text. Its job is to preserve the canonical source
of truth as typed records that later RAG stages can consume safely.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from rag import NORMALIZATION_SCHEMA_VERSION


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
METRIC_REF_RE = re.compile(r"\bACH-[A-Z0-9-]+\b")
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\((?!https?://|mailto:|#)([^)]+\.md)(?:#[^)]+)?\)")
SKILL_LEVEL_RE = re.compile(r"^- \*\*Level:\*\*\s*(core|working|familiarity)\s*$", re.MULTILINE | re.IGNORECASE)

ROUTER_PATHS = {
    "experience/projects/index.md",
    "experience/roles/index.md",
    "experience/projects/github_portfolio.md",
}
NON_REUSABLE_STATUSES = {"draft", "deprecated", "needs_reconciliation"}


@dataclass(frozen=True)
class NormalizedSection:
    """A structural Markdown section, not yet a retrieval chunk."""

    section_id: str
    level: int
    title: str
    heading_path: list[str]
    semantic_type: str
    start_line: int
    end_line: int
    content: str


@dataclass(frozen=True)
class NormalizedRecord:
    """One canonical source record after deterministic normalization."""

    normalization_schema_version: int
    record_id: str
    record_type: str
    status: str
    confidence: str
    visibility: str
    public_safe: bool
    retrieval_class: str
    automatic_reuse_eligible: bool
    embedding_candidate: bool
    source_path: str
    source_commit: str | None
    source_refs: list[str]
    metric_refs: list[str]
    linked_markdown_paths: list[str]
    attributes: dict[str, Any]
    sections: list[NormalizedSection]
    content_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _json_safe(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def split_frontmatter(text: str) -> tuple[dict[str, Any], str, int]:
    """Return frontmatter, Markdown body, and 1-based body start line."""

    if not text.startswith("---\n"):
        raise ValueError("missing YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("unterminated YAML frontmatter")

    raw_frontmatter = text[4:end]
    data = yaml.safe_load(raw_frontmatter) or {}
    if not isinstance(data, dict):
        raise ValueError("frontmatter must be a YAML mapping")

    body = text[end + 5 :]
    body_start_line = text[: end + 5].count("\n") + 1
    return _json_safe(data), body, body_start_line


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "section"


def semantic_type_for_title(title: str) -> str:
    upper = title.upper()
    lowered = title.lower()

    if upper.startswith("ACH-"):
        return "metric"
    if upper.startswith("CONFLICT-"):
        return "conflict"
    if re.match(r"^Q-[A-Z0-9-]+\b", upper):
        return "open_question"
    if upper.startswith("CERT-"):
        return "credential"
    if "contribution" in lowered or "ownership" in lowered:
        return "ownership"
    if "boundar" in lowered or "usage constraint" in lowered or "usage rule" in lowered:
        return "boundary"
    if "summary" in lowered:
        return "summary"
    if "technolog" in lowered or "technical" in lowered:
        return "technology"
    if "skill" in lowered:
        return "skill_group"
    if "outcome" in lowered or "impact" in lowered or "result" in lowered:
        return "outcome"
    return "section"


def parse_sections(body: str, body_start_line: int, record_id: str) -> list[NormalizedSection]:
    """Parse Markdown headings into structural sections while preserving hierarchy."""

    lines = body.splitlines()
    headings: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines):
        match = HEADING_RE.match(line)
        if match:
            headings.append((index, len(match.group(1)), match.group(2).strip()))

    if not headings:
        content = body.strip()
        return [
            NormalizedSection(
                section_id=f"{record_id}::body",
                level=0,
                title="Body",
                heading_path=[],
                semantic_type="section",
                start_line=body_start_line,
                end_line=body_start_line + max(len(lines) - 1, 0),
                content=content,
            )
        ] if content else []

    sections: list[NormalizedSection] = []
    stack: list[tuple[int, str]] = []

    for position, (line_index, level, title) in enumerate(headings):
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, title))

        next_line_index = headings[position + 1][0] if position + 1 < len(headings) else len(lines)
        content_lines = lines[line_index + 1 : next_line_index]
        content = "\n".join(content_lines).strip()
        heading_path = [item[1] for item in stack]
        path_slug = "::".join(slugify(item) for item in heading_path)
        section_id = f"{record_id}::{path_slug}"

        sections.append(
            NormalizedSection(
                section_id=section_id,
                level=level,
                title=title,
                heading_path=heading_path,
                semantic_type=semantic_type_for_title(title),
                start_line=body_start_line + line_index,
                end_line=body_start_line + max(next_line_index - 1, line_index),
                content=content,
            )
        )

    return sections


def retrieval_class_for_path(source_path: str) -> str:
    if source_path.startswith("experience/_meta/"):
        return "policy"
    if source_path in ROUTER_PATHS:
        return "router"
    return "evidence"


def resolve_source_commit(repo_root: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    value = completed.stdout.strip()
    return value or None


def normalize_file(path: Path, repo_root: Path, source_commit: str | None = None) -> NormalizedRecord:
    text = path.read_text(encoding="utf-8")
    meta, body, body_start_line = split_frontmatter(text)
    source_path = path.relative_to(repo_root).as_posix()

    record_id = str(meta.get("record_id", "")).strip()
    if not record_id:
        raise ValueError(f"{source_path}: missing record_id")

    record_type = str(meta.get("record_type", "")).strip()
    status = str(meta.get("status", "")).strip()
    confidence = str(meta.get("confidence", "")).strip()
    visibility = str(meta.get("visibility", "")).strip()
    public_safe = meta.get("public_safe") is True
    retrieval_class = retrieval_class_for_path(source_path)

    automatic_reuse_eligible = public_safe and status not in NON_REUSABLE_STATUSES
    embedding_candidate = automatic_reuse_eligible and retrieval_class == "evidence"

    source_refs = [str(value) for value in meta.get("source_refs", [])]
    metric_refs = sorted(set(METRIC_REF_RE.findall(body)))
    linked_markdown_paths = sorted(set(MARKDOWN_LINK_RE.findall(body)))
    sections = parse_sections(body, body_start_line, record_id)

    reserved = {
        "schema_version",
        "record_id",
        "record_type",
        "status",
        "confidence",
        "visibility",
        "public_safe",
        "source_refs",
    }
    attributes = {key: value for key, value in meta.items() if key not in reserved}

    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()

    return NormalizedRecord(
        normalization_schema_version=NORMALIZATION_SCHEMA_VERSION,
        record_id=record_id,
        record_type=record_type,
        status=status,
        confidence=confidence,
        visibility=visibility,
        public_safe=public_safe,
        retrieval_class=retrieval_class,
        automatic_reuse_eligible=automatic_reuse_eligible,
        embedding_candidate=embedding_candidate,
        source_path=source_path,
        source_commit=source_commit,
        source_refs=source_refs,
        metric_refs=metric_refs,
        linked_markdown_paths=linked_markdown_paths,
        attributes=attributes,
        sections=sections,
        content_hash=digest,
    )


def normalize_corpus(repo_root: Path, source_commit: str | None = None) -> list[NormalizedRecord]:
    experience_root = repo_root / "experience"
    if not experience_root.is_dir():
        raise ValueError(f"missing experience directory: {experience_root}")

    commit = source_commit if source_commit is not None else resolve_source_commit(repo_root)
    records = [
        normalize_file(path, repo_root, commit)
        for path in sorted(experience_root.rglob("*.md"))
    ]

    record_ids = [record.record_id for record in records]
    if len(record_ids) != len(set(record_ids)):
        raise ValueError("normalized corpus contains duplicate record_id values")

    return records


def build_manifest(records: list[NormalizedRecord], source_commit: str | None) -> dict[str, Any]:
    class_counts: dict[str, int] = {}
    type_counts: dict[str, int] = {}
    for record in records:
        class_counts[record.retrieval_class] = class_counts.get(record.retrieval_class, 0) + 1
        type_counts[record.record_type] = type_counts.get(record.record_type, 0) + 1

    return {
        "normalization_schema_version": NORMALIZATION_SCHEMA_VERSION,
        "source_commit": source_commit,
        "record_count": len(records),
        "embedding_candidate_count": sum(record.embedding_candidate for record in records),
        "retrieval_class_counts": dict(sorted(class_counts.items())),
        "record_type_counts": dict(sorted(type_counts.items())),
        "record_ids": [record.record_id for record in records],
    }


def write_jsonl(records: list[NormalizedRecord], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="repository root")
    parser.add_argument("--output", default="artifacts/rag/records.jsonl")
    parser.add_argument("--manifest", default="artifacts/rag/manifest.json")
    parser.add_argument("--source-commit", default=None)
    parser.add_argument(
        "--check",
        action="store_true",
        help="parse and validate normalization without writing artifacts",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo).resolve()
    records = normalize_corpus(repo_root, args.source_commit)
    source_commit = records[0].source_commit if records else args.source_commit
    manifest = build_manifest(records, source_commit)

    if not args.check:
        output_path = repo_root / args.output
        manifest_path = repo_root / args.manifest
        write_jsonl(records, output_path)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    print(
        "Normalized "
        f"{manifest['record_count']} records; "
        f"{manifest['embedding_candidate_count']} future embedding candidates; "
        f"classes={manifest['retrieval_class_counts']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
