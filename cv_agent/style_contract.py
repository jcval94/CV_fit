from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from cv_agent.schemas import CVDocument, ValidationIssue, ValidationResult


StyleOwner = Literal["strategist", "writer", "validator", "reviser", "headhunter"]
StyleSeverity = Literal["hard", "advisory"]

MAX_SUMMARY_WORDS = 70
MAX_BULLET_WORDS = 38


@dataclass(frozen=True)
class StyleRule:
    code: str
    severity: StyleSeverity
    primary_owner: StyleOwner
    repair_owner: StyleOwner
    description: str


STYLE_RULES: tuple[StyleRule, ...] = (
    StyleRule(
        code="third_person_candidate_voice",
        severity="hard",
        primary_owner="writer",
        repair_owner="reviser",
        description="Employer-facing narrative must not refer to the candidate in third person.",
    ),
    StyleRule(
        code="explicit_first_person_pronoun",
        severity="hard",
        primary_owner="writer",
        repair_owner="reviser",
        description="Resume prose uses implied first person; personal pronouns are omitted.",
    ),
    StyleRule(
        code="weak_responsibility_opener",
        severity="hard",
        primary_owner="writer",
        repair_owner="reviser",
        description="Bullets must open with action/ownership, not responsibility labels or weak participation phrases.",
    ),
    StyleRule(
        code="summary_too_long",
        severity="hard",
        primary_owner="writer",
        repair_owner="reviser",
        description=f"Summary must remain concise at no more than {MAX_SUMMARY_WORDS} words.",
    ),
    StyleRule(
        code="bullet_too_long",
        severity="hard",
        primary_owner="writer",
        repair_owner="reviser",
        description=f"A single bullet must remain scannable at no more than {MAX_BULLET_WORDS} words.",
    ),
    StyleRule(
        code="mixed_bullet_punctuation",
        severity="hard",
        primary_owner="writer",
        repair_owner="reviser",
        description="Bullets within the same experience/project block use one terminal-punctuation convention.",
    ),
    StyleRule(
        code="repeated_leading_verb",
        severity="advisory",
        primary_owner="writer",
        repair_owner="reviser",
        description="Avoid repetitive leading verbs when stronger accurate alternatives exist.",
    ),
    StyleRule(
        code="content_priority",
        severity="advisory",
        primary_owner="strategist",
        repair_owner="reviser",
        description="The strongest vacancy-relevant impact should appear before weaker responsibilities or projects.",
    ),
    StyleRule(
        code="narrative_redundancy",
        severity="advisory",
        primary_owner="writer",
        repair_owner="reviser",
        description="Summary, headline, skills and experience should add information rather than repeat one another.",
    ),
    StyleRule(
        code="keyword_stuffing",
        severity="advisory",
        primary_owner="strategist",
        repair_owner="reviser",
        description="Vacancy language should be used only where evidence supports a natural claim.",
    ),
)

RULE_BY_CODE = {rule.code: rule for rule in STYLE_RULES}

THIRD_PERSON_START_RE = re.compile(
    r"^\s*(?:he|she|his|her|the candidate|this candidate|mr\.?\s+|ms\.?\s+|"
    r"él|ella|el candidato|la candidata|este candidato|esta candidata)\b",
    re.IGNORECASE,
)
FIRST_PERSON_START_RE = re.compile(
    r"^\s*(?:i|i'm|i’ve|i've|my|me|we|our|yo|mi|mis|me|nosotros|nosotras|nuestro|nuestra|nuestros|nuestras)\b",
    re.IGNORECASE,
)
WEAK_OPENER_RE = re.compile(
    r"^\s*(?:responsible for|in charge of|tasked with|worked on|helped with|participated in|"
    r"responsable de|encargad[oa] de|a cargo de|trabaj[ée] en|ayud[ée] (?:a|con)|particip[ée] en)\b",
    re.IGNORECASE,
)
WORD_RE = re.compile(r"\b[\wÀ-ÿ+#./-]+\b", re.UNICODE)
LEADING_WORD_RE = re.compile(r"^\s*([A-Za-zÀ-ÿ]+)")


def _word_count(text: str) -> int:
    return len(WORD_RE.findall(text))


