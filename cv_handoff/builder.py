from __future__ import annotations

import argparse
import html as html_lib
import json
import re
import shutil
from pathlib import Path
from typing import Any


REDACTED_KEYS = {
    "email",
    "phone",
    "phone_number",
    "mobile",
    "address",
    "private_contact",
    "personal_email",
}


FINAL_REVIEW_PROMPT = """# Final CV review

Act as the final editor before this application is sent.

Your goal is not to regenerate the CV from scratch. Improve the existing proposal into the strongest accurate, credible and concise version for this vacancy.

## Read these first
1. `review_context.json`: why the automated CV did or did not pass, including quality, coverage, gaps and presentation diagnostics.
2. `vacancy.md` / `vacancy.json`: what the employer actually asks for.
3. `cv_proposed.json` and `cv_proposed.html`: the current content and rendered proposal.
4. `match_plan.json`: requirement-level supported / partial / unsupported coverage from the matching stage.
5. `evidence_snapshot.json`: public-safe evidence split into proposal refs and opportunity refs selected by matching, including constraints and claim boundaries.
6. `html_base.html.j2`: the visual/template baseline.
7. `public_identity.yaml`: identity fields that are safe to commit publicly.
8. `cover_letter_proposed.md`, when present, to keep the application narrative consistent.
9. The repository `experience/` evidence only when the snapshot is insufficient or a stronger factual angle is needed.

## Rules
- Use the vacancy to decide what deserves emphasis.
- Use real candidate evidence as the factual boundary.
- Never invent technologies, responsibilities, metrics, employers, titles, dates, achievements or contact details.
- Respect every evidence constraint/boundary in `evidence_snapshot.json`.
- Use `proposal_refs` to verify current claims and `opportunity_refs` to find stronger evidence the automated CV failed to surface.
- Transferable experience may be reframed when the connection is defensible, but never presented as direct experience when it is not.
- Prefer quantified evidence and concrete outcomes over adjectives.
- Remove true-but-distracting material when it weakens the application.
- Treat automated scores as diagnostics, not as instructions to mechanically optimize wording.
- Fix the specific weaknesses in `review_context.json` when evidence allows it; otherwise document the gap rather than hiding it.
- Preserve the base HTML system unless there is a clear usability, ATS, pagination or visual reason to change it.
- Keep the document self-contained, print-safe, Letter sized and ideally no more than two pages.
- Match the language of the vacancy.
- Do not add years of experience to the headline.
- Optimize for a senior recruiter reading the first 10–20 seconds.
- This repository is public. Use only `public_identity.yaml`; never add private email, phone or address to committed artifacts.

## Deliverables
Create:
- `final.html`: the final public-safe, self-contained CV ready to render.
- `review_notes.md`: a concise explanation of the most important changes, remaining gaps, evidence used, and any claim deliberately not made.

The automated quality KPI is advisory. A below-target proposal can still become the strongest honest application.
"""


def _read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            if str(key).lower() in REDACTED_KEYS:
                continue
            cleaned[str(key)] = _redact(item)
        return cleaned
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _clean_html_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(?:p|div|li|h[1-6]|ul|ol)>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_lib.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def _quality_score(run_report: dict[str, Any], generation_entry: dict[str, Any]) -> float | int | None:
    raw = ((run_report.get("final_review") or {}).get("overall_score"))
    if raw is None:
        raw = generation_entry.get("headhunter_score")
    if raw is None or isinstance(raw, bool):
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return int(value) if value.is_integer() else round(value, 1)


def _source_date(vacancy: dict[str, Any]) -> str | None:
    candidates: list[str] = []
    for row in vacancy.get("provenance", []):
        for key in ("source_search_date", "source_updated_at"):
            value = str(row.get(key) or "")
            if len(value) >= 10 and value[:10].count("-") == 2:
                candidates.append(value[:10])
    posted = str(vacancy.get("posted_date") or "")
    if len(posted) >= 10 and posted[:10].count("-") == 2:
        candidates.append(posted[:10])
    return max(candidates) if candidates else None


def _date_rank(value: Any) -> int:
    text = str(value or "")[:10].replace("-", "")
    return int(text) if text.isdigit() else 0


