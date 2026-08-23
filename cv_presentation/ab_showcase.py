from __future__ import annotations

import argparse
import html
import json
import shutil
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def _fmt_cost(value: Any) -> str:
    try:
        return f"${float(value):.4f}"
    except (TypeError, ValueError):
        return "n/a"


def _fmt_delta(value: Any, suffix: str = "") -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "n/a"
    sign = "+" if number > 0 else ""
    return f"{sign}{number:.2f}{suffix}"


def _line(text: str) -> str:
    return f"<li>{_safe(text)}</li>"


def _render_cv(cv: dict[str, Any]) -> str:
    def evidence_line(item: dict[str, Any]) -> str:
        return _safe(item.get("text") or "")

    experience = []
    for item in cv.get("experience", []):
        bullets = "".join(_line(str(bullet.get("text") or "")) for bullet in item.get("bullets", []))
        experience.append(
            f'<section class="cv-section"><div class="role-head"><strong>{_safe(item.get("organization"))}</strong>'
            f'<span>{_safe(item.get("period"))}</span></div><div class="role-title">{_safe(item.get("title"))}</div>'
            f'<ul>{bullets}</ul></section>'
        )

    projects = []
    for item in cv.get("projects", []):
        bullets = "".join(_line(str(bullet.get("text") or "")) for bullet in item.get("bullets", []))
        projects.append(
            f'<section class="cv-section"><strong>{_safe(item.get("name"))}</strong><ul>{bullets}</ul></section>'
        )

    skills = " · ".join(evidence_line(item) for item in cv.get("skills", []))
    education = "".join(_line(evidence_line(item)) for item in cv.get("education", []))
    certifications = "".join(_line(evidence_line(item)) for item in cv.get("certifications", []))
    return f"""
    <div class="paper">
      <div class="paper-head"><h3>{evidence_line(cv.get('headline', {}))}</h3><p>{evidence_line(cv.get('summary', {}))}</p></div>
      <h4>Experience</h4>{''.join(experience)}
      {('<h4>Selected projects</h4>' + ''.join(projects)) if projects else ''}
      <h4>Skills</h4><p class="skills">{skills}</p>
      {('<h4>Education</h4><ul>' + education + '</ul>') if education else ''}
      {('<h4>Certifications</h4><ul>' + certifications + '</ul>') if certifications else ''}
    </div>
    """


def _audit_card(case: dict[str, Any]) -> str:
    baseline = case.get("baseline", {})
    optimized = case.get("optimized", {})
    comparison = case.get("comparison", {})
    audit = case.get("agent_audit", {})
    mapping = case.get("blind_mapping", {})
    return f"""
    <div class="reveal-panel" data-reveal="{_safe(case.get('vacancy_id'))}">
      <div class="reveal-grid">
        <article><h4>Blind mapping</h4><p>Left: <strong>{_safe(mapping.get('left'))}</strong><br>Right: <strong>{_safe(mapping.get('right'))}</strong></p></article>
        <article><h4>Generation cost</h4><p>Baseline {_fmt_cost(baseline.get('cost_usd'))}<br>Optimized {_fmt_cost(optimized.get('cost_usd'))}<br><strong>Savings {_fmt_delta(comparison.get('cost_savings_pct'), '%')}</strong></p></article>
        <article><h4>Quality delta</h4><p>Baseline HH {_safe(baseline.get('headhunter_score'))}<br>Optimized HH {_safe(optimized.get('headhunter_score'))}<br><strong>Delta {_fmt_delta(comparison.get('headhunter_score_delta'))}</strong></p></article>
        <article><h4>Agent blind audit</h4><p>Pass 1: <strong>{_safe(audit.get('pass_1_winner_variant'))}</strong><br>Pass 2 swapped: <strong>{_safe(audit.get('pass_2_winner_variant'))}</strong><br>Consensus: <strong>{_safe(audit.get('consensus'))}</strong></p></article>
      </div>
      <div class="details"><strong>Optimized mechanics:</strong> {_safe(optimized.get('iterations'))} review(s), premium={_safe(optimized.get('premium_model_used'))}, early-stop={_safe(optimized.get('early_stop_reason') or 'no')}. Machine gate: <strong>{_safe(comparison.get('machine_gate_pass'))}</strong>.</div>
    </div>
    """


