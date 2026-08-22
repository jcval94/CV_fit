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


def _pct(value: Any) -> str:
    try:
        return f"{float(value) * 100:.0f}%"
    except (TypeError, ValueError):
        return "n/a"


def _status_class(value: Any) -> str:
    normalized = str(value or "").upper()
    return "ok" if normalized in {"PASS", "READY", "READY TO SEND"} else "warn"


def _source_date_matches(record: dict[str, Any], target_date: str) -> bool:
    for item in record.get("provenance", []):
        if str(item.get("source_search_date") or "") == target_date:
            return True
        if str(item.get("source_updated_at") or "").startswith(target_date):
            return True
        if target_date in str(item.get("source_path") or ""):
            return True
    return False


def _primary(bundle: dict[str, Any] | None) -> dict[str, Any]:
    if not bundle:
        return {}
    return next((item for item in bundle.get("templates", []) if item.get("role") == "primary"), {})


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
            "visual_eval_file",
            "presentation_review_file",
        ):
            name = template.get(key)
            if name:
                allowed.add(str(name))
    for name in sorted(allowed):
        source = run_dir / name
        if source.exists() and source.is_file():
            shutil.copy2(source, destination / source.name)


def _metric(label: str, value: Any, *, status: bool = False) -> str:
    cls = f"metric-value {_status_class(value)}" if status else "metric-value"
    return f'<div class="metric"><span>{_safe(label)}</span><strong class="{cls}">{_safe(value)}</strong></div>'


