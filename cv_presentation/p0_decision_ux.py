from __future__ import annotations

import argparse
import json
from pathlib import Path


P0_UX_MARKER = 'data-cvfit-p0-decision-ux="1"'

_P0_CSS = r'''
/* Decision-first P0 UX layer. Keep many metrics, but give them clear hierarchy. */
.fit-strip,.process-metrics{display:none!important}
.feed-post{overflow:visible}
.post-head{border-bottom:0}
.vacancy-cta{background:white!important;color:var(--blue)!important;border:1px solid #b9c8d8!important;font-weight:700!important}
.post-body{padding:14px 16px 16px!important;border-top:1px solid #edf0f2}
.recommendation-banner{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:14px;align-items:start;border:1px solid #d7dee7;border-left-width:5px;border-radius:11px;padding:12px 14px;margin:0 0 12px;background:#f8fafc}
.recommendation-banner.ready{border-left-color:#219653;background:#f2fbf5}
.recommendation-banner.review{border-left-color:#d59a00;background:#fffbef}
.recommendation-banner.blocked{border-left-color:#c55252;background:#fff6f6}
.recommendation-kicker{display:block;font-size:10px;line-height:1.2;font-weight:850;letter-spacing:.7px;text-transform:uppercase;color:var(--muted);margin-bottom:3px}
.recommendation-banner strong{display:block;font-size:17px;line-height:1.25;margin-bottom:3px}
.recommendation-banner p{margin:0;color:#4b5563;font-size:12px;line-height:1.45}
.recommendation-state{white-space:nowrap;border-radius:999px;padding:5px 9px;font-size:10px;font-weight:850;letter-spacing:.35px;text-transform:uppercase;background:white;border:1px solid currentColor}
.recommendation-banner.ready .recommendation-state{color:#176b34}
.recommendation-banner.review .recommendation-state{color:#8a5a00}
.recommendation-banner.blocked .recommendation-state{color:#9d2525}
.decision-metrics{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;margin:0 0 8px}
.decision-metric{background:white;border:1px solid #dfe4ea;border-radius:10px;padding:9px 10px;min-width:0}
.decision-metric span{display:block;color:var(--muted);font-size:10px;line-height:1.1;margin-bottom:4px}
.decision-metric strong{display:block;font-size:17px;line-height:1.15;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.decision-metric.primary{border-color:#bad3e8;background:#f6fbff}
.supporting-metrics{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 2px}
.supporting-metric{display:inline-flex;align-items:center;gap:5px;border:1px solid #e0e4e9;border-radius:999px;padding:4px 7px;background:#f8f9fb;color:#4b5563;font-size:10px;line-height:1.2;max-width:100%}
.supporting-metric b{color:#252b33;font-weight:800}
.metrics-origin{margin-top:8px!important}
.post-summary{font-size:13px!important;line-height:1.5!important;margin:11px 0 8px!important}
.post-links{align-items:center}
.cv-send-cta{background:white!important;color:var(--blue)!important;border:1px solid #b9c8d8!important;font-weight:700!important}
.cv-send-cta.review{background:white!important;color:var(--blue)!important;border-color:#b9c8d8!important}
.post-review.decision-actions{border-top:1px solid #edf0f2;border-bottom:1px solid #edf0f2;padding:12px 16px!important;background:#fbfcfd!important;align-items:center!important}
.post-review.decision-actions>div:first-child strong{font-size:13px}
.post-review.decision-actions .local-note{font-size:10px}
.feed-review-actions button{min-height:34px;padding:7px 11px!important}
.feed-review-actions button[data-review="SEND"]{background:var(--blue)!important;color:white!important;border-color:var(--blue)!important;font-weight:850!important;box-shadow:0 1px 2px rgba(0,0,0,.08)}
.feed-review-actions button[data-review="SEND"].selected{background:#12609e!important;color:white!important;border-color:#12609e!important}
.feed-review-actions button[data-review="REVISE"],.feed-review-actions button[data-review="REJECT"]{background:white!important;color:#374151!important;border-color:#cfd5dc!important}
.feed-review-actions button[data-review="REVISE"].selected{background:#fff4d6!important;border-color:#e0b94d!important;color:#8a5200!important}
.feed-review-actions button[data-review="REJECT"].selected{background:#fde8e8!important;border-color:#db8d8d!important;color:#9d2525!important}
.feed-review-current{font-size:10px!important;min-width:88px!important}
.cv-gallery{display:block!important;padding:14px!important;background:#e9edf2!important;border-top:0!important}
.cv-tile{border:1px solid #d5d9de;border-radius:10px;overflow:hidden;background:white!important}
.cv-tile.alternate-cv{display:none}
.cv-tile.alternate-cv.is-open{display:block;margin-top:12px}
.cv-canvas{height:780px!important}
.alternate-toggle{width:100%;margin-top:10px;border:1px solid #cbd5df;border-radius:9px;background:white;color:var(--blue);padding:9px 12px;font-weight:750;cursor:pointer;text-align:center}
.alternate-toggle:hover{background:#f5f9fc}
.alternate-toggle .toggle-sub{display:block;color:var(--muted);font-size:10px;font-weight:500;margin-top:1px}
@media(max-width:1000px){.decision-metrics{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:800px){
  .recommendation-banner{grid-template-columns:1fr;gap:8px}
  .recommendation-state{justify-self:start}
  .decision-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}
  .decision-metric strong{font-size:15px}
  .supporting-metrics{gap:5px}
  .post-review.decision-actions{align-items:flex-start!important}
  .feed-review-actions{width:100%}
  .feed-review-actions button[data-review="SEND"]{flex:1 1 100%}
  .cv-canvas{height:650px!important}
}
'''.strip()

