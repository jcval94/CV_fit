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


def _quality_score(run_report: dict[str, Any] | None) -> float | int | None:
    value = ((run_report or {}).get("final_review") or {}).get("overall_score")
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() else round(number, 1)


def _quality_label(run_report: dict[str, Any] | None) -> str:
    score = _quality_score(run_report)
    return "n/a" if score is None else f"{score}/100"


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


def _primary(bundle: dict[str, Any] | None) -> dict[str, Any]:
    return _template(bundle, "primary")


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
    quality_label = _quality_label(run_report)

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
              <iframe loading="lazy" title="{_safe(label)} CV" src="{_safe(item.get('html_file'))}"></iframe>
              <div class="buttons">{''.join(buttons)}</div>
            </article>
            """)
        preview_html = '<section class="previews">' + "".join(cards) + "</section>"
        cover = '<a class="action-link" href="cover_letter_final.md" target="_blank" rel="noopener">Cover letter</a>'
    else:
        preview_html = '<div class="empty">No public CV bundle was generated for this vacancy in the current run.</div>'

    status = (
        "READY TO SEND"
        if bundle and bundle.get("ready_to_send")
        else "SENDABLE · REVIEW ADVISED"
        if bundle
        else "NOT GENERATED"
    )
    content_metrics = "".join([
        _metric("Quality KPI", quality_label),
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
:root{{--ink:#111827;--muted:#64748b;--line:#e2e8f0;--panel:#fff;--bg:#f4f6f8;--ok:#166534;--warn:#92400e}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 Arial,Helvetica,sans-serif}}main{{max-width:1540px;margin:auto;padding:28px}}a{{color:#0f4c81}}.back{{display:inline-block;margin-bottom:16px}}.hero,.panel,.preview-card{{background:var(--panel);border:1px solid var(--line);border-radius:14px}}.hero{{padding:22px;margin-bottom:16px}}h1{{margin:0;font-size:28px}}h2{{margin:5px 0 0}}.meta{{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}}.pill{{background:#eef2f7;border-radius:999px;padding:4px 9px;color:#475569}}.overall{{font-weight:800}}.dash{{display:grid;grid-template-columns:1fr 1.4fr;gap:16px;margin-bottom:20px}}.panel{{padding:17px}}.panel h3{{margin:0 0 10px;font-size:14px;text-transform:uppercase;letter-spacing:.7px}}.metric-grid{{display:grid;grid-template-columns:repeat(2,minmax(130px,1fr));gap:1px;background:var(--line);border:1px solid var(--line);border-radius:10px;overflow:hidden}}.metric{{background:#fff;padding:9px 11px;display:flex;justify-content:space-between;gap:12px}}.metric span{{color:var(--muted)}}.metric-value.ok{{color:var(--ok)}}.metric-value.warn{{color:var(--warn)}}.review-box{{margin-top:13px;padding:12px;background:#f8fafc;border:1px solid var(--line);border-radius:10px}}.review-actions{{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}}button,.action-link,.buttons a{{border:1px solid #cbd5e1;background:#fff;border-radius:8px;padding:7px 10px;text-decoration:none;color:#0f4c81;cursor:pointer}}button[data-decision="SEND"]{{border-color:#86efac}}button[data-decision="REVISE"]{{border-color:#fde68a}}button[data-decision="REJECT"]{{border-color:#fecaca}}.review-current{{font-weight:700}}.small{{font-size:12px;color:var(--muted)}}.previews{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}.preview-card{{overflow:hidden}}.preview-head{{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:12px 14px;border-bottom:1px solid var(--line)}}.preview-head h2{{font-size:16px;margin:0}}.preview-head span{{font-size:12px;color:var(--muted);text-align:right}}iframe{{width:100%;height:900px;border:0;background:#ddd}}.buttons{{display:flex;gap:7px;flex-wrap:wrap;padding:11px 14px}}.empty{{background:#fff;border:1px dashed #94a3b8;padding:30px;border-radius:14px}}@media(max-width:960px){{.dash,.previews{{grid-template-columns:1fr}}iframe{{height:720px}}.metric-grid{{grid-template-columns:1fr}}}}
</style></head><body><main>
<a class="back" href="../../index.html">← Vacancy feed</a>
<section class="hero"><h1>{company}</h1><h2>{role}</h2><div class="meta"><span class="pill">source fit {_safe(fit if fit is not None else 'n/a')}</span><span class="pill">RAG coverage {_safe(coverage if coverage is not None else 'n/a')}</span><span class="pill">JD {fidelity}</span><span class="pill overall {_status_class(status)}">{_safe(status)}</span></div><p><a href="{url}" target="_blank" rel="noopener">Original vacancy / apply</a> · {cover}</p></section>
<section class="dash"><article class="panel"><h3>Content</h3><div class="metric-grid">{content_metrics}</div><div class="review-box"><strong>Human review — local browser only</strong><div class="small">This choice is stored only in this browser's localStorage. It is not published, committed or sent anywhere.</div><div class="review-actions"><button type="button" data-decision="SEND">Mark send</button><button type="button" data-decision="REVISE">Mark revise</button><button type="button" data-decision="REJECT">Mark reject</button></div><div class="small">Current: <span class="review-current" id="human-review">not reviewed</span></div></div></article><article class="panel"><h3>Presentation — Technical Modern</h3><div class="metric-grid">{presentation_metrics}</div></article></section>
{preview_html}
<script>
(()=>{{const key='cvfit-human-review:{vacancy_id}';const current=document.getElementById('human-review');const render=()=>{{current.textContent=localStorage.getItem(key)||'not reviewed';}};document.querySelectorAll('[data-decision]').forEach(btn=>btn.addEventListener('click',()=>{{localStorage.setItem(key,btn.dataset.decision);render();}}));render();}})();
</script></main></body></html>"""