def _vacancy_markdown(vacancy: dict[str, Any]) -> str:
    def bullets(values: Any) -> str:
        if not isinstance(values, list) or not values:
            return "_Not separately structured; read the description below._"
        cleaned = [_clean_html_text(item) for item in values if str(item).strip()]
        return "\n".join(f"- {item}" for item in cleaned if item)

    fit_strengths = vacancy.get("fit_strengths") or []
    fit_gaps = vacancy.get("fit_gaps") or []
    parts = [
        f"# {vacancy.get('company', '')} — {vacancy.get('role_title', '')}",
        "",
        f"- Vacancy ID: `{vacancy.get('vacancy_id', '')}`",
        f"- Posted: {vacancy.get('posted_date') or 'Not specified'}",
        f"- Location: {vacancy.get('location_raw') or vacancy.get('city') or 'Not specified'}",
        f"- Work model: {vacancy.get('work_model') or 'Not specified'}",
        f"- Source fit: {vacancy.get('fit_score') if vacancy.get('fit_score') is not None else 'n/a'}",
        f"- JD fidelity: {vacancy.get('jd_fidelity') or 'n/a'}",
        f"- Original vacancy: {vacancy.get('url') or ''}",
        "",
        "## Employer description",
        "",
        _clean_html_text(vacancy.get("description") or vacancy.get("fit_summary") or "_Not provided._"),
        "",
        "## Structured responsibilities",
        "",
        bullets(vacancy.get("responsibilities")),
        "",
        "## Structured requirements",
        "",
        bullets(vacancy.get("requirements")),
        "",
        "## Source-level fit strengths",
        "",
        bullets(fit_strengths),
        "",
        "## Source-level fit gaps",
        "",
        bullets(fit_gaps),
        "",
    ]
    return "\n".join(parts)


def _collect_evidence_refs(value: Any) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "evidence_refs" and isinstance(item, list):
                refs.update(str(ref) for ref in item if str(ref).strip())
            else:
                refs.update(_collect_evidence_refs(item))
    elif isinstance(value, list):
        for item in value:
            refs.update(_collect_evidence_refs(item))
    return refs


def _load_evidence_snapshot(evidence_state: Path, refs: set[str]) -> dict[str, Any]:
    found: dict[str, dict[str, Any]] = {}
    if evidence_state.exists():
        for path in sorted((evidence_state / "chunks").glob("*.json")):
            payload = _read_json(path, {})
            for chunk in payload.get("chunks", []) if isinstance(payload, dict) else []:
                if not isinstance(chunk, dict):
                    continue
                chunk_id = str(chunk.get("chunk_id") or "")
                if chunk_id not in refs or chunk.get("public_safe") is not True:
                    continue
                found[chunk_id] = {
                    "chunk_id": chunk_id,
                    "title": chunk.get("title"),
                    "text": chunk.get("text"),
                    "constraints": chunk.get("constraints") or [],
                    "confidence": chunk.get("confidence"),
                    "proficiency": chunk.get("proficiency"),
                    "source_path": chunk.get("source_path"),
                    "record_type": chunk.get("record_type"),
                    "chunk_type": chunk.get("chunk_type"),
                    "metric_refs": chunk.get("metric_refs") or [],
                }
    return {
        "schema_version": 1,
        "requested_ref_count": len(refs),
        "resolved_ref_count": len(found),
        "missing_refs": sorted(refs - set(found)),
        "evidence": [found[key] for key in sorted(found)],
    }


