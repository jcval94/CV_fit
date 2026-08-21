from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class RecommendationTrace:
    """Trace contract for future matching; no CV generation happens here."""

    vacancy_id: str
    vacancy_chunk_ids: list[str]
    vacancy_source_paths: list[str]
    evidence_record_ids: list[str]
    evidence_source_paths: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_trace(
    trace: RecommendationTrace,
    vacancy_index: dict[str, Any],
    evidence_records: list[dict[str, Any]],
) -> None:
    vacancy_chunks = set(vacancy_index.get("vacancy_chunks", {}).get(trace.vacancy_id, []))
    missing_chunks = sorted(set(trace.vacancy_chunk_ids) - vacancy_chunks)
    if missing_chunks:
        raise ValueError(f"trace references unknown vacancy chunks: {missing_chunks}")

    by_id = {record["record_id"]: record for record in evidence_records}
    missing_evidence = sorted(set(trace.evidence_record_ids) - set(by_id))
    if missing_evidence:
        raise ValueError(f"trace references unknown evidence records: {missing_evidence}")

    actual_vacancy_sources: set[str] = set()
    for chunk_id in trace.vacancy_chunk_ids:
        actual_vacancy_sources.update(vacancy_index["chunks"][chunk_id].get("source_paths", []))
    if not set(trace.vacancy_source_paths).issubset(actual_vacancy_sources):
        raise ValueError("vacancy source paths are not supported by traced chunks")

    actual_evidence_sources = {by_id[item]["source_path"] for item in trace.evidence_record_ids}
    if not set(trace.evidence_source_paths).issubset(actual_evidence_sources):
        raise ValueError("evidence source paths are not supported by traced records")
