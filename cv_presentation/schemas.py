from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


SectionKey = Literal["summary", "experience", "projects", "skills", "education", "certifications"]
SectionMode = Literal["always", "auto", "never"]
PageSize = Literal["letter", "a4"]
DensityMode = Literal["compact", "normal", "spacious"]
FitStatus = Literal["FIT", "NEEDS_REVISION"]

DEFAULT_SECTION_ORDER: list[str] = [
    "summary",
    "experience",
    "projects",
    "skills",
    "education",
    "certifications",
]
DEFAULT_SECTION_MODES: dict[str, str] = {
    "summary": "always",
    "experience": "always",
    "projects": "auto",
    "skills": "always",
    "education": "always",
    "certifications": "auto",
}


class CandidateIdentity(BaseModel):
    name: str
    location: str | None = None
    linkedin: str | None = None
    github: str | None = None
    website: str | None = None
    email: str | None = None
    phone: str | None = None

    @field_validator("name")
    @classmethod
    def _name_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("candidate name is required for presentation")
        return value

    @field_validator("location", "linkedin", "github", "website", "email", "phone")
    @classmethod
    def _clean_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class IdentityResolution(BaseModel):
    identity: CandidateIdentity
    field_sources: dict[str, Literal["public_file", "environment"]] = Field(default_factory=dict)
    private_fields_included: list[Literal["email", "phone"]] = Field(default_factory=list)
    artifact_visibility: Literal["public", "private"] = "public"


class DocumentSpec(BaseModel):
    page_size: PageSize = "letter"
    target_pages: int = Field(default=2, ge=1, le=3)
    template_id: str = "ats_classic_v1"


class LayoutSpec(BaseModel):
    section_order: list[SectionKey] = Field(default_factory=lambda: list(DEFAULT_SECTION_ORDER))
    section_modes: dict[SectionKey, SectionMode] = Field(default_factory=lambda: dict(DEFAULT_SECTION_MODES))

    @model_validator(mode="after")
    def _validate_sections(self) -> "LayoutSpec":
        expected = set(DEFAULT_SECTION_ORDER)
        order = list(self.section_order)
        if len(order) != len(set(order)):
            raise ValueError("section_order contains duplicates")
        if set(order) != expected:
            missing = sorted(expected - set(order))
            extra = sorted(set(order) - expected)
            raise ValueError(f"section_order must contain every supported section exactly once; missing={missing}, extra={extra}")
        if set(self.section_modes) != expected:
            missing = sorted(expected - set(self.section_modes))
            extra = sorted(set(self.section_modes) - expected)
            raise ValueError(f"section_modes must define every supported section; missing={missing}, extra={extra}")
        if self.section_modes["summary"] == "never" or self.section_modes["experience"] == "never":
            raise ValueError("summary and experience cannot be disabled")
        return self


class DensitySpec(BaseModel):
    mode: DensityMode = "normal"
    max_summary_words: int = Field(default=80, ge=30, le=140)
    max_role_bullets: int = Field(default=4, ge=1, le=8)
    min_role_bullets: int = Field(default=1, ge=1, le=4)
    max_projects: int = Field(default=2, ge=0, le=6)
    max_project_bullets: int = Field(default=3, ge=1, le=6)
    min_project_bullets: int = Field(default=1, ge=1, le=3)
    max_skills: int = Field(default=10, ge=3, le=30)
    min_skills: int = Field(default=5, ge=1, le=15)
    max_education: int = Field(default=2, ge=1, le=6)
    max_certifications: int = Field(default=4, ge=0, le=12)
    estimated_chars_per_line: int = Field(default=92, ge=60, le=130)
    estimated_lines_per_page: int = Field(default=50, ge=35, le=70)

    @model_validator(mode="after")
    def _validate_min_max(self) -> "DensitySpec":
        if self.min_role_bullets > self.max_role_bullets:
            raise ValueError("min_role_bullets cannot exceed max_role_bullets")
        if self.min_project_bullets > self.max_project_bullets:
            raise ValueError("min_project_bullets cannot exceed max_project_bullets")
        if self.min_skills > self.max_skills:
            raise ValueError("min_skills cannot exceed max_skills")
        return self


class PresentationConfig(BaseModel):
    schema_version: int = 1
    document: DocumentSpec = Field(default_factory=DocumentSpec)
    layout: LayoutSpec = Field(default_factory=LayoutSpec)
    density: DensitySpec = Field(default_factory=DensitySpec)


class PresentationLine(BaseModel):
    text: str
    evidence_refs: list[str] = Field(min_length=1)


class PresentationExperienceItem(BaseModel):
    organization: str
    title: str
    period: str
    evidence_refs: list[str] = Field(min_length=1)
    bullets: list[PresentationLine]


class PresentationProjectItem(BaseModel):
    name: str
    evidence_refs: list[str] = Field(min_length=1)
    bullets: list[PresentationLine]


class CVPresentationModel(BaseModel):
    schema_version: int = 1
    source_cv_hash: str
    config_hash: str
    candidate: CandidateIdentity
    language: str
    target_role: str
    headline: PresentationLine
    summary: PresentationLine
    experience: list[PresentationExperienceItem]
    projects: list[PresentationProjectItem] = Field(default_factory=list)
    skills: list[PresentationLine] = Field(default_factory=list)
    education: list[PresentationLine] = Field(default_factory=list)
    certifications: list[PresentationLine] = Field(default_factory=list)
    document: DocumentSpec
    layout: LayoutSpec
    density: DensitySpec


class FittingOmission(BaseModel):
    section: SectionKey
    item_index: int | None = None
    bullet_index: int | None = None
    reason: str
    evidence_refs: list[str] = Field(default_factory=list)


class FitReport(BaseModel):
    schema_version: int = 1
    status: FitStatus
    source_cv_hash: str
    config_hash: str
    estimated_line_units_before: int
    estimated_line_units_after: int
    estimated_line_budget: int
    summary_word_count: int
    omissions: list[FittingOmission] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
