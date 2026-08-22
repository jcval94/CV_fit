from __future__ import annotations

import re
from typing import Any

from cv_agent.schemas import CVDocument, ValidationIssue, ValidationResult


MAX_SKILLS = 15
MAX_PROJECTS = 2
MAX_CERTIFICATIONS = 5

IDENTITY_MARKERS = (
    "lead data scientist",
    "senior data scientist",
    "machine learning engineer",
    "ai/ml engineer",
    "científico de datos senior",
    "cientifica de datos senior",
    "ingeniero de machine learning",
    "ingeniera de machine learning",
    "ingeniero de ia/ml",
    "ingeniera de ia/ml",
)

MANDATORY_CERTIFICATION_MARKERS = {
    "bourbaki": ("bourbaki", "genai aplicado"),
    "scrum_master": ("professional scrum master", "scrum master i"),
    "harvard_cs50": ("cs50", "introduction to computer science"),
}

GENAI_MARKERS = ("genai", "generative ai", "ia generativa")
FORBIDDEN_EMPLOYER_FACING_PATTERNS = (
    r"evidence unavailable",
    r"evidence not available",
    r"not provided in supplied evidence",
    r"information unavailable",
    r"información no disponible",
    r"evidencia no disponible",
)

EDITORIAL_ANCHOR_TITLES = {
    "LLM Application Design",
    "CERT-PSM-I-2020",
    "CERT-CS50-HARVARDX-2020",
    "GenAI Aplicado: ChatGPT & Gemini",
}
EDITORIAL_ANCHOR_RECORD_IDS = {"cert-bourbaki-genai-2026"}


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()


def _is_public_cv_evidence(chunk: dict[str, Any]) -> bool:
    return bool(chunk.get("cv_eligible")) and bool(chunk.get("public_safe"))


