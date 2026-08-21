from __future__ import annotations

import argparse
import json
from pathlib import Path

from cv_presentation.build import build_presentation_model, load_cv_document, load_presentation_config
from cv_presentation.fit import fit_presentation_model
from cv_presentation.identity import resolve_candidate_identity


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build and deterministically fit a presentation-ready CV model without rendering HTML/PDF."
    )
    parser.add_argument("--cv", required=True, help="cv_final.json or a raw CVDocument JSON")
    parser.add_argument("--config", default=None, help="presentation YAML; defaults to the built-in contract")
    parser.add_argument("--identity-public", default=None, help="public-safe identity YAML; private contact is rejected")
    parser.add_argument("--include-private-contact", action="store_true")
    parser.add_argument("--artifact-visibility", choices=["public", "private"], default="public")
    parser.add_argument("--allow-private-in-public-artifact", action="store_true")
    parser.add_argument("--output", required=True)
    parser.add_argument("--fit-report", required=True)
    args = parser.parse_args()

    cv = load_cv_document(Path(args.cv))
    config = load_presentation_config(Path(args.config) if args.config else None)
    identity_resolution = resolve_candidate_identity(
        public_identity_path=Path(args.identity_public) if args.identity_public else None,
        include_private_contact=args.include_private_contact,
        artifact_visibility=args.artifact_visibility,
        allow_private_in_public_artifact=args.allow_private_in_public_artifact,
    )
    model = build_presentation_model(cv, candidate=identity_resolution.identity, config=config)
    fitted, report = fit_presentation_model(model)
    _write_json(Path(args.output), fitted.model_dump(mode="json"))
    _write_json(Path(args.fit_report), report.model_dump(mode="json"))
    print(json.dumps({
        "status": report.status,
        "estimated_line_units_before": report.estimated_line_units_before,
        "estimated_line_units_after": report.estimated_line_units_after,
        "estimated_line_budget": report.estimated_line_budget,
        "omissions": len(report.omissions),
        "private_fields_included": identity_resolution.private_fields_included,
    }, sort_keys=True))
    return 0 if report.status == "FIT" else 2
