from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel

from cv_agent.context import assemble_application_context, load_evidence_catalog
from cv_agent.editorial_policy import validate_editorial_policy
from cv_agent.model_policy import MAX_REVIEW_ITERATIONS, model_ids, policy_for_iteration
from cv_agent.prompts import HEADHUNTER_INSTRUCTION, REVISER_INSTRUCTION, STRATEGIST_INSTRUCTION, WRITER_INSTRUCTION
from cv_agent.render import render_markdown
from cv_agent.schemas import CVDocument, HeadhunterReview, StrategyOutput
from cv_agent.validators import quality_gate, validate_claims, validate_language, validate_structure


MAX_MODEL_EVIDENCE_CHUNKS = 40
MAX_MODEL_EVIDENCE_CHARS = 70000


class StructuredClient(Protocol):
    async def call(
        self,
        *,
        name: str,
        model: str,
        instruction: str,
        payload: dict,
        output_schema: type[BaseModel],
        max_output_tokens: int = 6000,
    ) -> BaseModel: ...


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _ordered_evidence_ids(match_plan: dict[str, Any]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for requirement in match_plan.get("requirements", []):
        for chunk_id in requirement.get("evidence_chunk_ids", []):
            if chunk_id not in seen:
                seen.add(chunk_id)
                ordered.append(chunk_id)
    return ordered


def _budget_evidence(
    chunks: list[dict[str, Any]],
    match_plan: dict[str, Any],
    required_evidence_ids: list[str],
) -> list[dict[str, Any]]:
    by_id = {chunk["chunk_id"]: chunk for chunk in chunks}
    ordered_ids: list[str] = []
    seen: set[str] = set()

    # Stable chronology, education, GenAI and mandatory certifications are
    # budgeted first. Vacancy-specific retrieval still controls the remaining
    # projects/skills/metrics, but may not crowd stable editorial facts out.
    for chunk_id in required_evidence_ids:
        if chunk_id in by_id and chunk_id not in seen:
            seen.add(chunk_id)
            ordered_ids.append(chunk_id)
    for chunk_id in _ordered_evidence_ids(match_plan):
        if chunk_id in by_id and chunk_id not in seen:
            seen.add(chunk_id)
            ordered_ids.append(chunk_id)
    for chunk_id in sorted(by_id):
        if chunk_id not in seen:
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
        limit_hit = len(result) >= MAX_MODEL_EVIDENCE_CHUNKS or used_chars + size > MAX_MODEL_EVIDENCE_CHARS
        if limit_hit:
            if chunk_id in required_set:
                raise ValueError(
                    "required CV evidence exceeds the model evidence budget; "
                    "increase the explicit budget rather than silently dropping chronology/editorial anchors"
                )
            break
        result.append(compact)
        used_chars += size

    missing_required = sorted(required_set - {item["chunk_id"] for item in result})
    if missing_required:
        raise ValueError(f"required CV evidence was not fully budgeted: {missing_required}")
    return result


def _validate_strategy(strategy: StrategyOutput, available_ids: set[str], expected_language: str) -> None:
    if strategy.language != expected_language:
        raise ValueError(f"strategy language {strategy.language!r} does not match required {expected_language!r}")
    unknown = sorted(set(strategy.selected_evidence_chunk_ids) - available_ids)
    if unknown:
        raise ValueError(f"strategy selected unknown/ineligible evidence chunks: {unknown}")
    if not strategy.selected_evidence_chunk_ids:
        raise ValueError("strategy selected no evidence chunks")


def _attach_required_evidence(strategy: StrategyOutput, required_ids: list[str]) -> None:
    ordered: list[str] = []
    seen: set[str] = set()
    for chunk_id in required_ids + list(strategy.selected_evidence_chunk_ids):
        if chunk_id not in seen:
            seen.add(chunk_id)
            ordered.append(chunk_id)
    strategy.selected_evidence_chunk_ids = ordered


def _candidate_rank(review: HeadhunterReview, validators_pass: bool) -> tuple[int, int, int]:
    return (1 if validators_pass else 0, review.overall_score, review.scores.evidence_strength)


def _apply_editorial_gate(gate, editorial) -> None:
    if editorial.status != "PASS":
        if "editorial_validation_failed" not in gate.reasons:
            gate.reasons.append("editorial_validation_failed")
        gate.passed = False


async def run_agentic_cv(
    *,
    vacancy_id: str,
    client: StructuredClient,
    output_dir: Path,
    vacancy_state: Path = Path("vacancy_state"),
    evidence_state: Path = Path("rag_state"),
    run_id: str = "manual",
    retrieval_mode: str | None = None,
) -> dict[str, Any]:
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
    model_evidence = _budget_evidence(
        context["evidence_chunks"],
        context["match_plan"],
        required_evidence_ids,
    )
    available_ids = {chunk["chunk_id"] for chunk in model_evidence}
    if not model_evidence:
        raise ValueError(f"no eligible evidence available for vacancy {vacancy_id}")
    if required_evidence_ids and not set(required_evidence_ids).issubset(available_ids):
        raise ValueError("required evidence is incomplete after evidence budgeting")

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

    iteration_records: list[dict[str, Any]] = []
    best: tuple[tuple[int, int, int], int, CVDocument, HeadhunterReview, dict[str, Any]] | None = None
    quality_target_reached = False

    for iteration in range(1, MAX_REVIEW_ITERATIONS + 1):
        policy = policy_for_iteration(iteration)
        review = await client.call(
            name=f"senior_headhunter_{iteration}",
            model=policy.reviewer_model,
            instruction=HEADHUNTER_INSTRUCTION,
            payload={
                "iteration": iteration,
                "max_iterations": MAX_REVIEW_ITERATIONS,
                "vacancy": vacancy,
                "application_language": expected_language,
                "match_plan": context["match_plan"],
                "canonical_backbone_chunk_ids": canonical_backbone_ids,
                "editorial_anchor_chunk_ids": editorial_anchor_ids,
                "approved_evidence": selected_evidence,
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
        validators_pass = (
            factual.status == language.status == structure.status == editorial.status == "PASS"
        )

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

    if best is None:
        raise RuntimeError("review loop produced no evaluated CV candidate")

    _, best_iteration, final_cv, final_review, final_validation = best
    final_status = "PASS" if quality_target_reached else "COMPLETED_BELOW_TARGET"
    quality_note = None if quality_target_reached else (
        "Maximum of 5 Senior Headhunter review iterations reached without satisfying all quality gates. "
        "The best evaluated CV is returned; review run_report.json before submitting."
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

    final_refs: set[str] = set()

    def add_refs(values: list[str]) -> None:
        final_refs.update(values)

    add_refs(final_cv.headline.evidence_refs)
    add_refs(final_cv.summary.evidence_refs)
    for item in final_cv.experience:
        add_refs(item.evidence_refs)
        for bullet in item.bullets:
            add_refs(bullet.evidence_refs)
    for item in final_cv.projects:
        add_refs(item.evidence_refs)
        for bullet in item.bullets:
            add_refs(bullet.evidence_refs)
    for line in final_cv.skills + final_cv.education + final_cv.certifications:
        add_refs(line.evidence_refs)

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
        "application_language": expected_language,
        "language_confidence": vacancy.get("language_confidence"),
        "language_source": vacancy.get("language_source"),
        "status": final_status,
        "quality_target_reached": quality_target_reached,
        "quality_note": quality_note,
        "max_review_iterations": MAX_REVIEW_ITERATIONS,
        "iterations_executed": len(iteration_records),
        "best_review_iteration": best_iteration,
        "model_escalation": [item["model_policy"] for item in iteration_records],
        "premium_model_used": any(item["model_policy"]["premium"] for item in iteration_records),
        "canonical_backbone_chunk_ids": canonical_backbone_ids,
        "editorial_anchor_chunk_ids": editorial_anchor_ids,
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
