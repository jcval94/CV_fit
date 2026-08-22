from __future__ import annotations

from pathlib import Path


ENHANCEMENT_MARKER = 'data-cvfit-feed-enhanced="1"'

_SEARCH_PANEL = r'''
<div class="feed-search" role="search" aria-label="Search vacancies">
  <label for="vacancy-search">Search this feed</label>
  <div class="feed-search-row">
    <input id="vacancy-search" type="search" autocomplete="off" placeholder="Company, role, location or skill…" aria-describedby="vacancy-search-help">
    <button id="vacancy-search-clear" type="button">Clear</button>
  </div>
  <div id="vacancy-search-help" class="feed-search-help"><span id="vacancy-search-count" aria-live="polite"></span> Tip: press <kbd>/</kbd> to search and <kbd>Esc</kbd> to clear.</div>
</div>
'''.strip()

_EXTRA_CSS = r'''
/* CV_fit feed enhancement layer */
.feed-search{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px;box-shadow:var(--shadow)}
.feed-search label{display:block;font-weight:750;margin-bottom:7px}
.feed-search-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px}
.feed-search input{width:100%;border:1px solid #ccd0d5;border-radius:9px;padding:10px 12px;background:white;color:var(--ink);font:inherit;outline:none}
.feed-search input:focus{border-color:#8ebce1;box-shadow:0 0 0 3px rgba(23,105,170,.12)}
.feed-search button{border:1px solid #ccd0d5;border-radius:9px;background:white;padding:0 12px;color:var(--blue);cursor:pointer;font-weight:700}
.feed-search-help{margin-top:6px;color:var(--muted);font-size:11px}
kbd{font:10px/1.2 ui-monospace,SFMono-Regular,Consolas,monospace;border:1px solid #ccd0d5;background:#f6f7f8;border-radius:4px;padding:1px 4px}
.feed-post.search-hidden{display:none}
.feed-review-actions button[data-review="SEND"].selected{background:#e5f7ea;border-color:#77c48f;color:#176b34}
.feed-review-actions button[data-review="REVISE"].selected{background:#fff4d6;border-color:#e0b94d;color:#8a5200}
.feed-review-actions button[data-review="REJECT"].selected{background:#fde8e8;border-color:#db8d8d;color:#9d2525}
.feed-post:focus-within{outline:2px solid rgba(23,105,170,.16);outline-offset:2px}
@media(max-width:800px){.feed-search{border-radius:10px}.feed-search-row{grid-template-columns:1fr}.feed-search button{padding:9px 12px}}
'''.strip()

_EXTRA_JS = r'''
<script data-cvfit-feed-enhanced="1">
(()=>{
  const normalize=value=>(value||'').toString().toLocaleLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
  const input=document.getElementById('vacancy-search');
  const clear=document.getElementById('vacancy-search-clear');
  const count=document.getElementById('vacancy-search-count');
  const posts=[...document.querySelectorAll('.feed-post')];
  if(!input||!clear||!count)return;

  document.querySelectorAll('[data-filter]').forEach((btn,index)=>{
    btn.setAttribute('aria-pressed',index===0?'true':'false');
    btn.addEventListener('click',()=>{
      document.querySelectorAll('[data-filter]').forEach(x=>x.setAttribute('aria-pressed',x===btn?'true':'false'));
      requestAnimationFrame(updateCount);
    });
  });

  posts.forEach(post=>{
    post.setAttribute('tabindex','-1');
    post.dataset.searchText=normalize(post.textContent);
  });

  const visiblePosts=()=>posts.filter(post=>!post.classList.contains('is-hidden')&&!post.classList.contains('search-hidden'));
  function updateCount(){
    const visible=visiblePosts().length;
    count.textContent=`${visible} of ${posts.length} vacancies shown.`;
  }
  function applySearch(){
    const query=normalize(input.value.trim());
    posts.forEach(post=>post.classList.toggle('search-hidden',Boolean(query)&&!post.dataset.searchText.includes(query)));
    updateCount();
  }
  function resetSearch(){input.value='';applySearch();input.focus();}

  input.addEventListener('input',applySearch);
  clear.addEventListener('click',resetSearch);
  document.addEventListener('keydown',event=>{
    if(event.key==='/'&&!event.ctrlKey&&!event.metaKey&&!event.altKey&&document.activeElement!==input){event.preventDefault();input.focus();}
    if(event.key==='Escape'&&document.activeElement===input){event.preventDefault();resetSearch();}
  });
  updateCount();
})();
</script>
'''.strip()


def enhance_feed_index(site_dir: Path) -> dict[str, object]:
    """Add no-cost UX enhancements to an already-rendered vacancy feed.

    This function intentionally edits only ``index.html``. It never reads or
    changes CV content, application bundles, human decisions or model state.
    It is idempotent so repeated GitHub Pages refreshes are safe.
    """
    index_path = site_dir / "index.html"
    if not index_path.exists():
        raise FileNotFoundError(index_path)

    source = index_path.read_text(encoding="utf-8")
    if ENHANCEMENT_MARKER in source:
        return {"enhanced": False, "reason": "already_enhanced"}

    feed_anchor = '<section class="feed">'
    if feed_anchor not in source:
        raise ValueError("expected vacancy feed markup was not found in index.html")
    if "</style>" not in source or "</body>" not in source:
        raise ValueError("index.html is missing required style/body closing tags")

    source = source.replace(feed_anchor, feed_anchor + _SEARCH_PANEL, 1)
    source = source.replace("</style>", _EXTRA_CSS + "\n</style>", 1)
    source = source.replace("</body>", _EXTRA_JS + "\n</body>", 1)
    index_path.write_text(source, encoding="utf-8")

    return {
        "enhanced": True,
        "features": [
            "vacancy_search",
            "search_result_count",
            "keyboard_shortcuts",
            "accessible_filter_state",
            "decision_specific_selected_styles",
        ],
    }
