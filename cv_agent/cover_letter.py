from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel

from cv_agent.model_policy import model_ids
from cv_agent.prompts import COVER_LETTER_INSTRUCTION
from cv_agent.schemas import CVDocument, CoverLetterDocument


class StructuredCoverLetterClient(Protocol):
    async def call(
        self,
        *,
        name: str,
        model: str,
        instruction: str,
        payload: dict,
        output_schema: type[BaseModel],
        max_output_tokens: int = 2500,
    ) -> BaseModel: ...


def collect_cv_evidence_refs(cv: CVDocument) -> set[str]:
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


def _compact_cv(cv: CVDocument) -> dict[str, Any]:
    return {
        "headline": cv.headline.model_dump(),
        "summary": cv.summary.model_dump(),
        "experience": [item.model_dump() for item in cv.experience],
        "projects": [item.model_dump() for item in cv.projects],
        "skills": [item.model_dump() for item in cv.skills],
        "education": [item.model_dump() for item in cv.education],
        "certifications": [item.model_dump() for item in cv.certifications],
    }


def validate_cover_letter(
    letter: CoverLetterDocument,
    *,
    vacancy: dict[str, Any],
    allowed_evidence_refs: set[str],
) -> None:
    expected_language = vacancy.get("application_language")
    expected_company = str(vacancy.get("company") or "").strip()
    expected_role = str(vacancy.get("role_title") or "").strip()
    if letter.language != expected_language:
        raise ValueError(f"cover letter language {letter.language!r} != application language {expected_language!r}")
    if letter.company.casefold().strip() != expected_company.casefold():
        raise ValueError(f"cover letter company {letter.company!r} != vacancy company {expected_company!r}")
    if letter.role.casefold().strip() != expected_role.casefold():
        raise ValueError(f"cover letter role {letter.role!r} != vacancy role {expected_role!r}")

    words = sum(len(paragraph.text.split()) for paragraph in letter.paragraphs)
    if words > 200:
        raise ValueError(f"cover letter exceeds 200-word paragraph budget: {words}")

    unknown: set[str] = set()
    for paragraph in letter.paragraphs:
        unknown.update(set(paragraph.evidence_refs) - allowed_evidence_refs)
    if unknown:
        raise ValueError(f"cover letter used evidence refs outside final CV: {sorted(unknown)}")


def render_cover_letter_markdown(letter: CoverLetterDocument) -> str:
    lines = [letter.salutation.strip(), ""]
    for paragraph in letter.paragraphs:
        lines.extend([paragraph.text.strip(), ""])
    lines.append(letter.closing.strip())
    return "\n".join(lines).strip() + "\n"


async def generate_cover_letter(
    *,
    client: StructuredCoverLetterClient,
    vacancy: dict[str, Any],
    final_cv: CVDocument,
    output_dir: Path | None = None,
) -> CoverLetterDocument:
    allowed = collect_cv_evidence_refs(final_cv)
    if not allowed:
        raise ValueError("final CV contains no evidence refs for cover-letter grounding")
    models = model_ids()
    result = await client.call(
        name="cover_letter_writer",
        model=models["economy"],
        instruction=COVER_LETTER_INSTRUCTION,
        payload={
            "application_language": vacancy.get("application_language"),
            "vacancy": {
                "company": vacancy.get("company"),
                "role_title": vacancy.get("role_title"),
                "location": vacancy.get("location"),
                "requirements": vacancy.get("requirements", []),
                "responsibilities": vacancy.get("responsibilities", []),
            },
            "final_cv": _compact_cv(final_cv),
            "approved_evidence_ids": sorted(allowed),
        },
        output_schema=CoverLetterDocument,
        max_output_tokens=2200,
    )
    assert isinstance(result, CoverLetterDocument)
    validate_cover_letter(result, vacancy=vacancy, allowed_evidence_refs=allowed)
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "cover_letter_final.json").write_text(
            result.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )
        (output_dir / "cover_letter_final.md").write_text(
            render_cover_letter_markdown(result), encoding="utf-8"
        )
    return result
