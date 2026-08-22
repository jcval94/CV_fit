from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from cv_agent.adk_runtime import AdkStructuredClient
from cv_presentation.branding import resolve_brand_profile, tokens_from_brand, validate_design_tokens
from cv_presentation.build import build_presentation_model, load_cv_document
from cv_presentation.design_agent import DesignReview, review_design
from cv_presentation.fit import fit_presentation_model
from cv_presentation.identity import resolve_candidate_identity
from cv_presentation.pagination import build_page_plan
from cv_presentation.physical_layout import PhysicalLayoutReport, validate_html_and_export_pdf
from cv_presentation.render_html import write_html
from cv_presentation.schemas import PresentationConfig
from cv_presentation.templates import get_template_policy


class PresentationGateBlocked(ValueError):
    """Expected product gate rejection, distinct from an internal execution error."""


class FitAttempt(BaseModel):
    attempt: int
    chars_per_line: int
    lines_per_page: int
    fit_status: str
    expected_pages: int | None = None
    physical_status: str | None = None
    physical_reasons: list[str] = Field(default_factory=list)


class TemplateBundle(BaseModel):
    template_id: str
    role: Literal["primary", "alternate"]
    html_file: str
    pdf_file: str
    screenshot_file: str
    fit_report_file: str
    design_report_file: str
    physical_report_file: str
    fit_status: str
    design_status: str
    physical_status: str
    expected_pages: int
    attempts: list[FitAttempt]


class ApplicationBundleReport(BaseModel):
    schema_version: int = 1
    vacancy_id: str
    company: str
    role_title: str
    application_url: str
    content_quality_target_reached: bool
    cover_letter_ready: bool
    primary_template: str
    alternate_template: str
    templates: list[TemplateBundle]
    ready_to_send: bool
    reasons: list[str] = Field(default_factory=list)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, BaseModel):
        payload = payload.model_dump(mode="json")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _design_for_template(
    *,
    client: AdkStructuredClient,
    template_id: str,
    company: str,
    brand_profiles_dir: Path,
) -> tuple[Any, DesignReview, Any]:
    policy = get_template_policy(template_id)
    profile = resolve_brand_profile(company=company, profiles_dir=brand_profiles_dir)
    tokens = tokens_from_brand(profile)
    deterministic = validate_design_tokens(tokens)
    if not policy.locked_visual_system and not tokens.brand_verified:
        raise PresentationGateBlocked(f"adaptive primary template requires a verified brand profile for {company!r}")
    if not policy.locked_visual_system and not deterministic.passed:
        raise PresentationGateBlocked(
            f"brand profile for {company!r} fails deterministic contrast checks: {deterministic.reasons}"
        )
    review, deterministic = asyncio.run(
        review_design(client=client, template_id=template_id, tokens=tokens, target_pages=2)
    )
    if review.decision != "PASS" or not review.ats_safe or not review.print_safe:
        raise PresentationGateBlocked(f"design review did not pass for {template_id}: {review.model_dump()}")
    return tokens, review, deterministic


def _template_attempt_profiles(template_id: str) -> list[tuple[int, int]]:
    # Later attempts deliberately make the deterministic fitter more conservative.
    # No claim text is rewritten or font size silently reduced.
    if template_id == "harvard_v1":
        return [(84, 46), (78, 43), (72, 40), (66, 37), (60, 35)]
    if "sidebar" in template_id:
        return [(84, 46), (78, 43), (72, 40), (66, 37), (60, 35)]
    return [(92, 50), (86, 47), (80, 44), (72, 40), (64, 36)]