def build_ab_showcase(*, experiment_root: Path, site_dir: Path) -> dict[str, Any]:
    report = _read_json(experiment_root / "ab_report.json")
    site_dir.mkdir(parents=True, exist_ok=True)
    cards: list[str] = []
    js_cases: list[dict[str, Any]] = []
    for case in report.get("cases", []):
        vacancy_id = str(case["vacancy_id"])
        case_dir = experiment_root / "cases" / vacancy_id
        left = _read_json(case_dir / "candidate_left.json")
        right = _read_json(case_dir / "candidate_right.json")
        cards.append(f"""
        <article class="case" data-case="{_safe(vacancy_id)}">
          <header class="case-head">
            <div><span class="eyebrow">Blind case</span><h2>{_safe(case.get('company'))}</h2><h3>{_safe(case.get('role_title'))}</h3></div>
            <div class="case-meta"><span>RAG {_safe(case.get('coverage_score'))}</span><a href="{_safe(case.get('url'))}" target="_blank" rel="noopener">Vacancy ↗</a></div>
          </header>
          <div class="blind-note">Both CVs use identical neutral presentation. Process identity, cost and agent preference remain hidden until <strong>all cases</strong> have a human vote.</div>
          <div class="pair"><section><div class="candidate-label">CV LEFT</div>{_render_cv(left)}</section><section><div class="candidate-label">CV RIGHT</div>{_render_cv(right)}</section></div>
          <div class="vote-row">
            <button type="button" data-vote="left">LEFT is better</button>
            <button type="button" data-vote="tie">Essentially tied</button>
            <button type="button" data-vote="right">RIGHT is better</button>
            <span class="vote-status">not voted</span>
          </div>
          {_audit_card(case)}
        </article>
        """)
        js_cases.append({
            "vacancy_id": vacancy_id,
            "mapping": case.get("blind_mapping", {}),
            "machine_gate_pass": case.get("comparison", {}).get("machine_gate_pass"),
            "savings_pct": case.get("comparison", {}).get("cost_savings_pct"),
            "quality_delta": case.get("comparison", {}).get("headhunter_score_delta"),
        })

    payload = json.dumps(js_cases, ensure_ascii=False).replace("</", "<\\/")
    index = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CV_fit — Blind cost A/B audit</title>
