from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from cv_agent.context import assemble_application_context, load_evidence_catalog
from cv_agent.editorial_policy import validate_editorial_policy
from cv_agent.model_policy import MAX_REVIEW_ITERATIONS, cost_optimized_policy_for_iteration, model_ids
from cv_agent.prompts import HEADHUNTER_INSTRUCTION, REVISER_INSTRUCTION, STRATEGIST_INSTRUCTION, WRITER_INSTRUCTION
from cv_agent.render import render_markdown
from cv_agent.schemas import CVDocument, HeadhunterReview, StrategyOutput
from cv_agent.validators import quality_gate, validate_claims, validate_language, validate_structure
from cv_agent.workflow import (
    StructuredClient,
    _apply_editorial_gate,
    _attach_required_evidence,
    _candidate_rank,
    _repair_style_before_headhunter,
    _validate_strategy,
    _write_json,
)


OPTIMIZED_MAX_EVIDENCE_CHUNKS = 28
OPTIMIZED_MAX_EVIDENCE_CHARS = 45000
OPTIMIZATION_PROFILE = "cost_v1"


def _ordered_evidence_ids(match_plan: dict[str, Any]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for requirement in match_plan.get("requirements", []):
        for chunk_id in requirement.get("evidence_chunk_ids", []):
            if chunk_id not in seen:
                seen.add(chunk_id)
                ordered.append(chunk_id)
    return ordered


def _budget_evidence_cost(
    chunks: list[dict[str, Any]],
    match_plan: dict[str, Any],
    required_evidence_ids: list[str],
) -> list[dict[str, Any]]:
    """Use the same evidence ordering as baseline with a tighter model-facing budget."""

    by_id = {chunk["chunk_id"]: chunk for chunk in chunks}
    ordered_ids: list[str] = []
    seen: set[str] = set()
    for chunk_id in required_evidence_ids + _ordered_evidence_ids(match_plan) + sorted(by_id):
        if chunk_id in by_id and chunk_id not in seen:
            seen.add(chunk_id)
            ordered_ids.append(chunk_id)

    result: list[dict[str, Any]] = []
    used_chars = 0
    required_set = set(required_evidence_ids)
    for chunk_id in ordered_ids:
        chunk = by_id.get(chunk_id)
        if not chunk or not chunk.get("cv_eligible"):
            continue
        compact = {
            "chunk_id": chunk["chunk_id"],
            "record_id": chunk["record_id"],
            "chunk_type": chunk["chunk_type"],
            "title": chunk["title"],
            "text": chunk["text"],
            "proficiency": chunk.get("proficiency"),
            "metric_refs": chunk.get("metric_refs", []),
            "constraints": chunk.get("constraints", []),
            "source_path": chunk["source_path"],
            "attributes": chunk.get("attributes", {}),
        }
        size = len(json.dumps(compact, ensure_ascii=False))
        limit_hit = len(result) >= OPTIMIZED_MAX_EVIDENCE_CHUNKS or used_chars + size > OPTIMIZED_MAX_EVIDENCE_CHARS
        if limit_hit:
            if chunk_id in required_set:
                raise ValueError(
                    "required CV evidence exceeds optimized evidence budget; "
                    "cost profile refuses to drop governed anchors"
                )
            break
        result.append(compact)
        used_chars += size

    missing_required = sorted(required_set - {item["chunk_id"] for item in result})
    if missing_required:
        raise ValueError(f"required CV evidence was not fully budgeted: {missing_required}")
    return result


def _cv_evidence_ids(cv: CVDocument) -> set[str]:
    refs: set[str] = set()

    def add(values: list[str]) -> None:
        refs.update(values)

    add(cv.headline.evidence_refs)
    add(cv.summary.evidence_refs)
    for item in cv.experience:
        add(item.evidence_refs)
        for bullet in item.bullets:
            add(bullet.evidence_refs)
    for item in cv.projects:
        add(item.evidence_refs)
        for bullet in item.bullets:
            add(bullet.evidence_refs)
    for line in cv.skills + cv.education + cv.certifications:
        add(line.evidence_refs)
    return refs


def _review_evidence(
    selected_evidence: list[dict[str, Any]],
    cv: CVDocument,
    required_evidence_ids: list[str],
) -> list[dict[str, Any]]:
    keep = _cv_evidence_ids(cv) | set(required_evidence_ids)
    return [chunk for chunk in selected_evidence if chunk["chunk_id"] in keep]


def _compact_match_plan(match_plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "coverage_score": match_plan.get("coverage_score"),
        "coverage_counts": match_plan.get("coverage_counts", {}),
        "requirements": [
            {
                "requirement": item.get("requirement"),
                "coverage": item.get("coverage"),
            }
            for item in match_plan.get("requirements", [])
        ],
    }


def _validators_pass(validation_payload: dict[str, Any]) -> bool:
    return all(
        validation_payload.get(name, {}).get("status") == "PASS"
        for name in ("factual", "language", "structure", "editorial")
    )


def _stagnation_reason(iteration_records: list[dict[str, Any]]) -> str | None:
    """Stop only after three reviews when safe validators pass and feedback has stalled."""

    if len(iteration_records) < 3:
        return None
    current = iteration_records[-1]
    previous = iteration_records[-2]
    if not (_validators_pass(current["validation"]) and _validators_pass(previous["validation"])):
        return None

    previous_best = max(item["review"]["overall_score"] for item in iteration_records[:-1])
    current_score = int(current["review"]["overall_score"])
    if current_score > previous_best + 1:
        return None

    current_reasons = set(current["validation"]["quality_gate"].get("reasons", []))
    previous_reasons = set(previous["validation"]["quality_gate"].get("reasons", []))
    current_sections = {item.get("section") for item in current["review"].get("blocking_issues", [])}
    previous_sections = {item.get("section") for item in previous["review"].get("blocking_issues", [])}
    if current_reasons == previous_reasons and current_sections == previous_sections:
        return "stagnant_quality_after_three_reviews"
    return None


async def run_cost_optimized_cv(
    *,
    vacancy_id: str,
    client: StructuredClient,
    output_dir: Path,
    vacancy_state: Path = Path("vacancy_state"),
    evidence_state: Path = Path("rag_state"),
    run_id: str = "manual-cost-v1",
    retrieval_mode: str | None = None,
) -> dict[str, Any]:
    """A/B-only cost profile with the same deterministic editorial/style gates as production."""

    context = assemble_application_context(
        vacancy_id,
        vacancy_state=vacancy_state,
        evidence_state=evidence_state,
        retrieval_mode=retrieval_mode,
    )
    vacancy = context["vacancy"]
    expected_language = vacancy["application_language"]
    canonical_backbone_ids = list(context.get("canonical_backbone_chunk_ids", []))
    editorial_anchor_ids = list(context.get("editorial_anchor_chunk_ids", []))
    required_evidence_ids = list(dict.fromkeys(canonical_backbone_ids + editorial_anchor_ids))
    model_evidence = _budget_evidence_cost(
        context["evidence_chunks"],
        context["match_plan"],
        required_evidence_ids,
    )
    available_ids = {chunk["chunk_id"] for chunk in model_evidence}
    if not model_evidence:
        raise ValueError(f"no eligible evidence available for vacancy {vacancy_id}")
    if required_evidence_ids and not set(required_evidence_ids).issubset(available_ids):
        raise ValueError("required evidence is incomplete after optimized evidence budgeting")

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "match_plan.json", context["match_plan"])
    _write_json(output_dir / "canonical_backbone.json", {
        "chunk_ids": canonical_backbone_ids,
        "editorial_anchor_chunk_ids": editorial_anchor_ids,
        "source_paths": sorted({
            chunk["source_path"] for chunk in model_evidence
            if chunk["chunk_id"] in set(required_evidence_ids)
        }),
    })

    models = model_ids()
    strategist_model = os.getenv("CV_FIT_MODEL_STRATEGIST", models["balanced"])
    writer_model = os.getenv("CV_FIT_MODEL_WRITER", models["balanced"])

    strategy = await client.call(
        name="cv_strategist",
        model=strategist_model,
        instruction=STRATEGIST_INSTRUCTION,
        payload={
            "vacancy": vacancy,
            "application_language": expected_language,
            "match_plan": context["match_plan"],
            "canonical_backbone_chunk_ids": canonical_backbone_ids,
            "editorial_anchor_chunk_ids": editorial_anchor_ids,
            "eligible_evidence": model_evidence,
        },
        output_schema=StrategyOutput,
        max_output_tokens=4500,
    )
    assert isinstance(strategy, StrategyOutput)
    _validate_strategy(strategy, available_ids, expected_language)
    _attach_required_evidence(strategy, required_evidence_ids)
    _write_json(output_dir / "strategy.json", strategy.model_dump())

    strategy_ids = set(strategy.selected_evidence_chunk_ids)
    selected_evidence = [chunk for chunk in model_evidence if chunk["chunk_id"] in strategy_ids]
    evidence_catalog = load_evidence_catalog(evidence_state)

    cv = await client.call(
        name="cv_writer",
        model=writer_model,
        instruction=WRITER_INSTRUCTION,
        payload={
            "vacancy": vacancy,
            "application_language": expected_language,
            "strategy": strategy.model_dump(),
            "canonical_backbone_chunk_ids": canonical_backbone_ids,
            "editorial_anchor_chunk_ids": editorial_anchor_ids,
            "approved_evidence": selected_evidence,
        },
        output_schema=CVDocument,
        max_output_tokens=7000,
    )
    assert isinstance(cv, CVDocument)
    _write_json(output_dir / "drafts" / "cv_initial.json", cv.model_dump())

    cv, style_preflight = await _repair_style_before_headhunter(
        cv=cv,
        client=client,
        vacancy=vacancy,
        expected_language=expected_language,
        strategy=strategy,
        canonical_backbone_ids=canonical_backbone_ids,
        editorial_anchor_ids=editorial_anchor_ids,
        selected_evidence=selected_evidence,
        evidence_catalog=evidence_catalog,
        strategy_ids=strategy_ids,
    )
    _write_json(output_dir / "style_preflight.json", style_preflight)
    if style_preflight.get("repaired"):
        _write_json(output_dir / "drafts" / "cv_style_repaired.json", cv.model_dump())

    iteration_records: list[dict[str, Any]] = []
    best: tuple[tuple[int, int, int], int, CVDocument, HeadhunterReview, dict[str, Any]] | None = None
    quality_target_reached = False
    stop_reason: str | None = None
    previous_review: HeadhunterReview | None = None
    previous_validation: dict[str, Any] | None = None

    for iteration in range(1, MAX_REVIEW_ITERATIONS + 1):
        policy = cost_optimized_policy_for_iteration(
            iteration,
            previous_score=previous_review.overall_score if previous_review else None,
            previous_blocking_issues=len(previous_review.blocking_issues) if previous_review else None,
            previous_validators_pass=_validators_pass(previous_validation or {}),
        )
        reviewer_evidence = _review_evidence(selected_evidence, cv, required_evidence_ids)
        review = await client.call(
            name=f"senior_headhunter_{iteration}",
            model=policy.reviewer_model,
            instruction=HEADHUNTER_INSTRUCTION,
            payload={
                "iteration": iteration,
                "max_iterations": MAX_REVIEW_ITERATIONS,
                "vacancy": vacancy,
                "application_language": expected_language,
                "match_plan": _compact_match_plan(context["match_plan"]),
                "canonical_backbone_chunk_ids": canonical_backbone_ids,
                "editorial_anchor_chunk_ids": editorial_anchor_ids,
                "approved_evidence": reviewer_evidence,
                "cv": cv.model_dump(),
            },
            output_schema=HeadhunterReview,
            max_output_tokens=policy.max_output_tokens,
        )
        assert isinstance(review, HeadhunterReview)
        factual = validate_claims(cv, evidence_catalog, strategy_ids)
        language = validate_language(cv, expected_language)
        structure = validate_structure(cv)
        editorial = validate_editorial_policy(cv)
        gate = quality_gate(review, factual, language, structure)
        _apply_editorial_gate(gate, editorial)
        validators_pass = factual.status == language.status == structure.status == editorial.status == "PASS"

        validation_payload = {
            "factual": factual.model_dump(),
            "language": language.model_dump(),
            "structure": structure.model_dump(),
            "editorial": editorial.model_dump(),
            "quality_gate": gate.model_dump(),
        }
        record = {
            "iteration": iteration,
            "model_policy": policy.to_dict(),
            "review_context_evidence_count": len(reviewer_evidence),
            "review": review.model_dump(),
            "validation": validation_payload,
        }
        iteration_records.append(record)
        _write_json(output_dir / "reviews" / f"iteration_{iteration:02d}.json", record)
        _write_json(output_dir / "drafts" / f"cv_reviewed_{iteration:02d}.json", cv.model_dump())

        rank = _candidate_rank(review, validators_pass)
        if best is None or rank > best[0]:
            best = (rank, iteration, cv, review, validation_payload)

        if gate.passed:
            best = (rank, iteration, cv, review, validation_payload)
            quality_target_reached = True
            break

        stop_reason = _stagnation_reason(iteration_records)
        if stop_reason:
            break
        if iteration == MAX_REVIEW_ITERATIONS:
            break

        cv = await client.call(
            name=f"cv_reviser_{iteration}",
            model=policy.reviser_model,
            instruction=REVISER_INSTRUCTION,
            payload={
                "iteration": iteration,
                "vacancy": vacancy,
                "application_language": expected_language,
                "strategy": strategy.model_dump(),
                "canonical_backbone_chunk_ids": canonical_backbone_ids,
                "editorial_anchor_chunk_ids": editorial_anchor_ids,
                "approved_evidence": selected_evidence,
                "current_cv": cv.model_dump(),
                "headhunter_review": review.model_dump(),
                "deterministic_validation": validation_payload,
            },
            output_schema=CVDocument,
            max_output_tokens=policy.max_output_tokens,
        )
        assert isinstance(cv, CVDocument)
        previous_review = review
        previous_validation = validation_payload

    if best is None:
        raise RuntimeError("review loop produced no evaluated CV candidate")

    _, best_iteration, final_cv, final_review, final_validation = best
    final_status = "PASS" if quality_target_reached else "COMPLETED_BELOW_TARGET"
    if quality_target_reached:
        quality_note = None
    elif stop_reason:
        quality_note = (
            "Cost-aware A/B profile stopped after repeated non-improving review feedback while deterministic "
            "validators remained PASS. The best evaluated CV is returned for blind comparison."
        )
    else:
        quality_note = (
            "Maximum review budget reached without satisfying all quality gates. "
            "The best evaluated CV is returned for blind comparison."
        )
    final_gate_reasons = [] if quality_target_reached else list(
        final_validation.get("quality_gate", {}).get("reasons", [])
    )

    _write_json(output_dir / "cv_final.json", {
        "quality_status": final_status,
        "quality_target_reached": quality_target_reached,
        "quality_note": quality_note,
        "best_review_iteration": best_iteration,
        "cv": final_cv.model_dump(),
    })
    (output_dir / "cv_final.md").write_text(render_markdown(final_cv), encoding="utf-8")

    final_refs = _cv_evidence_ids(final_cv)
    trace = {
        "vacancy_id": vacancy_id,
        "vacancy_source_paths": sorted({ref["source_path"] for ref in vacancy.get("provenance", [])}),
        "vacancy_content_hash": vacancy.get("content_hash"),
        "canonical_backbone_chunk_ids": canonical_backbone_ids,
        "editorial_anchor_chunk_ids": editorial_anchor_ids,
        "evidence_chunk_ids": sorted(final_refs),
        "evidence_record_ids": sorted({evidence_catalog[ref]["record_id"] for ref in final_refs if ref in evidence_catalog}),
        "evidence_source_paths": sorted({evidence_catalog[ref]["source_path"] for ref in final_refs if ref in evidence_catalog}),
    }
    _write_json(output_dir / "evidence_trace.json", trace)

    report = {
        "schema_version": 1,
        "run_id": run_id,
        "vacancy_id": vacancy_id,
        "optimization_profile": OPTIMIZATION_PROFILE,
        "application_language": expected_language,
        "language_confidence": vacancy.get("language_confidence"),
        "language_source": vacancy.get("language_source"),
        "status": final_status,
        "quality_target_reached": quality_target_reached,
        "quality_note": quality_note,
        "max_review_iterations": MAX_REVIEW_ITERATIONS,
        "iterations_executed": len(iteration_records),
        "best_review_iteration": best_iteration,
        "early_stop_reason": stop_reason,
        "model_escalation": [item["model_policy"] for item in iteration_records],
        "premium_model_used": any(item["model_policy"]["premium"] for item in iteration_records),
        "model_evidence_count": len(model_evidence),
        "selected_evidence_count": len(selected_evidence),
        "canonical_backbone_chunk_ids": canonical_backbone_ids,
        "editorial_anchor_chunk_ids": editorial_anchor_ids,
        "style_preflight": style_preflight,
        "final_review": final_review.model_dump(),
        "final_validation": final_validation,
        "final_gate_reasons": final_gate_reasons,
        "match_coverage_score": context["match_plan"].get("coverage_score"),
        "unsupported_requirements": [
            item["requirement"] for item in context["match_plan"].get("requirements", []) if item.get("coverage") == "unsupported"
        ],
        "evidence_trace_file": "evidence_trace.json",
        "final_cv_file": "cv_final.md",
    }
    _write_json(output_dir / "run_report.json", report)
    return report
