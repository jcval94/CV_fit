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
Canonical Vacancy v1
        ↓
application-language inference
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

## Canonical identity

`vacancy_id` is derived from normalized company + role + location. This is deliberately independent from source-native IDs so the same opening can collapse across GPTW and Vacantes feeds. If location is missing, the normalized URL participates in the identity key.

This rule is deterministic and auditable. It may still merge two truly separate openings with the same company/title/location or fail to merge listings whose titles differ materially; that trade-off is documented rather than hidden.

## Incrementality and idempotence

`vacancy_state/manifest.json` stores a SHA-256 for every source file. Unchanged files are not reparsed. New, modified or deleted files identify the affected vacancy IDs. Only those IDs are re-merged, re-chunked and reindexed; unchanged vacancies keep their existing index entries.

The manifest also stores `pipeline_version`. A change to normalization/chunk semantics increments this version and triggers one controlled rebuild, preventing unchanged raw JSON from retaining stale derived records after a code upgrade. Normal runs remain incremental.

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

- `vac-...::core`: role/company/location/seniority/application language/context
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