def _detail_page(
    record: dict[str, Any],
    bundle: dict[str, Any] | None,
    run_report: dict[str, Any] | None,
) -> str:
    company = _safe(record.get("company"))
    role = _safe(record.get("role_title"))
    vacancy_id = _safe(record.get("vacancy_id"))
    url = _safe(record.get("url"))
    fit = record.get("fit_score")
    coverage = (run_report or {}).get("match_coverage_score")
    fidelity = _safe(record.get("jd_fidelity"))
    final_review = (run_report or {}).get("final_review", {})
    final_validation = (run_report or {}).get("final_validation", {})

    primary = _primary(bundle)
    page_util = list(primary.get("page_utilization") or [])
    ratios = dict(primary.get("section_area_ratios") or {})
    counts = dict(primary.get("section_item_counts") or {})

    preview_html = ""
    cover = ""
    if bundle:
        cards = []
        for item in bundle.get("templates", []):
            label = "Technical Modern / primary" if item.get("role") == "primary" else "Harvard Executive / alternate"
            status_line = (
                f"physical {_safe(item.get('physical_status'))} · visual {_safe(item.get('visual_status'))} · "
                f"review {_safe(item.get('presentation_review_status'))} · {_safe(item.get('expected_pages'))} page(s)"
            )
            buttons = [
                f'<a href="{_safe(item.get("html_file"))}" target="_blank" rel="noopener">Open HTML</a>',
                f'<a href="{_safe(item.get("pdf_file"))}" target="_blank" rel="noopener">Open PDF</a>',
                f'<a href="{_safe(item.get("physical_report_file"))}" target="_blank" rel="noopener">Physical</a>',
                f'<a href="{_safe(item.get("visual_eval_file"))}" target="_blank" rel="noopener">Visual eval</a>',
                f'<a href="{_safe(item.get("presentation_review_file"))}" target="_blank" rel="noopener">Presentation review</a>',
            ]
            cards.append(f"""
            <article class="preview-card">
              <div class="preview-head"><h2>{_safe(label)}</h2><span>{status_line}</span></div>
              <iframe title="{_safe(label)} CV" src="{_safe(item.get('html_file'))}"></iframe>
              <div class="buttons">{''.join(buttons)}</div>
            </article>
            """)
        preview_html = '<section class="previews">' + "".join(cards) + "</section>"
        cover = '<a class="action-link" href="cover_letter_final.md" target="_blank" rel="noopener">Cover letter</a>'
    else:
        preview_html = '<div class="empty">No public CV bundle was generated for this vacancy in the current run.</div>'

    status = "READY TO SEND" if bundle and bundle.get("ready_to_send") else "REVIEW REQUIRED"
    content_metrics = "".join([
        _metric("Headhunter", final_review.get("overall_score", "n/a")),
        _metric("Factual", final_validation.get("factual", {}).get("status", "n/a"), status=True),
        _metric("Editorial", final_validation.get("editorial", {}).get("status", "n/a"), status=True),
        _metric("Language", final_validation.get("language", {}).get("status", "n/a"), status=True),
    ])
    presentation_metrics = "".join([
        _metric("Physical layout", primary.get("physical_status", "n/a"), status=True),
        _metric("Visual balance", primary.get("visual_status", "n/a"), status=True),
        _metric("Presentation reviewer", primary.get("presentation_review_status", "n/a"), status=True),
        _metric("Pages", primary.get("expected_pages", "n/a")),
        _metric("Page 1 use", _pct(page_util[0]) if len(page_util) >= 1 else "n/a"),
        _metric("Page 2 use", _pct(page_util[1]) if len(page_util) >= 2 else "—"),
        _metric("Experience area", _pct(ratios.get("experience"))),
        _metric("Skills area", _pct(ratios.get("skills"))),
        _metric("Projects area", _pct(ratios.get("projects"))),
        _metric("Experience items", counts.get("experience", "n/a")),
        _metric("Skills", counts.get("skills", "n/a")),
        _metric("Projects", counts.get("projects", "n/a")),
        _metric("Certifications", counts.get("certifications", "n/a")),
    ])

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{company} — {role}</title>
<style>
:root{{--ink:#111827;--muted:#64748b;--line:#e2e8f0;--panel:#fff;--bg:#f4f6f8;--ok:#166534;--okbg:#dcfce7;--warn:#92400e;--warnbg:#fef3c7}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 Arial,Helvetica,sans-serif}}main{{max-width:1540px;margin:auto;padding:28px}}a{{color:#0f4c81}}.back{{display:inline-block;margin-bottom:16px}}.hero,.panel,.preview-card{{background:var(--panel);border:1px solid var(--line);border-radius:14px}}.hero{{padding:22px;margin-bottom:16px}}h1{{margin:0;font-size:28px}}h2{{margin:5px 0 0}}.meta{{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}}.pill{{background:#eef2f7;border-radius:999px;padding:4px 9px;color:#475569}}.overall{{font-weight:800}}.dash{{display:grid;grid-template-columns:1fr 1.4fr;gap:16px;margin-bottom:20px}}.panel{{padding:17px}}.panel h3{{margin:0 0 10px;font-size:14px;text-transform:uppercase;letter-spacing:.7px}}.metric-grid{{display:grid;grid-template-columns:repeat(2,minmax(130px,1fr));gap:1px;background:var(--line);border:1px solid var(--line);border-radius:10px;overflow:hidden}}.metric{{background:#fff;padding:9px 11px;display:flex;justify-content:space-between;gap:12px}}.metric span{{color:var(--muted)}}.metric-value.ok{{color:var(--ok)}}.metric-value.warn{{color:var(--warn)}}.review-box{{margin-top:13px;padding:12px;background:#f8fafc;border:1px solid var(--line);border-radius:10px}}.review-actions{{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}}button,.action-link,.buttons a{{border:1px solid #cbd5e1;background:#fff;border-radius:8px;padding:7px 10px;text-decoration:none;color:#0f4c81;cursor:pointer}}button[data-decision="SEND"]{{border-color:#86efac}}button[data-decision="REVISE"]{{border-color:#fde68a}}button[data-decision="REJECT"]{{border-color:#fecaca}}.review-current{{font-weight:700}}.small{{font-size:12px;color:var(--muted)}}.previews{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}.preview-card{{overflow:hidden}}.preview-head{{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:12px 14px;border-bottom:1px solid var(--line)}}.preview-head h2{{font-size:16px;margin:0}}.preview-head span{{font-size:12px;color:var(--muted);text-align:right}}iframe{{width:100%;height:900px;border:0;background:#ddd}}.buttons{{display:flex;gap:7px;flex-wrap:wrap;padding:11px 14px}}.empty{{background:#fff;border:1px dashed #94a3b8;padding:30px;border-radius:14px}}@media(max-width:960px){{.dash,.previews{{grid-template-columns:1fr}}iframe{{height:720px}}.metric-grid{{grid-template-columns:1fr}}}}
</style></head><body><main>
<a class="back" href="../../index.html">← Today's vacancies</a>
<section class="hero"><h1>{company}</h1><h2>{role}</h2><div class="meta"><span class="pill">source fit {_safe(fit if fit is not None else 'n/a')}</span><span class="pill">RAG coverage {_safe(coverage if coverage is not None else 'n/a')}</span><span class="pill">JD {fidelity}</span><span class="pill overall {_status_class(status)}">{_safe(status)}</span></div><p><a href="{url}" target="_blank" rel="noopener">Original vacancy / apply</a> · {cover}</p></section>
<section class="dash"><article class="panel"><h3>Content</h3><div class="metric-grid">{content_metrics}</div><div class="review-box"><strong>Human review — local browser only</strong><div class="small">This choice is stored only in this browser's localStorage. It is not published, committed or sent anywhere.</div><div class="review-actions"><button type="button" data-decision="SEND">Mark send</button><button type="button" data-decision="REVISE">Mark revise</button><button type="button" data-decision="REJECT">Mark reject</button></div><div class="small">Current: <span class="review-current" id="human-review">not reviewed</span></div></div></article><article class="panel"><h3>Presentation — Technical Modern</h3><div class="metric-grid">{presentation_metrics}</div></article></section>
{preview_html}
<script>
(()=>{{const key='cvfit-human-review:{vacancy_id}';const current=document.getElementById('human-review');const render=()=>{{current.textContent=localStorage.getItem(key)||'not reviewed';}};document.querySelectorAll('[data-decision]').forEach(btn=>btn.addEventListener('click',()=>{{localStorage.setItem(key,btn.dataset.decision);render();}}));render();}})();
</script></main></body></html>"""


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
        primary = _primary(bundle)
        primary_link = f"vacancies/{vacancy_id}/cv_primary.html" if bundle else None
        harvard_link = f"vacancies/{vacancy_id}/cv_alternate.html" if bundle else None
        links = [f'<a href="vacancies/{_safe(vacancy_id)}/index.html">Details</a>']
        if primary_link:
            links.append(f'<a href="{_safe(primary_link)}" target="_blank">Technical Modern</a>')
        if harvard_link:
            links.append(f'<a href="{_safe(harvard_link)}" target="_blank">Harvard Executive</a>')
        links.append(f'<a href="{_safe(record.get("url"))}" target="_blank" rel="noopener">Vacancy</a>')
        ratios = primary.get("section_area_ratios") or {}
        cards.append(f"""
        <article class="card">
          <div class="top"><div><h2>{_safe(record.get('company'))}</h2><h3>{_safe(record.get('role_title'))}</h3></div><span class="status {'ready' if ready else 'review'}">{_safe(status)}</span></div>
          <div class="meta"><span>source fit {_safe(record.get('fit_score') if record.get('fit_score') is not None else 'n/a')}</span><span>JD {_safe(record.get('jd_fidelity'))}</span><span>visual {_safe(primary.get('visual_status') or 'n/a')}</span><span>experience {_pct(ratios.get('experience'))}</span><span>skills {_pct(ratios.get('skills'))}</span></div>
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
            "has_technical_modern_html": bool(primary_link),
            "has_harvard_html": bool(harvard_link),
            "primary_physical_status": primary.get("physical_status"),
            "primary_visual_status": primary.get("visual_status"),
            "primary_presentation_review_status": primary.get("presentation_review_status"),
            "page_utilization": primary.get("page_utilization", []),
            "section_area_ratios": primary.get("section_area_ratios", {}),
            "section_item_counts": primary.get("section_item_counts", {}),
        })

    index = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CV_fit — vacancies {html.escape(target_date)}</title>