def _refresh_existing_packages(
    handoff_dir: Path,
    *,
    evidence_state: Path,
) -> list[str]:
    """Refresh schema-derived files even when the current generation batch is idempotent.

    Existing handoffs are durable review artifacts. Builder/schema improvements
    must therefore migrate them independently of whether a new CV was generated.
    """
    refreshed: list[str] = []
    for package_dir in sorted(path for path in handoff_dir.iterdir() if path.is_dir()):
        manifest_path = package_dir / "handoff.json"
        cv_path = package_dir / "cv_proposed.json"
        if not manifest_path.exists() or not cv_path.exists():
            continue

        cv_payload = _read_json(cv_path, {})
        match_plan_payload = _read_json(package_dir / "match_plan.json", {})
        proposal_refs = _collect_evidence_refs(cv_payload)
        selected_refs = {
            str(ref)
            for ref in (match_plan_payload.get("selected_evidence_chunk_ids") or [])
            if str(ref).strip()
        } if isinstance(match_plan_payload, dict) else set()
        opportunity_refs = selected_refs - proposal_refs

        snapshot = _load_evidence_snapshot(evidence_state, proposal_refs | opportunity_refs)
        snapshot["proposal_refs"] = sorted(proposal_refs)
        snapshot["opportunity_refs"] = sorted(opportunity_refs)
        _write_json(package_dir / "evidence_snapshot.json", snapshot)
        (package_dir / "prompt.md").write_text(FINAL_REVIEW_PROMPT, encoding="utf-8")

        manifest = _read_json(manifest_path, {})
        if isinstance(manifest, dict):
            manifest["schema_version"] = max(int(manifest.get("schema_version") or 1), 2)
            files = manifest.setdefault("files", {})
            files["evidence_snapshot"] = "evidence_snapshot.json"
            files["prompt"] = "prompt.md"
            _write_json(manifest_path, manifest)
        refreshed.append(package_dir.name)
    return refreshed


def _review_context(
    *,
    vacancy: dict[str, Any],
    cv_payload: dict[str, Any],
    run_report: dict[str, Any],
    generation_entry: dict[str, Any],
    bundle: dict[str, Any],
    pipeline_item: dict[str, Any],
) -> dict[str, Any]:
    final_review = run_report.get("final_review") or {}
    final_validation = run_report.get("final_validation") or {}
    return {
        "schema_version": 1,
        "pipeline_status": pipeline_item.get("status"),
        "quality_kpi": _quality_score(run_report, generation_entry),
        "quality_target_reached": bool(
            run_report.get("quality_target_reached")
            or cv_payload.get("quality_target_reached")
            or generation_entry.get("content_quality_target_reached")
        ),
        "quality_note": cv_payload.get("quality_note") or run_report.get("quality_note"),
        "application_language": run_report.get("application_language") or vacancy.get("application_language"),
        "review_stop_reason": run_report.get("review_stop_reason"),
        "final_gate_reasons": run_report.get("final_gate_reasons") or [],
        "style_preflight": _redact(run_report.get("style_preflight") or {}),
        "headhunter": {
            "decision": generation_entry.get("headhunter_decision") or final_review.get("decision"),
            "score": generation_entry.get("headhunter_score") or final_review.get("overall_score"),
            "iterations": generation_entry.get("headhunter_iterations"),
            "best_review_iteration": generation_entry.get("best_review_iteration") or cv_payload.get("best_review_iteration"),
            "blocking_issues": final_review.get("blocking_issues") or [],
        },
        "evidence_coverage": {
            "coverage_score": generation_entry.get("coverage_score") or run_report.get("match_coverage_score"),
            "unsupported_requirements": generation_entry.get("unsupported_requirements") or [],
        },
        "validation": _redact(final_validation),
        "presentation": {
            "ready_to_send": bool(bundle.get("ready_to_send")),
            "bundle_reasons": bundle.get("reasons") or [],
            "gate": _redact(generation_entry.get("presentation_gate") or {}),
        },
        "vacancy_fit": {
            "source_fit": vacancy.get("fit_score"),
            "strengths": vacancy.get("fit_strengths") or [],
            "gaps": vacancy.get("fit_gaps") or [],
            "tech_stack": vacancy.get("tech_stack") or [],
        },
    }


