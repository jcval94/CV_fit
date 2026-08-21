---
schema_version: 1
last_updated: 2026-08-20
status: validated_public
public_safe: true
project_type: generative_ai_system
source_repo: https://github.com/jcval94/ADNarrativa
primary_language: Python
---

# narrative_dna / ADNarrativa

## Summary

`narrative_dna` is a JSON-first system for converting speech transcripts into a stable, interpretable and auditable representation of narrative structure.

It is one of the strongest public repositories for demonstrating José Carlos's **production-minded Generative AI engineering** because it combines strict data contracts, deterministic validators, LLM classification, adjudication, semantic auditing, synthetic review, evaluation and an end-to-end CLI pipeline.

## Architectural principles

- JSON is the source of truth.
- Derived compact notation is compiled from validated JSON rather than edited manually.
- precision is preferred over false coverage
- high-temperature synthetic reviewers provide diversity, not final authority
- aggregation/adjudication remains conservative
- only high-confidence synthetic gold is eligible for regression testing
- CSV outputs are derived artifacts, not the canonical record

## Structured output / contract layer

The project uses:

- Pydantic models
- JSON Schemas
- strict validation
- versioned taxonomies
- versioned prompts
- deterministic validators
- explicit rejected labels / review flags

## OpenAI implementation evidence

The documented LLM client:

- uses the OpenAI Responses API
- uses strict Structured Outputs with JSON Schema
- validates every response with Pydantic
- reads credentials from environment variables
- uses configurable LLM parameters
- caches responses by versioned hash
- supports retries
- supports `dry_run`
- returns controlled failures so deterministic heuristics can act as fallback

## Evaluation / adjudication architecture

The system includes:

### Unit classifier
Combines contextual LLM classification with heuristic locks and deterministic revalidation.

### Conservative adjudicator
Escalates low-confidence or conflicting cases and can remove weak labels rather than maximizing label coverage.

### Similarity auditor
- configurable local/OpenAI embeddings
- cosine similarity
- nearest-neighbor comparison
- notation-distance analysis
- conflict outputs for review

### Synthetic review workflow

- prioritized review sets
- multiple configured synthetic reviewers
- conservative aggregation
- final adjudication
- reliability measurement
- high/medium/rejected confidence buckets
- controlled promotion to synthetic gold

### Relationship / chain detection

Deterministic relationship logic builds auditable narrative relations and multi-unit narrative chains while retaining evidence spans and version information.

## Evaluation outputs

The evaluator can produce:

- overall evaluation metrics
- label-level metrics
- confusion-group reports
- audit reports
- JSON and Markdown artifacts

The repository documents a maintained golden-regression fixture using only `synthetic_gold_high_confidence` with:

- `regression_pass_rate = 1.0`

This is a project regression quality gate, not an external production-accuracy benchmark.

## End-to-end engineering

The project includes:

- installable Python package structure
- CLI commands
- local no-LLM mode
- LLM-enabled mode
- manifests / run IDs
- JSONL outputs
- audit reports
- schema export
- inspection commands
- evaluation commands
- regression tests
- operating guide
- Colab quickstart

## Skills evidenced

- Generative AI application architecture
- OpenAI Responses API
- Structured Outputs
- JSON Schema
- Pydantic
- prompt/version management
- LLM evaluation / evals
- adjudication
- hallucination/error control
- embeddings / semantic similarity
- caching and retries
- deterministic fallbacks
- synthetic-data review workflows
- regression testing
- CLI / package engineering
- traceability / auditability

## Strong CV narratives

### Generative AI / AI Engineer

> Built a JSON-first LLM analysis pipeline using OpenAI Structured Outputs, Pydantic validation, deterministic fallbacks, semantic auditing, synthetic review/adjudication and regression evaluation.

### LLM Evaluation

> Designed a traceable LLM evaluation architecture with review-set prioritization, multi-reviewer synthetic evaluation, conservative adjudication and controlled promotion to high-confidence regression gold.

### AI Safety / Reliability

> Combined strict output schemas, deterministic validators, confidence escalation and fallback paths to keep an LLM classification pipeline auditable and bounded.

## Usage constraints

- The `1.0` regression pass rate applies only to the maintained high-confidence regression fixture.
- Do not call it an external benchmark, production accuracy or human-level performance.
- Do not claim fine-tuning or model training from this repository; the evidence is application architecture, evaluation and structured LLM orchestration.
