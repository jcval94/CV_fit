from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cv_matching.match import _coverage
from rag.dense import build_dense_index, retrieve_dense
from rag.hybrid import expand_graph, reciprocal_rank_fusion
from rag.rerank import apply_rerank


class FakeEmbeddingClient:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def embed(self, texts: list[str]):
        self.calls.append(list(texts))
        vectors = []
        for text in texts:
            lower = text.casefold()
            vectors.append([
                1.0 if "rollback" in lower or "deployment" in lower else 0.0,
                1.0 if "rag" in lower or "ground" in lower else 0.0,
                1.0 if "chronology" in lower or "2017" in lower or "four years" in lower else 0.0,
            ])
        return vectors, sum(len(text.split()) for text in texts)


class FakeReranker:
    def rerank(self, requirement, candidates):
        results = []
        for candidate in candidates:
            text = candidate.get("text", "").casefold()
            if requirement.casefold() == "aws bedrock" and "bedrock" not in text:
                support, relevance = "none", 10
            elif "aws" in text:
                support, relevance = "related", 50
            else:
                support, relevance = "direct", 90
            results.append({
                "chunk_id": candidate["chunk_id"],
                "relevance": relevance,
                "support": support,
                "reason": "fixture",
            })
        return results


class DenseIndexTests(unittest.TestCase):
    def test_incremental_dense_index_embeds_only_changed_active_chunks(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            lexical = {
                "chunks": {
                    "a": {"record_id": "r1", "chunk_type": "project_detail", "source_path": "experience/a.md", "content_hash": "h1", "text": "production deployment rollback"},
                    "b": {"record_id": "r2", "chunk_type": "project_detail", "source_path": "experience/b.md", "content_hash": "h2", "text": "RAG grounded knowledge"},
                },
                "record_chunks": {"r1": ["a"], "r2": ["b"]},
            }
            (state / "lexical_index.json").write_text(json.dumps(lexical), encoding="utf-8")
            client = FakeEmbeddingClient()
            first = build_dense_index(state, client=client, model="fake", dimensions=3)
            self.assertEqual(first["last_update"]["embedded"], 2)
            second = build_dense_index(state, client=client, model="fake", dimensions=3)
            self.assertEqual(second["last_update"]["embedded"], 0)
            self.assertEqual(len(client.calls), 1)

            lexical["chunks"]["b"]["content_hash"] = "h3"
            lexical["chunks"]["b"]["text"] = "RAG grounded knowledge changed"
            (state / "lexical_index.json").write_text(json.dumps(lexical), encoding="utf-8")
            third = build_dense_index(state, client=client, model="fake", dimensions=3)
            self.assertEqual(third["last_update"]["embedded"], 1)
            self.assertEqual(client.calls[-1], ["RAG grounded knowledge changed"])

    def test_dense_semantic_retrieval_can_find_paraphrase(self):
        client = FakeEmbeddingClient()
        dense = {
            "chunks": {
                "deploy": {"record_id": "r", "chunk_type": "project_detail", "source_path": "experience/a.md", "text": "production deployment rollback", "vector": [1.0, 0.0, 0.0]},
                "rag": {"record_id": "r2", "chunk_type": "project_detail", "source_path": "experience/b.md", "text": "RAG grounded knowledge", "vector": [0.0, 1.0, 0.0]},
            }
        }
        hits, _ = retrieve_dense(dense, "rollback strategy for model deployment", client=client, top_k=1)
        self.assertEqual(hits[0]["chunk_id"], "deploy")


class HybridGraphTests(unittest.TestCase):
    def test_rrf_combines_independent_rankings(self):
        lexical = [{"chunk_id": "a", "record_id": "r1", "score": 5}, {"chunk_id": "b", "record_id": "r2", "score": 4}]
        dense = [{"chunk_id": "b", "record_id": "r2", "score": .9}, {"chunk_id": "c", "record_id": "r3", "score": .8}]
        hits = reciprocal_rank_fusion(lexical, dense, top_k=3)
        self.assertEqual(hits[0]["chunk_id"], "b")
        self.assertEqual(hits[0]["retrieval_source"], "hybrid")

    def test_graph_expansion_adds_only_active_metric_chunk(self):
        lexical = {
            "chunks": {
                "project::summary": {"record_id": "project", "chunk_type": "project_detail", "source_path": "experience/project.md", "text": "project"},
                "achievement-metrics::ACH-X": {"record_id": "achievement-metrics", "chunk_type": "achievement_metric", "source_path": "experience/achievements/metrics.md", "text": "metric"},
            },
            "record_chunks": {"project": ["project::summary"], "achievement-metrics": ["achievement-metrics::ACH-X"]},
        }
        hits = [{"chunk_id": "project::summary", "record_id": "project", "score": 1.0, "source_path": "experience/project.md"}]
        relations = [{"source": "project", "relation": "references_metric", "target": "ACH-X"}]
        expanded = expand_graph(hits, lexical_index=lexical, relations=relations)
        graph_hits = [hit for hit in expanded if hit.get("retrieval_source") == "graph"]
        self.assertEqual([hit["chunk_id"] for hit in graph_hits], ["achievement-metrics::ACH-X"])


class RerankerSafetyTests(unittest.TestCase):
    def test_broad_aws_evidence_does_not_support_bedrock(self):
        hits = [{
            "chunk_id": "skills::aws",
            "record_id": "skills",
            "chunk_type": "skill",
            "source_path": "experience/skills.md",
            "proficiency": "working",
            "text": "AWS — working. Professional AWS/EMR/PySpark analytical workloads.",
            "score": 1.0,
        }]
        reranked = apply_rerank("AWS Bedrock", hits, client=FakeReranker())
        self.assertEqual(reranked, [])
        coverage, _ = _coverage("AWS Bedrock", reranked)
        self.assertEqual(coverage, "unsupported")


if __name__ == "__main__":
    unittest.main()
