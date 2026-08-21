from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from cv_agent.adk_runtime import AdkStructuredClient
from cv_presentation.application_bundle import build_application_bundle


def _read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def finalize_batch(
    *,
    batch_report: Path,
    outputs: Path,
    vacancy_state: Path,
    generation_state: Path,
    identity_public: Path,
    brand_profiles_dir: Path,
    max_design_cost_usd: float,
) -> dict[str, Any]:
    batch = _read_json(batch_report)
    manifest_path = generation_state / "manifest.json"
    manifest = _read_json(manifest_path, {"entries": {}})
    entries = manifest.setdefault("entries", {})
    client = AdkStructuredClient(max_estimated_cost_usd=max_design_cost_usd)
    results: list[dict[str, Any]] = []

    for item in batch.get("results", []):
        vacancy_id = str(item.get("vacancy_id") or "")
        run_id = item.get("run_id")
        if not vacancy_id or not run_id:
            results.append({"vacancy_id": vacancy_id, "status": "SKIPPED_NO_FRESH_OUTPUT"})
            continue
        vacancy_path = vacancy_state / "records" / f"{vacancy_id}.json"
        run_dir = outputs / vacancy_id / str(run_id)
        if not vacancy_path.exists() or not (run_dir / "cv_final.json").exists():
            results.append({"vacancy_id": vacancy_id, "status": "SKIPPED_MISSING_OUTPUT"})
            continue

        vacancy = _read_json(vacancy_path)
        try:
            report = build_application_bundle(
                vacancy=vacancy,
                run_dir=run_dir,
                identity_public_path=identity_public,
                brand_profiles_dir=brand_profiles_dir,
                design_client=client,
            )
            status = "PASS" if report.ready_to_send else "REVIEW_REQUIRED"
            results.append({
                "vacancy_id": vacancy_id,
                "run_id": run_id,
                "status": status,
                "ready_to_send": report.ready_to_send,
                "application_bundle_file": str(run_dir / "application_bundle_report.json"),
            })
            entry = entries.setdefault(vacancy_id, {})
            entry["content_quality_target_reached"] = report.content_quality_target_reached
            entry["presentation_gate"] = {
                "primary_template": report.primary_template,
                "primary_physical_status": next(x.physical_status for x in report.templates if x.role == "primary"),
                "alternate_template": report.alternate_template,
                "alternate_physical_status": next(x.physical_status for x in report.templates if x.role == "alternate"),
                "cover_letter_ready": report.cover_letter_ready,
                "reasons": report.reasons,
            }
            entry["ready_to_send"] = report.ready_to_send
            entry["review_required"] = not report.ready_to_send
            entry["application_bundle_file"] = "application_bundle_report.json"
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"[:2000]
            results.append({
                "vacancy_id": vacancy_id,
                "run_id": run_id,
                "status": "FAILED_PRESENTATION_GATE",
                "ready_to_send": False,
                "error": error,
            })
            entry = entries.setdefault(vacancy_id, {})
            entry["ready_to_send"] = False
            entry["review_required"] = True
            entry["presentation_gate"] = {"status": "FAIL", "error": error}

    _write_json(manifest_path, manifest)
    summary = {
        "schema_version": 1,
        "source_batch_run_id": batch.get("run_id"),
        "result_counts": {
            status: sum(x["status"] == status for x in results)
            for status in sorted({x["status"] for x in results})
        },
        "design_usage": client.telemetry_snapshot(),
        "results": results,
    }
    output_path = batch_report.parent / "application_bundle_batch_report.json"
    _write_json(output_path, summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Build branded+Harvard HTML/PDF bundles and finalize ready_to_send.")
    parser.add_argument("--batch-report", required=True)
    parser.add_argument("--outputs", default="outputs/auto")
    parser.add_argument("--vacancy-state", default="vacancy_state")
    parser.add_argument("--generation-state", default="generation_state")
    parser.add_argument("--identity-public", default="cv_presentation/identity.public.yaml")
    parser.add_argument("--brand-profiles-dir", default="cv_presentation/brands")
    parser.add_argument("--max-design-cost-usd", type=float, default=2.0)
    args = parser.parse_args()
    if args.max_design_cost_usd <= 0:
        parser.error("--max-design-cost-usd must be > 0")

    report = finalize_batch(
        batch_report=Path(args.batch_report),
        outputs=Path(args.outputs),
        vacancy_state=Path(args.vacancy_state),
        generation_state=Path(args.generation_state),
        identity_public=Path(args.identity_public),
        brand_profiles_dir=Path(args.brand_profiles_dir),
        max_design_cost_usd=args.max_design_cost_usd,
    )
    print(json.dumps({"result_counts": report["result_counts"]}, ensure_ascii=False, sort_keys=True))
    return 0 if not report["result_counts"].get("FAILED_PRESENTATION_GATE") else 2


if __name__ == "__main__":
    raise SystemExit(main())
