from __future__ import annotations

import argparse
import html
import json
import shutil
from pathlib import Path
from typing import Any


def _read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _safe(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def _source_date_matches(record: dict[str, Any], target_date: str) -> bool:
    for item in record.get("provenance", []):
        if str(item.get("source_search_date") or "") == target_date:
            return True
        if str(item.get("source_updated_at") or "").startswith(target_date):
            return True
        if target_date in str(item.get("source_path") or ""):
            return True
    return False


def _copy_public_artifacts(run_dir: Path, destination: Path, bundle: dict[str, Any]) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    allowed = {"application_bundle_report.json", "cover_letter_final.md"}
    for template in bundle.get("templates", []):
        for key in (
            "html_file",
            "pdf_file",
            "screenshot_file",
            "fit_report_file",
            "design_report_file",
            "physical_report_file",
        ):
            name = template.get(key)
            if name:
                allowed.add(str(name))
    for name in sorted(allowed):
        source = run_dir / name
        if source.exists() and source.is_file():
            shutil.copy2(source, destination / source.name)


def _detail_page(record: dict[str, Any], bundle: dict[str, Any] | None, run_report: dict[str, Any] | None) -> str:
    company = _safe(record.get("company"))
    role = _safe(record.get("role_title"))
    url = _safe(record.get("url"))
    fit = record.get("fit_score")
    coverage = (run_report or {}).get("match_coverage_score")
    fidelity = _safe(record.get("jd_fidelity"))

    preview_html = ""
    cover = ""
    if bundle:
        cards = []
        for item in bundle.get("templates", []):
            label = "Branded / primary" if item.get("role") == "primary" else "Harvard / alternate"
            cards.append(f"""
            <article class="preview-card">
              <div class="preview-head"><h2>{_safe(label)}</h2><span>{_safe(item.get('physical_status'))} · {_safe(item.get('expected_pages'))} page(s)</span></div>
              <iframe title="{_safe(label)} CV" src="{_safe(item.get('html_file'))}"></iframe>
              <div class="buttons">
                <a href="{_safe(item.get('html_file'))}" target="_blank" rel="noopener">Open HTML</a>
                <a href="{_safe(item.get('pdf_file'))}" target="_blank" rel="noopener">Open PDF</a>
                <a href="{_safe(item.get('physical_report_file'))}" target="_blank" rel="noopener">Layout report</a>
              </div>
            </article>
            """)
        preview_html = '<section class="previews">' + "".join(cards) + "</section>"
        cover = '<p><a class="cover" href="cover_letter_final.md" target="_blank" rel="noopener">View concise cover letter</a></p>'
    else:
        preview_html = "<div class=\"empty\">No public CV bundle was generated for this vacancy in the current daily run.</div>"

    status = "READY TO SEND" if bundle and bundle.get("ready_to_send") else "REVIEW / BLOCKED"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{company} — {role}</title>
<style>
body{{margin:0;background:#f3f4f6;color:#111827;font:15px/1.5 Arial,Helvetica,sans-serif}}main{{max-width:1500px;margin:auto;padding:28px}}a{{color:#0f4c81}}.back{{display:inline-block;margin-bottom:18px}}.hero{{background:white;border:1px solid #e5e7eb;border-radius:16px;padding:22px;margin-bottom:22px}}h1{{margin:0 0 8px;font-size:28px}}.meta{{display:flex;gap:10px;flex-wrap:wrap;color:#4b5563}}.pill{{background:#eef2ff;border-radius:999px;padding:4px 9px}}.status{{font-weight:700}}.previews{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}.preview-card{{background:white;border:1px solid #e5e7eb;border-radius:16px;overflow:hidden}}.preview-head{{display:flex;justify-content:space-between;align-items:center;padding:14px 16px;border-bottom:1px solid #e5e7eb}}.preview-head h2{{font-size:17px;margin:0}}iframe{{width:100%;height:900px;border:0;background:#ddd}}.buttons{{display:flex;gap:8px;flex-wrap:wrap;padding:12px 16px}}.buttons a,.cover{{text-decoration:none;border:1px solid #d1d5db;background:#fff;border-radius:8px;padding:7px 10px}}.empty{{background:#fff;border:1px dashed #9ca3af;padding:30px;border-radius:14px}}@media(max-width:900px){{.previews{{grid-template-columns:1fr}}iframe{{height:720px}}}}
</style></head><body><main>
<a class="back" href="../../index.html">← Today's vacancies</a>
<section class="hero"><h1>{company}</h1><h2>{role}</h2><div class="meta"><span class="pill">source fit: {_safe(fit if fit is not None else 'n/a')}</span><span class="pill">deterministic coverage: {_safe(coverage if coverage is not None else 'n/a')}</span><span class="pill">JD: {fidelity}</span><span class="pill status">{_safe(status)}</span></div><p><a href="{url}" target="_blank" rel="noopener">Open original vacancy / apply</a></p>{cover}</section>
{preview_html}
</main></body></html>"""


def build_showcase(
    *,
    target_date: str,
    vacancy_state: Path,
    bundle_batch_report: Path,
    outputs: Path,
    site_dir: Path,
) -> dict[str, Any]:
    if site_dir.exists():
        shutil.rmtree(site_dir)
    site_dir.mkdir(parents=True, exist_ok=True)
    batch = _read_json(bundle_batch_report, {"results": []})
    batch_by_id = {str(item.get("vacancy_id")): item for item in batch.get("results", []) if item.get("vacancy_id")}

    records = []
    for path in sorted((vacancy_state / "records").glob("*.json")):
        record = _read_json(path)
        if _source_date_matches(record, target_date):
            records.append(record)
    records.sort(key=lambda item: (-(float(item.get("fit_score") or 0)), str(item.get("company") or "")))

    cards: list[str] = []
    summary_rows: list[dict[str, Any]] = []
    for record in records:
        vacancy_id = str(record["vacancy_id"])
        batch_item = batch_by_id.get(vacancy_id)
        bundle = None
        run_report = None
        detail_dir = site_dir / "vacancies" / vacancy_id
        if batch_item and batch_item.get("run_id"):
            run_dir = outputs / vacancy_id / str(batch_item["run_id"])
            bundle_path = run_dir / "application_bundle_report.json"
            if bundle_path.exists():
                bundle = _read_json(bundle_path)
                _copy_public_artifacts(run_dir, detail_dir, bundle)
                if (run_dir / "run_report.json").exists():
                    run_report = _read_json(run_dir / "run_report.json")
        detail_dir.mkdir(parents=True, exist_ok=True)
        _write(detail_dir / "index.html", _detail_page(record, bundle, run_report))

        ready = bool(bundle and bundle.get("ready_to_send"))
        status = "READY" if ready else (batch_item or {}).get("status", "NOT GENERATED")
        primary_link = f"vacancies/{vacancy_id}/cv_primary.html" if bundle else None
        harvard_link = f"vacancies/{vacancy_id}/cv_alternate.html" if bundle else None
        links = [f'<a href="vacancies/{_safe(vacancy_id)}/index.html">Details</a>']
        if primary_link:
            links.append(f'<a href="{_safe(primary_link)}" target="_blank">Branded HTML</a>')
        if harvard_link:
            links.append(f'<a href="{_safe(harvard_link)}" target="_blank">Harvard HTML</a>')
        links.append(f'<a href="{_safe(record.get("url"))}" target="_blank" rel="noopener">Vacancy</a>')
        cards.append(f"""
        <article class="card">
          <div class="top"><div><h2>{_safe(record.get('company'))}</h2><h3>{_safe(record.get('role_title'))}</h3></div><span class="status {'ready' if ready else 'review'}">{_safe(status)}</span></div>
          <div class="meta"><span>source fit {_safe(record.get('fit_score') if record.get('fit_score') is not None else 'n/a')}</span><span>JD {_safe(record.get('jd_fidelity'))}</span><span>{_safe(record.get('work_model'))}</span><span>{_safe(record.get('location_raw') or record.get('city'))}</span></div>
          <p>{_safe(record.get('fit_summary') or record.get('description') or '')}</p>
          <div class="links">{' '.join(links)}</div>
        </article>
        """)
        summary_rows.append({
            "vacancy_id": vacancy_id,
            "company": record.get("company"),
            "role_title": record.get("role_title"),
            "url": record.get("url"),
            "fit_score": record.get("fit_score"),
            "jd_fidelity": record.get("jd_fidelity"),
            "generation_status": status,
            "ready_to_send": ready,
            "has_branded_html": bool(primary_link),
            "has_harvard_html": bool(harvard_link),
        })

    index = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CV_fit — vacancies {html.escape(target_date)}</title>
<style>
body{{margin:0;background:#f6f7fb;color:#111827;font:15px/1.5 Arial,Helvetica,sans-serif}}main{{max-width:1180px;margin:auto;padding:36px 22px 70px}}header{{margin-bottom:26px}}h1{{font-size:34px;margin:0}}header p{{color:#4b5563;max-width:760px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}}.card{{background:white;border:1px solid #e5e7eb;border-radius:16px;padding:18px;box-shadow:0 3px 14px rgba(0,0,0,.035)}}.top{{display:flex;justify-content:space-between;gap:12px}}h2{{margin:0;font-size:20px}}h3{{margin:4px 0 0;font-size:15px;font-weight:600;color:#374151}}.status{{height:max-content;border-radius:999px;padding:4px 8px;font-size:11px;font-weight:800}}.ready{{background:#dcfce7;color:#166534}}.review{{background:#fef3c7;color:#92400e}}.meta{{display:flex;gap:6px;flex-wrap:wrap;margin:13px 0}}.meta span{{background:#f3f4f6;border-radius:999px;padding:3px 7px;font-size:12px;color:#4b5563}}.card p{{font-size:13px;color:#4b5563;min-height:38px}}.links{{display:flex;flex-wrap:wrap;gap:7px}}.links a{{text-decoration:none;border:1px solid #d1d5db;border-radius:8px;padding:6px 8px;color:#0f4c81;background:white}}.note{{margin-top:24px;padding:14px;border-left:4px solid #9ca3af;background:#fff;color:#4b5563}}
</style></head><body><main><header><h1>Today's CV_fit vacancies</h1><p>Search date <strong>{html.escape(target_date)}</strong>. Source fit and deterministic evidence coverage are intentionally separate. A CV is marked ready only after content quality, cover letter, design review and Chromium/PDF physical-layout gates pass.</p></header><section class="grid">{''.join(cards)}</section><div class="note">Public preview uses only the repository's public-safe candidate identity. Private contact details are never published here.</div></main></body></html>"""
    _write(site_dir / "index.html", index)
    _write(site_dir / "showcase.json", json.dumps({"date": target_date, "vacancies": summary_rows}, ensure_ascii=False, indent=2) + "\n")
    _write(site_dir / ".nojekyll", "")
    return {"date": target_date, "vacancy_count": len(summary_rows), "ready_count": sum(x["ready_to_send"] for x in summary_rows), "vacancies": summary_rows}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a static GitHub Pages showcase for one vacancy search date.")
    parser.add_argument("--date", required=True)
    parser.add_argument("--vacancy-state", default="vacancy_state")
    parser.add_argument("--bundle-batch-report", required=True)
    parser.add_argument("--outputs", default="outputs/auto")
    parser.add_argument("--site-dir", default="_site")
    args = parser.parse_args()
    report = build_showcase(
        target_date=args.date,
        vacancy_state=Path(args.vacancy_state),
        bundle_batch_report=Path(args.bundle_batch_report),
        outputs=Path(args.outputs),
        site_dir=Path(args.site_dir),
    )
    print(json.dumps({"date": report["date"], "vacancy_count": report["vacancy_count"], "ready_count": report["ready_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
