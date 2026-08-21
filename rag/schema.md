# Normalized record schema v1

This file documents the stable output contract produced by `rag.normalize`.

## Record-level fields

| Field | Type | Meaning |
|---|---|---|
| `normalization_schema_version` | integer | Version of the normalized-output contract |
| `record_id` | string | Canonical ID inherited from `experience/` |
| `record_type` | string | Canonical source record type |
| `status` | string | Canonical record status |
| `confidence` | string | Record-level evidence confidence |
| `visibility` | string | Source visibility |
| `public_safe` | boolean | Whether the committed record is safe for public use |
| `retrieval_class` | enum | `evidence`, `router`, or `policy` |
| `automatic_reuse_eligible` | boolean | Whether downstream automation may reuse the record without resolving status first |
| `embedding_candidate` | boolean | Whether this record may later enter the ordinary evidence embedding corpus |
| `source_path` | string | Repository-relative canonical source path |
| `source_commit` | string/null | Git commit used to build the normalized output |
| `source_refs` | list[string] | Canonical provenance IDs |
| `metric_refs` | list[string] | `ACH-*` IDs referenced by source text |
| `linked_markdown_paths` | list[string] | Relative Markdown links visible in source text |
| `attributes` | object | Non-core frontmatter retained without reinterpretation |
| `sections` | list[object] | Structural Markdown sections |
| `content_hash` | string | SHA-256 of the complete canonical source file |

## Section fields

| Field | Type | Meaning |
|---|---|---|
| `section_id` | string | Deterministic structural ID derived from `record_id` and heading hierarchy |
| `level` | integer | Markdown heading level |
| `title` | string | Original heading title |
| `heading_path` | list[string] | Parent-aware heading hierarchy |
| `semantic_type` | string | Lightweight deterministic label such as `ownership`, `boundary`, `metric`, or `credential` |
| `start_line` | integer | Source line where the heading starts |
| `end_line` | integer | Last source line belonging to the section |
| `content` | string | Section body excluding the heading |

## Important boundary

A normalized section is **not yet a retrieval chunk**. Later chunking may merge small adjacent sections, split oversized sections, attach parent context, and copy record-level constraints. The normalization layer must remain loss-minimizing and should not make retrieval-specific compression decisions.
