# Automatic vacancy-specific CV generation

This layer turns the existing vacancy ingest + professional RAG + ADK CV workflow into an incremental queue. It does **not** apply to jobs or send CVs.

## Trigger semantics

On `main`, vacancy ingestion captures the first incremental run report before the existing no-op proof. `reindexed_vacancy_ids` are the new/semantically modified candidates for CV generation. Previously deferred candidates are also reconsidered.

## Gates

A paid generation is attempted only when:

1. the feature switch in `vacancy-ingest.yml` is enabled;
2. the canonical vacancy exists;
3. `jd_generation_eligible` passes the existing preflight and language is known;
4. the vacancy/generation fingerprint is not already terminal;
5. the per-run capacity limit has not been reached.

Automatic generation uses `hybrid-rerank` retrieval. Generated output is marked `ready_to_send: true` only when the complete Senior Headhunter + deterministic quality gate passes. `COMPLETED_BELOW_TARGET` is preserved as review-only.

## Idempotence

The fingerprint includes:

- canonical vacancy `content_hash`;
- professional retrieval-state fingerprint (`manifest`, lexical, dense and relation state);
- retrieval mode;
- automatic-generation pipeline version.

An unchanged terminal fingerprint is never regenerated automatically. A source/evidence change produces a new fingerprint.

## Cost and failure controls

- default maximum: 5 paid vacancy generations per ingest run;
- ADK estimated-cost guard: USD 2.00 per vacancy by default;
- excess candidates are persisted as `DEFERRED_CAP` and retried on the next run;
- same-fingerprint failures become `FAILED_REVIEW_REQUIRED` and do not enter a paid retry loop;
- sparse/ineligible JDs are persisted as `SKIPPED_NOT_ELIGIBLE` without a generation call.

Dense query embeddings and the lightweight retrieval reranker are not part of ADK generation telemetry, so the USD guard is intentionally described as the **ADK generation-call budget**, not a full OpenAI invoice cap.

## Public-repo boundary

`generation_state/manifest.json` contains only sanitized metadata. CV text and detailed per-run artifacts remain under gitignored `outputs/` and are uploaded by GitHub Actions as short-lived artifacts.
