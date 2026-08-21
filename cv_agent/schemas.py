from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class StrategyOutput(BaseModel):
    target_role: str
    language: str
    positioning: str
    selected_evidence_chunk_ids: list[str]
    selected_metric_ids: list[str] = Field(default_factory=list)
    selected_skills: list[str] = Field(default_factory=list)
    coverage_gaps: list[str] = Field(default_factory=list)
    omit: list[str] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)


class CVBullet(BaseModel):
    text: str
    evidence_refs: list[str] = Field(min_length=1)


class CVExperienceItem(BaseModel):
    organization: str
    title: str
    period: str
    bullets: list[CVBullet]


class CVProjectItem(BaseModel):
    name: str
    bullets: list[CVBullet]


class CVDocument(BaseModel):
    language: str
    target_role: str
    headline: str
    summary: CVBullet
    experience: list[CVExperienceItem]
    projects: list[CVProjectItem] = Field(default_factory=list)
    skills: list[str]
    education: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)


class ReviewScores(BaseModel):
    vacancy_alignment: int = Field(ge=0, le=100)
    opening_impact: int = Field(ge=0, le=100)
    evidence_strength: int = Field(ge=0, le=100)
    specificity: int = Field(ge=0, le=100)
    seniority_signal: int = Field(ge=0, le=100)
    ats_clarity: int = Field(ge=0, le=100)
    language_quality: int = Field(ge=0, le=100)
    conciseness: int = Field(ge=0, le=100)


class ReviewIssue(BaseModel):
    section: str
    problem: str
    required_change: str


class HeadhunterReview(BaseModel):
    decision: Literal["PASS", "REVISE"]
    overall_score: int = Field(ge=0, le=100)
    scores: ReviewScores
    blocking_issues: list[ReviewIssue] = Field(default_factory=list)
    optional_improvements: list[str] = Field(default_factory=list)
    rationale: str


class ValidationIssue(BaseModel):
    code: str
    message: str
    location: str | None = None


class ValidationResult(BaseModel):
    status: Literal["PASS", "FAIL", "WARN"]
    issues: list[ValidationIssue] = Field(default_factory=list)


class QualityGateResult(BaseModel):
    passed: bool
    reasons: list[str]