def rebuild_index(
    handoff_dir: Path,
    *,
    repository: str = "jcval94/CV_fit",
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for manifest_path in sorted(handoff_dir.glob("*/handoff.json")):
        row = _read_json(manifest_path, {})
        if isinstance(row, dict) and row.get("vacancy_id"):
            rows.append(row)
    rows.sort(
        key=lambda row: (
            row.get("status") == "finalized",
            -(float(row.get("source_fit") or 0)),
            -_date_rank(row.get("source_date")),
            str(row.get("company") or ""),
        )
    )
    payload = {
        "schema_version": 2,
        "repository": repository,
        "selection_policy": "pending first; then source_fit descending; then recency descending",
        "pending_count": sum(row.get("status") != "finalized" for row in rows),
        "finalized_count": sum(row.get("status") == "finalized" for row in rows),
        "candidates": rows,
    }
    _write_json(handoff_dir / "index.json", payload)
    return payload


def build_handoffs(
    *,
    batch_report: Path,
    outputs: Path,
    vacancy_state: Path,
    template_file: Path,
    handoff_dir: Path,
    generation_manifest: Path = Path("generation_state/manifest.json"),
    evidence_state: Path = Path("rag_state"),
    public_identity: Path = Path("cv_presentation/identity.public.yaml"),
    repository: str = "jcval94/CV_fit",
) -> dict[str, Any]:
    batch = _read_json(batch_report, {"results": []})
    generation = _read_json(generation_manifest, {"entries": {}})
    generation_entries = generation.get("entries", {}) if isinstance(generation, dict) else {}
    handoff_dir.mkdir(parents=True, exist_ok=True)
    built: list[str] = []
    skipped: list[dict[str, str]] = []

    for item in batch.get("results", []):
        vacancy_id = str(item.get("vacancy_id") or "")
        run_id = str(item.get("run_id") or "")
        if not vacancy_id or not run_id:
            continue

        vacancy_path = vacancy_state / "records" / f"{vacancy_id}.json"
        run_dir = outputs / vacancy_id / run_id
        cv_json = run_dir / "cv_final.json"
        if not vacancy_path.exists() or not cv_json.exists():
            skipped.append({"vacancy_id": vacancy_id, "reason": "missing_vacancy_or_cv"})
            continue

        vacancy = _read_json(vacancy_path)
        cv_payload = _read_json(cv_json)
        run_report = _read_json(run_dir / "run_report.json", {})
        bundle = _read_json(run_dir / "application_bundle_report.json", {})
        generation_entry = generation_entries.get(vacancy_id, {}) if isinstance(generation_entries, dict) else {}
        package_dir = handoff_dir / vacancy_id
        package_dir.mkdir(parents=True, exist_ok=True)

        primary = next(
            (
                row
                for row in bundle.get("templates", [])
                if isinstance(row, dict) and row.get("role") == "primary"
            ),
            {},
        )
        proposed_html = run_dir / str(primary.get("html_file") or "cv_primary.html")
        proposed_md = run_dir / "cv_final.md"
        cover_letter = run_dir / "cover_letter_final.md"
        match_plan = run_dir / "match_plan.json"

        (package_dir / "vacancy.md").write_text(_vacancy_markdown(vacancy), encoding="utf-8")
        _write_json(package_dir / "vacancy.json", _redact(vacancy))
        _write_json(package_dir / "cv_proposed.json", _redact(cv_payload))
        match_plan_payload = _read_json(match_plan, {}) if match_plan.exists() else {}
        if match_plan_payload:
            _write_json(package_dir / "match_plan.json", _redact(match_plan_payload))
        _write_json(
            package_dir / "review_context.json",
            _review_context(
                vacancy=vacancy,
                cv_payload=cv_payload,
                run_report=run_report,
                generation_entry=generation_entry if isinstance(generation_entry, dict) else {},
                bundle=bundle,
                pipeline_item=item,
            ),
        )
        proposal_refs = _collect_evidence_refs(cv_payload)
        selected_refs = {
            str(ref)
            for ref in (match_plan_payload.get("selected_evidence_chunk_ids") or [])
            if str(ref).strip()
        } if isinstance(match_plan_payload, dict) else set()
        opportunity_refs = selected_refs - proposal_refs
        snapshot = _load_evidence_snapshot(evidence_state, proposal_refs | opportunity_refs)
        snapshot["proposal_refs"] = sorted(proposal_refs)
        snapshot["opportunity_refs"] = sorted(opportunity_refs)
        _write_json(package_dir / "evidence_snapshot.json", snapshot)

        if proposed_html.exists():
            shutil.copy2(proposed_html, package_dir / "cv_proposed.html")
        if proposed_md.exists():
            shutil.copy2(proposed_md, package_dir / "cv_proposed.md")
        if template_file.exists():
            shutil.copy2(template_file, package_dir / "html_base.html.j2")
        if public_identity.exists():
            shutil.copy2(public_identity, package_dir / "public_identity.yaml")
        if cover_letter.exists():
            shutil.copy2(cover_letter, package_dir / "cover_letter_proposed.md")
        (package_dir / "prompt.md").write_text(FINAL_REVIEW_PROMPT, encoding="utf-8")

        quality = _quality_score(run_report, generation_entry if isinstance(generation_entry, dict) else {})
        final_exists = (package_dir / "final.html").exists()
        base_url = f"https://github.com/{repository}/tree/main/handoff/{vacancy_id}"
        raw_base = f"https://raw.githubusercontent.com/{repository}/main/handoff/{vacancy_id}"
        manifest = {
            "schema_version": 2,
            "vacancy_id": vacancy_id,
            "company": vacancy.get("company"),
            "role_title": vacancy.get("role_title"),
            "source_date": _source_date(vacancy),
            "source_fit": vacancy.get("fit_score"),
            "quality_kpi": quality,
            "pipeline_status": item.get("status"),
            "ready_to_send": bool(bundle.get("ready_to_send")),
            "status": "finalized" if final_exists else "pending_final_review",
            "run_id": run_id,
            "vacancy_url": vacancy.get("url"),
            "repo_folder_url": base_url,
            "contact_policy": "public_safe_only_in_repo",
            "files": {
                "review_context": "review_context.json",
                "match_plan": "match_plan.json" if match_plan.exists() else None,
                "evidence_snapshot": "evidence_snapshot.json",
                "vacancy": "vacancy.md",
                "vacancy_json": "vacancy.json",
                "cv_proposed": "cv_proposed.json",
                "cv_proposed_markdown": "cv_proposed.md" if proposed_md.exists() else None,
                "cv_proposed_html": "cv_proposed.html" if proposed_html.exists() else None,
                "html_base": "html_base.html.j2" if template_file.exists() else None,
                "public_identity": "public_identity.yaml" if public_identity.exists() else None,
                "cover_letter_proposed": "cover_letter_proposed.md" if cover_letter.exists() else None,
                "prompt": "prompt.md",
                "final_html": "final.html" if final_exists else None,
                "final_pdf": "final.pdf" if (package_dir / "final.pdf").exists() else None,
                "review_notes": "review_notes.md" if (package_dir / "review_notes.md").exists() else None,
            },
            "links": {
                "proposed_html": f"{raw_base}/cv_proposed.html" if proposed_html.exists() else None,
                "final_html": f"{raw_base}/final.html" if final_exists else None,
                "final_pdf": f"{raw_base}/final.pdf" if (package_dir / "final.pdf").exists() else None,
            },
        }
        _write_json(package_dir / "handoff.json", manifest)
        built.append(vacancy_id)

    refreshed_existing = _refresh_existing_packages(
        handoff_dir,
        evidence_state=evidence_state,
    )
    index = rebuild_index(handoff_dir, repository=repository)
    return {
        "built": built,
        "refreshed_existing": refreshed_existing,
        "skipped": skipped,
        "index": index,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build versioned ChatGPT Work final-review packages.")
    parser.add_argument("--batch-report", required=True)
    parser.add_argument("--outputs", default="outputs/auto")
    parser.add_argument("--vacancy-state", default="vacancy_state")
    parser.add_argument("--template-file", default="cv_presentation/templates/technical_modern_v1.html.j2")
    parser.add_argument("--handoff-dir", default="handoff")
    parser.add_argument("--generation-manifest", default="generation_state/manifest.json")
    parser.add_argument("--evidence-state", default="rag_state")
    parser.add_argument("--public-identity", default="cv_presentation/identity.public.yaml")
    parser.add_argument("--repository", default="jcval94/CV_fit")
    args = parser.parse_args()

    report = build_handoffs(
        batch_report=Path(args.batch_report),
        outputs=Path(args.outputs),
        vacancy_state=Path(args.vacancy_state),
        template_file=Path(args.template_file),
        handoff_dir=Path(args.handoff_dir),
        generation_manifest=Path(args.generation_manifest),
        evidence_state=Path(args.evidence_state),
        public_identity=Path(args.public_identity),
        repository=args.repository,
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
