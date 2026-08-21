# RAG foundation — Phase 1: normalization

This directory prepares the canonical `experience/` source of truth for future retrieval.

## Scope of this phase

Phase 1 performs only deterministic parsing and normalization:

```text
experience/*.md
      ↓
frontmatter + Markdown parser
      ↓
normalized records
      ↓
records.jsonl + manifest.json
```

It intentionally does **not** implement:

- retrieval chunks
- token splitting or overlap
- embeddings
- vector databases
- BM25 / lexical indexes
- reranking
- graph expansion
- context packing
- CV generation

Those stages should only be added after the normalized record representation is inspected and stable.

## Why normalization comes first

The repository already encodes governance rules that ordinary text splitters would lose:

- `record_id`, `record_type`, status and confidence
- `public_safe` and source provenance
- exact metric references through `ACH-*`
- ownership and usage boundaries
- strict skill proficiency
- router records versus primary evidence
- conflict/policy records that constrain downstream use

The normalizer preserves those semantics before any text is transformed for retrieval.

## Retrieval classes

Every normalized record receives one of three classes:

- `evidence`: primary candidate for later semantic/lexical retrieval
- `router`: retrieval-routing documents such as `projects/index.md` and `roles/index.md`; not embedding candidates
- `policy`: governance records under `experience/_meta/`; not embedding candidates

`projects/github_portfolio.md` is also treated as `router` because its purpose is evidence inventory/routing and it heavily overlaps the project records it references.

## Normalized record contract

Each JSONL record includes:

- `normalization_schema_version`
- canonical identity: `record_id`, `record_type`
- governance: `status`, `confidence`, `visibility`, `public_safe`
- retrieval controls: `retrieval_class`, `automatic_reuse_eligible`, `embedding_candidate`
- provenance: `source_path`, `source_commit`, `source_refs`
- relations visible in source text: `metric_refs`, `linked_markdown_paths`
- non-core frontmatter under `attributes`
- hierarchical Markdown `sections`
- deterministic `content_hash`

Sections are structural units only. They are **not retrieval chunks yet**.

## Build

Validate parsing without writing generated files:

```bash
python -m rag.normalize --repo . --check
```

Generate the normalized artifacts locally:

```bash
python -m rag.normalize --repo .
```

This writes:

```text
artifacts/rag/records.jsonl
artifacts/rag/manifest.json
```

Generated artifacts are intentionally gitignored. They are reproducible outputs, not canonical source data.

## Design invariants

1. `experience/` remains the canonical source; generated RAG artifacts never overwrite it.
2. Normalization is deterministic and provider-agnostic.
3. Router and policy records never become ordinary embedding candidates.
4. `needs_reconciliation`, `draft`, and `deprecated` records are not eligible for automatic reuse.
5. Exact metrics remain referenced by `ACH-*`; normalization does not copy or reinterpret numbers.
6. Markdown structure is preserved so later chunking can be semantic and parent-aware.
7. Source commit and content hashes support future incremental indexing.
