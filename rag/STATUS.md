# RAG status

This document describes the retrieval state of `CV_fit` as of 2026-08-21.

## Current maturity

The professional-evidence RAG is **operational as a deterministic retrieval v1**, not merely scaffolded.

```text
experience/**/*.md                     canonical professional evidence
        ↓
rag.normalize                          deterministic normalization
        ↓
rag.evidence                           typed semantic chunks + policy eligibility
        ↓
rag_state/records + chunks             versioned derived evidence state
        ↓
rag_state/lexical_index.json           incremental public-safe lexical retrieval
        ↓
cv_matching                            vacancy requirement ↔ evidence matching
        ↓
cv_agent.context                       grounded context assembly
        ↓
CV Strategist / Writer / Headhunter    LLM workflow
        ↓
deterministic claim validators         post-generation grounding gate
```

### Implemented

- governed canonical professional source under `experience/`
- deterministic normalization with stable record identity and content hashes
- semantic typed chunks rather than arbitrary recursive text splitting
- atomic `ACH-*` metric chunks with local public/CV-use eligibility
- atomic skill chunks preserving `core | working | familiarity`
- credentials, project/role sections, ownership boundaries and policy chunks
- public-safe / CV-eligible filtering before evidence enters the active index
- versioned incremental `rag_state/` with manifest and no-op idempotence checks
- lexical retrieval over eligible professional evidence
- deterministic relation extraction into `rag_state/relations.json`
- vacancy-to-evidence matching with `strong | partial | weak | unsupported`
- grounded context budgeting before model calls
- output claim, metric, proficiency, language and structure validation

### Not implemented yet

- dense embeddings / vector index
- lexical + dense hybrid fusion
- semantic reranker
- automatic graph expansion using `relations.json`
- production retrieval quality benchmark across a larger labeled vacancy suite
- automatic CV generation on every new vacancy

Dense/vector retrieval is intentionally deferred until the first authenticated canary run is evaluated. The deterministic lexical layer remains transparent and gives a stable baseline against which dense retrieval can be measured.

## Canonical professional sources

The active professional RAG source is **only** `experience/**/*.md`. Vacancy JSON is never treated as evidence about the candidate.

The current state contains **34 canonical professional source records**:

| Source family | Count | Purpose |
| --- | ---: | --- |
| `experience/_meta/` | 3 | data contract, conflicts, open questions / policy |
| `experience/achievements/` | 1 | canonical `ACH-*` metric registry |
| `experience/certifications.md` | 1 | credentials and usage eligibility |
| `experience/education.md` | 1 | formal education |
| `experience/profile.md` | 1 | stable professional positioning |
| `experience/projects/` | 22 | project-level evidence and boundaries |
| `experience/roles/` | 4 | chronology and role scope |
| `experience/skills.md` | 1 | governed skill proficiency |
| **Total** | **34** | |

The latest persisted post-merge no-op run on `main` reports:

- discovered: 34
- unchanged: 34
- new: 0
- modified: 0
- impacted records: 0
- reindexed records: 0
- status: success

This proves that unchanged professional evidence is not reparsed/reindexed on a normal incremental run.

## Vacancy corpus: separate retrieval domain

Vacancies are a separate corpus:

- `GPTW/**/*.json`
- `Vacantes/**/*.json`

They normalize into `vacancy_state/`, not `rag_state/`. Their purpose is to describe the target role and drive retrieval from professional evidence.

The vacancy side currently has:

- canonical vacancy normalization and deduplication
- application-language detection
- JD fidelity gate (`full | partial | sparse`)
- semantic vacancy chunks
- incremental lexical index
- source provenance
- no-op idempotence checks

The Konfío `AI/ML Engineer Sr.` enriched canary adds a structured capture derived from the active official posting while preserving the original feed as a separate source. Cross-source deduplication must produce one canonical vacancy with both provenance references.

## Retrieval safety boundary

Only evidence chunks that are both public-safe and CV-eligible can enter active professional retrieval. Policy/router material can inform governance but is not silently converted into candidate claims.

Important examples:

- a `familiarity` skill cannot support expert/advanced wording;
- exact metrics require an approved public `ACH-*` record;
- unresolved/private metrics remain blocked;
- negative ownership/specialization boundaries remain executable constraints;
- an `unsupported` vacancy requirement stays unsupported rather than being filled by invention.

## Next retrieval milestone

The immediate milestone is **not embeddings**. It is an authenticated canary evaluation:

1. full/eligible Konfío JD
2. current lexical professional retrieval
3. vacancy↔evidence match inspection
4. OpenAI-backed ADK generation with bounded five-review loop
5. factual/language/structure validation
6. per-agent token and estimated-cost telemetry
7. human review of misses and false-positive evidence

Only after that run should dense embeddings / hybrid retrieval be added, and only if the canary demonstrates retrieval misses that the lexical baseline cannot reliably solve.
