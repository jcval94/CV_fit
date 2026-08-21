# RAG architecture decisions — phase 1

## ADR-001 — Normalize before chunking

**Decision:** canonical Markdown is parsed into structured normalized records before any retrieval chunking or embedding.

**Reason:** the source contains governance semantics — metric IDs, ownership boundaries, proficiency, status, confidence and provenance — that generic text splitting would otherwise weaken or lose.

## ADR-002 — Separate evidence, router and policy records

**Decision:** normalized records are classified as `evidence`, `router`, or `policy`.

**Reason:** routing indexes and governance documents intentionally repeat terminology. Allowing them to compete with primary evidence in the same future embedding corpus would create high-similarity but low-value retrieval results.

## ADR-003 — Preserve normalized sections without treating them as chunks

**Decision:** Markdown headings are converted into parent-aware structural sections, but no token limit, overlap or embedding behavior is applied in phase 1.

**Reason:** chunking requires separate decisions about parent-child retrieval, maximum size, boundary propagation and special handling of metrics/skills/certifications. Those decisions should be inspectable against lossless normalized input.

## ADR-004 — No provider/framework dependency yet

**Decision:** phase 1 uses Python standard library plus PyYAML only.

**Reason:** normalization is repository infrastructure, not retrieval-provider infrastructure. It should remain deterministic and portable if the later vector store, embedding model or orchestration framework changes.

## ADR-005 — Generated records are reproducible artifacts

**Decision:** `records.jsonl` and `manifest.json` are generated under `artifacts/rag/` and are gitignored.

**Reason:** `experience/` remains the source of truth. Derived RAG artifacts should be rebuilt from the source and tied to `source_commit` and `content_hash`, not edited manually.
