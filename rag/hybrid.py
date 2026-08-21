from __future__ import annotations

import unicodedata
from collections import defaultdict
from typing import Any

from rag.evidence import retrieve_evidence


RRF_K = 60
DEFAULT_LEXICAL_WEIGHT = 1.0
DEFAULT_DENSE_WEIGHT = 1.0


def _search_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return " ".join(
        "".join(ch for ch in normalized if not unicodedata.combining(ch)).casefold().split()
    )


def _index_hit(chunk_id: str, meta: dict[str, Any], *, reason: str) -> dict[str, Any]:
    return {
        "chunk_id": chunk_id,
        "record_id": meta.get("record_id"),
        "score": 1.0,
        "chunk_type": meta.get("chunk_type"),
        "source_path": meta.get("source_path"),
        "proficiency": meta.get("proficiency"),
        "constraints": meta.get("constraints", []),
        "metric_refs": meta.get("metric_refs", []),
        "text": meta.get("text", ""),
        "retrieval_source": "anchor",
        "anchor_reason": reason,
    }


def deterministic_anchors(
    query: str,
    *,
    lexical_index: dict[str, Any],
    max_anchors: int = 4,
) -> list[dict[str, Any]]:
    """Return high-value structural candidates that semantic ranking can miss.

    Anchors do not assert support and do not bypass the reranker. They only make
    canonical evidence available to downstream ranking when the query itself
    explicitly asks for a structure represented in the source of truth:

    * a named skill/technology -> the exact `skills` chunk;
    * an explicit duration in years -> canonical employment-period role chunks.

    All candidates come from the active lexical index, so public/CV eligibility
    remains identical to normal retrieval policy.
    """
    if max_anchors <= 0:
        return []

    query_norm = _search_text(query)
    chunks = lexical_index.get("chunks", {})
    anchors: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(chunk_id: str, meta: dict[str, Any], reason: str) -> None:
        if len(anchors) >= max_anchors or chunk_id in seen:
            return
        seen.add(chunk_id)
        anchors.append(_index_hit(chunk_id, meta, reason=reason))

    for chunk_id, meta in sorted(chunks.items()):
        if meta.get("record_id") != "skills" or meta.get("chunk_type") != "skill":
            continue
        title = _search_text((meta.get("text") or "").splitlines()[0] if meta.get("text") else "")
        if title and len(title) >= 2 and title in query_norm:
            add(chunk_id, meta, "exact_named_skill")

    # Any explicit years requirement is a chronology query even when the JD says
    # "four years in ML engineering" rather than literally "years of experience".
    asks_duration = any(term in query_norm.split() for term in ("anos", "years", "year", "yrs"))
    if asks_duration:
        canonical_roles: list[tuple[str, dict[str, Any]]] = []
        other_roles: list[tuple[str, dict[str, Any]]] = []
        for chunk_id, meta in sorted(chunks.items()):
            if not str(meta.get("record_id") or "").startswith("role-"):
                continue
            if meta.get("chunk_type") != "role_detail":
                continue
            text_norm = _search_text(meta.get("text") or "")
            if "period" not in text_norm and "periodo" not in text_norm:
                continue
            pair = (chunk_id, meta)
            if chunk_id.endswith("canonical-employment-record") or "overall period" in text_norm:
                canonical_roles.append(pair)
            else:
                other_roles.append(pair)
        for chunk_id, meta in canonical_roles + other_roles:
            add(chunk_id, meta, "career_chronology")

    return anchors


def inject_deterministic_anchors(
    query: str,
    hits: list[dict[str, Any]],
    *,
    lexical_index: dict[str, Any],
    max_anchors: int = 4,
) -> list[dict[str, Any]]:
    anchors = deterministic_anchors(query, lexical_index=lexical_index, max_anchors=max_anchors)
    if not anchors:
        return hits
    anchored_ids = {hit["chunk_id"] for hit in anchors}
    return anchors + [hit for hit in hits if hit["chunk_id"] not in anchored_ids]


def normalize_relations(payload: Any) -> list[dict[str, str]]:
    """Normalize the persisted relation contract into a list of relation edges."""
    if payload is None:
        return []
    if isinstance(payload, dict):
        edges = payload.get("relations", [])
    elif isinstance(payload, list):
        edges = payload
    else:
        raise TypeError(f"unsupported relations payload type: {type(payload).__name__}")

    if not isinstance(edges, list):
        raise ValueError("relations payload must contain a list under 'relations'")
    invalid = [index for index, edge in enumerate(edges) if not isinstance(edge, dict)]
    if invalid:
        raise ValueError(f"relations payload contains non-object edges at indexes {invalid[:5]}")
    return edges


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
    relations: Any,
    max_expansions: int = 8,
) -> list[dict[str, Any]]:
    """Add one-hop eligible evidence linked to retrieved records."""
    if max_expansions <= 0:
        return hits

    active_chunks = lexical_index.get("chunks", {})
    record_chunks = lexical_index.get("record_chunks", {})
    edges_by_source: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for edge in normalize_relations(relations):
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
                candidates = [f"achievement-metrics::{edge.get('target')}"]
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
    relations: Any = None,
    top_k: int = 8,
    candidate_k: int = 20,
    graph_expansion: bool = True,
) -> list[dict[str, Any]]:
    lexical_hits = retrieve_evidence(lexical_index, query, top_k=candidate_k)
    fused = reciprocal_rank_fusion(lexical_hits, dense_hits[:candidate_k], top_k=top_k)
    fused = inject_deterministic_anchors(
        query,
        fused,
        lexical_index=lexical_index,
        max_anchors=max(2, min(4, top_k // 2)),
    )
    if graph_expansion and relations:
        return expand_graph(
            fused,
            lexical_index=lexical_index,
            relations=relations,
            max_expansions=max(2, top_k // 2),
        )
    return fused
