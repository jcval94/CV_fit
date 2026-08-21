from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Protocol

from cv_agent.openai_provider import prepare_openai_environment, validate_openai_model_id


DEFAULT_RERANK_MODEL = "gpt-5.6-luna"
MAX_RERANK_CANDIDATES = 12


class RerankClient(Protocol):
    def rerank(self, requirement: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]: ...


@dataclass
class OpenAIRerankClient:
    model: str = DEFAULT_RERANK_MODEL

    def rerank(self, requirement: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        prepare_openai_environment(required=True)
        from openai import OpenAI

        model = validate_openai_model_id(self.model)
        compact = [
            {
                "chunk_id": hit["chunk_id"],
                "text": hit.get("text", "")[:2400],
                "proficiency": hit.get("proficiency"),
                "constraints": hit.get("constraints", []),
            }
            for hit in candidates[:MAX_RERANK_CANDIDATES]
        ]
        schema = {
            "type": "object",
            "properties": {
                "results": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "chunk_id": {"type": "string"},
                            "relevance": {"type": "integer", "minimum": 0, "maximum": 100},
                            "support": {"type": "string", "enum": ["direct", "related", "none"]},
                            "reason": {"type": "string"},
                        },
                        "required": ["chunk_id", "relevance", "support", "reason"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["results"],
            "additionalProperties": False,
        }
        instruction = (
            "Rerank professional evidence for one job requirement. Use only the candidate text. "
            "Be conservative. A related broad technology does not prove a named specialization: "
            "AWS does not prove AWS Bedrock; agentic workflows do not prove LangGraph; CI/CD does not prove GitLab; "
            "containerization does not prove Kubernetes production ownership. Mark direct only when the evidence "
            "explicitly supports the requested capability. Preserve proficiency and constraints. Return every supplied chunk_id once."
        )
        response = OpenAI().responses.create(
            model=model,
            input=json.dumps({"instruction": instruction, "requirement": requirement, "candidates": compact}, ensure_ascii=False),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "evidence_rerank",
                    "strict": True,
                    "schema": schema,
                },
                "verbosity": "low",
            },
            store=False,
        )
        payload = json.loads(response.output_text)
        return payload["results"]


def apply_rerank(
    requirement: str,
    hits: list[dict[str, Any]],
    *,
    client: RerankClient,
    top_k: int = 6,
    drop_none: bool = True,
) -> list[dict[str, Any]]:
    if not hits:
        return []
    raw = client.rerank(requirement, hits[:MAX_RERANK_CANDIDATES])
    allowed = {hit["chunk_id"]: hit for hit in hits[:MAX_RERANK_CANDIDATES]}
    seen: set[str] = set()
    reranked: list[dict[str, Any]] = []
    for item in raw:
        chunk_id = item.get("chunk_id")
        if chunk_id not in allowed or chunk_id in seen:
            continue
        seen.add(chunk_id)
        support = item.get("support")
        if drop_none and support == "none":
            continue
        hit = dict(allowed[chunk_id])
        hit["rerank_relevance"] = int(item.get("relevance", 0))
        hit["rerank_support"] = support
        hit["rerank_reason"] = item.get("reason", "")
        hit["pre_rerank_score"] = hit.get("score")
        hit["score"] = float(hit["rerank_relevance"])
        reranked.append(hit)
    reranked.sort(key=lambda item: (-item["rerank_relevance"], item["chunk_id"]))
    return reranked[:top_k]


def configured_rerank_model() -> str:
    return validate_openai_model_id(os.getenv("CV_FIT_RERANK_MODEL", DEFAULT_RERANK_MODEL))
