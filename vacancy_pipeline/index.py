from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from typing import Any

from vacancy_pipeline.models import RetrievalHit, VacancyChunk

INDEX_SCHEMA_VERSION = 1


def tokenize(text: str) -> list[str]:
    value = unicodedata.normalize("NFKD", text)
    value = "".join(ch for ch in value if not unicodedata.combining(ch)).casefold()
    return [token for token in re.findall(r"[a-z0-9][a-z0-9+#.-]*", value) if len(token) > 1]


def empty_index() -> dict[str, Any]:
    return {"schema_version": INDEX_SCHEMA_VERSION, "chunks": {}, "postings": {}, "vacancy_chunks": {}}


def remove_vacancy(index: dict[str, Any], vacancy_id: str) -> None:
    chunk_ids = list(index.get("vacancy_chunks", {}).pop(vacancy_id, []))
    for chunk_id in chunk_ids:
        meta = index.get("chunks", {}).pop(chunk_id, None)
        if not meta:
            continue
        for token in meta.get("terms", {}):
            posting = index.get("postings", {}).get(token, [])
            if chunk_id in posting:
                posting.remove(chunk_id)
            if not posting:
                index.get("postings", {}).pop(token, None)


def add_chunks(index: dict[str, Any], chunks: list[VacancyChunk]) -> None:
    if not chunks:
        return
    vacancy_id = chunks[0].vacancy_id
    remove_vacancy(index, vacancy_id)
    index.setdefault("vacancy_chunks", {})[vacancy_id] = []
    for chunk in chunks:
        counts = Counter(tokenize(chunk.text))
        index["chunks"][chunk.chunk_id] = {
            "vacancy_id": chunk.vacancy_id,
            "chunk_type": chunk.chunk_type,
            "content_hash": chunk.content_hash,
            "source_paths": chunk.source_paths,
            "terms": dict(sorted(counts.items())),
            "text": chunk.text,
        }
        index["vacancy_chunks"][vacancy_id].append(chunk.chunk_id)
        for token in counts:
            posting = index["postings"].setdefault(token, [])
            if chunk.chunk_id not in posting:
                posting.append(chunk.chunk_id)
                posting.sort()


def retrieve(index: dict[str, Any], query: str, top_k: int = 5) -> list[RetrievalHit]:
    query_terms = Counter(tokenize(query))
    if not query_terms:
        return []
    chunks = index.get("chunks", {})
    total_docs = max(len(chunks), 1)
    candidate_ids: set[str] = set()
    for token in query_terms:
        candidate_ids.update(index.get("postings", {}).get(token, []))

    scored: list[RetrievalHit] = []
    for chunk_id in candidate_ids:
        meta = chunks[chunk_id]
        score = 0.0
        terms = meta.get("terms", {})
        for token, qtf in query_terms.items():
            tf = terms.get(token, 0)
            if not tf:
                continue
            df = len(index.get("postings", {}).get(token, []))
            idf = math.log((total_docs + 1) / (df + 1)) + 1.0
            score += (1.0 + math.log(tf)) * idf * qtf
        if score > 0:
            scored.append(RetrievalHit(
                chunk_id=chunk_id,
                vacancy_id=meta["vacancy_id"],
                score=round(score, 6),
                chunk_type=meta["chunk_type"],
                text=meta["text"],
                source_paths=list(meta.get("source_paths", [])),
            ))
    scored.sort(key=lambda hit: (-hit.score, hit.chunk_id))
    return scored[:top_k]
