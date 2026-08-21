from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cv_matching import MATCH_SCHEMA_VERSION
from rag.dense import OpenAIEmbeddingClient, retrieve_dense
from rag.evidence import retrieve_evidence
from rag.hybrid import hybrid_retrieve
from rag.rerank import OpenAIRerankClient, apply_rerank, configured_rerank_model


PROFICIENCY_RANK = {"familiarity": 1, "working": 2, "core": 3}
GENERIC_REQUIREMENT_TERMS = {
    "machine learning", "data science", "analytics", "python", "sql", "ai", "artificial intelligence"
}
RETRIEVAL_MODES = {"auto", "lexical", "hybrid", "hybrid-rerank"}


@dataclass(frozen=True)
class RequirementMatch:
    requirement: str
    requirement_type: str
    importance: str
    coverage: str
    evidence_chunk_ids: list[str]
    evidence_record_ids: list[str]
    evidence_source_paths: list[str]
    rationale: str
    retrieval_mode: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirement": self.requirement,
            "requirement_type": self.requirement_type,
            "importance": self.importance,
            "coverage": self.coverage,
            "evidence_chunk_ids": self.evidence_chunk_ids,
            "evidence_record_ids": self.evidence_record_ids,
            "evidence_source_paths": self.evidence_source_paths,
            "rationale": self.rationale,
            "retrieval_mode": self.retrieval_mode,
        }


def _read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def extract_requirements(vacancy: dict[str, Any]) -> list[tuple[str, str, str]]:
    """Return unique (text, type, importance) requirements without LLM inference."""
    requirements: list[tuple[str, str, str]] = []
    seen: set[str] = set()

    def add(text: Any, kind: str, importance: str) -> None:
        if not isinstance(text, str):
            return
        text = _clean(text)
        key = text.casefold()
        if not text or key in seen:
            return
        seen.add(key)
        requirements.append((text, kind, importance))

    for tech in vacancy.get("tech_stack", []):
        add(tech, "technology_or_capability", "critical")
    for req in vacancy.get("requirements", []):
        add(req, "requirement", "critical")
    for responsibility in vacancy.get("responsibilities", []):
        add(responsibility, "responsibility", "important")

    if not requirements:
        add(vacancy.get("role_title", ""), "role_signal", "important")
    return requirements


def _coverage(requirement: str, hits: list[dict[str, Any]]) -> tuple[str, str]:
    if not hits:
        return "unsupported", "No eligible professional evidence chunk matched this requirement."

    rerank_direct = [hit for hit in hits if hit.get("rerank_support") == "direct"]
    rerank_related = [hit for hit in hits if hit.get("rerank_support") == "related"]
    if any("rerank_support" in hit for hit in hits):
        if not rerank_direct and rerank_related:
            return "weak", "The semantic reranker found related evidence but no direct support for the requested capability."
        if not rerank_direct:
            return "unsupported", "The semantic reranker found no direct professional evidence for this requirement."
        hits = rerank_direct + rerank_related

    skill_hits = [hit for hit in hits if hit.get("chunk_type") == "skill"]
    best_level = max((PROFICIENCY_RANK.get((hit.get("proficiency") or "").casefold(), 0) for hit in skill_hits), default=0)
    distinct_records = len({hit["record_id"] for hit in hits if hit.get("record_id")})
    top_score = float(hits[0].get("score", 0))
    key = requirement.casefold()

    if best_level >= 3 or (best_level >= 2 and distinct_records >= 2):
        return "strong", "Matched demonstrated skill proficiency with corroborating evidence."
    if best_level == 1:
        return "weak", "Only familiarity-level skill evidence was found; do not upgrade proficiency."
    if distinct_records >= 2 or top_score >= 4 or key in GENERIC_REQUIREMENT_TERMS:
        return "partial", "Relevant evidence exists, but the matcher cannot prove full requirement coverage."
    return "weak", "A limited match exists; treat it as supporting evidence only."


def _resolve_mode(requested: str, evidence_state: Path) -> str:
    if requested not in RETRIEVAL_MODES:
        raise ValueError(f"unsupported retrieval mode: {requested}")
    if requested == "auto":
        return "hybrid" if (evidence_state / "dense_index.json").exists() else "lexical"
    return requested


def _retrieve_for_requirement(
    requirement: str,
    *,
    lexical_index: dict[str, Any],
    dense_index: dict[str, Any] | None,
    relations: list[dict[str, str]],
    mode: str,
    top_k: int,
    embedding_client: OpenAIEmbeddingClient | None,
    rerank_client: OpenAIRerankClient | None,
) -> list[dict[str, Any]]:
    if mode == "lexical":
        return retrieve_evidence(lexical_index, requirement, top_k=top_k)
    if dense_index is None or embedding_client is None:
        raise RuntimeError(f"retrieval mode {mode!r} requires rag_state/dense_index.json and OpenAI embeddings")

    dense_hits, _ = retrieve_dense(dense_index, requirement, client=embedding_client, top_k=max(20, top_k * 3))
    hits = hybrid_retrieve(
        requirement,
        lexical_index=lexical_index,
        dense_hits=dense_hits,
        relations=relations,
        top_k=max(top_k, 10 if mode == "hybrid-rerank" else top_k),
        candidate_k=max(20, top_k * 3),
        graph_expansion=True,
    )
    if mode == "hybrid-rerank":
        if rerank_client is None:
            raise RuntimeError("hybrid-rerank mode requires an OpenAI rerank client")
        hits = apply_rerank(requirement, hits, client=rerank_client, top_k=top_k)
    return hits[:top_k]


