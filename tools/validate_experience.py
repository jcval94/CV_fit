#!/usr/bin/env python3
"""Validate the canonical professional-evidence repository."""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import yaml


REQUIRED_FIELDS = {
    "schema_version",
    "record_id",
    "record_type",
    "status",
    "last_updated",
    "confidence",
    "visibility",
    "public_safe",
    "source_refs",
}
SOURCE_REQUIRED_FIELDS = {
    "id",
    "title",
    "type",
    "authority",
    "coverage",
    "sensitivity",
    "repository_storage",
    "permitted_use",
}
RECORD_TYPES = {
    "profile",
    "education",
    "certifications",
    "skills",
    "role",
    "project",
    "achievement_registry",
    "governance",
    "conflict_log",
}
STATUSES = {
    "draft",
    "needs_reconciliation",
    "canonical",
    "validated_public",
    "validated_public_supporting",
    "deprecated",
}
CONFIDENCE = {"high", "medium", "low"}
SKILL_LEVELS = {"core", "working", "familiarity"}
METRIC_ID = re.compile(r"^##\s+(ACH-[A-Z0-9-]+)\b", re.MULTILINE)
METRIC_REFERENCE = re.compile(r"\bACH-[A-Z0-9-]+\b")
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\((?!https?://|mailto:|#)([^)]+\.md)(?:#[^)]+)?\)")
SKILL_LEVEL = re.compile(r"^- \*\*Level:\*\*\s*([^\n]+?)\s*$", re.MULTILINE)


def split_frontmatter(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("missing YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("unterminated YAML frontmatter")
    data = yaml.safe_load(text[4:end]) or {}
    if not isinstance(data, dict):
        raise ValueError("frontmatter must be a YAML mapping")
    return data, text[end + 5 :]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", default=".")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    experience = repo / "experience"
    source_file = experience / "_meta" / "sources.yaml"
    errors: list[str] = []
    warnings: list[str] = []

    try:
        source_data = yaml.safe_load(source_file.read_text(encoding="utf-8")) or {}
        sources = source_data.get("sources", [])
        if source_data.get("schema_version") != 3:
            errors.append(f"{source_file.relative_to(repo)}: schema_version must be 3")
        if not isinstance(sources, list):
            raise ValueError("sources must be a list")

        source_ids: set[str] = set()
        for index, item in enumerate(sources, start=1):
            if not isinstance(item, dict):
                errors.append(f"{source_file.relative_to(repo)}: source #{index} must be a mapping")
                continue
            missing = sorted(SOURCE_REQUIRED_FIELDS - set(item))
            if missing:
                errors.append(
                    f"{source_file.relative_to(repo)}: source #{index} missing fields "
                    f"{', '.join(missing)}"
                )
            source_id = item.get("id")
            if not isinstance(source_id, str) or not re.fullmatch(r"SRC-[A-Z0-9-]+", source_id):
                errors.append(f"{source_file.relative_to(repo)}: invalid source ID {source_id!r}")
            elif source_id in source_ids:
                errors.append(f"{source_file.relative_to(repo)}: duplicate source ID {source_id}")
            else:
                source_ids.add(source_id)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR {source_file}: cannot load source registry: {exc}")
        return 1

    seen_records: dict[str, Path] = {}
    all_metric_ids: list[tuple[str, Path]] = []
    record_bodies: list[tuple[Path, str]] = []
    markdown_files = sorted(experience.rglob("*.md"))

    for path in markdown_files:
        rel = path.relative_to(repo)
        try:
            meta, body = split_frontmatter(path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{rel}: {exc}")
            continue
        record_bodies.append((path, body))

        missing = sorted(REQUIRED_FIELDS - set(meta))
        if missing:
            errors.append(f"{rel}: missing fields {', '.join(missing)}")

        if meta.get("schema_version") != 3:
            errors.append(f"{rel}: schema_version must be 3")
        if meta.get("record_type") not in RECORD_TYPES:
            errors.append(f"{rel}: invalid record_type {meta.get('record_type')!r}")
        if meta.get("status") not in STATUSES:
            errors.append(f"{rel}: invalid status {meta.get('status')!r}")
        if meta.get("confidence") not in CONFIDENCE:
            errors.append(f"{rel}: invalid confidence {meta.get('confidence')!r}")
        if meta.get("visibility") != "public" or meta.get("public_safe") is not True:
            errors.append(f"{rel}: committed records must be public/public_safe")

        updated = meta.get("last_updated")
        if isinstance(updated, date):
            updated = updated.isoformat()
        if not isinstance(updated, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", updated):
            errors.append(f"{rel}: last_updated must be YYYY-MM-DD")

        record_id = meta.get("record_id")
        if not isinstance(record_id, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", record_id):
            errors.append(f"{rel}: invalid record_id {record_id!r}")
        elif record_id in seen_records:
            errors.append(f"{rel}: duplicate record_id also used by {seen_records[record_id].relative_to(repo)}")
        else:
            seen_records[record_id] = path

        refs = meta.get("source_refs")
        if not isinstance(refs, list):
            errors.append(f"{rel}: source_refs must be a list")
        else:
            unknown = sorted(set(refs) - source_ids)
            if unknown:
                errors.append(f"{rel}: unknown source_refs {', '.join(unknown)}")
            if not refs and meta.get("record_type") not in {"governance"}:
                warnings.append(f"{rel}: no source_refs")

        if "To be populated" in body or meta.get("status") == "draft":
            warnings.append(f"{rel}: incomplete record is not eligible for automatic reuse")

        if meta.get("record_type") == "skills":
            levels = SKILL_LEVEL.findall(body)
            if not levels:
                errors.append(f"{rel}: skills record contains no explicit Level fields")
            for level in levels:
                normalized = level.strip().lower()
                if normalized not in SKILL_LEVELS:
                    errors.append(
                        f"{rel}: invalid skill Level {level!r}; allowed values are "
                        f"{', '.join(sorted(SKILL_LEVELS))}"
                    )

        for metric in METRIC_ID.findall(body):
            all_metric_ids.append((metric, path))

        for target in MARKDOWN_LINK.findall(body):
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                errors.append(f"{rel}: broken internal Markdown link {target}")

    counts = Counter(metric for metric, _ in all_metric_ids)
    for metric, count in sorted(counts.items()):
        if count > 1:
            locations = sorted({str(path.relative_to(repo)) for item, path in all_metric_ids if item == metric})
            errors.append(f"duplicate metric ID {metric}: {', '.join(locations)}")

    defined_metric_ids = set(counts)
    for path, body in record_bodies:
        unknown_metrics = sorted(set(METRIC_REFERENCE.findall(body)) - defined_metric_ids)
        if unknown_metrics:
            errors.append(
                f"{path.relative_to(repo)}: unknown metric references {', '.join(unknown_metrics)}"
            )

    for item in warnings:
        print(f"WARNING {item}")
    for item in errors:
        print(f"ERROR {item}")

    print(
        f"Validated {len(markdown_files)} Markdown records, "
        f"{len(seen_records)} unique record IDs, {len(source_ids)} source IDs "
        f"and {len(all_metric_ids)} metric IDs."
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
