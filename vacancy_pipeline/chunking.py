from __future__ import annotations

import hashlib
from dataclasses import replace
from typing import Iterable

from vacancy_pipeline.contract import semantic_hash
from vacancy_pipeline.models import ProvenanceRef, VacancyChunk, VacancyRecord


def _union_lists(records: Iterable[VacancyRecord], field: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for record in records:
        for item in getattr(record, field):
            key = item.casefold()
            if key not in seen:
                seen.add(key)
                out.append(item)
    return out


def _quality(record: VacancyRecord) -> tuple[int, int, str]:
    scalar_fields = [
        record.seniority,
        record.company_category,
        record.location_raw,
        record.city,
        record.work_model,
        record.posted_date,
        record.posted_date_raw,
        record.url,
        record.salary,
        record.description,
        record.fit_summary,
    ]
    populated = sum(bool(value) for value in scalar_fields)
    list_items = sum(
        len(getattr(record, field))
        for field in ("tech_stack", "requirements", "responsibilities", "fit_strengths", "fit_gaps")
    )
    source_path = record.provenance[0].source_path if record.provenance else ""
    return populated, list_items, source_path


def merge_records(records: list[VacancyRecord]) -> VacancyRecord:
    if not records:
        raise ValueError("cannot merge an empty vacancy record set")
    vacancy_ids = {record.vacancy_id for record in records}
    if len(vacancy_ids) != 1:
        raise ValueError("all merged records must share vacancy_id")

    preferred = sorted(records, key=lambda r: (-_quality(r)[0], -_quality(r)[1], _quality(r)[2]))[0]
    provenance: list[ProvenanceRef] = []
    seen_prov: set[tuple[str, int]] = set()
    for record in sorted(records, key=lambda r: r.provenance[0].source_path if r.provenance else ""):
        for ref in record.provenance:
            key = (ref.source_path, ref.source_entry_index)
            if key not in seen_prov:
                seen_prov.add(key)
                provenance.append(ref)

    merged = replace(
        preferred,
        tech_stack=_union_lists(records, "tech_stack"),
        requirements=_union_lists(records, "requirements"),
        responsibilities=_union_lists(records, "responsibilities"),
        fit_strengths=_union_lists(records, "fit_strengths"),
        fit_gaps=_union_lists(records, "fit_gaps"),
        provenance=provenance,
        content_hash="",
    )
    payload = merged.to_dict()
    payload.pop("content_hash", None)
    payload.pop("provenance", None)
    return replace(merged, content_hash=semantic_hash(payload))


def _chunk(vacancy: VacancyRecord, chunk_type: str, lines: list[str]) -> VacancyChunk | None:
    text = "\n".join(line.strip() for line in lines if line and line.strip()).strip()
    if not text:
        return None
    chunk_id = f"{vacancy.vacancy_id}::{chunk_type}"
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    sources = sorted({ref.source_path for ref in vacancy.provenance})
    return VacancyChunk(chunk_id, vacancy.vacancy_id, chunk_type, text, digest, sources)


def build_chunks(vacancy: VacancyRecord) -> list[VacancyChunk]:
    core_lines = [
        f"Role: {vacancy.role_title}",
        f"Company: {vacancy.company}",
        f"Seniority: {vacancy.seniority}" if vacancy.seniority else "",
        f"Company category: {vacancy.company_category}" if vacancy.company_category else "",
        f"Location: {vacancy.location_raw}" if vacancy.location_raw else "",
        f"Work model: {vacancy.work_model}" if vacancy.work_model else "",
        f"Description: {vacancy.description}" if vacancy.description else "",
    ]
    requirement_lines: list[str] = []
    if vacancy.tech_stack:
        requirement_lines.append("Technologies / capabilities: " + "; ".join(vacancy.tech_stack))
    if vacancy.requirements:
        requirement_lines.append("Requirements: " + "; ".join(vacancy.requirements))
    if vacancy.responsibilities:
        requirement_lines.append("Responsibilities: " + "; ".join(vacancy.responsibilities))

    fit_lines: list[str] = []
    if vacancy.fit_score is not None:
        fit_lines.append(f"Source fit score: {vacancy.fit_score:g}/100")
    if vacancy.fit_summary:
        fit_lines.append("Source fit summary: " + vacancy.fit_summary)
    if vacancy.fit_strengths:
        fit_lines.append("Source strengths: " + "; ".join(vacancy.fit_strengths))
    if vacancy.fit_gaps:
        fit_lines.append("Source gaps: " + "; ".join(vacancy.fit_gaps))

    chunks = [
        _chunk(vacancy, "core", core_lines),
        _chunk(vacancy, "requirements", requirement_lines),
        _chunk(vacancy, "source-fit", fit_lines),
    ]
    return [chunk for chunk in chunks if chunk is not None]
