from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cv_agent.backbone import select_canonical_backbone
from cv_agent.preflight import assert_vacancy_generation_ready
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
    allow_sparse_jd: bool = False,
    retrieval_mode: str | None = None,
) -> dict[str, Any]:
    vacancy = load_vacancy(vacancy_id, vacancy_state)
    assert_vacancy_generation_ready(vacancy, allow_sparse_jd=allow_sparse_jd)

    match_plan = build_match(
        vacancy_id,
        vacancy_state=vacancy_state,
        evidence_state=evidence_state,
        retrieval_mode=retrieval_mode,
    )
    catalog = load_evidence_catalog(evidence_state)

    # Vacancy-specific retrieval decides which projects/skills/metrics are useful,
    # but stable chronology and education must never compete for semantic top-k.
    # Those facts form a separate canonical backbone and are always available to
    # the strategist/writer/reviewer.
    backbone = select_canonical_backbone(catalog)
    backbone_ids = [item["chunk_id"] for item in backbone]
    seen = set(backbone_ids)

    selected: list[dict[str, Any]] = list(backbone)
    for chunk_id in match_plan.get("selected_evidence_chunk_ids", []):
        chunk = catalog.get(chunk_id)
        if not chunk or not chunk.get("cv_eligible") or chunk_id in seen:
            continue
        selected.append(chunk)
        seen.add(chunk_id)

    return {
        "vacancy": vacancy,
        "match_plan": match_plan,
        "canonical_backbone_chunk_ids": backbone_ids,
        "evidence_chunks": selected,
        "evidence_chunk_ids": [item["chunk_id"] for item in selected],
        "evidence_source_paths": sorted({item["source_path"] for item in selected}),
    }
