from __future__ import annotations

import math

from cv_presentation.schemas import CVPresentationModel, FitReport, FittingOmission


STICKY_CERT_MARKERS = ("bourbaki", "professional scrum master", "cs50")
STICKY_GENAI_MARKERS = ("genai", "generative ai", "ia generativa")


def _text_lines(text: str, chars_per_line: int) -> int:
    return max(1, math.ceil(max(len(text.strip()), 1) / chars_per_line))


def _is_sticky_cert(text: str) -> bool:
    lowered = text.casefold()
    return any(marker in lowered for marker in STICKY_CERT_MARKERS)


def _is_genai_skill(text: str) -> bool:
    lowered = text.casefold()
    return any(marker in lowered for marker in STICKY_GENAI_MARKERS)


def estimate_line_units(model: CVPresentationModel) -> int:
    chars = model.density.estimated_chars_per_line
    lines = 0

    lines += 2 + _text_lines(model.headline.text, chars)
    contact_values = [
        model.candidate.location,
        model.candidate.email,
        model.candidate.phone,
        model.candidate.linkedin,
        model.candidate.github,
        model.candidate.website,
    ]
    contact_count = sum(bool(value) for value in contact_values)
    if contact_count:
        lines += max(1, math.ceil(contact_count / 3))

    section_modes = model.layout.section_modes
    if section_modes["summary"] != "never":
        lines += 1 + _text_lines(model.summary.text, chars)
    if section_modes["experience"] != "never":
        lines += 1
        for item in model.experience:
            lines += 2
            lines += sum(1 + _text_lines(bullet.text, chars) for bullet in item.bullets)
    if section_modes["education"] != "never" and model.education:
        lines += 1 + sum(_text_lines(item.text, chars) for item in model.education)
    if section_modes["projects"] != "never" and model.projects:
        lines += 1
        for item in model.projects:
            lines += 1
            lines += sum(1 + _text_lines(bullet.text, chars) for bullet in item.bullets)
    if section_modes["skills"] != "never" and model.skills:
        lines += 1 + sum(_text_lines(item.text, chars) for item in model.skills)
    if section_modes["certifications"] != "never" and model.certifications:
        lines += 1 + sum(_text_lines(item.text, chars) for item in model.certifications)
    return lines


def _drop_tail(items: list, keep: int, *, section: str, reason: str, omissions: list[FittingOmission]) -> list:
    if len(items) <= keep:
        return items
    kept = list(items[:keep])
    for index, item in enumerate(items[keep:], start=keep):
        omissions.append(FittingOmission(
            section=section,
            item_index=index,
            reason=reason,
            evidence_refs=list(getattr(item, "evidence_refs", [])),
        ))
    return kept


def _limit_skills(items: list, keep: int, omissions: list[FittingOmission]) -> list:
    if len(items) <= keep:
        return items
    sticky = [item for item in items if _is_genai_skill(item.text)]
    remaining = [item for item in items if not _is_genai_skill(item.text)]
    selected = (sticky[:1] + remaining)[:keep]
    selected_ids = {id(item) for item in selected}
    for index, item in enumerate(items):
        if id(item) not in selected_ids:
            omissions.append(FittingOmission(
                section="skills",
                item_index=index,
                reason="exceeds max_skills; lower-priority non-GenAI skill omitted",
                evidence_refs=list(item.evidence_refs),
            ))
    return selected


def _limit_certifications(items: list, keep: int, omissions: list[FittingOmission]) -> list:
    sticky = [item for item in items if _is_sticky_cert(item.text)]
    optional = [item for item in items if not _is_sticky_cert(item.text)]
    selected = sticky + optional[: max(0, keep - len(sticky))]
    selected_ids = {id(item) for item in selected}
    for index, item in enumerate(items):
        if id(item) not in selected_ids:
            omissions.append(FittingOmission(
                section="certifications",
                item_index=index,
                reason="exceeds certification budget; optional tail credential omitted",
                evidence_refs=list(item.evidence_refs),
            ))
    return selected


def _remove_last_nonsticky_skill(model: CVPresentationModel, omissions: list[FittingOmission]) -> bool:
    for index in range(len(model.skills) - 1, -1, -1):
        item = model.skills[index]
        if _is_genai_skill(item.text):
            continue
        removed = model.skills.pop(index)
        omissions.append(FittingOmission(
            section="skills",
            item_index=index,
            reason="lower-priority skill removed before projects/experience to satisfy page budget",
            evidence_refs=list(removed.evidence_refs),
        ))
        return True
    return False


def _remove_last_optional_cert(model: CVPresentationModel, omissions: list[FittingOmission]) -> bool:
    for index in range(len(model.certifications) - 1, -1, -1):
        item = model.certifications[index]
        if _is_sticky_cert(item.text):
            continue
        removed = model.certifications.pop(index)
        omissions.append(FittingOmission(
            section="certifications",
            item_index=index,
            reason="optional certification removed first to satisfy page budget",
            evidence_refs=list(removed.evidence_refs),
        ))
        return True
    return False


