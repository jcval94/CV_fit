# Professional evidence RAG

`rag/` transforms the canonical Markdown under `experience/` into deterministic, retrieval-safe professional evidence. It never mutates the source of truth.

## Pipeline

```text
experience/**/*.md
        ↓
schema-v3 validation
        ↓
rag.normalize
        ↓
hierarchical normalized records
        ↓
rag.evidence
        ↓
typed semantic evidence chunks
        ↓
relations + transparent lexical index
        ↓
versioned rag_state/
```

Dense embeddings/vector infrastructure are deliberately deferred. The current lexical layer is deterministic, cheap and auditable, and gives the ADK workflow stable evidence IDs before adding another retrieval dependency.

## Normalization layer

`rag.normalize` preserves:

- `record_id`, `record_type`, status and confidence
- `public_safe` and source provenance
- exact `ACH-*` references
- ownership and usage boundaries
- strict skill proficiency
- router/evidence/policy classification
- Markdown heading hierarchy
- source commit and content hash

Normalized sections remain structural units; they are not blindly treated as retrieval chunks.

## Semantic evidence chunking

`rag.evidence` has specialized rules instead of a fixed token splitter:

- **Metrics:** one atomic chunk per `ACH-*`; public/CV eligibility is evaluated from that metric entry, not from the file-level flag.
- **Skills:** one chunk per skill/language entry; exact `core | working | familiarity` or language proficiency is metadata.
- **Credentials:** one chunk per credential; inactive/expired entries are conservatively excluded from automatic reuse.
- **Projects/roles:** semantic heading chunks with parent ownership/usage boundaries attached as constraints.
- **Router records:** excluded from ordinary evidence retrieval.
- **Policy records:** may be represented for governance but never compete in normal evidence retrieval.

Every chunk has a stable ID, source path, source refs, constraints, metric refs, proficiency where applicable and a deterministic content hash.

## Incrementality

`rag_state/manifest.json` tracks a SHA-256 per professional source file. A normal run:

- skips unchanged files completely;
- reparses/rechunks/reindexes only new or modified records;
- removes deleted records and their postings;
- retains stable chunks/index entries for unaffected records.

A semantic pipeline-version change forces one controlled rebuild, then normal incremental behavior resumes.

## State

```text
rag_state/
├── manifest.json
├── lexical_index.json
├── relations.json
├── records/
├── chunks/
├── runs/
└── latest_run.json
```

This state is derived and versioned for auditability. `experience/` remains authoritative.

## Retrieval safety

Only chunks that are both ordinary `evidence` and `cv_eligible` enter the professional lexical index. This prevents router/policy documents, blocked metrics and non-reusable records from being retrieved as candidate claims.

The downstream matcher treats retrieval as evidence discovery, not permission to strengthen a claim. In particular, a `familiarity` skill remains `familiarity` regardless of vacancy wording.

## Commands

Validate Phase 1 normalization:

```bash
python -m rag.normalize --repo . --check
```

Build/update versioned evidence state:

```bash
python -m rag.evidence --repo . --state-dir rag_state --run-id local
```

Recovery/full validation only:

```bash
python -m rag.evidence --repo . --state-dir /tmp/rag_state --run-id rebuild --full-rebuild
```

Retrieve:

```bash
python -m rag.retrieve "fraud anomaly detection Python" --state-dir rag_state --top-k 8
```

`.github/workflows/evidence-rag.yml` validates full state on PRs and updates `rag_state/` incrementally on `main`.