<style>
:root{{--bg:#eef1f4;--panel:#fff;--ink:#172033;--muted:#64748b;--line:#d9e0e7;--blue:#1769aa;--soft:#f7f9fb;--ok:#166534;--warn:#92400e}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 Arial,Helvetica,sans-serif}}a{{color:var(--blue)}}.top{{position:sticky;top:0;z-index:20;background:rgba(255,255,255,.97);border-bottom:1px solid var(--line)}}.top-inner{{max-width:1500px;margin:auto;padding:12px 22px;display:flex;justify-content:space-between;align-items:center;gap:18px}}.tabs{{display:flex;gap:8px}}.tabs a{{text-decoration:none;padding:8px 11px;border-radius:8px}}.tabs .active{{background:#e7f3ff;font-weight:800}}main{{max-width:1500px;margin:22px auto 80px;padding:0 22px}}.intro,.case,.summary{{background:var(--panel);border:1px solid var(--line);border-radius:14px}}.intro{{padding:20px;margin-bottom:18px}}.intro h1{{margin:0 0 5px}}.intro p{{margin:5px 0;color:var(--muted)}}.case{{margin:18px 0;overflow:hidden}}.case-head{{display:flex;justify-content:space-between;gap:20px;padding:16px 18px;border-bottom:1px solid var(--line)}}.case-head h2{{margin:0;font-size:19px}}.case-head h3{{margin:2px 0 0;font-size:14px;font-weight:600}}.eyebrow{{font-size:10px;text-transform:uppercase;letter-spacing:.8px;color:var(--muted);font-weight:800}}.case-meta{{display:flex;gap:8px;align-items:center;flex-wrap:wrap}}.case-meta span,.case-meta a{{background:var(--soft);border:1px solid var(--line);border-radius:999px;padding:5px 9px;text-decoration:none}}.blind-note{{padding:10px 18px;background:#fff8e5;border-bottom:1px solid #f2dc99;color:#6f5300}}.pair{{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--line)}}.pair>section{{background:#e5e8ec;padding:14px;min-width:0}}.candidate-label{{text-align:center;font-weight:900;letter-spacing:1px;margin-bottom:9px}}.paper{{background:white;max-width:760px;margin:auto;padding:30px 34px;min-height:980px;box-shadow:0 1px 6px rgba(0,0,0,.15)}}.paper-head{{border-bottom:2px solid #1f2937;padding-bottom:12px;margin-bottom:15px}}.paper-head h3{{margin:0 0 6px;font-size:19px}}.paper-head p{{margin:0;color:#475569}}.paper h4{{font-size:12px;text-transform:uppercase;letter-spacing:.9px;margin:18px 0 8px;border-bottom:1px solid #cbd5e1;padding-bottom:4px}}.cv-section{{margin:10px 0}}.role-head{{display:flex;justify-content:space-between;gap:12px}}.role-title{{font-style:italic;color:#475569}}.paper ul{{margin:5px 0;padding-left:19px}}.paper li{{margin:3px 0}}.skills{{font-size:12px}}.vote-row{{padding:14px 18px;display:flex;gap:8px;align-items:center;justify-content:center;flex-wrap:wrap;border-top:1px solid var(--line)}}button{{border:1px solid #b9c5d1;background:white;border-radius:9px;padding:9px 13px;cursor:pointer;font-weight:750}}button.selected{{background:#e7f3ff;border-color:#70a9d6;color:#0f4c81}}.vote-status{{color:var(--muted);min-width:90px}}.reveal-panel{{display:none;padding:16px 18px;background:#f5f9fc;border-top:1px solid var(--line)}}body.revealed .reveal-panel{{display:block}}.reveal-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}}.reveal-grid article{{background:white;border:1px solid var(--line);border-radius:10px;padding:11px}}.reveal-grid h4{{margin:0 0 5px}}.reveal-grid p{{margin:0}}.details{{margin-top:10px}}.summary{{display:none;padding:18px;margin:18px 0}}body.revealed .summary{{display:block}}.summary-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}}.summary-grid div{{background:var(--soft);border:1px solid var(--line);border-radius:10px;padding:11px}}@media(max-width:1000px){{.pair{{grid-template-columns:1fr}}.reveal-grid,.summary-grid{{grid-template-columns:1fr 1fr}}.paper{{min-height:auto}}}}@media(max-width:620px){{.top-inner,.case-head{{align-items:flex-start;flex-direction:column}}.reveal-grid,.summary-grid{{grid-template-columns:1fr}}main{{padding:0 10px}}.paper{{padding:22px 18px}}}}
</style></head><body>
<header class="top"><div class="top-inner"><strong>CV_fit</strong><nav class="tabs"><a href="../index.html">Vacancy feed</a><a class="active" href="index.html">Blind A/B Cost Lab</a></nav></div></header>
<main><section class="intro"><h1>Blind A/B cost audit</h1><p>Experiment <code>{_safe(report.get('experiment_id'))}</code>. Existing production CVs are compared against the cost-optimized process. Vote on employer-facing quality only.</p><p><strong>Important:</strong> cost, process identity and agent audit stay hidden until every case has a vote. Votes are stored only in this browser.</p></section>
<section class="summary" id="summary"><h2>Experiment revealed</h2><div class="summary-grid"><div><span>Human baseline wins</span><strong id="human-baseline">0</strong></div><div><span>Human optimized wins</span><strong id="human-optimized">0</strong></div><div><span>Human ties</span><strong id="human-ties">0</strong></div><div><span>Machine-gate passes</span><strong>{_safe(report.get('machine_gate_pass_count'))}/{_safe(report.get('completed_case_count'))}</strong></div></div><p>Mean generation savings: <strong>{_fmt_delta(report.get('mean_cost_savings_pct'), '%')}</strong> · mean Headhunter delta: <strong>{_fmt_delta(report.get('mean_headhunter_score_delta'))}</strong>. Audit-agent costs are experiment overhead and are excluded from generation savings.</p></section>
{''.join(cards)}
</main>
<script>
(()=>{{
const experiment={json.dumps(str(report.get('experiment_id')))};
const cases={payload};
const key=id=>`cvfit-ab-vote:${{experiment}}:${{id}}`;
function renderCase(el){{const id=el.dataset.case;const vote=localStorage.getItem(key(id));el.querySelectorAll('[data-vote]').forEach(btn=>btn.classList.toggle('selected',btn.dataset.vote===vote));el.querySelector('.vote-status').textContent=vote?`voted: ${{vote}}`:'not voted';}}
function allVoted(){{return cases.length>0&&cases.every(item=>localStorage.getItem(key(item.vacancy_id)));}}
function revealIfComplete(){{if(!allVoted())return;document.body.classList.add('revealed');let base=0,opt=0,ties=0;for(const item of cases){{const vote=localStorage.getItem(key(item.vacancy_id));if(vote==='tie'){{ties++;continue;}}const winner=item.mapping[vote];if(winner==='baseline')base++;if(winner==='optimized')opt++;}}document.getElementById('human-baseline').textContent=base;document.getElementById('human-optimized').textContent=opt;document.getElementById('human-ties').textContent=ties;}}
document.querySelectorAll('.case').forEach(el=>{{renderCase(el);el.querySelectorAll('[data-vote]').forEach(btn=>btn.addEventListener('click',()=>{{localStorage.setItem(key(el.dataset.case),btn.dataset.vote);renderCase(el);revealIfComplete();}}));}});revealIfComplete();
}})();
</script></body></html>"""
    (site_dir / "index.html").write_text(index, encoding="utf-8")
    shutil.copy2(experiment_root / "ab_report.json", site_dir / "ab_report.json")
    return report


def attach_navigation(site_dir: Path) -> bool:
    index_path = site_dir / "index.html"
    if not index_path.exists():
        return False
    text = index_path.read_text(encoding="utf-8")
    if "cvfit-ab-nav" in text:
        return False
    style = '<style id="cvfit-ab-nav-style">.cvfit-ab-nav a{display:inline-block;text-decoration:none;background:#e7f3ff;color:#1769aa;border-radius:9px;padding:7px 10px;font-weight:800;white-space:nowrap}</style>'
    if "</head>" in text:
        text = text.replace("</head>", style + "</head>", 1)
    nav = '<nav class="cvfit-ab-nav"><a href="ab-testing/index.html">Blind A/B Cost Lab</a></nav>'
    if '<div class="top-stats">' in text:
        text = text.replace('<div class="top-stats">', nav + '<div class="top-stats">', 1)
    elif "<body>" in text:
        text = text.replace("<body>", "<body>" + nav, 1)
    else:
        return False
    index_path.write_text(text, encoding="utf-8")
    return True


def restore_persisted(*, persisted_dir: Path, site_dir: Path) -> bool:
    source = persisted_dir / "site"
    if not (source / "index.html").exists():
        return False
    target = site_dir / "ab-testing"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    attach_navigation(site_dir)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or restore the blind CV cost A/B GitHub Pages tab.")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--experiment-root", required=True)
    build.add_argument("--site-dir", required=True)
    attach = sub.add_parser("attach")
    attach.add_argument("--site-dir", required=True)
    restore = sub.add_parser("restore")
    restore.add_argument("--persisted-dir", default="generation_state/ab_audit")
    restore.add_argument("--site-dir", required=True)
    args = parser.parse_args()

    if args.command == "build":
        build_ab_showcase(experiment_root=Path(args.experiment_root), site_dir=Path(args.site_dir))
        return 0
    if args.command == "attach":
        return 0 if attach_navigation(Path(args.site_dir)) else 1
    restored = restore_persisted(persisted_dir=Path(args.persisted_dir), site_dir=Path(args.site_dir))
    return 0 if restored else 1


if __name__ == "__main__":
    raise SystemExit(main())
