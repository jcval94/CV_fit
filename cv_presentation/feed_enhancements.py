from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ENHANCEMENT_MARKER = 'data-cvfit-feed-enhanced="1"'
PROCESS_METRICS_FILE = "process_metrics.json"
MAX_HEADHUNTER_REVIEWS = 5

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
.process-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px;margin:12px 0 2px}
.process-metric{background:#f7f8fa;border:1px solid #e1e4e8;border-radius:9px;padding:8px 9px;min-width:0}
.process-metric span{display:block;color:var(--muted);font-size:10px;line-height:1.1;margin-bottom:3px}
.process-metric strong{display:block;font-size:12px;line-height:1.2;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cv-send-cta{display:inline-flex!important;align-items:center;gap:6px;background:#1877f2!important;color:white!important;border-color:#1877f2!important;font-weight:800}
.cv-send-cta.review{background:#fff4d6!important;color:#8a5200!important;border-color:#e0b94d!important}
.cv-tile:first-child{position:relative}
.cv-tile:first-child:before{content:"RECOMMENDED";position:absolute;z-index:4;top:10px;left:10px;background:#1877f2;color:#fff;font-size:9px;font-weight:800;letter-spacing:.35px;border-radius:999px;padding:4px 7px;box-shadow:0 1px 3px rgba(0,0,0,.18)}
.page-count-badge{display:inline-flex;align-items:center;border-radius:999px;background:#eef2f7;color:#475569;font-size:10px;font-weight:800;padding:3px 7px;margin-left:6px}
.metrics-origin{display:block;margin-top:7px;color:var(--muted);font-size:10px}
/* The deployed preview is the final HTML itself. One wide column gives the
   fixed 8.5in Letter canvas enough viewport width to retain visible sheet edges. */
.cv-gallery{grid-template-columns:1fr!important;gap:14px!important;padding:14px!important;background:#e8eaed!important}
.cv-tile{border:1px solid #d5d9de;border-radius:10px;overflow:hidden;background:white!important}
.cv-canvas{height:900px!important;padding:0!important;background:#e9edf2!important;display:block!important}
.cv-html-preview{display:block;width:100%;height:100%;border:0;background:#e9edf2}
@media(max-width:800px){.feed-search{border-radius:10px}.feed-search-row{grid-template-columns:1fr}.feed-search button{padding:9px 12px}.process-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.cv-canvas{height:720px!important}}
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

  const safe=value=>value===null||value===undefined||value===''?'n/a':String(value);
  const money=value=>{
    if(value===null||value===undefined||value==='')return 'n/a';
    const parsed=Number(value);
    return Number.isFinite(parsed)?`$${parsed.toFixed(4)}`:'n/a';
  };
  const metric=(label,value)=>`<div class="process-metric"><span>${label}</span><strong>${safe(value)}</strong></div>`;
  const visiblePosts=()=>posts.filter(post=>!post.classList.contains('is-hidden')&&!post.classList.contains('search-hidden'));
  function updateCount(){count.textContent=`${visiblePosts().length} of ${posts.length} vacancies shown.`;}
  function refreshSearchText(post){post.dataset.searchText=normalize(post.textContent);}

  document.querySelectorAll('[data-filter]').forEach((btn,index)=>{
    btn.setAttribute('aria-pressed',index===0?'true':'false');
    btn.addEventListener('click',()=>{
      document.querySelectorAll('[data-filter]').forEach(x=>x.setAttribute('aria-pressed',x===btn?'true':'false'));
      requestAnimationFrame(updateCount);
    });
  });

  posts.forEach(post=>{post.setAttribute('tabindex','-1');refreshSearchText(post);});

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

  function upgradeHtmlPreviews(post){
    post.querySelectorAll('.cv-image-link[href*=".html"]').forEach(link=>{
      const canvas=link.closest('.cv-canvas');
      if(!canvas||canvas.querySelector('.cv-html-preview'))return;
      const frame=document.createElement('iframe');
      frame.className='cv-html-preview';
      frame.loading='lazy';
      frame.src=link.href;
      frame.title=(link.querySelector('img')?.alt||'CV')+' — live HTML preview';
      canvas.replaceChildren(frame);
    });
  }

  function addRecommendedCta(post){
    if(post.querySelector('.cv-send-cta'))return;
    const primary=post.querySelector('.cv-gallery .cv-tile');
    if(!primary)return;
    const html=primary.querySelector('.cv-actions a[href*=".html"]');
    const pdf=primary.querySelector('.cv-actions a[href$=".pdf"],.cv-actions a[href$=".PDF"]');
    const target=html||pdf;
    if(!target)return;
    const ready=post.dataset.status==='ready';
    const cta=document.createElement('a');
    cta.className='cv-send-cta'+(ready?'':' review');
    cta.href=target.href;cta.target='_blank';cta.rel='noopener';
    cta.textContent=ready?'Open CV to send →':'Review recommended CV →';
    const links=post.querySelector('.post-links')||post.querySelector('.post-body');
    links?.appendChild(cta);
  }

  function addProcessMetrics(post,row,process){
    if(post.querySelector('.process-metrics'))return;
    const rounds=process?.headhunter_iterations;
    const bestRound=process?.best_review_iteration;
    const headhunter=process?.headhunter_score ?? row?.headhunter_score;
    const coverage=process?.coverage_score ?? row?.rag_coverage;
    const gaps=process?.unsupported_requirements_count;
    const quality=process?.content_quality_target_reached===true?'PASS':process?.content_quality_target_reached===false?'NOT REACHED':'n/a';
    const premium=process?.premium_model_used===true?'yes':process?.premium_model_used===false?'no':'n/a';
    const presentation=process?.presentation_gate_status;
    const totalCost=process?.total_pipeline_known_cost_usd;
    const costComplete=process?.total_pipeline_cost_complete===true?'complete':process?.total_pipeline_cost_complete===false?'partial':'n/a';
    const block=document.createElement('div');
    block.className='process-metrics';
    block.innerHTML=[
      metric('Headhunter score',headhunter),
      metric('Review rounds',rounds?`${rounds}/5`:'n/a'),
      metric('Best round',bestRound||'n/a'),
      metric('RAG coverage',coverage),
      metric('Unsupported gaps',gaps),
      metric('Quality target',quality),
      metric('Pipeline OpenAI cost',money(totalCost)),
      metric('Cost coverage',costComplete),
      metric('Generation cost',money(process?.generation_cost_usd)),
      metric('Cover-letter cost',money(process?.cover_letter_cost_usd)),
      metric('Presentation cost',money(process?.presentation_cost_usd)),
      metric('Premium model',premium),
      metric('Retrieval',process?.retrieval_mode),
      metric('Presentation gate',presentation),
      metric('Generation',process?.status),
      metric('Logic version',process?.generation_logic_version),
    ].join('');
    const body=post.querySelector('.post-body');
    body?.appendChild(block);
    if(process?.metrics_origin==='carried_forward'||process?.metrics_origin==='recovered_versioned_history'){
      const note=document.createElement('span');
      note.className='metrics-origin';
      note.textContent=process.metrics_origin==='recovered_versioned_history'
        ?'Some metrics were recovered from verified versioned history after a retry had overwritten them.'
        :'Some non-status metrics were carried forward from the last published valid run instead of being replaced by missing retry data.';
      body?.appendChild(note);
    }
    refreshSearchText(post);
  }

  async function addPageCount(post){
    const vacancy=post.dataset.vacancy;if(!vacancy)return;
    try{
      const response=await fetch(`vacancies/${encodeURIComponent(vacancy)}/application_bundle_report.json`,{cache:'no-store'});
      if(!response.ok)return;
      const bundle=await response.json();
      const templates=[...(bundle.templates||[])];
      const tiles=[...post.querySelectorAll('.cv-gallery .cv-tile')];
      ['primary','alternate'].forEach((role,index)=>{
        const item=templates.find(x=>x.role===role);const tile=tiles[index];
        if(!item||!tile)return;
        const pages=Number(item.expected_pages||0);if(!pages)return;
        const head=tile.querySelector('.cv-tile-head');
        if(head&&!head.querySelector('.page-count-badge')){
          const badge=document.createElement('span');badge.className='page-count-badge';badge.textContent=`${pages} page${pages===1?'':'s'}`;head.appendChild(badge);
        }
      });
    }catch(_error){}
  }

  Promise.all([
    fetch('showcase.json',{cache:'no-store'}).then(r=>r.ok?r.json():{}).catch(()=>({})),
    fetch('process_metrics.json',{cache:'no-store'}).then(r=>r.ok?r.json():{}).catch(()=>({})),
  ]).then(([showcase,processPayload])=>{
    const rows=new Map((showcase.vacancies||[]).map(row=>[String(row.vacancy_id),row]));
    const metrics=processPayload.entries||{};
    posts.forEach(post=>{
      const id=String(post.dataset.vacancy||'');
      upgradeHtmlPreviews(post);
      addRecommendedCta(post);
      addProcessMetrics(post,rows.get(id)||{},metrics[id]||{});
      void addPageCount(post);
    });
    applySearch();
  });

  updateCount();
})();
</script>
'''.strip()


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _review_rounds(entry: dict[str, Any]) -> int | None:
    value = entry.get("headhunter_iterations")
    if isinstance(value, int) and value > 0:
        return value
    if entry.get("status") == "COMPLETED_BELOW_TARGET":
        return MAX_HEADHUNTER_REVIEWS
    return None


def _present(value: Any) -> bool:
    return value is not None and value != ""


def _metric_value(entry: dict[str, Any], key: str) -> Any:
    value = entry.get(key)
    if _present(value):
        return value
    last = entry.get("last_known_metrics")
    if isinstance(last, dict):
        return last.get(key)
    return None


def _generation_cost(entry: dict[str, Any]) -> float | None:
    for key in ("known_estimated_cost_usd", "estimated_cost_usd", "attempt_known_cost_usd"):
        value = _metric_value(entry, key)
        if _present(value):
            try:
                return float(value)
            except (TypeError, ValueError):
                pass
    return None


def build_process_metrics(manifest_path: Path) -> dict[str, Any]:
    manifest = _read_json(manifest_path, {"entries": {}})
    rows: dict[str, Any] = {}
    for vacancy_id, raw in manifest.get("entries", {}).items():
        entry = dict(raw or {})
        gate_raw = _metric_value(entry, "presentation_gate")
        gate = dict(gate_raw or {}) if isinstance(gate_raw, dict) else {}
        unsupported_raw = _metric_value(entry, "unsupported_requirements")
        unsupported = list(unsupported_raw or []) if isinstance(unsupported_raw, list) else []
        generation_cost = _generation_cost(entry)
        total_known = entry.get("total_pipeline_known_cost_usd")
        total_complete = entry.get("total_pipeline_cost_complete")
        if not _present(total_known):
            stage_values = [generation_cost, entry.get("cover_letter_cost_usd"), entry.get("presentation_cost_usd")]
            parsed: list[float] = []
            for value in stage_values:
                if _present(value):
                    try:
                        parsed.append(float(value))
                    except (TypeError, ValueError):
                        pass
            total_known = round(sum(parsed), 8) if parsed else None
            if total_complete is None:
                total_complete = len(parsed) == 3
        rows[str(vacancy_id)] = {
            "status": entry.get("status"),
            "ready_to_send": bool(entry.get("ready_to_send")),
            "review_required": bool(entry.get("review_required")),
            "coverage_score": _metric_value(entry, "coverage_score"),
            "estimated_cost_usd": _metric_value(entry, "estimated_cost_usd"),
            "generation_cost_usd": generation_cost,
            "cover_letter_cost_usd": entry.get("cover_letter_cost_usd"),
            "presentation_cost_usd": entry.get("presentation_cost_usd"),
            "total_pipeline_known_cost_usd": total_known,
            "total_pipeline_cost_complete": total_complete,
            "cumulative_known_cost_usd": entry.get("cumulative_known_cost_usd"),
            "unsupported_requirements_count": len(unsupported),
            "content_quality_target_reached": _metric_value(entry, "content_quality_target_reached"),
            "retrieval_mode": entry.get("retrieval_mode"),
            "generation_logic_version": entry.get("generation_logic_version"),
            "presentation_gate_status": gate.get("status"),
            "primary_template": gate.get("primary_template"),
            "cover_letter_ready": gate.get("cover_letter_ready"),
            "headhunter_iterations": _review_rounds(entry) or _metric_value(entry, "headhunter_iterations"),
            "best_review_iteration": _metric_value(entry, "best_review_iteration"),
            "headhunter_score": _metric_value(entry, "headhunter_score"),
            "headhunter_decision": _metric_value(entry, "headhunter_decision"),
            "premium_model_used": _metric_value(entry, "premium_model_used"),
            "metrics_origin": "last_known" if isinstance(entry.get("last_known_metrics"), dict) else "current",
        }
    return {"schema_version": 2, "entries": rows}


def _merge_published_metrics(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    """Never replace a previously valid observable with null from a later retry."""
    carry_fields = {
        "coverage_score",
        "estimated_cost_usd",
        "generation_cost_usd",
        "cover_letter_cost_usd",
        "presentation_cost_usd",
        "total_pipeline_known_cost_usd",
        "total_pipeline_cost_complete",
        "cumulative_known_cost_usd",
        "unsupported_requirements_count",
        "content_quality_target_reached",
        "presentation_gate_status",
        "primary_template",
        "cover_letter_ready",
        "headhunter_iterations",
        "best_review_iteration",
        "headhunter_score",
        "headhunter_decision",
        "premium_model_used",
    }
    merged = dict(current)
    carried = False
    for key in carry_fields:
        if not _present(merged.get(key)) and _present(previous.get(key)):
            merged[key] = previous[key]
            carried = True
    if carried:
        merged["metrics_origin"] = "carried_forward"
    return merged


def enhance_feed_index(
    site_dir: Path,
    *,
    generation_manifest_path: Path = Path("generation_state/manifest.json"),
) -> dict[str, object]:
    """Enhance an already-rendered vacancy feed without regenerating CVs."""
    index_path = site_dir / "index.html"
    if not index_path.exists():
        raise FileNotFoundError(index_path)

    previous_payload = _read_json(site_dir / PROCESS_METRICS_FILE, {"entries": {}})
    process_metrics = build_process_metrics(generation_manifest_path)

    # One-time, auditable recovery for metrics that are provably present in
    # versioned repository history but were erased by a later failed retry.
    recovered_payload = _read_json(generation_manifest_path.parent / "recovered_metrics.json", {"entries": {}})
    recovered_rows = recovered_payload.get("entries", {}) if isinstance(recovered_payload, dict) else {}
    for vacancy_id, current in list(process_metrics["entries"].items()):
        recovered = recovered_rows.get(vacancy_id)
        if isinstance(recovered, dict):
            merged = _merge_published_metrics(recovered, current)
            if merged.get("metrics_origin") == "carried_forward":
                merged["metrics_origin"] = "recovered_versioned_history"
            if not _present(merged.get("total_pipeline_known_cost_usd")) and _present(merged.get("generation_cost_usd")):
                merged["total_pipeline_known_cost_usd"] = merged["generation_cost_usd"]
                merged["total_pipeline_cost_complete"] = False
            process_metrics["entries"][vacancy_id] = merged

    previous_rows = previous_payload.get("entries", {}) if isinstance(previous_payload, dict) else {}
    for vacancy_id, current in list(process_metrics["entries"].items()):
        previous = previous_rows.get(vacancy_id)
        if isinstance(previous, dict):
            process_metrics["entries"][vacancy_id] = _merge_published_metrics(previous, current)

    (site_dir / PROCESS_METRICS_FILE).write_text(
        json.dumps(process_metrics, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    source = index_path.read_text(encoding="utf-8")
    if ENHANCEMENT_MARKER in source:
        return {"enhanced": False, "reason": "already_enhanced", "process_metric_entries": len(process_metrics["entries"])}

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
        "process_metric_entries": len(process_metrics["entries"]),
        "features": [
            "vacancy_search",
            "search_result_count",
            "keyboard_shortcuts",
            "accessible_filter_state",
            "decision_specific_selected_styles",
            "recommended_cv_cta",
            "explicit_page_count",
            "live_html_sheet_previews",
            "process_metrics",
            "stage_cost_breakdown",
            "valid_metric_carry_forward",
            "verified_history_recovery",
        ],
    }