def match_vacancy_to_evidence(
    vacancy: dict[str, Any],
    evidence_index: dict[str, Any],
    *,
    top_k_per_requirement: int = 6,
    retrieval_mode: str = "lexical",
    dense_index: dict[str, Any] | None = None,
    relations: list[dict[str, str]] | None = None,
    embedding_client: OpenAIEmbeddingClient | None = None,
    rerank_client: OpenAIRerankClient | None = None,
) -> dict[str, Any]:
    matches: list[RequirementMatch] = []
    all_chunks: set[str] = set()
    all_records: set[str] = set()
    all_sources: set[str] = set()

    for requirement, kind, importance in extract_requirements(vacancy):
        hits = _retrieve_for_requirement(
            requirement,
            lexical_index=evidence_index,
            dense_index=dense_index,
            relations=relations or [],
            mode=retrieval_mode,
            top_k=top_k_per_requirement,
            embedding_client=embedding_client,
            rerank_client=rerank_client,
        )
        coverage, rationale = _coverage(requirement, hits)
        chunk_ids = [hit["chunk_id"] for hit in hits]
        record_ids = sorted({hit["record_id"] for hit in hits if hit.get("record_id")})
        sources = sorted({hit["source_path"] for hit in hits if hit.get("source_path")})
        all_chunks.update(chunk_ids)
        all_records.update(record_ids)
        all_sources.update(sources)
        matches.append(RequirementMatch(
            requirement=requirement,
            requirement_type=kind,
            importance=importance,
            coverage=coverage,
            evidence_chunk_ids=chunk_ids,
            evidence_record_ids=record_ids,
            evidence_source_paths=sources,
            rationale=rationale,
            retrieval_mode=retrieval_mode,
        ))

    counts = {name: sum(item.coverage == name for item in matches) for name in ("strong", "partial", "weak", "unsupported")}
    total = max(len(matches), 1)
    weighted = (counts["strong"] * 1.0 + counts["partial"] * 0.65 + counts["weak"] * 0.3) / total
    return {
        "schema_version": MATCH_SCHEMA_VERSION,
        "vacancy_id": vacancy["vacancy_id"],
        "vacancy_content_hash": vacancy.get("content_hash"),
        "retrieval_mode": retrieval_mode,
        "coverage_score": round(weighted * 100, 1),
        "coverage_counts": counts,
        "requirements": [item.to_dict() for item in matches],
        "selected_evidence_chunk_ids": sorted(all_chunks),
        "selected_evidence_record_ids": sorted(all_records),
        "selected_evidence_source_paths": sorted(all_sources),
        "guardrails": [
            "unsupported requirements must not be turned into candidate claims",
            "familiarity proficiency must never be upgraded to working or core",
            "exact metrics require approved ACH-* evidence",
            "named technologies require direct evidence after semantic reranking before being treated as supported",
        ],
    }


def build_match(
    vacancy_id: str,
    *,
    vacancy_state: Path = Path("vacancy_state"),
    evidence_state: Path = Path("rag_state"),
    retrieval_mode: str | None = None,
) -> dict[str, Any]:
    vacancy = _read_json(vacancy_state / "records" / f"{vacancy_id}.json")
    lexical = _read_json(evidence_state / "lexical_index.json")
    requested = retrieval_mode or os.getenv("CV_FIT_RETRIEVAL_MODE", "auto")
    mode = _resolve_mode(requested, evidence_state)
    dense = None
    relations = _read_json(evidence_state / "relations.json", [])
    embedder = None
    reranker = None

    if mode != "lexical":
        dense = _read_json(evidence_state / "dense_index.json")
        embedder = OpenAIEmbeddingClient(model=dense["model"], dimensions=int(dense["dimensions"]))
    if mode == "hybrid-rerank":
        reranker = OpenAIRerankClient(model=configured_rerank_model())

    return match_vacancy_to_evidence(
        vacancy,
        lexical,
        retrieval_mode=mode,
        dense_index=dense,
        relations=relations,
        embedding_client=embedder,
        rerank_client=reranker,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Match one canonical vacancy to eligible professional evidence.")
    parser.add_argument("vacancy_id")
    parser.add_argument("--vacancy-state", default="vacancy_state")
    parser.add_argument("--evidence-state", default="rag_state")
    parser.add_argument("--retrieval-mode", choices=sorted(RETRIEVAL_MODES), default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    result = build_match(
        args.vacancy_id,
        vacancy_state=Path(args.vacancy_state),
        evidence_state=Path(args.evidence_state),
        retrieval_mode=args.retrieval_mode,
    )
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
