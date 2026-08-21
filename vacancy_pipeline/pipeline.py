from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from vacancy_pipeline import STATE_SCHEMA_VERSION, VACANCY_PIPELINE_VERSION
from vacancy_pipeline.chunking import build_chunks, merge_records
from vacancy_pipeline.contract import VacancyValidationError, load_and_adapt, sha256_bytes
from vacancy_pipeline.index import add_chunks, empty_index, remove_vacancy
from vacancy_pipeline.models import ProvenanceRef, VacancyRecord

LOG = logging.getLogger("vacancy_pipeline")
SOURCE_DIRS = ("GPTW", "Vacantes")


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _source_key(source_path: str) -> str:
    digest = hashlib.sha256(source_path.encode("utf-8")).hexdigest()[:16]
    stem = source_path.replace("/", "__").replace("\\", "__")
    stem = "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in stem)
    return f"{stem[:80]}--{digest}"


def _record_from_dict(data: dict[str, Any]) -> VacancyRecord:
    provenance = [ProvenanceRef(**item) for item in data.get("provenance", [])]
    payload = dict(data)
    payload["provenance"] = provenance
    return VacancyRecord(**payload)


def _load_source_records(state_dir: Path, manifest_entry: dict[str, Any]) -> list[VacancyRecord]:
    if manifest_entry.get("status") != "valid":
        return []
    state_file = state_dir / manifest_entry["state_file"]
    data = _read_json(state_file, {})
    return [_record_from_dict(item) for item in data.get("records", [])]


def discover_source_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for directory in SOURCE_DIRS:
        root = repo_root / directory
        if root.is_dir():
            files.extend(path for path in root.rglob("*.json") if path.is_file())
    return sorted(files, key=lambda path: path.relative_to(repo_root).as_posix())


def _load_index(state_dir: Path) -> dict[str, Any]:
    data = _read_json(state_dir / "lexical_index.json", None)
    return data if isinstance(data, dict) else empty_index()


def _clear_for_full_rebuild(state_dir: Path) -> None:
    for name in ("sources", "records", "chunks", "quarantine"):
        path = state_dir / name
        if path.exists():
            shutil.rmtree(path)
    for name in ("manifest.json", "lexical_index.json", "latest_run.json"):
        path = state_dir / name
        if path.exists():
            path.unlink()