def select_editorial_anchor_evidence(catalog: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Return sticky evidence needed by the user's stable editorial policy.

    These anchors do not imply vacancy fit. They only make stable GenAI and
    mandatory certification evidence available to the Writer/Reviser so those
    sections can satisfy deterministic editorial requirements without inventing
    claims or relying on semantic top-k retrieval.
    """
    selected: list[dict[str, Any]] = []
    for chunk in catalog.values():
        if not _is_public_cv_evidence(chunk):
            continue
        title = str(chunk.get("title") or "")
        record_id = str(chunk.get("record_id") or "")
        text = str(chunk.get("text") or "")
        if title in EDITORIAL_ANCHOR_TITLES or record_id in EDITORIAL_ANCHOR_RECORD_IDS:
            selected.append(chunk)
            continue
        if record_id == "certifications" and any(
            marker in text
            for marker in ("Professional Scrum Master I", "CS50's Introduction to Computer Science")
        ):
            selected.append(chunk)
    selected.sort(key=lambda item: (str(item.get("record_id") or ""), str(item.get("chunk_id") or "")))
    return selected


def _all_text(cv: CVDocument) -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = [
        ("target_role", cv.target_role),
        ("headline", cv.headline.text),
        ("summary", cv.summary.text),
    ]
    for i, item in enumerate(cv.experience):
        values.extend([
            (f"experience[{i}].organization", item.organization),
            (f"experience[{i}].title", item.title),
            (f"experience[{i}].period", item.period),
        ])
        values.extend((f"experience[{i}].bullets[{j}]", bullet.text) for j, bullet in enumerate(item.bullets))
    for i, item in enumerate(cv.projects):
        values.append((f"projects[{i}].name", item.name))
        values.extend((f"projects[{i}].bullets[{j}]", bullet.text) for j, bullet in enumerate(item.bullets))
    values.extend((f"skills[{i}]", line.text) for i, line in enumerate(cv.skills))
    values.extend((f"education[{i}]", line.text) for i, line in enumerate(cv.education))
    values.extend((f"certifications[{i}]", line.text) for i, line in enumerate(cv.certifications))
    return values


def _has_bbva_progression(cv: CVDocument) -> bool:
    bbva_items = [item for item in cv.experience if "bbva" in _norm(item.organization)]
    if len(bbva_items) >= 2:
        return len({_norm(item.title) for item in bbva_items}) >= 2
    if not bbva_items:
        return False
    combined = " ".join(
        [bbva_items[0].title] + [bullet.text for bullet in bbva_items[0].bullets]
    ).casefold()
    markers = ("expert", "associate", "analyst", "senior")
    return sum(marker in combined for marker in markers) >= 2


def validate_editorial_policy(cv: CVDocument) -> ValidationResult:
    issues: list[ValidationIssue] = []

    identity_text = _norm(f"{cv.target_role} {cv.headline.text}")
    if not any(marker in identity_text for marker in IDENTITY_MARKERS):
        issues.append(ValidationIssue(
            code="identity_outside_canonical_family",
            message="Primary identity must remain within Lead/Senior Data Scientist, Machine Learning Engineer or AI/ML Engineer.",
            location="headline",
        ))

    bbva_indices = [i for i, item in enumerate(cv.experience) if "bbva" in _norm(item.organization)]
    ms_indices = [i for i, item in enumerate(cv.experience) if "management solutions" in _norm(item.organization)]
    if not bbva_indices:
        issues.append(ValidationIssue(code="bbva_missing", message="BBVA must remain in the professional chronology.", location="experience"))
    if not ms_indices:
        issues.append(ValidationIssue(code="management_solutions_missing", message="Management Solutions must remain in the professional chronology.", location="experience"))
    if bbva_indices and ms_indices and min(ms_indices) <= max(bbva_indices):
        issues.append(ValidationIssue(
            code="management_solutions_order",
            message="Management Solutions must appear below all BBVA chronology entries.",
            location="experience",
        ))
    if bbva_indices and not _has_bbva_progression(cv):
        issues.append(ValidationIssue(
            code="bbva_progression_missing",
            message="BBVA must show relevant progression rather than a single flattened stage.",
            location="experience",
        ))

    if len(cv.projects) > MAX_PROJECTS:
        issues.append(ValidationIssue(code="too_many_projects", message=f"Selected projects must be <= {MAX_PROJECTS}.", location="projects"))
    if len(cv.skills) > MAX_SKILLS:
        issues.append(ValidationIssue(code="too_many_skills", message=f"Skills must be <= {MAX_SKILLS} and vacancy-relevant.", location="skills"))

    skill_text = " ".join(line.text for line in cv.skills).casefold()
    if not any(marker in skill_text for marker in GENAI_MARKERS):
        issues.append(ValidationIssue(code="genai_skill_missing", message="Skills must always include an explicit GenAI / Generative AI capability.", location="skills"))

    cert_text = " ".join(line.text for line in cv.certifications).casefold()
    for label, markers in MANDATORY_CERTIFICATION_MARKERS.items():
        if not any(marker in cert_text for marker in markers):
            issues.append(ValidationIssue(
                code=f"mandatory_certification_missing_{label}",
                message=f"Mandatory certification {label} is missing from the CV.",
                location="certifications",
            ))
    if len(cv.certifications) > MAX_CERTIFICATIONS:
        issues.append(ValidationIssue(
            code="too_many_certifications",
            message=f"Certifications must stay concise: mandatory three plus at most {MAX_CERTIFICATIONS - 3} vacancy-relevant extras.",
            location="certifications",
        ))

    if not cv.education:
        issues.append(ValidationIssue(code="education_missing", message="Education is a required senior-CV section.", location="education"))
    if not cv.skills:
        issues.append(ValidationIssue(code="skills_missing", message="Skills section cannot be empty.", location="skills"))
    if not cv.certifications:
        issues.append(ValidationIssue(code="certifications_missing", message="Certifications section cannot be empty.", location="certifications"))

    for location, text in _all_text(cv):
        if not text.strip():
            issues.append(ValidationIssue(code="empty_employer_facing_field", message="Employer-facing fields may not be empty.", location=location))
            continue
        lowered = text.casefold()
        for pattern in FORBIDDEN_EMPLOYER_FACING_PATTERNS:
            if re.search(pattern, lowered):
                issues.append(ValidationIssue(
                    code="diagnostic_language_exposed",
                    message="Internal evidence/availability diagnostics must never appear in employer-facing CV content.",
                    location=location,
                ))
                break

    return ValidationResult(status="PASS" if not issues else "FAIL", issues=issues)
