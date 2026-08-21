from __future__ import annotations

import re
from typing import Any, Iterable

from cv_agent.schemas import CVDocument, HeadhunterReview, QualityGateResult, ValidationIssue, ValidationResult


QUANTIFIED_RE = re.compile(r"(?:\b\d+(?:[.,]\d+)?\s*%|\b\d+(?:[.,]\d+)?\s*[xX]\b|\bMXN\b|\bUSD\b|\$\s*\d|\b\d+\s*->\s*\d+)")
EN_MARKERS = {"the", "and", "with", "for", "led", "built", "developed", "designed", "improved", "model", "data", "business", "production"}
ES_MARKERS = {"el", "la", "los", "las", "con", "para", "lideró", "desarrolló", "diseñó", "mejoró", "modelo", "datos", "negocio", "producción"}
EXPERT_TERMS = {"expert", "expertise", "advanced", "mastery", "experto", "experta", "dominio avanzado"}


def _all_evidence_lines(cv: CVDocument) -> list[tuple[str, Any]]:
    values: list[tuple[str, Any]] = [("headline", cv.headline), ("summary", cv.summary)]
    for i, item in enumerate(cv.experience):
        values.append((f"experience[{i}].identity", item))
        values.extend((f"experience[{i}].bullets[{j}]", bullet) for j, bullet in enumerate(item.bullets))
    for i, item in enumerate(cv.projects):
        values.append((f"projects[{i}].identity", item))
        values.extend((f"projects[{i}].bullets[{j}]", bullet) for j, bullet in enumerate(item.bullets))
    values.extend((f"skills[{i}]", line) for i, line in enumerate(cv.skills))
    values.extend((f"education[{i}]", line) for i, line in enumerate(cv.education))
    values.extend((f"certifications[{i}]", line) for i, line in enumerate(cv.certifications))
    return values


def _text_for_line(line: Any) -> str:
    if hasattr(line, "text"):
        return str(line.text)
    if hasattr(line, "organization"):
        return f"{line.organization} {line.title} {line.period}"
    if hasattr(line, "name"):
        return str(line.name)
    return ""


def _refs_for_line(line: Any) -> list[str]:
    return list(getattr(line, "evidence_refs", []) or [])


def validate_claims(
    cv: CVDocument,
    evidence_catalog: dict[str, dict[str, Any]],
    allowed_evidence_ids: Iterable[str],
) -> ValidationResult:
    allowed = set(allowed_evidence_ids)
    issues: list[ValidationIssue] = []

    for location, line in _all_evidence_lines(cv):
        text = _text_for_line(line)
        refs = _refs_for_line(line)
        if not refs:
            issues.append(ValidationIssue(code="missing_evidence_ref", message="CV claim has no evidence reference.", location=location))
            continue
        unknown = [ref for ref in refs if ref not in evidence_catalog]
        if unknown:
            issues.append(ValidationIssue(code="unknown_evidence_ref", message=f"Unknown evidence refs: {unknown}", location=location))
            continue
        outside = [ref for ref in refs if ref not in allowed]
        if outside:
            issues.append(ValidationIssue(code="evidence_outside_match", message=f"Evidence was not selected for this vacancy: {outside}", location=location))
        ineligible = [ref for ref in refs if not evidence_catalog[ref].get("cv_eligible")]
        if ineligible:
            issues.append(ValidationIssue(code="ineligible_evidence", message=f"Evidence is not eligible for automatic CV reuse: {ineligible}", location=location))

        if location.startswith(("summary", "experience", "projects")) and QUANTIFIED_RE.search(text):
            metric_refs = [ref for ref in refs if evidence_catalog[ref].get("chunk_type") == "achievement_metric"]
            if not metric_refs:
                issues.append(ValidationIssue(code="quantified_claim_without_metric", message="Quantified claim requires an approved ACH-* metric evidence chunk.", location=location))

        lowered = text.casefold()
        for ref in refs:
            chunk = evidence_catalog.get(ref, {})
            if (chunk.get("proficiency") or "").casefold() == "familiarity" and any(term in lowered for term in EXPERT_TERMS):
                issues.append(ValidationIssue(code="proficiency_escalation", message=f"Familiarity evidence {ref} cannot support expert/advanced wording.", location=location))

    return ValidationResult(status="PASS" if not issues else "FAIL", issues=issues)


def _cv_text(cv: CVDocument) -> str:
    parts = [cv.target_role, cv.headline.text, cv.summary.text]
    for item in cv.experience:
        parts.extend([item.organization, item.title, item.period])
        parts.extend(bullet.text for bullet in item.bullets)
    for item in cv.projects:
        parts.append(item.name)
        parts.extend(bullet.text for bullet in item.bullets)
    parts.extend(line.text for line in cv.skills + cv.education + cv.certifications)
    return " ".join(parts)


def validate_language(cv: CVDocument, expected_language: str) -> ValidationResult:
    issues: list[ValidationIssue] = []
    if expected_language == "und":
        return ValidationResult(status="WARN", issues=[ValidationIssue(code="language_undetermined", message="Application language is undetermined; generation should normally be blocked.")])
    if cv.language != expected_language:
        issues.append(ValidationIssue(code="language_code_mismatch", message=f"CV language={cv.language!r} but vacancy requires {expected_language!r}."))

    words = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", _cv_text(cv).casefold())
    en = sum(word in EN_MARKERS for word in words)
    es = sum(word in ES_MARKERS for word in words)
    if expected_language == "en" and es >= en + 4:
        issues.append(ValidationIssue(code="language_content_mismatch", message="CV content appears predominantly Spanish although English is required."))
    if expected_language == "es" and en >= es + 4:
        issues.append(ValidationIssue(code="language_content_mismatch", message="CV content appears predominantly English although Spanish is required."))
    return ValidationResult(status="PASS" if not issues else "FAIL", issues=issues)


def validate_structure(cv: CVDocument) -> ValidationResult:
    issues: list[ValidationIssue] = []
    if not cv.experience:
        issues.append(ValidationIssue(code="missing_experience", message="CV must include professional experience."))
    bullet_count = sum(len(item.bullets) for item in cv.experience) + sum(len(item.bullets) for item in cv.projects)
    if bullet_count < 3:
        issues.append(ValidationIssue(code="too_few_bullets", message="CV needs at least three evidence-grounded accomplishment/ownership bullets."))
    if bullet_count > 18:
        issues.append(ValidationIssue(code="too_many_bullets", message="CV is too verbose for the target compact format."))
    return ValidationResult(status="PASS" if not issues else "FAIL", issues=issues)


def quality_gate(
    review: HeadhunterReview,
    factual: ValidationResult,
    language: ValidationResult,
    structure: ValidationResult,
) -> QualityGateResult:
    reasons: list[str] = []
    if review.decision != "PASS":
        reasons.append("headhunter_decision_not_pass")
    if review.overall_score < 92:
        reasons.append("overall_score_below_92")
    if review.scores.vacancy_alignment < 90:
        reasons.append("vacancy_alignment_below_90")
    if review.scores.evidence_strength < 95:
        reasons.append("evidence_strength_below_95")
    if review.scores.language_quality < 95:
        reasons.append("language_quality_below_95")
    if review.blocking_issues:
        reasons.append("blocking_issues_present")
    if factual.status != "PASS":
        reasons.append("factual_validation_failed")
    if language.status != "PASS":
        reasons.append("language_validation_failed")
    if structure.status != "PASS":
        reasons.append("structure_validation_failed")
    return QualityGateResult(passed=not reasons, reasons=reasons)