def _feed_cv_preview(vacancy_id: str, item: dict[str, Any], *, label: str) -> str:
    if not item:
        return f"""
        <section class="cv-tile unavailable">
          <div class="cv-tile-head"><div><span class="eyebrow">CV</span><h4>{_safe(label)}</h4></div><span class="mini-status warn">not generated</span></div>
          <div class="cv-empty">No CV artifact available in this run.</div>
        </section>
        """

    base = f"vacancies/{_safe(vacancy_id)}/"
    screenshot = item.get("screenshot_file")
    html_file = item.get("html_file")
    pdf_file = item.get("pdf_file")
    status = item.get("presentation_review_status") or item.get("visual_status") or item.get("physical_status") or "n/a"
    pages = item.get("expected_pages", "n/a")
    preview = (
        f'<a class="cv-image-link" href="{base}{_safe(html_file)}" target="_blank" rel="noopener">'
        f'<img loading="lazy" src="{base}{_safe(screenshot)}" alt="{_safe(label)} CV preview"></a>'
        if screenshot and html_file
        else '<div class="cv-empty">Preview image unavailable.</div>'
    )
    actions = []
    if html_file:
        actions.append(f'<a href="{base}{_safe(html_file)}" target="_blank" rel="noopener">Open HTML</a>')
    if pdf_file:
        actions.append(f'<a href="{base}{_safe(pdf_file)}" target="_blank" rel="noopener">PDF</a>')
    return f"""
    <section class="cv-tile">
      <div class="cv-tile-head"><div><span class="eyebrow">CV</span><h4>{_safe(label)}</h4></div><div class="cv-status-stack"><span class="mini-status {_status_class(status)}">{_safe(status)}</span><span class="pages">{_safe(pages)} page(s)</span></div></div>
      <div class="cv-canvas">{preview}</div>
      <div class="cv-actions">{''.join(actions)}</div>
    </section>
    """


