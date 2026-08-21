from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, Field

from cv_agent.model_policy import model_ids
from cv_presentation.branding import DesignTokens, DesignValidation, validate_design_tokens


DESIGN_REVIEW_INSTRUCTION = """
You are a conservative document design reviewer for professional CVs.
You do NOT invent brand colors, logos, fonts, or corporate identity from memory.
You receive already-resolved brand tokens plus deterministic contrast checks.

Review only:
- legibility and hierarchy on US Letter pages;
- whether supplied brand colors are safe for headings, accents, sidebars and small text;
- whether the supplied font stacks are professional and readable;
- whether the requested density is plausible for a CV;
- ATS safety and print clarity.

Hard rules:
- Never claim unverified tokens are official or institutional.
- Never output a color that was not supplied in the input.
- If contrast checks fail, require revision and recommend limiting failing colors to non-text accents rather than changing the brand palette.
- Never alter the Harvard template. For Harvard, return PASS with preserve_template=true and no style changes.
- Avoid decorative charts, skill bars, photos and dense iconography.
""".strip()


class DesignReview(BaseModel):
    decision: Literal["PASS", "REVISE"]
    preserve_template: bool = False
    primary_usage: Literal["headings_and_accents", "accents_only", "sidebar_background"] = "headings_and_accents"
    secondary_usage: Literal["headings_and_accents", "accents_only", "sidebar_background"] = "accents_only"
    density_adjustment: Literal["none", "compact", "normal"] = "none"
    ats_safe: bool
    print_safe: bool
    notes: list[str] = Field(default_factory=list)


class StructuredDesignClient(Protocol):
    async def call(self, *, name: str, model: str, instruction: str, payload: dict, output_schema: type[BaseModel], max_output_tokens: int = 2000) -> BaseModel: ...


async def review_design(
    *,
    client: StructuredDesignClient,
    template_id: str,
    tokens: DesignTokens,
    target_pages: int,
) -> tuple[DesignReview, DesignValidation]:
    validation = validate_design_tokens(tokens)
    if template_id == "harvard_v1":
        return (
            DesignReview(
                decision="PASS",
                preserve_template=True,
                ats_safe=True,
                print_safe=True,
                notes=["Harvard visual system is locked; only content may change."],
            ),
            validation,
        )

    models = model_ids()
    result = await client.call(
        name="cv_design_reviewer",
        model=models["economy"],
        instruction=DESIGN_REVIEW_INSTRUCTION,
        payload={
            "template_id": template_id,
            "target_pages": target_pages,
            "brand_tokens": tokens.model_dump(),
            "deterministic_contrast": validation.model_dump(),
        },
        output_schema=DesignReview,
        max_output_tokens=1600,
    )
    assert isinstance(result, DesignReview)
    if not validation.passed and result.decision == "PASS":
        raise ValueError("design reviewer cannot PASS tokens that fail deterministic contrast validation")
    if result.preserve_template:
        raise ValueError("preserve_template is reserved for harvard_v1")
    return result, validation