def run_pipeline(
    repo_root: Path,
    state_dir: Path,
    *,
    run_id: str | None = None,
    full_rebuild: bool = False,
    fail_on_quarantine: bool = False,
    source_commit: str | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    state_dir = state_dir.resolve()
    manifest_path = state_dir / "manifest.json"
    existing_manifest = _read_json(manifest_path, {"schema_version": STATE_SCHEMA_VERSION, "sources": {}})
    if existing_manifest.get("pipeline_version") != VACANCY_PIPELINE_VERSION:
        full_rebuild = True
        LOG.info(
            "pipeline version changed previous=%s current=%s; forcing controlled rebuild",
            existing_manifest.get("pipeline_version"),
            VACANCY_PIPELINE_VERSION,
        )
    if full_rebuild:
        _clear_for_full_rebuild(state_dir)

    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    source_commit = source_commit or os.getenv("GITHUB_SHA")
    manifest = _read_json(manifest_path, {"schema_version": STATE_SCHEMA_VERSION, "pipeline_version": VACANCY_PIPELINE_VERSION, "sources": {}})
    previous_sources: dict[str, dict[str, Any]] = dict(manifest.get("sources", {}))
    next_sources: dict[str, dict[str, Any]] = dict(previous_sources)
    index = _load_index(state_dir)

    discovered = discover_source_files(repo_root)
    current_paths = {path.relative_to(repo_root).as_posix(): path for path in discovered}
    new_paths: list[str] = []
    modified_paths: list[str] = []
    unchanged_paths: list[str] = []
    quarantined_paths: list[str] = []
    deleted_paths = sorted(set(previous_sources) - set(current_paths))
    impacted_vacancy_ids: set[str] = set()
    validation_errors: dict[str, list[str]] = {}

    LOG.info("run=%s discovered=%d previous=%d", run_id, len(discovered), len(previous_sources))

    for source_path, path in current_paths.items():
        raw = path.read_bytes()
        source_hash = sha256_bytes(raw)
        previous = previous_sources.get(source_path)
        if previous and previous.get("source_hash") == source_hash:
            unchanged_paths.append(source_path)
            continue

        if previous:
            modified_paths.append(source_path)
            impacted_vacancy_ids.update(previous.get("vacancy_ids", []))
        else:
            new_paths.append(source_path)

        key = _source_key(source_path)
        state_rel = f"sources/{key}.json"
        state_file = state_dir / state_rel
        try:
            _, records = load_and_adapt(path, repo_root, source_commit)
            vacancy_ids = sorted({record.vacancy_id for record in records})
            impacted_vacancy_ids.update(vacancy_ids)
            _write_json(state_file, {
                "schema_version": STATE_SCHEMA_VERSION,
                "source_path": source_path,
                "source_hash": source_hash,
                "status": "valid",
                "records": [record.to_dict() for record in records],
            })
            next_sources[source_path] = {
                "source_hash": source_hash,
                "status": "valid",
                "state_file": state_rel,
                "vacancy_ids": vacancy_ids,
            }
            quarantine_current = state_dir / "quarantine" / f"{key}--current.errors.json"
            if quarantine_current.exists():
                quarantine_current.unlink()
            LOG.info("validated source=%s vacancies=%d", source_path, len(records))
        except VacancyValidationError as exc:
            quarantined_paths.append(source_path)
            validation_errors[source_path] = exc.errors
            next_sources[source_path] = {
                "source_hash": source_hash,
                "status": "invalid",
                "state_file": state_rel,
                "vacancy_ids": [],
                "errors": exc.errors,
            }
            _write_json(state_file, {
                "schema_version": STATE_SCHEMA_VERSION,
                "source_path": source_path,
                "source_hash": source_hash,
                "status": "invalid",
                "records": [],
                "errors": exc.errors,
            })
            quarantine_dir = state_dir / "quarantine"
            quarantine_dir.mkdir(parents=True, exist_ok=True)
            raw_copy = quarantine_dir / f"{key}--{source_hash[:12]}.json"
            raw_copy.write_bytes(raw)
            _write_json(quarantine_dir / f"{key}--current.errors.json", {
                "source_path": source_path,
                "source_hash": source_hash,
                "errors": exc.errors,
                "run_id": run_id,
            })
            LOG.error("quarantined source=%s errors=%s", source_path, " | ".join(exc.errors))

    for source_path in deleted_paths:
        previous = previous_sources[source_path]
        impacted_vacancy_ids.update(previous.get("vacancy_ids", []))
        state_rel = previous.get("state_file")
        if state_rel:
            state_file = state_dir / state_rel
            if state_file.exists():
                state_file.unlink()
        next_sources.pop(source_path, None)
        LOG.info("deleted source=%s", source_path)

    contributions: dict[str, list[VacancyRecord]] = {vacancy_id: [] for vacancy_id in impacted_vacancy_ids}
    for entry in next_sources.values():
        for record in _load_source_records(state_dir, entry):
            if record.vacancy_id in contributions:
                contributions[record.vacancy_id].append(record)

    reindexed_ids: list[str] = []
    deleted_vacancy_ids: list[str] = []
    semantic_unchanged_ids: list[str] = []
    for vacancy_id in sorted(impacted_vacancy_ids):
        record_path = state_dir / "records" / f"{vacancy_id}.json"
        chunk_path = state_dir / "chunks" / f"{vacancy_id}.json"
        existing = _read_json(record_path, None)
        variants = contributions.get(vacancy_id, [])
        if not variants:
            if record_path.exists():
                record_path.unlink()
            if chunk_path.exists():
                chunk_path.unlink()
            remove_vacancy(index, vacancy_id)
            deleted_vacancy_ids.append(vacancy_id)
            continue

        merged = merge_records(variants)
        record_dict = merged.to_dict()
        existing_hash = existing.get("content_hash") if isinstance(existing, dict) else None
        existing_sources = sorted(
            ref.get("source_path") for ref in existing.get("provenance", [])
        ) if isinstance(existing, dict) else []
        next_source_paths = sorted(ref.source_path for ref in merged.provenance)
        _write_json(record_path, record_dict)
        chunks = build_chunks(merged)
        _write_json(chunk_path, {
            "schema_version": STATE_SCHEMA_VERSION,
            "vacancy_id": vacancy_id,
            "chunks": [chunk.to_dict() for chunk in chunks],
        })

        if existing_hash == merged.content_hash and existing_sources == next_source_paths:
            semantic_unchanged_ids.append(vacancy_id)
        else:
            add_chunks(index, chunks)
            reindexed_ids.append(vacancy_id)

    for posting in index.get("postings", {}).values():
        posting.sort()
    for chunk_ids in index.get("vacancy_chunks", {}).values():
        chunk_ids.sort()
    index["chunks"] = dict(sorted(index.get("chunks", {}).items()))
    index["postings"] = dict(sorted(index.get("postings", {}).items()))
    index["vacancy_chunks"] = dict(sorted(index.get("vacancy_chunks", {}).items()))
    _write_json(state_dir / "lexical_index.json", index)

    _write_json(manifest_path, {
        "schema_version": STATE_SCHEMA_VERSION,
        "pipeline_version": VACANCY_PIPELINE_VERSION,
        "last_run_id": run_id,
        "sources": dict(sorted(next_sources.items())),
    })

    active_vacancies = len(list((state_dir / "records").glob("*.json"))) if (state_dir / "records").exists() else 0
    report = {
        "schema_version": STATE_SCHEMA_VERSION,
        "pipeline_version": VACANCY_PIPELINE_VERSION,
        "run_id": run_id,
        "source_commit": source_commit,
        "status": "completed_with_quarantine" if quarantined_paths else "success",
        "source_counts": {
            "discovered": len(discovered),
            "new": len(new_paths),
            "modified": len(modified_paths),
            "unchanged": len(unchanged_paths),
            "deleted": len(deleted_paths),
            "quarantined": len(quarantined_paths),
        },
        "vacancy_counts": {
            "active": active_vacancies,
            "impacted": len(impacted_vacancy_ids),
            "reindexed": len(reindexed_ids),
            "semantic_unchanged": len(semantic_unchanged_ids),
            "deleted": len(deleted_vacancy_ids),
        },
        "paths": {
            "new": new_paths,
            "modified": modified_paths,
            "unchanged": unchanged_paths,
            "deleted": deleted_paths,
            "quarantined": quarantined_paths,
        },
        "reindexed_vacancy_ids": reindexed_ids,
        "deleted_vacancy_ids": deleted_vacancy_ids,
        "validation_errors": validation_errors,
    }
    _write_json(state_dir / "runs" / f"{run_id}.json", report)
    _write_json(state_dir / "latest_run.json", report)
    LOG.info(
        "completed run=%s status=%s active=%d impacted=%d reindexed=%d quarantined=%d",
        run_id,
        report["status"],
        active_vacancies,
        len(impacted_vacancy_ids),
        len(reindexed_ids),
        len(quarantined_paths),
    )
    if fail_on_quarantine and quarantined_paths:
        raise VacancyValidationError("pipeline", [f"{len(quarantined_paths)} source file(s) quarantined"])
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Incrementally ingest vacancy JSON files.")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--state-dir", default="vacancy_state")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--full-rebuild", action="store_true")
    parser.add_argument("--source-commit", default=None)
    parser.add_argument("--fail-on-quarantine", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO), format="%(levelname)s %(message)s")
    repo_root = Path(args.repo).resolve()
    state_dir = Path(args.state_dir)
    if not state_dir.is_absolute():
        state_dir = repo_root / state_dir
    try:
        run_pipeline(
            repo_root,
            state_dir,
            run_id=args.run_id,
            full_rebuild=args.full_rebuild,
            fail_on_quarantine=args.fail_on_quarantine,
            source_commit=args.source_commit,
        )
    except VacancyValidationError as exc:
        LOG.error("pipeline failed: %s", exc)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
