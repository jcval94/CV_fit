from __future__ import annotations

import argparse
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from cv_agent.openai_provider import prepare_openai_environment


DENSE_SCHEMA_VERSION = 1
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-large"
DEFAULT_EMBEDDING_DIMENSIONS = 1024
EMBEDDING_PRICE_USD_PER_MILLION = {"text-embedding-3-large": 0.13, "text-embedding-3-small": 0.02}


class EmbeddingClient(Protocol):
    def embed(self, texts: list[str]) -> tuple[list[list[float]], int]: ...


@dataclass
class OpenAIEmbeddingClient:
    model: str = DEFAULT_EMBEDDING_MODEL
    dimensions: int = DEFAULT_EMBEDDING_DIMENSIONS

    def embed(self, texts: list[str]) -> tuple[list[list[float]], int]:
        if not texts:
            return [], 0
        prepare_openai_environment(required=True)
        from openai import OpenAI

        client = OpenAI()
        response = client.embeddings.create(
            model=self.model,
            input=texts,
            dimensions=self.dimensions,
            encoding_format="float",
        )
        vectors = [item.embedding for item in sorted(response.data, key=lambda item: item.index)]
        usage = getattr(response, "usage", None)
        tokens = int(getattr(usage, "total_tokens", 0) or getattr(usage, "prompt_tokens", 0) or 0)
        return vectors, tokens


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def _cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return _dot(left, right) / (left_norm * right_norm)


def build_dense_index(
    evidence_state: Path,
    *,
    client: EmbeddingClient,
    model: str = DEFAULT_EMBEDDING_MODEL,
    dimensions: int = DEFAULT_EMBEDDING_DIMENSIONS,
    force: bool = False,
) -> dict[str, Any]:
    """Incrementally embed only active CV-eligible chunks from the lexical evidence index."""

    evidence_state = evidence_state.resolve()
    lexical = _read_json(evidence_state / "lexical_index.json", {})
    lexical_chunks: dict[str, dict[str, Any]] = lexical.get("chunks", {})
    path = evidence_state / "dense_index.json"
    previous = _read_json(path, {})

    compatible = (
        previous.get("schema_version") == DENSE_SCHEMA_VERSION
        and previous.get("model") == model
        and previous.get("dimensions") == dimensions
    )
    existing: dict[str, dict[str, Any]] = previous.get("chunks", {}) if compatible and not force else {}

    active_ids = set(lexical_chunks)
    removed = sorted(set(existing) - active_ids)
    for chunk_id in removed:
        existing.pop(chunk_id, None)

    changed_ids = sorted(
        chunk_id
        for chunk_id, meta in lexical_chunks.items()
        if force
        or chunk_id not in existing
        or existing[chunk_id].get("content_hash") != meta.get("content_hash")
    )

    total_tokens = 0
    if changed_ids:
        texts = [lexical_chunks[chunk_id]["text"] for chunk_id in changed_ids]
        vectors, total_tokens = client.embed(texts)
        if len(vectors) != len(changed_ids):
            raise RuntimeError("embedding provider returned a different vector count than requested")
        for chunk_id, vector in zip(changed_ids, vectors):
            if len(vector) != dimensions:
                raise RuntimeError(
                    f"embedding dimension mismatch for {chunk_id}: {len(vector)} != {dimensions}"
                )
            source = lexical_chunks[chunk_id]
            existing[chunk_id] = {
                "content_hash": source.get("content_hash"),
                "record_id": source.get("record_id"),
                "chunk_type": source.get("chunk_type"),
                "source_path": source.get("source_path"),
                "proficiency": source.get("proficiency"),
                "constraints": source.get("constraints", []),
                "metric_refs": source.get("metric_refs", []),
                "text": source.get("text", ""),
                "vector": vector,
            }

    price = EMBEDDING_PRICE_USD_PER_MILLION.get(model)
    estimated_cost = None if price is None else round(total_tokens * price / 1_000_000.0, 8)
    result = {
        "schema_version": DENSE_SCHEMA_VERSION,
        "model": model,
        "dimensions": dimensions,
        "chunks": dict(sorted(existing.items())),
        "last_update": {
            "active": len(active_ids),
            "embedded": len(changed_ids),
            "removed": len(removed),
            "input_tokens": total_tokens,
            "estimated_cost_usd": estimated_cost,
        },
    }
    _write_json(path, result)
    return result


def retrieve_dense(
    dense_index: dict[str, Any],
    query: str,
    *,
    client: EmbeddingClient,
    top_k: int = 8,
) -> tuple[list[dict[str, Any]], int]:
    vectors, tokens = client.embed([query])
    if not vectors:
        return [], tokens
    query_vector = vectors[0]
    hits: list[dict[str, Any]] = []
    for chunk_id, meta in dense_index.get("chunks", {}).items():
        score = _cosine(query_vector, meta.get("vector", []))
        hits.append({
            "chunk_id": chunk_id,
            "record_id": meta.get("record_id"),
            "score": score,
            "chunk_type": meta.get("chunk_type"),
            "source_path": meta.get("source_path"),
            "proficiency": meta.get("proficiency"),
            "constraints": meta.get("constraints", []),
            "metric_refs": meta.get("metric_refs", []),
            "text": meta.get("text", ""),
            "retrieval_source": "dense",
        })
    hits.sort(key=lambda item: (-item["score"], item["chunk_id"]))
    return hits[:top_k], tokens


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the incremental OpenAI dense index for eligible professional evidence.")
    parser.add_argument("--state-dir", default="rag_state")
    parser.add_argument("--model", default=os.getenv("CV_FIT_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL))
    parser.add_argument(
        "--dimensions",
        type=int,
        default=int(os.getenv("CV_FIT_EMBEDDING_DIMENSIONS", str(DEFAULT_EMBEDDING_DIMENSIONS))),
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.dimensions <= 0:
        parser.error("--dimensions must be positive")
    result = build_dense_index(
        Path(args.state_dir),
        client=OpenAIEmbeddingClient(model=args.model, dimensions=args.dimensions),
        model=args.model,
        dimensions=args.dimensions,
        force=args.force,
    )
    print(json.dumps(result["last_update"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