def _render_until_physical_fit(
    *,
    cv,
    candidate,
    template_id: str,
    role: Literal["primary", "alternate"],
    output_dir: Path,
    tokens,
    design_review: DesignReview,
    deterministic_design,
) -> TemplateBundle:
    attempts: list[FitAttempt] = []
    final_fit_report = None
    final_physical: PhysicalLayoutReport | None = None
    final_expected_pages = 0

    html_path = output_dir / f"cv_{role}.html"
    pdf_path = output_dir / f"cv_{role}.pdf"
    screenshot_path = output_dir / f"cv_{role}.png"
    fit_report_path = output_dir / f"fit_report_{role}.json"
    design_report_path = output_dir / f"design_report_{role}.json"
    physical_report_path = output_dir / f"physical_layout_{role}.json"

    _write_json(design_report_path, {
        "template_id": template_id,
        "locked_visual_system": get_template_policy(template_id).locked_visual_system,
        "brand_verified": tokens.brand_verified,
        "brand_source_kind": tokens.brand_source_kind,
        "brand_source_url": tokens.brand_source_url,
        "deterministic_validation": deterministic_design.model_dump(mode="json"),
        "design_review": design_review.model_dump(mode="json"),
    })

    for attempt_number, (chars_per_line, lines_per_page) in enumerate(_template_attempt_profiles(template_id), start=1):
        config = PresentationConfig()
        config.document.template_id = template_id
        config.document.page_size = "letter"
        config.document.target_pages = 2
        config.density.estimated_chars_per_line = chars_per_line
        config.density.estimated_lines_per_page = lines_per_page
        model = build_presentation_model(cv, candidate=candidate, config=config)
        fitted, fit_report = fit_presentation_model(model)
        final_fit_report = fit_report
        expected_pages = len(build_page_plan(fitted))
        final_expected_pages = expected_pages
        write_html(fitted, html_path, tokens=tokens, design_review=design_review)
        physical = validate_html_and_export_pdf(
            html_path,
            pdf_path,
            expected_pages=expected_pages,
            screenshot_path=screenshot_path,
        )
        final_physical = physical
        attempts.append(FitAttempt(
            attempt=attempt_number,
            chars_per_line=chars_per_line,
            lines_per_page=lines_per_page,
            fit_status=fit_report.status,
            expected_pages=expected_pages,
            physical_status=physical.status,
            physical_reasons=list(physical.reasons),
        ))
        if fit_report.status == "FIT" and physical.status == "PASS":
            break

    assert final_fit_report is not None and final_physical is not None
    _write_json(fit_report_path, final_fit_report)
    _write_json(physical_report_path, final_physical)

    return TemplateBundle(
        template_id=template_id,
        role=role,
        html_file=html_path.name,
        pdf_file=pdf_path.name,
        screenshot_file=screenshot_path.name,
        fit_report_file=fit_report_path.name,
        design_report_file=design_report_path.name,
        physical_report_file=physical_report_path.name,
        fit_status=final_fit_report.status,
        design_status=design_review.decision,
        physical_status=final_physical.status,
        expected_pages=final_expected_pages,
        attempts=attempts,
    )


def build_application_bundle(
    *,
    vacancy: dict[str, Any],
    run_dir: Path,
    identity_public_path: Path,
    brand_profiles_dir: Path,
    design_client: AdkStructuredClient,
    primary_template: str = "technical_modern_v1",
    alternate_template: str = "harvard_v1",
) -> ApplicationBundleReport:
    cv_path = run_dir / "cv_final.json"
    if not cv_path.exists():
        raise FileNotFoundError(f"missing final CV: {cv_path}")
    cv = load_cv_document(cv_path)
    identity = resolve_candidate_identity(
        public_identity_path=identity_public_path,
        include_private_contact=False,
        artifact_visibility="public",
    ).identity

    run_report_path = run_dir / "run_report.json"
    run_report = json.loads(run_report_path.read_text(encoding="utf-8")) if run_report_path.exists() else {}
    quality_reached = bool(run_report.get("quality_target_reached"))
    cover_letter_ready = (run_dir / "cover_letter_final.json").exists() and (run_dir / "cover_letter_final.md").exists()

    bundles: list[TemplateBundle] = []
    for template_id, role in ((primary_template, "primary"), (alternate_template, "alternate")):
        tokens, design_review, deterministic = _design_for_template(
            client=design_client,
            template_id=template_id,
            company=str(vacancy["company"]),
            brand_profiles_dir=brand_profiles_dir,
        )
        bundles.append(_render_until_physical_fit(
            cv=cv,
            candidate=identity,
            template_id=template_id,
            role=role,
            output_dir=run_dir,
            tokens=tokens,
            design_review=design_review,
            deterministic_design=deterministic,
        ))

    primary = next(item for item in bundles if item.role == "primary")
    reasons: list[str] = []
    if not quality_reached:
        reasons.append("content_quality_target_not_reached")
    if not cover_letter_ready:
        reasons.append("cover_letter_missing")
    if primary.fit_status != "FIT":
        reasons.append("primary_template_fit_failed")
    if primary.design_status != "PASS":
        reasons.append("primary_template_design_failed")
    if primary.physical_status != "PASS":
        reasons.append("primary_template_physical_layout_failed")

    report = ApplicationBundleReport(
        vacancy_id=str(vacancy["vacancy_id"]),
        company=str(vacancy["company"]),
        role_title=str(vacancy["role_title"]),
        application_url=str(vacancy["url"]),
        content_quality_target_reached=quality_reached,
        cover_letter_ready=cover_letter_ready,
        primary_template=primary_template,
        alternate_template=alternate_template,
        templates=bundles,
        ready_to_send=not reasons,
        reasons=reasons,
    )
    _write_json(run_dir / "application_bundle_report.json", report)
    return report
