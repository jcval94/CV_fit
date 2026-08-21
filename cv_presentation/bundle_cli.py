from __future__ import annotations

import argparse
import json
from pathlib import Path

from cv_agent.adk_runtime import AdkStructuredClient
from cv_presentation.application_bundle import build_application_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description="Build branded and Harvard HTML/PDF variants and run the physical presentation gate.")
    parser.add_argument("--vacancy-id", required=True)
    parser.add_argument("--vacancy-state", default="vacancy_state")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--identity-public", default="cv_presentation/identity.public.yaml")
    parser.add_argument("--brand-profiles-dir", default="cv_presentation/brands")
    parser.add_argument("--max-design-cost-usd", type=float, default=0.5)
    args = parser.parse_args()
    if args.max_design_cost_usd <= 0:
        parser.error("--max-design-cost-usd must be > 0")

    vacancy_path = Path(args.vacancy_state) / "records" / f"{args.vacancy_id}.json"
    vacancy = json.loads(vacancy_path.read_text(encoding="utf-8"))
    client = AdkStructuredClient(max_estimated_cost_usd=args.max_design_cost_usd)
    report = build_application_bundle(
        vacancy=vacancy,
        run_dir=Path(args.run_dir),
        identity_public_path=Path(args.identity_public),
        brand_profiles_dir=Path(args.brand_profiles_dir),
        design_client=client,
    )
    usage_path = Path(args.run_dir) / "design_usage_report.json"
    usage_path.write_text(json.dumps(client.telemetry_snapshot(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "vacancy_id": report.vacancy_id,
        "ready_to_send": report.ready_to_send,
        "primary_template": report.primary_template,
        "alternate_template": report.alternate_template,
        "reasons": report.reasons,
    }, ensure_ascii=False, sort_keys=True))
    return 0 if report.ready_to_send else 2


if __name__ == "__main__":
    raise SystemExit(main())
