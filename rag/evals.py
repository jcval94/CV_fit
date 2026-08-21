from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

from rag.evidence import retrieve_evidence


PROFICIENCY_RANK = {None: 0, "familiarity": 1, "working": 2, "core": 3}


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_case(case: dict[str, Any], hits: list[dict[str, Any]], *, top_k: int) -> dict[str, Any]:
    hits = hits[:top_k]
    records = [hit.get("record_id") for hit in hits]
    expected = set(case.get("expected_any_record_ids", []))
    forbidden = set(case.get("forbidden_record_ids", []))
    negative = bool(case.get("negative"))

    reciprocal_rank = 0.0
    if expected:
        for rank, record_id in enumerate(records, start=1):
            if record_id in expected:
                reciprocal_rank = 1.0 / rank
                break
    recall = 1.0 if expected and any(record_id in expected for record_id in records) else (1.0 if not expected else 0.0)

    direct_hits = [hit for hit in hits if hit.get("rerank_support") == "direct"]
    if negative:
        # Before semantic reranking any retrieved evidence is conservatively treated
        # as a potential false positive. After reranking only direct support violates
        # a declared negative case.
        safe_negative = not direct_hits if any("rerank_support" in hit for hit in hits) else not hits
    else:
        safe_negative = True

    forbidden_hits = [hit["chunk_id"] for hit in hits if hit.get("record_id") in forbidden]
    if any("rerank_support" in hit for hit in hits):
        forbidden_direct_hits = [
            hit["chunk_id"] for hit in hits
            if hit.get("record_id") in forbidden and hit.get("rerank_support") == "direct"
        ]
    else:
        forbidden_direct_hits = forbidden_hits

    proficiency_ok = True
    max_allowed = case.get("required_max_proficiency")
    if max_allowed:
        allowed_rank = PROFICIENCY_RANK[max_allowed]
        observed = max((PROFICIENCY_RANK.get((hit.get("proficiency") or "").casefold(), 0) for hit in hits), default=0)
        proficiency_ok = observed <= allowed_rank

    passed = recall == 1.0 and safe_negative and not forbidden_direct_hits and proficiency_ok
    return {
        "id": case["id"],
        "query": case["query"],
        "passed": passed,
        "recall_at_k": recall,
        "reciprocal_rank": reciprocal_rank,
        "safe_negative": safe_negative,
        "proficiency_ok": proficiency_ok,
        "forbidden_direct_hits": forbidden_direct_hits,
        "hit_chunk_ids": [hit["chunk_id"] for hit in hits],
        "hit_record_ids": records,
    }


def evaluate_suite(
    cases: list[dict[str, Any]],
    retrieve: Callable[[str, int], list[dict[str, Any]]],
    *,
    top_k: int = 6,
) -> dict[str, Any]:
    results = [evaluate_case(case, retrieve(case["query"], top_k), top_k=top_k) for case in cases]
    positive = [result for result, case in zip(results, cases) if not case.get("negative")]
    negative = [result for result, case in zip(results, cases) if case.get("negative")]
    return {
        "schema_version": 1,
        "top_k": top_k,
        "case_count": len(results),
        "passed": sum(result["passed"] for result in results),
        "pass_rate": round(sum(result["passed"] for result in results) / max(len(results), 1), 4),
        "positive_recall_at_k": round(sum(result["recall_at_k"] for result in positive) / max(len(positive), 1), 4),
        "positive_mrr": round(sum(result["reciprocal_rank"] for result in positive) / max(len(positive), 1), 4),
        "negative_safety_rate": round(sum(result["safe_negative"] for result in negative) / max(len(negative), 1), 4),
        "forbidden_direct_hit_count": sum(len(result["forbidden_direct_hits"]) for result in results),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate the deterministic lexical professional retrieval baseline.")
    parser.add_argument("--state-dir", default="rag_state")
    parser.add_argument("--cases", default="evals/retrieval/cases.json")
    parser.add_argument("--top-k", type=int, default=6)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    index = _read_json(Path(args.state_dir) / "lexical_index.json")
    cases = _read_json(Path(args.cases))["cases"]
    report = evaluate_suite(cases, lambda query, k: retrieve_evidence(index, query, top_k=k), top_k=args.top_k)
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
