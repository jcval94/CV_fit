from __future__ import annotations

from pathlib import Path


STATUS_MARKER = 'data-cvfit-send-status="1"'

_STATUS_CSS = r'''
/* Browser-local application tracking. This is intentionally not server-side evidence. */
.feed-review-actions [data-review],
.feed-review-actions [data-review-current],
.review-actions [data-decision],
#human-review { display:none!important; }
.cv-send-status-toggle{border:1px solid #aeb6c2!important;background:#f5f6f7!important;color:#475569!important;border-radius:999px!important;padding:7px 11px!important;font-size:11px!important;font-weight:800!important;cursor:pointer!important;white-space:nowrap}
.cv-send-status-toggle.sent{background:#e5f7ea!important;border-color:#77c48f!important;color:#176b34!important}
.cv-send-status-note{font-size:10px;color:var(--muted,#65676b);margin-left:6px}
'''.strip()

_STATUS_JS = r'''
<script data-cvfit-send-status="1">
(()=>{
  const SENT='CV enviado';
  const NOT_SENT='CV no enviado';
  const readStatus=id=>{
    const key=`cvfit-send-status:${id}`;
    const saved=localStorage.getItem(key);
    if(saved===SENT||saved===NOT_SENT)return saved;
    // One-time compatibility with the previous local SEND/REVISE/REJECT control.
    return localStorage.getItem(`cvfit-human-review:${id}`)==='SEND'?SENT:NOT_SENT;
  };
  const render=(button,id)=>{
    const value=readStatus(id);
    button.textContent=`Status: ${value}`;
    button.classList.toggle('sent',value===SENT);
    button.setAttribute('aria-pressed',value===SENT?'true':'false');
    button.setAttribute('aria-label',`Cambiar status. Actual: ${value}`);
  };
  document.querySelectorAll('[data-cv-send-status]').forEach(button=>{
    const id=button.dataset.cvSendStatus;
    if(!id)return;
    render(button,id);
    button.addEventListener('click',()=>{
      const next=readStatus(id)===SENT?NOT_SENT:SENT;
      localStorage.setItem(`cvfit-send-status:${id}`,next);
      render(button,id);
    });
  });
})();
</script>
'''.strip()


def _inject_common(html: str) -> str:
    if STATUS_MARKER in html:
        return html
    if "</style>" in html:
        html = html.replace("</style>", _STATUS_CSS + "\n</style>", 1)
    elif "</head>" in html:
        html = html.replace("</head>", f"<style>{_STATUS_CSS}</style></head>", 1)
    if "</body>" not in html:
        raise ValueError("expected closing body tag while adding CV send status")
    return html.replace("</body>", _STATUS_JS + "\n</body>", 1)


def _inject_feed(index_html: str) -> str:
    html = index_html.replace(
        "<div><strong>Human decision</strong><span class=\"local-note\">stored only in this browser</span></div>",
        "<div><strong>Status</strong><span class=\"local-note\">control manual, guardado sólo en este navegador</span></div>",
    )
    marker = '<div class="feed-review-actions">'
    replacement = (
        marker
        + '<button type="button" class="cv-send-status-toggle" '
          'data-cv-send-status="__CVFIT_DYNAMIC__">Status: CV no enviado</button>'
        + '<span class="cv-send-status-note">manual</span>'
    )
    if marker not in html:
        raise ValueError("expected feed review controls while adding CV send status")
    html = html.replace(marker, replacement)
    # Replace each placeholder with the owning feed-post vacancy id using a bounded pass.
    chunks: list[str] = []
    cursor = 0
    token = 'data-cv-send-status="__CVFIT_DYNAMIC__"'
    while True:
        pos = html.find(token, cursor)
        if pos < 0:
            chunks.append(html[cursor:])
            break
        post_start = html.rfind('<article class="feed-post"', 0, pos)
        vacancy_key = 'data-vacancy="'
        vacancy_pos = html.find(vacancy_key, post_start, pos) if post_start >= 0 else -1
        if vacancy_pos < 0:
            raise ValueError("could not resolve vacancy id for feed status control")
        value_start = vacancy_pos + len(vacancy_key)
        value_end = html.find('"', value_start)
        vacancy_id = html[value_start:value_end]
        chunks.append(html[cursor:pos])
        chunks.append(f'data-cv-send-status="{vacancy_id}"')
        cursor = pos + len(token)
    return _inject_common("".join(chunks))


def _inject_detail(detail_html: str, vacancy_id: str) -> str:
    html = detail_html.replace(
        "<strong>Human review — local browser only</strong>",
        "<strong>Status — local browser only</strong>",
    )
    marker = '<div class="review-actions">'
    replacement = (
        marker
        + f'<button type="button" class="cv-send-status-toggle" data-cv-send-status="{vacancy_id}">'
          'Status: CV no enviado</button>'
        + '<span class="cv-send-status-note">control manual</span>'
    )
    if marker in html:
        html = html.replace(marker, replacement, 1)
    return _inject_common(html)


def apply_manual_send_status(site_dir: Path) -> dict[str, int | bool]:
    """Add a two-state sent/not-sent control without claiming server-side application evidence.

    The value lives only in browser localStorage. It is deliberately separate from
    application_state.json and decision-grade ROI because a static Pages click is
    not authenticated/persisted evidence of an employer application.
    """
    index_path = site_dir / "index.html"
    if not index_path.exists():
        raise FileNotFoundError(index_path)

    index = index_path.read_text(encoding="utf-8")
    if STATUS_MARKER not in index:
        index_path.write_text(_inject_feed(index), encoding="utf-8")

    detail_count = 0
    vacancies_dir = site_dir / "vacancies"
    if vacancies_dir.exists():
        for detail_path in sorted(vacancies_dir.glob("*/index.html")):
            vacancy_id = detail_path.parent.name
            text = detail_path.read_text(encoding="utf-8")
            if STATUS_MARKER in text:
                continue
            detail_path.write_text(_inject_detail(text, vacancy_id), encoding="utf-8")
            detail_count += 1

    return {"applied": True, "detail_pages_updated": detail_count}
