from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from cv_agent.adk_runtime import AdkStructuredClient
from cv_presentation.branding import resolve_brand_profile, tokens_from_brand, validate_design_tokens
from cv_presentation.design_agent import DesignReview, review_design
from cv_presentation.render_html import write_html
from cv_presentation.schemas import CVPresentationModel
from cv_presentation.templates import get_template_policy


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a fitted CVPresentationModel to a reviewed US-Letter HTML template.")
    parser.add_argument("--presentation", required=True, help="fitted CVPresentationModel JSON")
    parser.add_argument("--company", required=True, help="target vacancy company")
    parser.add_argument("--brand-profile", default=None, help="explicit verified/manual company brand YAML")
    parser.add_argument("--brand-profiles-dir", default="cv_presentation/brands")
    parser.add_argument("--live-design-review", action="store_true", help="use the OpenAI-backed design reviewer before rendering")
    parser.add_argument("--max-design-cost-usd", type=float, default=0.25)
    parser.add_argument("--output", required=True)
    parser.add_argument("--design-report", required=True)
    args = parser.parse_args()

    model = CVPresentationModel.model_validate_json(Path(args.presentation).read_text(encoding="utf-8"))
    policy = get_template_policy(model.document.template_id)
    profile = resolve_brand_profile(
        company=args.company,
        explicit_path=Path(args.brand_profile) if args.brand_profile else None,
        profiles_dir=Path(args.brand_profiles_dir) if args.brand_profiles_dir else None,
    )
    tokens = tokens_from_brand(profile)
    deterministic = validate_design_tokens(tokens)

    design_review: DesignReview | None = None
    usage = None
    if policy.locked_visual_system:
        # Harvard never spends a model call because the design is intentionally immutable.
        design_review, deterministic = asyncio.run(
            review_design(
                client=AdkStructuredClient(max_estimated_cost_usd=args.max_design_cost_usd),
                template_id=model.document.template_id,
                tokens=tokens,
                target_pages=model.document.target_pages,
            )
        )
    elif args.live_design_review:
        client = AdkStructuredClient(max_estimated_cost_usd=args.max_design_cost_usd)
        design_review, deterministic = asyncio.run(
            review_design(
                client=client,
                template_id=model.document.template_id,
                tokens=tokens,
                target_pages=model.document.target_pages,
            )
        )
        usage = client.telemetry_snapshot()
    elif not deterministic.passed:
        raise ValueError("brand tokens fail deterministic contrast checks; live design review cannot override unsafe contrast")

    write_html(model, Path(args.output), tokens=tokens, design_review=design_review)
    report = {
        "template_id": model.document.template_id,
        "template_source": policy.source_name,
        "locked_visual_system": policy.locked_visual_system,
        "company": args.company,
        "brand_verified": tokens.brand_verified,
        "brand_source_kind": tokens.brand_source_kind,
        "brand_source_url": tokens.brand_source_url,
        "deterministic_validation": deterministic.model_dump(mode="json"),
        "design_review": design_review.model_dump(mode="json") if design_review else None,
        "design_usage": usage,
        "target_pages": model.document.target_pages,
        "page_size": model.document.page_size,
    }
    _write_json(Path(args.design_report), report)
    print(json.dumps({
        "template_id": report["template_id"],
        "brand_verified": report["brand_verified"],
        "contrast_passed": deterministic.passed,
        "design_review": design_review.decision if design_review else "NOT_RUN",
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
