from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from vacancy_pipeline.fidelity import assess_jd_fidelity


@dataclass(frozen=True)
class ProvenanceRef:
    source_path: str
    source_hash: str
    source_format: str
    source_entry_index: int
    source_native_id: str | None = None
    source_commit: str | None = None
    source_updated_at: str | None = None
    source_search_date: str | None = None


@dataclass(frozen=True)
class VacancyRecord:
    schema_version: int
    vacancy_id: str
    company: str
    role_title: str
    seniority: str | None
    company_category: str | None
    location_raw: str | None
    city: str | None
    work_model: str | None
    posted_date: str | None
    posted_date_raw: str | None
    url: str | None
    salary: str | None
    tech_stack: list[str]
    requirements: list[str]
    responsibilities: list[str]
    description: str | None
    application_language: str
    language_confidence: float
    language_source: str
    fit_score: float | None
    fit_summary: str | None
    fit_strengths: list[str]
    fit_gaps: list[str]
    identity_key: str
    content_hash: str
    provenance: list[ProvenanceRef] = field(default_factory=list)
    jd_fidelity: str = field(init=False)
    jd_fidelity_score: float = field(init=False)
    jd_fidelity_reasons: list[str] = field(init=False)
    jd_generation_eligible: bool = field(init=False)

    def __post_init__(self) -> None:
        assessment = assess_jd_fidelity(
            description=self.description,
            requirements=self.requirements,
            responsibilities=self.responsibilities,
        )
        object.__setattr__(self, "jd_fidelity", assessment.classification)
        object.__setattr__(self, "jd_fidelity_score", assessment.score)
        object.__setattr__(self, "jd_fidelity_reasons", list(assessment.reasons))
        object.__setattr__(self, "jd_generation_eligible", assessment.generation_eligible)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VacancyChunk:
    chunk_id: str
    vacancy_id: str
    chunk_type: str
    text: str
    content_hash: str
    source_paths: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RetrievalHit:
    chunk_id: str
    vacancy_id: str
    score: float
    chunk_type: str
    text: str
    source_paths: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
