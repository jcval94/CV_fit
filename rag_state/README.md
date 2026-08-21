# Versioned professional evidence retrieval state

This directory is derived from the canonical Markdown under `experience/`.

It is deliberately separate from `vacancy_state/`:

- `experience/` is the canonical professional source of truth.
- `rag_state/` contains normalized records, semantic evidence chunks, relations, and a transparent lexical retrieval index.
- `vacancy_state/` contains normalized vacancies and vacancy chunks.

The normal execution path is incremental. Source-file SHA-256 values in `manifest.json` determine which professional records are reparsed and reindexed. A pipeline-version change forces a controlled rebuild because derived semantics may have changed.

Generated state is auditable and versioned in Git at this stage; no external vector database is required yet.