def _feed_post(
    record: dict[str, Any],
    bundle: dict[str, Any] | None,
    run_report: dict[str, Any] | None,
    batch_item: dict[str, Any] | None,
) -> str:
    vacancy_id = str(record["vacancy_id"])
    company = str(record.get("company") or "Unknown company")
    role = str(record.get("role_title") or "Role")
    location = record.get("location_raw") or record.get("city") or "Location not specified"
    work_model = record.get("work_model") or ""
    fit = record.get("fit_score")
    coverage = (run_report or {}).get("match_coverage_score")
    ready = bool(bundle and bundle.get("ready_to_send"))
    sendable = bool(bundle)
    status = (
        "READY"
        if ready
        else "SENDABLE · REVIEW ADVISED"
        if sendable
        else (batch_item or {}).get("status", "NOT GENERATED")
    )
    primary = _template(bundle, "primary")
    alternate = _template(bundle, "alternate")
    final_review = (run_report or {}).get("final_review", {})
    headhunter = final_review.get("overall_score", "n/a")
    quality_label = _quality_label(run_report)
    summary = record.get("fit_summary") or record.get("description") or ""
    initials = "".join(part[:1] for part in company.split()[:2]).upper() or "CV"

    primary_preview = _feed_cv_preview(vacancy_id, primary, label="Technical Modern")
    alternate_preview = _feed_cv_preview(vacancy_id, alternate, label="Harvard Executive")
    cover_link = (
        f'<a href="vacancies/{_safe(vacancy_id)}/cover_letter_final.md" target="_blank" rel="noopener">Cover letter</a>'
        if bundle
        else ""
    )
    ready_class = "ok" if ready else "warn"

    return f"""
    <article class="feed-post" data-status="{'ready' if ready else 'review'}" data-vacancy="{_safe(vacancy_id)}">
      <header class="post-head">
        <div class="avatar" aria-hidden="true">{_safe(initials)}</div>
        <div class="post-identity">
          <div class="company-line"><h2>{_safe(company)}</h2><span class="post-status {ready_class}">{_safe(status)}</span></div>
          <h3>{_safe(role)}</h3>
          <div class="subline">{_safe(location)}{(' · ' + _safe(work_model)) if work_model else ''}</div>
        </div>
        <a class="vacancy-cta" href="{_safe(record.get('url'))}" target="_blank" rel="noopener">View vacancy ↗</a>
      </header>

      <div class="post-body">
        <div class="fit-strip">
          <span><b>Source fit</b> {_safe(fit if fit is not None else 'n/a')}</span>
          <span><b>RAG coverage</b> {_safe(coverage if coverage is not None else 'n/a')}</span>
          <span><b>Quality KPI</b> {_safe(quality_label)}</span>
          <span><b>JD</b> {_safe(record.get('jd_fidelity') or 'n/a')}</span>
          <span><b>Visual</b> {_safe(primary.get('visual_status') or 'n/a')}</span>
        </div>
        <p class="post-summary">{_safe(summary)}</p>
        <div class="post-links"><a href="vacancies/{_safe(vacancy_id)}/index.html">Full review</a>{cover_link}</div>
      </div>

      <div class="cv-gallery">{primary_preview}{alternate_preview}</div>

      <footer class="post-review">
        <div><strong>Human decision</strong><span class="local-note">stored only in this browser</span></div>
        <div class="feed-review-actions">
          <button type="button" data-review="SEND">SEND</button>
          <button type="button" data-review="REVISE">REVISE</button>
          <button type="button" data-review="REJECT">REJECT</button>
          <span class="feed-review-current" data-review-current>not reviewed</span>
        </div>
      </footer>
    </article>
    """


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

    feed_posts: list[str] = []
    summary_rows: list[dict[str, Any]] = []
    ready_count = 0
    generated_count = 0

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
                generated_count += 1
                if (run_dir / "run_report.json").exists():
                    run_report = _read_json(run_dir / "run_report.json")
        detail_dir.mkdir(parents=True, exist_ok=True)
        _write(detail_dir / "index.html", _detail_page(record, bundle, run_report))

        ready = bool(bundle and bundle.get("ready_to_send"))
        if ready:
            ready_count += 1
        status = "READY" if ready else (batch_item or {}).get("status", "NOT GENERATED")
        primary = _primary(bundle)
        primary_link = f"vacancies/{vacancy_id}/{primary.get('html_file')}" if primary.get("html_file") else None
        alternate = _template(bundle, "alternate")
        harvard_link = f"vacancies/{vacancy_id}/{alternate.get('html_file')}" if alternate.get("html_file") else None

        feed_posts.append(_feed_post(record, bundle, run_report, batch_item))
        summary_rows.append({
            "vacancy_id": vacancy_id,
            "company": record.get("company"),
            "role_title": record.get("role_title"),
            "url": record.get("url"),
            "fit_score": record.get("fit_score"),
            "jd_fidelity": record.get("jd_fidelity"),
            "generation_status": status,
            "ready_to_send": ready,
            "sendable": bool(bundle),
            "quality_score": _quality_score(run_report),
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
<title>CV_fit — vacancy feed {html.escape(target_date)}</title>
<style>
:root{{--bg:#f0f2f5;--panel:#fff;--ink:#1c1e21;--muted:#65676b;--line:#dfe3e8;--blue:#1769aa;--blue-soft:#e7f3ff;--ok:#1f7a3f;--ok-bg:#e5f7ea;--warn:#9a5a00;--warn-bg:#fff4d6;--shadow:0 1px 2px rgba(0,0,0,.12)}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 Arial,Helvetica,sans-serif}}a{{color:var(--blue)}}button{{font:inherit}}.topbar{{position:sticky;top:0;z-index:20;background:rgba(255,255,255,.96);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}}.topbar-inner{{max-width:1240px;margin:auto;padding:12px 20px;display:flex;align-items:center;justify-content:space-between;gap:18px}}.brand{{display:flex;align-items:center;gap:10px}}.brand-mark{{width:38px;height:38px;border-radius:11px;background:var(--blue);color:white;display:grid;place-items:center;font-weight:800}}.brand h1{{font-size:19px;margin:0}}.brand small{{display:block;color:var(--muted)}}.top-stats{{display:flex;gap:7px;flex-wrap:wrap;justify-content:flex-end}}.top-stat{{background:#f5f6f7;border:1px solid var(--line);border-radius:999px;padding:5px 9px;color:var(--muted)}}.layout{{max-width:1240px;margin:20px auto 70px;padding:0 20px;display:grid;grid-template-columns:220px minmax(0,820px) 180px;gap:18px;align-items:start}}.side{{position:sticky;top:84px}}.side-card{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px;box-shadow:var(--shadow)}}.side h2{{font-size:13px;text-transform:uppercase;letter-spacing:.6px;margin:0 0 10px;color:var(--muted)}}.filter{{width:100%;border:0;background:transparent;text-align:left;padding:9px 10px;border-radius:8px;cursor:pointer;color:#374151}}.filter:hover,.filter.active{{background:var(--blue-soft);color:var(--blue);font-weight:700}}.legend{{font-size:12px;color:var(--muted)}}.legend p{{margin:8px 0}}.feed{{display:flex;flex-direction:column;gap:18px}}.feed-intro{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:17px;box-shadow:var(--shadow)}}.feed-intro h2{{margin:0 0 4px;font-size:19px}}.feed-intro p{{margin:0;color:var(--muted)}}.feed-post{{background:var(--panel);border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow);overflow:hidden}}.post-head{{display:grid;grid-template-columns:46px minmax(0,1fr) auto;gap:11px;align-items:center;padding:14px 16px;border-bottom:1px solid #edf0f2}}.avatar{{width:46px;height:46px;border-radius:50%;display:grid;place-items:center;background:linear-gradient(135deg,#dcecff,#edf5ff);color:#135a91;font-weight:800;font-size:15px;border:1px solid #cbdcf0}}.company-line{{display:flex;align-items:center;gap:8px;flex-wrap:wrap}}.company-line h2{{margin:0;font-size:17px}}.post-identity h3{{margin:1px 0 0;font-size:14px;font-weight:650}}.subline{{font-size:12px;color:var(--muted);margin-top:2px}}.post-status,.mini-status{{border-radius:999px;padding:3px 7px;font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.25px}}.ok{{background:var(--ok-bg);color:var(--ok)}}.warn{{background:var(--warn-bg);color:var(--warn)}}.vacancy-cta{{text-decoration:none;background:var(--blue);color:white;border-radius:8px;padding:8px 11px;font-weight:700;white-space:nowrap}}.post-body{{padding:12px 16px 14px}}.fit-strip{{display:flex;gap:7px;flex-wrap:wrap}}.fit-strip span{{background:#f5f6f7;border-radius:999px;padding:4px 8px;color:#4b5563;font-size:12px}}.post-summary{{margin:11px 0 8px;color:#4b5563}}.post-links{{display:flex;gap:12px;flex-wrap:wrap;font-size:13px}}.cv-gallery{{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--line);border-top:1px solid var(--line);border-bottom:1px solid var(--line)}}.cv-tile{{background:#f7f8fa;min-width:0}}.cv-tile-head{{background:white;padding:10px 12px;display:flex;align-items:center;justify-content:space-between;gap:10px}}.eyebrow{{display:block;font-size:9px;font-weight:800;letter-spacing:.7px;color:var(--muted);text-transform:uppercase}}.cv-tile h4{{margin:1px 0 0;font-size:14px}}.cv-status-stack{{text-align:right}}.pages{{display:block;margin-top:2px;color:var(--muted);font-size:10px}}.cv-canvas{{height:560px;overflow:hidden;padding:10px;display:flex;align-items:flex-start;justify-content:center;background:#e8eaed}}.cv-image-link{{display:block;width:100%;height:100%;overflow-y:auto;overflow-x:hidden;background:white;border-radius:4px;box-shadow:0 1px 5px rgba(0,0,0,.18)}}.cv-image-link img{{display:block;width:100%;height:auto}}.cv-actions{{background:white;padding:9px 12px;display:flex;gap:7px;flex-wrap:wrap;border-top:1px solid #edf0f2}}.cv-actions a{{text-decoration:none;border:1px solid #ccd0d5;border-radius:7px;padding:5px 8px;font-size:12px;background:white}}.cv-empty{{height:100%;display:grid;place-items:center;color:var(--muted);padding:24px;text-align:center}}.post-review{{display:flex;justify-content:space-between;align-items:center;gap:14px;padding:11px 16px;background:white}}.local-note{{display:block;font-size:10px;color:var(--muted);font-weight:normal}}.feed-review-actions{{display:flex;gap:6px;align-items:center;flex-wrap:wrap;justify-content:flex-end}}.feed-review-actions button{{border:1px solid #ccd0d5;background:white;border-radius:7px;padding:6px 9px;cursor:pointer;font-size:11px;font-weight:750}}.feed-review-actions button[data-review="SEND"]{{border-color:#8bd3a2}}.feed-review-actions button[data-review="REVISE"]{{border-color:#f0cf73}}.feed-review-actions button[data-review="REJECT"]{{border-color:#eea0a0}}.feed-review-actions button.selected{{background:var(--blue-soft);border-color:#8ebce1;color:var(--blue)}}.feed-review-current{{font-size:11px;color:var(--muted);min-width:76px;text-align:right}}.feed-post.is-hidden{{display:none}}.privacy-note{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:12px;font-size:11px;color:var(--muted)}}
@media(max-width:1050px){{.layout{{grid-template-columns:180px minmax(0,1fr)}}.side.right{{display:none}}}}
@media(max-width:800px){{.topbar-inner{{align-items:flex-start}}.top-stats{{display:none}}.layout{{display:block;padding:0 10px;margin-top:10px}}.side.left{{position:static;margin-bottom:10px}}.side-card.filters{{display:flex;gap:4px;padding:7px;overflow-x:auto}}.side-card.filters h2{{display:none}}.filter{{width:auto;white-space:nowrap}}.feed{{gap:10px}}.feed-intro{{border-radius:10px}}.feed-post{{border-radius:10px}}.post-head{{grid-template-columns:42px minmax(0,1fr);padding:12px}}.avatar{{width:42px;height:42px}}.vacancy-cta{{grid-column:1/-1;text-align:center}}.post-body{{padding:10px 12px}}.cv-gallery{{grid-template-columns:1fr}}.cv-canvas{{height:620px}}.post-review{{align-items:flex-start;flex-direction:column}}.feed-review-actions{{justify-content:flex-start}}}}
</style></head><body>
<div class="topbar"><div class="topbar-inner"><div class="brand"><div class="brand-mark">CV</div><div><h1>CV_fit Review Feed</h1><small>{html.escape(target_date)} · vacancy-to-CV pipeline</small></div></div><div class="top-stats"><span class="top-stat">{len(summary_rows)} vacancies</span><span class="top-stat">{generated_count} sendable</span><span class="top-stat">{ready_count} passed all gates</span></div></div></div>
<main class="layout">
  <aside class="side left"><div class="side-card filters"><h2>Feed filter</h2><button class="filter active" data-filter="all">All ({len(summary_rows)})</button><button class="filter" data-filter="ready">Ready ({ready_count})</button><button class="filter" data-filter="review">Review ({len(summary_rows)-ready_count})</button></div></aside>
  <section class="feed"><div class="feed-intro"><h2>Today's vacancies and generated CVs</h2><p>Generated CVs remain available even when the quality target is not reached. Use the visible Quality KPI and review warning to decide whether to send as-is or edit first.</p></div>{''.join(feed_posts)}</section>
  <aside class="side right"><div class="side-card legend"><h2>What you are seeing</h2><p><b>Quality KPI</b> is the latest Headhunter overall score out of 100.</p><p><b>SENDABLE · REVIEW ADVISED</b> means a usable CV artifact exists but did not clear every automated quality gate.</p><p><b>Source fit</b> comes from the vacancy source.</p><p><b>RAG coverage</b> is deterministic evidence coverage and stays separate.</p><p><b>Technical Modern</b> is the primary branded ATS-first CV.</p><p><b>Harvard Executive</b> keeps its locked visual system.</p></div><div class="privacy-note" style="margin-top:10px">Public-safe identity only. Human decisions stay in localStorage and are never published.</div></aside>
</main>
<script>
(()=>{{
  const posts=[...document.querySelectorAll('.feed-post')];
  document.querySelectorAll('[data-filter]').forEach(btn=>btn.addEventListener('click',()=>{{
    document.querySelectorAll('[data-filter]').forEach(x=>x.classList.remove('active'));btn.classList.add('active');
    const filter=btn.dataset.filter;posts.forEach(post=>post.classList.toggle('is-hidden',filter!=='all'&&post.dataset.status!==filter));
  }}));
  posts.forEach(post=>{{
    const key='cvfit-human-review:'+post.dataset.vacancy;
    const current=post.querySelector('[data-review-current]');
    const buttons=[...post.querySelectorAll('[data-review]')];
    const render=()=>{{const value=localStorage.getItem(key)||'not reviewed';current.textContent=value;buttons.forEach(btn=>btn.classList.toggle('selected',btn.dataset.review===value));}};
    buttons.forEach(btn=>btn.addEventListener('click',()=>{{localStorage.setItem(key,btn.dataset.review);render();}}));render();
  }});
}})();
</script></body></html>"""

    _write(site_dir / "index.html", index)
    _write(site_dir / "showcase.json", json.dumps({
        "schema_version": 2,
        "view": "vacancy_cv_feed",
        "date": target_date,
        "vacancies": summary_rows,
    }, ensure_ascii=False, indent=2) + "\n")
    _write(site_dir / ".nojekyll", "")
    return {
        "date": target_date,
        "vacancy_count": len(summary_rows),
        "generated_count": generated_count,
        "ready_count": ready_count,
        "vacancies": summary_rows,
    }


def refresh_existing_showcase(site_dir: Path) -> dict[str, Any]:
    """Validate an existing showcase artifact and report its current publishable state.

    The Pages refresh workflow operates on a previously uploaded _site artifact.
    It should never require model calls or rebuild CVs; this function restores
    the lightweight contract expected by showcase_refresh.py.
    """
    index_path = site_dir / "index.html"
    payload_path = site_dir / "showcase.json"
    if not index_path.exists():
        raise FileNotFoundError(index_path)
    payload = _read_json(payload_path, {"vacancies": []})
    rows = payload.get("vacancies", []) if isinstance(payload, dict) else []
    generated_count = sum(
        bool(row.get("sendable"))
        or bool(row.get("has_technical_modern_html"))
        or bool(row.get("has_harvard_html"))
        for row in rows
        if isinstance(row, dict)
    )
    ready_count = sum(
        bool(row.get("ready_to_send"))
        for row in rows
        if isinstance(row, dict)
    )
    return {
        "date": payload.get("date") if isinstance(payload, dict) else None,
        "vacancy_count": len(rows),
        "generated_count": generated_count,
        "ready_count": ready_count,
        "sendable_count": generated_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Showcase V2 as a vacancy + two-CV review feed.")
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
    print(json.dumps({
        "date": report["date"],
        "vacancy_count": report["vacancy_count"],
        "generated_count": report["generated_count"],
        "ready_count": report["ready_count"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
