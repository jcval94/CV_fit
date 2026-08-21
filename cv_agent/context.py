from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cv_matching.match import build_match


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_vacancy(vacancy_id: str, vacancy_state: Path) -> dict[str, Any]:
    path = vacancy_state / "records" / f"{vacancy_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"canonical vacancy not found: {path}")
    return read_json(path)


def load_evidence_catalog(evidence_state: Path) -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    chunks_dir = evidence_state / "chunks"
    if not chunks_dir.exists():
        return catalog
    for path in sorted(chunks_dir.glob("*.json")):
        payload = read_json(path)
        for chunk in payload.get("chunks", []):
            chunk_id = chunk.get("chunk_id")
            if chunk_id:
                catalog[chunk_id] = chunk
    return catalog


def assemble_application_context(
    vacancy_id: str,
    *,
    vacancy_state: Path = Path("vacancy_state"),
    evidence_state: Path = Path("rag_state"),
) -> dict[str, Any]:
    vacancy = load_vacancy(vacancy_id, vacancy_state)
    match_plan = build_match(vacancy_id, vacancy_state=vacancy_state, evidence_state=evidence_state)
    catalog = load_evidence_catalog(evidence_state)
    selected_ids = match_plan.get("selected_evidence_chunk_ids", [])
    selected = [catalog[chunk_id] for chunk_id in selected_ids if chunk_id in catalog and catalog[chunk_id].get("cv_eligible")]
    selected.sort(key=lambda item: item["chunk_id"])

    if vacancy.get("application_language") == "und":
        raise ValueError(
            f"vacancy {vacancy_id} has undetermined application_language; "
            "set an explicit source language before CV generation"
        )

    return {
        "vacancy": vacancy,
        "match_plan": match_plan,
        "evidence_chunks": selected,
        "evidence_chunk_ids": [item["chunk_id"] for item in selected],
        "evidence_source_paths": sorted({item["source_path"] for item in selected}),
    }
