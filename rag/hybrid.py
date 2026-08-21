from __future__ import annotations

from collections import defaultdict
from typing import Any

from rag.evidence import retrieve_evidence


RRF_K = 60
DEFAULT_LEXICAL_WEIGHT = 1.0
DEFAULT_DENSE_WEIGHT = 1.0


def reciprocal_rank_fusion(
    lexical_hits: list[dict[str, Any]],
    dense_hits: list[dict[str, Any]],
    *,
    lexical_weight: float = DEFAULT_LEXICAL_WEIGHT,
    dense_weight: float = DEFAULT_DENSE_WEIGHT,
    rrf_k: int = RRF_K,
    top_k: int = 8,
) -> list[dict[str, Any]]:
    """Fuse lexical and dense rankings without pretending their raw scores are comparable."""

    if rrf_k <= 0:
        raise ValueError("rrf_k must be positive")
    by_id: dict[str, dict[str, Any]] = {}
    fusion: defaultdict[str, float] = defaultdict(float)
    ranks: defaultdict[str, dict[str, int]] = defaultdict(dict)

    for source, hits, weight in (
        ("lexical", lexical_hits, lexical_weight),
        ("dense", dense_hits, dense_weight),
    ):
        for rank, hit in enumerate(hits, start=1):
            chunk_id = hit["chunk_id"]
            by_id.setdefault(chunk_id, dict(hit))
            fusion[chunk_id] += weight / (rrf_k + rank)
            ranks[chunk_id][source] = rank

    fused: list[dict[str, Any]] = []
    for chunk_id, score in fusion.items():
        hit = dict(by_id[chunk_id])
        hit["score"] = score
        hit["rrf_score"] = score
        hit["retrieval_ranks"] = dict(ranks[chunk_id])
        hit["retrieval_source"] = "hybrid" if len(ranks[chunk_id]) > 1 else next(iter(ranks[chunk_id]))
        fused.append(hit)
    fused.sort(key=lambda item: (-item["rrf_score"], item["chunk_id"]))
    return fused[:top_k]


def expand_graph(
    hits: list[dict[str, Any]],
    *,
    lexical_index: dict[str, Any],
    relations: list[dict[str, str]],
    max_expansions: int = 8,
) -> list[dict[str, Any]]:
    """Add one-hop eligible evidence linked to retrieved records.

    Policy/router content never enters because expansion can only resolve chunks
    already present in the active CV-eligible lexical index.
    """

    if max_expansions <= 0:
        return hits

    active_chunks = lexical_index.get("chunks", {})
    record_chunks = lexical_index.get("record_chunks", {})
    edges_by_source: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for edge in relations:
        edges_by_source[edge.get("source", "")].append(edge)

    existing = {hit["chunk_id"] for hit in hits}
    expanded: list[dict[str, Any]] = list(hits)
    expansion_count = 0

    for seed in hits:
        if expansion_count >= max_expansions:
            break
        record_id = seed.get("record_id")
        for edge in edges_by_source.get(record_id, []):
            if expansion_count >= max_expansions:
                break
            candidates: list[str] = []
            if edge.get("relation") == "references_metric":
                candidates = [f"achievement-metrics::{edge.get('target')}" ]
            elif edge.get("relation") == "links_to":
                candidates = list(record_chunks.get(edge.get("target", ""), []))[:2]

            for chunk_id in candidates:
                if expansion_count >= max_expansions:
                    break
                if chunk_id in existing or chunk_id not in active_chunks:
                    continue
                meta = active_chunks[chunk_id]
                expanded.append({
                    "chunk_id": chunk_id,
                    "record_id": meta.get("record_id"),
                    "score": float(seed.get("score", 0.0)) * 0.5,
                    "chunk_type": meta.get("chunk_type"),
                    "source_path": meta.get("source_path"),
                    "proficiency": meta.get("proficiency"),
                    "constraints": meta.get("constraints", []),
                    "metric_refs": meta.get("metric_refs", []),
                    "text": meta.get("text", ""),
                    "retrieval_source": "graph",
                    "graph_seed_chunk_id": seed["chunk_id"],
                    "graph_relation": edge.get("relation"),
                })
                existing.add(chunk_id)
                expansion_count += 1

    return expanded


def hybrid_retrieve(
    query: str,
    *,
    lexical_index: dict[str, Any],
    dense_hits: list[dict[str, Any]],
    relations: list[dict[str, str]] | None = None,
    top_k: int = 8,
    candidate_k: int = 20,
    graph_expansion: bool = True,
) -> list[dict[str, Any]]:
    lexical_hits = retrieve_evidence(lexical_index, query, top_k=candidate_k)
    fused = reciprocal_rank_fusion(lexical_hits, dense_hits[:candidate_k], top_k=top_k)
    if graph_expansion and relations:
        return expand_graph(fused, lexical_index=lexical_index, relations=relations, max_expansions=max(2, top_k // 2))
    return fused