def fit_presentation_model(model: CVPresentationModel) -> tuple[CVPresentationModel, FitReport]:
    fitted = model.model_copy(deep=True)
    omissions: list[FittingOmission] = []
    reasons: list[str] = []
    notes = [
        "Estimated line units are a pre-render heuristic; Chromium physical-layout validation remains authoritative for final page count.",
        "The fitter never rewrites or truncates claim text; it only selects already-approved ordered content.",
        "Editorial pruning order is certifications -> non-GenAI skills -> projects -> lower-priority experience bullets; education and mandatory career continuity are preserved.",
    ]
    before = estimate_line_units(fitted)
    density = fitted.density
    modes = fitted.layout.section_modes

    for section in ("projects", "skills", "education", "certifications"):
        if modes[section] == "never":
            values = list(getattr(fitted, section))
            for index, item in enumerate(values):
                omissions.append(FittingOmission(
                    section=section,
                    item_index=index,
                    reason="section disabled by presentation configuration",
                    evidence_refs=list(getattr(item, "evidence_refs", [])),
                ))
            setattr(fitted, section, [])

    for role_index, role in enumerate(fitted.experience):
        if len(role.bullets) > density.max_role_bullets:
            for bullet_index, bullet in enumerate(role.bullets[density.max_role_bullets:], start=density.max_role_bullets):
                omissions.append(FittingOmission(
                    section="experience",
                    item_index=role_index,
                    bullet_index=bullet_index,
                    reason="exceeds max_role_bullets; tail bullets are lower presentation priority",
                    evidence_refs=list(bullet.evidence_refs),
                ))
            role.bullets = role.bullets[:density.max_role_bullets]

    if modes["projects"] != "never":
        fitted.projects = _drop_tail(
            fitted.projects,
            density.max_projects,
            section="projects",
            reason="exceeds max_projects; tail projects are lower presentation priority",
            omissions=omissions,
        )
        for project_index, project in enumerate(fitted.projects):
            if len(project.bullets) > density.max_project_bullets:
                for bullet_index, bullet in enumerate(project.bullets[density.max_project_bullets:], start=density.max_project_bullets):
                    omissions.append(FittingOmission(
                        section="projects",
                        item_index=project_index,
                        bullet_index=bullet_index,
                        reason="exceeds max_project_bullets; tail bullets are lower presentation priority",
                        evidence_refs=list(bullet.evidence_refs),
                    ))
                project.bullets = project.bullets[:density.max_project_bullets]

    if modes["skills"] != "never":
        fitted.skills = _limit_skills(fitted.skills, density.max_skills, omissions)
    if modes["education"] != "never":
        fitted.education = _drop_tail(
            fitted.education,
            density.max_education,
            section="education",
            reason="exceeds max_education; tail education items are lower presentation priority",
            omissions=omissions,
        )
    if modes["certifications"] != "never":
        fitted.certifications = _limit_certifications(fitted.certifications, density.max_certifications, omissions)

    budget = fitted.document.target_pages * density.estimated_lines_per_page

    def over_budget() -> bool:
        return estimate_line_units(fitted) > budget

    # Respect the user's hierarchy: Experience > Education > Projects > Skills > Certifications.
    while over_budget() and _remove_last_optional_cert(fitted, omissions):
        pass

    while over_budget() and len(fitted.skills) > density.min_skills:
        if not _remove_last_nonsticky_skill(fitted, omissions):
            break

    if modes["projects"] == "auto":
        changed = True
        while over_budget() and changed:
            changed = False
            for project_index in range(len(fitted.projects) - 1, -1, -1):
                project = fitted.projects[project_index]
                if len(project.bullets) > density.min_project_bullets:
                    bullet_index = len(project.bullets) - 1
                    bullet = project.bullets.pop()
                    omissions.append(FittingOmission(
                        section="projects",
                        item_index=project_index,
                        bullet_index=bullet_index,
                        reason="lower-priority project bullet removed after optional skills/certifications to satisfy page budget",
                        evidence_refs=list(bullet.evidence_refs),
                    ))
                    changed = True
                    if not over_budget():
                        break
        while over_budget() and fitted.projects:
            index = len(fitted.projects) - 1
            project = fitted.projects.pop()
            omissions.append(FittingOmission(
                section="projects",
                item_index=index,
                reason="optional project removed to satisfy estimated page budget",
                evidence_refs=list(project.evidence_refs),
            ))

    changed = True
    while over_budget() and changed:
        changed = False
        for role_index in range(len(fitted.experience) - 1, -1, -1):
            role = fitted.experience[role_index]
            if len(role.bullets) > density.min_role_bullets:
                bullet_index = len(role.bullets) - 1
                bullet = role.bullets.pop()
                omissions.append(FittingOmission(
                    section="experience",
                    item_index=role_index,
                    bullet_index=bullet_index,
                    reason="lowest-priority experience bullet removed only after lower editorial-priority sections",
                    evidence_refs=list(bullet.evidence_refs),
                ))
                changed = True
                if not over_budget():
                    break

    summary_words = len(fitted.summary.text.split())
    after = estimate_line_units(fitted)
    if summary_words > density.max_summary_words:
        reasons.append(
            f"summary_word_limit_exceeded:{summary_words}>{density.max_summary_words}; rewrite must happen upstream because fitter does not truncate claims"
        )
    if after > budget:
        reasons.append(f"estimated_line_budget_exceeded:{after}>{budget}")
    if not any(_is_genai_skill(item.text) for item in fitted.skills):
        reasons.append("mandatory_genai_skill_missing_after_fit")
    for marker in STICKY_CERT_MARKERS:
        if not any(marker in item.text.casefold() for item in fitted.certifications):
            reasons.append(f"mandatory_certification_missing_after_fit:{marker}")

    report = FitReport(
        status="FIT" if not reasons else "NEEDS_REVISION",
        source_cv_hash=fitted.source_cv_hash,
        config_hash=fitted.config_hash,
        estimated_line_units_before=before,
        estimated_line_units_after=after,
        estimated_line_budget=budget,
        summary_word_count=summary_words,
        omissions=omissions,
        reasons=reasons,
        notes=notes,
    )
    return fitted, report