_P0_JS = r'''
<script data-cvfit-p0-decision-ux="1">
(()=>{
  const posts=[...document.querySelectorAll('.feed-post')];
  if(!posts.length)return;

  const present=value=>value!==null&&value!==undefined&&value!=='';
  const safe=value=>present(value)?String(value):'n/a';
  const money=value=>{
    if(!present(value))return 'n/a';
    const parsed=Number(value);
    return Number.isFinite(parsed)?`$${parsed.toFixed(4)}`:'n/a';
  };
  const yesNo=value=>value===true?'yes':value===false?'no':'n/a';
  const quality=value=>value===true?'PASS':value===false?'NOT REACHED':'n/a';
  const decisionMetric=(label,value,primary=false)=>`<div class="decision-metric${primary?' primary':''}"><span>${label}</span><strong>${safe(value)}</strong></div>`;
  const supportMetric=(label,value)=>`<span class="supporting-metric"><b>${label}</b>${safe(value)}</span>`;

  function recommendation(post,process,row){
    const ready=process?.ready_to_send===true||post.dataset.status==='ready';
    const sendable=row?.sendable===true||Boolean(post.querySelector('.cv-actions a[href*=".html"],.cv-actions a[href$=".pdf"],.cv-actions a[href$=".PDF"]'));
    const blocked=String(process?.status||'').includes('FAILED')&&!ready&&!sendable;
    const gaps=Number(process?.unsupported_requirements_count||0);
    if(ready){
      return {
        tone:'ready',
        kicker:'Application recommendation',
        title:'Ready to apply with the recommended CV',
        state:'Ready',
        body:'The current artifact cleared the application gate. Review the primary HTML CV, then approve it for use.'
      };
    }
    if(blocked){
      return {
        tone:'blocked',
        kicker:'Application recommendation',
        title:'Do not apply with this artifact yet',
        state:'Blocked',
        body:'The latest generation state failed. Keep the vacancy, but resolve the pipeline or CV review issue before using this version.'
      };
    }
    if(sendable){
      return {
        tone:'review',
        kicker:'Application recommendation',
        title:'CV available to send — review advised',
        state:'Sendable',
        body:gaps>0
          ?`A usable CV artifact exists even though ${gaps} unsupported requirement${gaps===1?'':'s'} remain. Check the Quality KPI and send as-is if the trade-off is acceptable.`
          :'A usable CV artifact exists even though one or more automated quality gates did not clear. Check the Quality KPI and send as-is or edit first.'
      };
    }
    return {
      tone:'review',
      kicker:'Application recommendation',
      title:'No sendable CV artifact yet',
      state:'Review',
      body:'The vacancy remains worth reviewing, but no public CV bundle is available from the current run.'
    };
  }

  function addDecisionSummary(post,row,process){
    if(post.querySelector('.recommendation-banner'))return;
    const body=post.querySelector('.post-body');
    if(!body)return;
    const rec=recommendation(post,process,row);
    const banner=document.createElement('section');
    banner.className=`recommendation-banner ${rec.tone}`;
    banner.innerHTML=`<div><span class="recommendation-kicker">${rec.kicker}</span><strong>${rec.title}</strong><p>${rec.body}</p></div><span class="recommendation-state">${rec.state}</span>`;
    body.prepend(banner);

    const sourceFit=row?.fit_score;
    const headhunter=process?.headhunter_score;
    const coverage=process?.coverage_score;
    const gaps=process?.unsupported_requirements_count;
    const totalCost=process?.total_pipeline_known_cost_usd;
    const rounds=process?.headhunter_iterations;
    const bestRound=process?.best_review_iteration;
    const costCoverage=process?.total_pipeline_cost_complete===true?'complete':process?.total_pipeline_cost_complete===false?'partial':'n/a';

    const primary=document.createElement('div');
    primary.className='decision-metrics';
    primary.innerHTML=[
      decisionMetric('Source fit',sourceFit,true),
      decisionMetric('Quality KPI',present(headhunter)?`${headhunter}/100`:'n/a',true),
      decisionMetric('RAG coverage',coverage,true),
      decisionMetric('Unsupported gaps',gaps),
      decisionMetric('Pipeline cost',money(totalCost)),
    ].join('');
    banner.insertAdjacentElement('afterend',primary);

    const secondary=document.createElement('div');
    secondary.className='supporting-metrics';
    secondary.innerHTML=[
      supportMetric('JD',row?.jd_fidelity),
      supportMetric('Quality',quality(process?.content_quality_target_reached)),
      supportMetric('Presentation',process?.presentation_gate_status),
      supportMetric('Review rounds',rounds?`${rounds}/5`:'n/a'),
      supportMetric('Best round',bestRound),
      supportMetric('Cost coverage',costCoverage),
      supportMetric('Generation',process?.status),
      supportMetric('Premium model',yesNo(process?.premium_model_used)),
      supportMetric('Generation cost',money(process?.generation_cost_usd)),
      supportMetric('Cover cost',money(process?.cover_letter_cost_usd)),
      supportMetric('Presentation cost',money(process?.presentation_cost_usd)),
    ].join('');
    primary.insertAdjacentElement('afterend',secondary);
  }

  function simplifyActions(post){
    const gallery=post.querySelector('.cv-gallery');
    const review=post.querySelector('.post-review');
    if(review&&gallery&&!review.classList.contains('decision-actions')){
      review.classList.add('decision-actions');
      post.insertBefore(review,gallery);
      const heading=review.querySelector('strong');
      if(heading)heading.textContent='Application decision';
    }
    const approve=post.querySelector('[data-review="SEND"]');
    const revise=post.querySelector('[data-review="REVISE"]');
    const reject=post.querySelector('[data-review="REJECT"]');
    if(approve)approve.textContent='Approve CV';
    if(revise)revise.textContent='Needs edits';
    if(reject)reject.textContent='Dismiss';
    const openCta=post.querySelector('.cv-send-cta');
    if(openCta)openCta.textContent='Open CV to send';

    const current=post.querySelector('[data-review-current]');
    const pretty={SEND:'approved',REVISE:'needs edits',REJECT:'dismissed'};
    const refresh=()=>{
      if(!current)return;
      const value=localStorage.getItem('cvfit-human-review:'+post.dataset.vacancy);
      current.textContent=value?(pretty[value]||value):'not reviewed';
    };
    post.querySelectorAll('[data-review]').forEach(button=>button.addEventListener('click',()=>requestAnimationFrame(refresh)));
    refresh();
  }

  function collapseAlternate(post){
    const gallery=post.querySelector('.cv-gallery');
    if(!gallery||gallery.querySelector('.alternate-toggle'))return;
    const tiles=[...gallery.querySelectorAll('.cv-tile')];
    if(tiles.length<2)return;
    const alternate=tiles[1];
    alternate.classList.add('alternate-cv');
    const toggle=document.createElement('button');
    const controlId=`alternate-${post.dataset.vacancy}`;
    alternate.id=controlId;
    toggle.type='button';
    toggle.className='alternate-toggle';
    toggle.setAttribute('aria-controls',controlId);
    toggle.setAttribute('aria-expanded','false');
    toggle.innerHTML='Compare alternate CV <span class="toggle-sub">Harvard Executive stays available without occupying the default review flow.</span>';
    gallery.appendChild(toggle);
    toggle.addEventListener('click',()=>{
      const open=alternate.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded',open?'true':'false');
      toggle.innerHTML=open
        ?'Hide alternate CV <span class="toggle-sub">Return to the recommended CV only.</span>'
        :'Compare alternate CV <span class="toggle-sub">Harvard Executive stays available without occupying the default review flow.</span>';
      if(open)alternate.scrollIntoView({behavior:'smooth',block:'start'});
    });
  }

  function applyPost(post,row,process){
    addDecisionSummary(post,row||{},process||{});
    simplifyActions(post);
    collapseAlternate(post);
  }

  Promise.all([
    fetch('showcase.json',{cache:'no-store'}).then(r=>r.ok?r.json():{}).catch(()=>({})),
    fetch('process_metrics.json',{cache:'no-store'}).then(r=>r.ok?r.json():{}).catch(()=>({})),
  ]).then(([showcase,processPayload])=>{
    const rows=new Map((showcase.vacancies||[]).map(row=>[String(row.vacancy_id),row]));
    const metrics=processPayload.entries||{};
    posts.forEach(post=>applyPost(post,rows.get(String(post.dataset.vacancy)),metrics[String(post.dataset.vacancy)]));
  });
})();
</script>
'''.strip()


def apply_p0_decision_ux(site_dir: Path) -> dict[str, object]:
    """Add the P0 decision-first layer to an already rendered/enhanced feed."""
    index_path = site_dir / "index.html"
    if not index_path.exists():
        raise FileNotFoundError(index_path)
    source = index_path.read_text(encoding="utf-8")
    if P0_UX_MARKER in source:
        return {"applied": False, "reason": "already_applied"}
    if "</style>" not in source or "</body>" not in source:
        raise ValueError("index.html is missing required style/body closing tags")
    source = source.replace("</style>", _P0_CSS + "\n</style>", 1)
    source = source.replace("</body>", _P0_JS + "\n</body>", 1)
    index_path.write_text(source, encoding="utf-8")
    return {
        "applied": True,
        "features": [
            "dominant_application_recommendation",
            "hierarchical_visible_metrics",
            "recommended_cv_only_by_default",
            "alternate_cv_progressive_disclosure",
            "single_primary_decision_action",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply decision-first P0 UX improvements to the CV_fit Pages feed.")
    parser.add_argument("--site-dir", default="_site")
    args = parser.parse_args()
    result = apply_p0_decision_ux(Path(args.site_dir))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
