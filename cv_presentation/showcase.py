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


def _template(bundle: dict[str, Any] | None, role: str) -> dict[str, Any]:
    if not bundle:
        return {}
    return next((item for item in bundle.get("templates", []) if item.get("role") == role), {})


def _template_label(item: dict[str, Any], *, role: str) -> str:
    template_id = str(item.get("template_id") or "")
    if template_id == "technical_modern_v1":
        return "Technical Modern"
    if template_id == "harvard_v1" or role == "alternate":
        return "Harvard Executive"
    return "Branded CV"


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


def _detail_page(record: dict[str, Any], bundle: dict[str, Any] | None, run_report: dict[str, Any] | None) -> str:
    company = _safe(record.get("company"))
    role = _safe(record.get("role_title"))
    vacancy_id = _safe(record.get("vacancy_id"))
    url = _safe(record.get("url"))
    fit = record.get("fit_score")
    coverage = (run_report or {}).get("match_coverage_score")
    fidelity = _safe(record.get("jd_fidelity"))

    preview_html = ""
    cover = ""
    if bundle:
        cards = []
        for item in bundle.get("templates", []):
            item_role = str(item.get("role") or "")
            label = _template_label(item, role=item_role)
            visual = item.get("visual_status")
            reviewer = item.get("presentation_review_status")
            extra = ""
            if visual:
                extra += f" · visual {_safe(visual)}"
            if reviewer:
                extra += f" · review {_safe(reviewer)}"
            cards.append(f"""
            <article class="preview-card">
              <div class="preview-head"><h2>{_safe(label)}</h2><span>{_safe(item.get('physical_status'))}{extra} · {_safe(item.get('expected_pages'))} page(s)</span></div>
              <iframe loading="lazy" title="{_safe(label)} CV" src="{_safe(item.get('html_file'))}"></iframe>
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
        preview_html = '<div class="empty">No public CV bundle was generated for this vacancy in the current daily run.</div>'

    status = "READY TO SEND" if bundle and bundle.get("ready_to_send") else "REVIEW / BLOCKED"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{company} — {role}</title>
<style>
body{{margin:0;background:#f3f4f6;color:#111827;font:15px/1.5 Arial,Helvetica,sans-serif}}main{{max-width:1500px;margin:auto;padding:28px}}a{{color:#0f4c81}}.back{{display:inline-block;margin-bottom:18px}}.hero{{background:white;border:1px solid #e5e7eb;border-radius:16px;padding:22px;margin-bottom:22px}}h1{{margin:0 0 8px;font-size:28px}}.meta{{display:flex;gap:10px;flex-wrap:wrap;color:#4b5563}}.pill{{background:#eef2ff;border-radius:999px;padding:4px 9px}}.status{{font-weight:700}}.previews{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}.preview-card{{background:white;border:1px solid #e5e7eb;border-radius:16px;overflow:hidden}}.preview-head{{display:flex;justify-content:space-between;align-items:center;padding:14px 16px;border-bottom:1px solid #e5e7eb;gap:10px}}.preview-head h2{{font-size:17px;margin:0}}.preview-head span{{font-size:12px;color:#64748b;text-align:right}}iframe{{width:100%;height:900px;border:0;background:#ddd}}.buttons{{display:flex;gap:8px;flex-wrap:wrap;padding:12px 16px}}.buttons a,.cover{{text-decoration:none;border:1px solid #d1d5db;background:#fff;border-radius:8px;padding:7px 10px}}.empty{{background:#fff;border:1px dashed #9ca3af;padding:30px;border-radius:14px}}@media(max-width:900px){{.previews{{grid-template-columns:1fr}}iframe{{height:720px}}}}
</style></head><body><main>
<a class="back" href="../../index.html">← Vacancy feed</a>
<section class="hero"><h1>{company}</h1><h2>{role}</h2><div class="meta"><span class="pill">source fit: {_safe(fit if fit is not None else 'n/a')}</span><span class="pill">RAG coverage: {_safe(coverage if coverage is not None else 'n/a')}</span><span class="pill">JD: {fidelity}</span><span class="pill status">{_safe(status)}</span></div><p><a href="{url}" target="_blank" rel="noopener">Open original vacancy / apply</a></p>{cover}</section>
{preview_html}
<script>
(()=>{{const key='cvfit-human-review:{vacancy_id}';if(!localStorage.getItem(key))return;document.title+=' · '+localStorage.getItem(key);}})();
</script></main></body></html>"""


def _existing(site_dir: Path, vacancy_id: str, name: str | None) -> bool:
    return bool(name and (site_dir / "vacancies" / vacancy_id / str(name)).exists())


def _feed_cv_preview(site_dir: Path, row: dict[str, Any], *, role: str) -> str:
    vacancy_id = str(row.get("vacancy_id") or "")
    if role == "primary":
        label = str(row.get("primary_label") or "Branded CV")
        html_file = str(row.get("primary_html_file") or "cv_primary.html")
        pdf_file = str(row.get("primary_pdf_file") or "cv_primary.pdf")
        screenshot = str(row.get("primary_screenshot_file") or "cv_primary.png")
        status = row.get("primary_presentation_review_status") or row.get("primary_visual_status") or row.get("primary_physical_status") or row.get("generation_status") or "n/a"
    else:
        label = str(row.get("alternate_label") or "Harvard Executive")
        html_file = str(row.get("alternate_html_file") or "cv_alternate.html")
        pdf_file = str(row.get("alternate_pdf_file") or "cv_alternate.pdf")
        screenshot = str(row.get("alternate_screenshot_file") or "cv_alternate.png")
        status = row.get("alternate_presentation_review_status") or row.get("alternate_visual_status") or row.get("alternate_physical_status") or row.get("generation_status") or "n/a"

    has_html = _existing(site_dir, vacancy_id, html_file)
    has_pdf = _existing(site_dir, vacancy_id, pdf_file)
    has_screenshot = _existing(site_dir, vacancy_id, screenshot)
    if not has_html and not has_pdf and not has_screenshot:
        return f"""
        <section class="cv-tile unavailable"><div class="cv-tile-head"><div><span class="eyebrow">CV</span><h4>{_safe(label)}</h4></div><span class="mini-status warn">not generated</span></div><div class="cv-empty">No CV artifact available in this run.</div></section>
        """

    base = f"vacancies/{_safe(vacancy_id)}/"
    preview = (
        f'<a class="cv-image-link" href="{base}{_safe(html_file)}" target="_blank" rel="noopener"><img loading="lazy" src="{base}{_safe(screenshot)}" alt="{_safe(label)} CV preview"></a>'
        if has_screenshot and has_html
        else '<div class="cv-empty">Preview image unavailable. Use the links below.</div>'
    )
    actions = []
    if has_html:
        actions.append(f'<a href="{base}{_safe(html_file)}" target="_blank" rel="noopener">Open HTML</a>')
    if has_pdf:
        actions.append(f'<a href="{base}{_safe(pdf_file)}" target="_blank" rel="noopener">PDF</a>')
    return f"""
    <section class="cv-tile"><div class="cv-tile-head"><div><span class="eyebrow">CV</span><h4>{_safe(label)}</h4></div><span class="mini-status">{_safe(status)}</span></div><div class="cv-canvas">{preview}</div><div class="cv-actions">{''.join(actions)}</div></section>
    """


def _feed_post(site_dir: Path, row: dict[str, Any]) -> str:
    vacancy_id = str(row.get("vacancy_id") or "")
    company = str(row.get("company") or "Unknown company")
    role = str(row.get("role_title") or "Role")
    ready = bool(row.get("ready_to_send"))
    status = "READY" if ready else str(row.get("generation_status") or "REVIEW")
    location = row.get("location") or ""
    work_model = row.get("work_model") or ""
    coverage = row.get("rag_coverage")
    headhunter = row.get("headhunter_score")
    summary = row.get("fit_summary") or ""
    initials = "".join(part[:1] for part in company.split()[:2]).upper() or "CV"
    detail_path = site_dir / "vacancies" / vacancy_id / "index.html"
    cover_path = site_dir / "vacancies" / vacancy_id / "cover_letter_final.md"

    context_bits = [str(x) for x in (location, work_model) if x]
    context = " · ".join(context_bits)
    fit_items = [f'<span><b>Source fit</b> {_safe(row.get("fit_score") if row.get("fit_score") is not None else "n/a")}</span>']
    if coverage is not None:
        fit_items.append(f'<span><b>RAG coverage</b> {_safe(coverage)}</span>')
    if headhunter is not None:
        fit_items.append(f'<span><b>Headhunter</b> {_safe(headhunter)}</span>')
    fit_items.append(f'<span><b>JD</b> {_safe(row.get("jd_fidelity") or "n/a")}</span>')

    links = []
    if detail_path.exists():
        links.append(f'<a href="vacancies/{_safe(vacancy_id)}/index.html">Full review</a>')
    if cover_path.exists():
        links.append(f'<a href="vacancies/{_safe(vacancy_id)}/cover_letter_final.md" target="_blank" rel="noopener">Cover letter</a>')

    return f"""
    <article class="feed-post" data-status="{'ready' if ready else 'review'}" data-vacancy="{_safe(vacancy_id)}">
      <header class="post-head"><div class="avatar" aria-hidden="true">{_safe(initials)}</div><div class="post-identity"><div class="company-line"><h2>{_safe(company)}</h2><span class="post-status {'ok' if ready else 'warn'}">{_safe(status)}</span></div><h3>{_safe(role)}</h3>{f'<div class="subline">{_safe(context)}</div>' if context else ''}</div><a class="vacancy-cta" href="{_safe(row.get('url'))}" target="_blank" rel="noopener">View vacancy ↗</a></header>
      <div class="post-body"><div class="fit-strip">{''.join(fit_items)}</div>{f'<p class="post-summary">{_safe(summary)}</p>' if summary else ''}<div class="post-links">{''.join(links)}</div></div>
      <div class="cv-gallery">{_feed_cv_preview(site_dir, row, role='primary')}{_feed_cv_preview(site_dir, row, role='alternate')}</div>
      <footer class="post-review"><div><strong>Human decision</strong><span class="local-note">stored only in this browser</span></div><div class="feed-review-actions"><button type="button" data-review="SEND">SEND</button><button type="button" data-review="REVISE">REVISE</button><button type="button" data-review="REJECT">REJECT</button><span class="feed-review-current" data-review-current>not reviewed</span></div></footer>
    </article>
    """


def render_feed_index(*, target_date: str, rows: list[dict[str, Any]], site_dir: Path) -> str:
    ready_count = sum(bool(row.get("ready_to_send")) for row in rows)
    generated_count = sum(
        _existing(site_dir, str(row.get("vacancy_id") or ""), str(row.get("primary_html_file") or "cv_primary.html"))
        or _existing(site_dir, str(row.get("vacancy_id") or ""), str(row.get("alternate_html_file") or "cv_alternate.html"))
        for row in rows
    )
    posts = "".join(_feed_post(site_dir, row) for row in rows)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CV_fit — vacancy feed {html.escape(target_date)}</title>
<style>
:root{{--bg:#f0f2f5;--panel:#fff;--ink:#1c1e21;--muted:#65676b;--line:#dfe3e8;--blue:#1769aa;--blue-soft:#e7f3ff;--ok:#1f7a3f;--ok-bg:#e5f7ea;--warn:#9a5a00;--warn-bg:#fff4d6;--shadow:0 1px 2px rgba(0,0,0,.12)}}*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 Arial,Helvetica,sans-serif}}a{{color:var(--blue)}}button{{font:inherit}}.topbar{{position:sticky;top:0;z-index:20;background:rgba(255,255,255,.96);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}}.topbar-inner{{max-width:1240px;margin:auto;padding:12px 20px;display:flex;align-items:center;justify-content:space-between;gap:18px}}.brand{{display:flex;align-items:center;gap:10px}}.brand-mark{{width:38px;height:38px;border-radius:11px;background:var(--blue);color:white;display:grid;place-items:center;font-weight:800}}.brand h1{{font-size:19px;margin:0}}.brand small{{display:block;color:var(--muted)}}.top-stats{{display:flex;gap:7px;flex-wrap:wrap;justify-content:flex-end}}.top-stat{{background:#f5f6f7;border:1px solid var(--line);border-radius:999px;padding:5px 9px;color:var(--muted)}}.layout{{max-width:1240px;margin:20px auto 70px;padding:0 20px;display:grid;grid-template-columns:220px minmax(0,820px) 180px;gap:18px;align-items:start}}.side{{position:sticky;top:84px}}.side-card{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px;box-shadow:var(--shadow)}}.side h2{{font-size:13px;text-transform:uppercase;letter-spacing:.6px;margin:0 0 10px;color:var(--muted)}}.filter{{width:100%;border:0;background:transparent;text-align:left;padding:9px 10px;border-radius:8px;cursor:pointer;color:#374151}}.filter:hover,.filter.active{{background:var(--blue-soft);color:var(--blue);font-weight:700}}.legend{{font-size:12px;color:var(--muted)}}.legend p{{margin:8px 0}}.feed{{display:flex;flex-direction:column;gap:18px}}.feed-intro{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:17px;box-shadow:var(--shadow)}}.feed-intro h2{{margin:0 0 4px;font-size:19px}}.feed-intro p{{margin:0;color:var(--muted)}}.feed-post{{background:var(--panel);border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow);overflow:hidden}}.post-head{{display:grid;grid-template-columns:46px minmax(0,1fr) auto;gap:11px;align-items:center;padding:14px 16px;border-bottom:1px solid #edf0f2}}.avatar{{width:46px;height:46px;border-radius:50%;display:grid;place-items:center;background:linear-gradient(135deg,#dcecff,#edf5ff);color:#135a91;font-weight:800;font-size:15px;border:1px solid #cbdcf0}}.company-line{{display:flex;align-items:center;gap:8px;flex-wrap:wrap}}.company-line h2{{margin:0;font-size:17px}}.post-identity h3{{margin:1px 0 0;font-size:14px;font-weight:650}}.subline{{font-size:12px;color:var(--muted);margin-top:2px}}.post-status,.mini-status{{border-radius:999px;padding:3px 7px;font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.25px}}.ok{{background:var(--ok-bg);color:var(--ok)}}.warn{{background:var(--warn-bg);color:var(--warn)}}.vacancy-cta{{text-decoration:none;background:var(--blue);color:white;border-radius:8px;padding:8px 11px;font-weight:700;white-space:nowrap}}.post-body{{padding:12px 16px 14px}}.fit-strip{{display:flex;gap:7px;flex-wrap:wrap}}.fit-strip span{{background:#f5f6f7;border-radius:999px;padding:4px 8px;color:#4b5563;font-size:12px}}.post-summary{{margin:11px 0 8px;color:#4b5563}}.post-links{{display:flex;gap:12px;flex-wrap:wrap;font-size:13px}}.cv-gallery{{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--line);border-top:1px solid var(--line);border-bottom:1px solid var(--line)}}.cv-tile{{background:#f7f8fa;min-width:0}}.cv-tile-head{{background:white;padding:10px 12px;display:flex;align-items:center;justify-content:space-between;gap:10px}}.eyebrow{{display:block;font-size:9px;font-weight:800;letter-spacing:.7px;color:var(--muted);text-transform:uppercase}}.cv-tile h4{{margin:1px 0 0;font-size:14px}}.cv-canvas{{height:560px;overflow:hidden;padding:10px;display:flex;align-items:flex-start;justify-content:center;background:#e8eaed}}.cv-image-link{{display:block;width:100%;height:100%;overflow-y:auto;overflow-x:hidden;background:white;border-radius:4px;box-shadow:0 1px 5px rgba(0,0,0,.18)}}.cv-image-link img{{display:block;width:100%;height:auto}}.cv-actions{{background:white;padding:9px 12px;display:flex;gap:7px;flex-wrap:wrap;border-top:1px solid #edf0f2}}.cv-actions a{{text-decoration:none;border:1px solid #ccd0d5;border-radius:7px;padding:5px 8px;font-size:12px;background:white}}.cv-empty{{height:100%;display:grid;place-items:center;color:var(--muted);padding:24px;text-align:center}}.post-review{{display:flex;justify-content:space-between;align-items:center;gap:14px;padding:11px 16px;background:white}}.local-note{{display:block;font-size:10px;color:var(--muted);font-weight:normal}}.feed-review-actions{{display:flex;gap:6px;align-items:center;flex-wrap:wrap;justify-content:flex-end}}.feed-review-actions button{{border:1px solid #ccd0d5;background:white;border-radius:7px;padding:6px 9px;cursor:pointer;font-size:11px;font-weight:750}}.feed-review-actions button.selected{{background:var(--blue-soft);border-color:#8ebce1;color:var(--blue)}}.feed-review-current{{font-size:11px;color:var(--muted);min-width:76px;text-align:right}}.feed-post.is-hidden{{display:none}}.privacy-note{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:12px;font-size:11px;color:var(--muted)}}@media(max-width:1050px){{.layout{{grid-template-columns:180px minmax(0,1fr)}}.side.right{{display:none}}}}@media(max-width:800px){{.topbar-inner{{align-items:flex-start}}.top-stats{{display:none}}.layout{{display:block;padding:0 10px;margin-top:10px}}.side.left{{position:static;margin-bottom:10px}}.side-card.filters{{display:flex;gap:4px;padding:7px;overflow-x:auto}}.side-card.filters h2{{display:none}}.filter{{width:auto;white-space:nowrap}}.feed{{gap:10px}}.post-head{{grid-template-columns:42px minmax(0,1fr);padding:12px}}.avatar{{width:42px;height:42px}}.vacancy-cta{{grid-column:1/-1;text-align:center}}.post-body{{padding:10px 12px}}.cv-gallery{{grid-template-columns:1fr}}.cv-canvas{{height:620px}}.post-review{{align-items:flex-start;flex-direction:column}}.feed-review-actions{{justify-content:flex-start}}}}
</style></head><body><div class="topbar"><div class="topbar-inner"><div class="brand"><div class="brand-mark">CV</div><div><h1>CV_fit Review Feed</h1><small>{html.escape(target_date)} · vacancy-to-CV pipeline</small></div></div><div class="top-stats"><span class="top-stat">{len(rows)} vacancies</span><span class="top-stat">{generated_count} with CVs</span><span class="top-stat">{ready_count} ready</span></div></div></div><main class="layout"><aside class="side left"><div class="side-card filters"><h2>Feed filter</h2><button class="filter active" data-filter="all">All ({len(rows)})</button><button class="filter" data-filter="ready">Ready ({ready_count})</button><button class="filter" data-filter="review">Review ({len(rows)-ready_count})</button></div></aside><section class="feed"><div class="feed-intro"><h2>Today's vacancies and generated CVs</h2><p>Each post keeps the vacancy and its two CV variants together. Scroll the document previews, open HTML/PDF, then mark your human decision without leaving the feed.</p></div>{posts}</section><aside class="side right"><div class="side-card legend"><h2>Review flow</h2><p><b>View vacancy</b> opens the original application link.</p><p><b>Branded / Technical</b> is the adaptive primary CV.</p><p><b>Harvard Executive</b> is the fixed alternate.</p><p><b>SEND / REVISE / REJECT</b> is local to your browser.</p></div><div class="privacy-note" style="margin-top:10px">Public-safe artifacts only. Human decisions are stored in localStorage and are never committed or published.</div></aside></main><script>(()=>{{const posts=[...document.querySelectorAll('.feed-post')];document.querySelectorAll('[data-filter]').forEach(btn=>btn.addEventListener('click',()=>{{document.querySelectorAll('[data-filter]').forEach(x=>x.classList.remove('active'));btn.classList.add('active');const filter=btn.dataset.filter;posts.forEach(post=>post.classList.toggle('is-hidden',filter!=='all'&&post.dataset.status!==filter));}}));posts.forEach(post=>{{const key='cvfit-human-review:'+post.dataset.vacancy;const current=post.querySelector('[data-review-current]');const buttons=[...post.querySelectorAll('[data-review]')];const render=()=>{{const value=localStorage.getItem(key)||'not reviewed';current.textContent=value;buttons.forEach(btn=>btn.classList.toggle('selected',btn.dataset.review===value));}};buttons.forEach(btn=>btn.addEventListener('click',()=>{{localStorage.setItem(key,btn.dataset.review);render();}}));render();}});}})();</script></body></html>"""


def refresh_existing_showcase(site_dir: Path) -> dict[str, Any]:
    """Rebuild only the feed index from an existing Pages artifact.

    This allows visual/UI changes to be deployed without spending model tokens or
    regenerating CV content. Existing HTML/PDF/PNG artifacts remain untouched.
    """
    payload = _read_json(site_dir / "showcase.json")
    target_date = str(payload.get("date") or "unknown")
    rows = list(payload.get("vacancies") or [])
    _write(site_dir / "index.html", render_feed_index(target_date=target_date, rows=rows, site_dir=site_dir))
    payload["view"] = "vacancy_cv_feed"
    _write(site_dir / "showcase.json", json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return {"date": target_date, "vacancy_count": len(rows)}


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
        primary = _template(bundle, "primary")
        alternate = _template(bundle, "alternate")
        final_review = (run_report or {}).get("final_review", {})
        summary_rows.append({
            "vacancy_id": vacancy_id,
            "company": record.get("company"),
            "role_title": record.get("role_title"),
            "url": record.get("url"),
            "fit_score": record.get("fit_score"),
            "fit_summary": record.get("fit_summary") or "",
            "jd_fidelity": record.get("jd_fidelity"),
            "location": record.get("location_raw") or record.get("city"),
            "work_model": record.get("work_model"),
            "rag_coverage": (run_report or {}).get("match_coverage_score"),
            "headhunter_score": final_review.get("overall_score"),
            "generation_status": status,
            "ready_to_send": ready,
            "primary_label": _template_label(primary, role="primary") if primary else "Branded CV",
            "primary_html_file": primary.get("html_file") or "cv_primary.html",
            "primary_pdf_file": primary.get("pdf_file") or "cv_primary.pdf",
            "primary_screenshot_file": primary.get("screenshot_file") or "cv_primary.png",
            "primary_physical_status": primary.get("physical_status"),
            "primary_visual_status": primary.get("visual_status"),
            "primary_presentation_review_status": primary.get("presentation_review_status"),
            "alternate_label": _template_label(alternate, role="alternate") if alternate else "Harvard Executive",
            "alternate_html_file": alternate.get("html_file") or "cv_alternate.html",
            "alternate_pdf_file": alternate.get("pdf_file") or "cv_alternate.pdf",
            "alternate_screenshot_file": alternate.get("screenshot_file") or "cv_alternate.png",
            "alternate_physical_status": alternate.get("physical_status"),
            "alternate_visual_status": alternate.get("visual_status"),
            "alternate_presentation_review_status": alternate.get("presentation_review_status"),
            "has_branded_html": bool(primary.get("html_file")),
            "has_harvard_html": bool(alternate.get("html_file")),
        })

    _write(site_dir / "index.html", render_feed_index(target_date=target_date, rows=summary_rows, site_dir=site_dir))
    _write(site_dir / "showcase.json", json.dumps({"date": target_date, "view": "vacancy_cv_feed", "vacancies": summary_rows}, ensure_ascii=False, indent=2) + "\n")
    _write(site_dir / ".nojekyll", "")
    return {
        "date": target_date,
        "vacancy_count": len(summary_rows),
        "ready_count": sum(bool(x["ready_to_send"]) for x in summary_rows),
        "vacancies": summary_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a static GitHub Pages vacancy + two-CV review feed.")
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