<style>
body{{margin:0;background:#f6f7fb;color:#111827;font:15px/1.5 Arial,Helvetica,sans-serif}}main{{max-width:1180px;margin:auto;padding:36px 22px 70px}}header{{margin-bottom:26px}}h1{{font-size:34px;margin:0}}header p{{color:#4b5563;max-width:850px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:16px}}.card{{background:white;border:1px solid #e5e7eb;border-radius:16px;padding:18px;box-shadow:0 3px 14px rgba(0,0,0,.035)}}.top{{display:flex;justify-content:space-between;gap:12px}}h2{{margin:0;font-size:20px}}h3{{margin:4px 0 0;font-size:15px;font-weight:600;color:#374151}}.status{{height:max-content;border-radius:999px;padding:4px 8px;font-size:11px;font-weight:800}}.ready{{background:#dcfce7;color:#166534}}.review{{background:#fef3c7;color:#92400e}}.meta{{display:flex;gap:6px;flex-wrap:wrap;margin:13px 0}}.meta span{{background:#f3f4f6;border-radius:999px;padding:3px 7px;font-size:12px;color:#4b5563}}.card p{{font-size:13px;color:#4b5563;min-height:38px}}.links{{display:flex;flex-wrap:wrap;gap:7px}}.links a{{text-decoration:none;border:1px solid #d1d5db;border-radius:8px;padding:6px 8px;color:#0f4c81;background:white}}.note{{margin-top:24px;padding:14px;border-left:4px solid #9ca3af;background:#fff;color:#4b5563}}
</style></head><body><main><header><h1>CV_fit Showcase V2</h1><p>Search date <strong>{html.escape(target_date)}</strong>. Source fit and RAG evidence coverage remain separate. Submission readiness now requires content quality, cover letter, deterministic design, Chromium/PDF physical safety, objective visual-balance metrics and the metric-grounded Presentation Reviewer.</p></header><section class="grid">{''.join(cards)}</section><div class="note">Public preview uses only repository public-safe identity. Human review buttons on detail pages use localStorage only; no choice is committed or published.</div></main></body></html>"""
    _write(site_dir / "index.html", index)
    _write(site_dir / "showcase.json", json.dumps({"schema_version": 2, "date": target_date, "vacancies": summary_rows}, ensure_ascii=False, indent=2) + "\n")
    _write(site_dir / ".nojekyll", "")
    return {"date": target_date, "vacancy_count": len(summary_rows), "ready_count": sum(x["ready_to_send"] for x in summary_rows), "vacancies": summary_rows}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Showcase V2 with content and objective CV presentation metrics.")
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
