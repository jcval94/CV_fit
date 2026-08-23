# Incremental vacancy ingestion

This package ingests JSON vacancy feeds under `GPTW/**` and `Vacantes/**` without mixing them with professional evidence under `experience/`.

## Pipeline

```text
GPTW/**/*.json + Vacantes/**/*.json
        ↓
source-format validation (atomic per file)
        ↓
adapters: gptw_v1 / vacantes_v1
        ↓
Canonical Vacancy v2
        ↓
application-language inference
        ↓
JD fidelity assessment
        ↓
stable vacancy_id + deduplication
        ↓
per-source normalized snapshots
        ↓
only impacted vacancy records
        ↓
semantic vacancy chunks
        ↓
incremental lexical index
        ↓
versioned run report / quarantine
```

The pipeline is intentionally provider-agnostic. It does not build embeddings or generate CVs.

## Application language

The canonical vacancy contains:

- `application_language`: `en | es | fr | und`
- `language_confidence`: `0..1`
- `language_source`: `explicit_source | vacancy_text | role_title | undetermined`

Priority is explicit source language, then substantive vacancy description/requirements/responsibilities, then role-title signal. Source-provided candidate fit commentary is deliberately excluded from language inference.

Downstream CV generation treats this as a hard constraint. `und` blocks automatic CV generation until the source language is made explicit.

## JD fidelity

Canonical Vacancy v2 derives four additional fields from employer-authored vacancy content:

- `jd_fidelity`: `full | partial | sparse`
- `jd_fidelity_score`: transparent `0..100` detail score
- `jd_fidelity_reasons`: the description/detail counts behind the classification
- `jd_generation_eligible`: `true` only for `partial` or `full`

Only the original `description`, `requirements` and `responsibilities` count toward this assessment. Source fit commentary, fit scores and inferred `tech_stack` terms are deliberately excluded because they are not substitutes for the employer's Job Description.

A `sparse` vacancy remains valid for discovery, ranking and evidence matching, but `cv_agent` blocks live CV generation before any model call. The intended recovery is to enrich the source JSON with the original JD, not to ask an LLM to infer missing requirements.

## Daily automatic enrichment handoff

Daily source files may be intentionally sparse. `Auto-enrich daily vacancy JDs` attempts to recover employer-authored `JobPosting` JSON-LD and writes only derived files under `GPTW/enriched/auto/` or `Vacantes/enriched/auto/`; it never rewrites the incoming feed.

GitHub deliberately prevents ordinary push workflows from recursively triggering from commits made with `GITHUB_TOKEN`. Therefore, when the enrichment workflow actually commits a derived JD, it explicitly dispatches `vacancy-ingest.yml` against `main`. This handoff is required: the bot-authored enrichment must pass through the same canonical merge, fidelity, deduplication and generation path as every other source.

If enrichment produces no new derived source, no additional ingest dispatch is created. The normal ingest triggered by the original daily source remains sufficient.

## Canonical identity

`vacancy_id` is derived from normalized company + role + location. This is deliberately independent from source-native IDs so the same opening can collapse across GPTW and Vacantes feeds. If location is missing, the normalized URL participates in the identity key.

This rule is deterministic and auditable. It may still merge two truly separate openings with the same company/title/location or fail to merge listings whose titles differ materially; that trade-off is documented rather than hidden.

## Incrementality and idempotence

`vacancy_state/manifest.json` stores a SHA-256 for every source file. Unchanged files are not reparsed. New, modified or deleted files identify the affected vacancy IDs. Only those IDs are re-merged, re-chunked and reindexed; unchanged vacancies keep their existing index entries.

The manifest also stores `pipeline_version`. A change to normalization/chunk semantics increments this version and triggers one controlled rebuild, preventing unchanged raw JSON from retaining stale derived records after a code upgrade. Normal runs remain incremental.

CI now executes an immediate second run after each validation/main update and requires a true no-op: zero new/modified sources, zero impacted vacancies and zero reindexed vacancies. This turns idempotence from a unit-test assumption into an E2E invariant.

A full rebuild exists for validation and recovery, but is not the normal execution path.

## Invalid files and quarantine

Input validation is file-atomic: one invalid entry quarantines the current version of the whole file. Its previous contribution is removed from the active index so stale data is not silently served. The raw invalid version and an error report are copied under `vacancy_state/quarantine/`.

For pull requests, CI uses `--fail-on-quarantine`. On `main`, quarantine is recorded and committed so the pipeline remains observable instead of failing without state.

## State layout

```text
vacancy_state/
├── manifest.json
├── lexical_index.json
├── sources/        # normalized snapshots by source file
├── records/        # one canonical record per vacancy_id
├── chunks/         # stable vacancy chunks
├── quarantine/     # invalid raw versions + errors
├── runs/           # immutable run reports keyed by run id / commit
└── latest_run.json
```

This is derived, versioned state. Input feeds remain canonical for vacancy provenance; `experience/` remains canonical for professional evidence.

## Chunking

Each vacancy produces up to three stable chunks:

- `vac-...::core`: role/company/location/seniority/application language/JD fidelity/context
- `vac-...::requirements`: technologies, requirements and responsibilities
- `vac-...::source-fit`: source-provided fit score/reasoning, kept separate so it is never confused with vacancy facts

`source-fit` is excluded from default matching retrieval; it is inspectable only through explicit opt-in.

The lexical index is a transparent first retrieval layer and a stable substrate for later dense embeddings. Vector infrastructure remains deferred.

## CLI

```bash
python -m vacancy_pipeline --repo . --state-dir vacancy_state --run-id local
python -m vacancy_pipeline.retrieve "fraud Python machine learning" --state-dir vacancy_state
```

Recovery / validation only:

```bash
python -m vacancy_pipeline --repo . --state-dir /tmp/vacancy-state --full-rebuild --fail-on-quarantine
```