def _narrative_lines(cv: CVDocument) -> list[tuple[str, str, bool]]:
    lines: list[tuple[str, str, bool]] = [
        ("summary", cv.summary.text, False),
    ]
    for i, item in enumerate(cv.experience):
        for j, bullet in enumerate(item.bullets):
            lines.append((f"experience[{i}].bullets[{j}]", bullet.text, True))
    for i, item in enumerate(cv.projects):
        for j, bullet in enumerate(item.bullets):
            lines.append((f"projects[{i}].bullets[{j}]", bullet.text, True))
    return lines


def _punctuation_issue(block: str, bullets: list[str]) -> ValidationIssue | None:
    if len(bullets) < 2:
        return None
    terminal_period = [text.rstrip().endswith(".") for text in bullets]
    if any(terminal_period) and not all(terminal_period):
        return ValidationIssue(
            code="mixed_bullet_punctuation",
            message="Bullets in the same block mix terminal-period conventions; use one convention consistently.",
            location=block,
        )
    return None


def validate_resume_style(cv: CVDocument) -> ValidationResult:
    """Validate deterministic, high-confidence resume-writing rules.

    Only HARD rules fail the CV. More subjective style concerns remain with the
    Strategist/Headhunter rather than turning brittle heuristics into blockers.
    """

    issues: list[ValidationIssue] = []

    summary_words = _word_count(cv.summary.text)
    if summary_words > MAX_SUMMARY_WORDS:
        issues.append(ValidationIssue(
            code="summary_too_long",
            message=f"Summary has {summary_words} words; maximum is {MAX_SUMMARY_WORDS}.",
            location="summary",
        ))

    for location, text, is_bullet in _narrative_lines(cv):
        if THIRD_PERSON_START_RE.search(text):
            issues.append(ValidationIssue(
                code="third_person_candidate_voice",
                message="CV narrative must use implied first person, not third-person candidate references.",
                location=location,
            ))
        if FIRST_PERSON_START_RE.search(text):
            issues.append(ValidationIssue(
                code="explicit_first_person_pronoun",
                message="CV narrative must use implied first person and omit explicit personal pronouns.",
                location=location,
            ))
        if is_bullet and WEAK_OPENER_RE.search(text):
            issues.append(ValidationIssue(
                code="weak_responsibility_opener",
                message="Start bullets with a concrete action/ownership verb rather than a responsibility or participation phrase.",
                location=location,
            ))
        if is_bullet:
            words = _word_count(text)
            if words > MAX_BULLET_WORDS:
                issues.append(ValidationIssue(
                    code="bullet_too_long",
                    message=f"Bullet has {words} words; maximum is {MAX_BULLET_WORDS} for scanability.",
                    location=location,
                ))

    for i, item in enumerate(cv.experience):
        issue = _punctuation_issue(
            f"experience[{i}].bullets",
            [bullet.text for bullet in item.bullets],
        )
        if issue:
            issues.append(issue)
    for i, item in enumerate(cv.projects):
        issue = _punctuation_issue(
            f"projects[{i}].bullets",
            [bullet.text for bullet in item.bullets],
        )
        if issue:
            issues.append(issue)

    return ValidationResult(status="PASS" if not issues else "FAIL", issues=issues)


def collect_style_advisories(cv: CVDocument) -> list[ValidationIssue]:
    """Return useful non-blocking style signals for future review/observability."""

    issues: list[ValidationIssue] = []
    leading: list[tuple[str, str]] = []
    for location, text, is_bullet in _narrative_lines(cv):
        if not is_bullet:
            continue
        match = LEADING_WORD_RE.search(text)
        if match:
            leading.append((location, match.group(1).casefold()))

    counts: dict[str, int] = {}
    for _, verb in leading:
        counts[verb] = counts.get(verb, 0) + 1
    repeated = {verb for verb, count in counts.items() if count >= 3}
    for location, verb in leading:
        if verb in repeated:
            issues.append(ValidationIssue(
                code="repeated_leading_verb",
                message=f"Leading verb {verb!r} is repeated at least three times; vary wording only when evidence permits.",
                location=location,
            ))
    return issues
