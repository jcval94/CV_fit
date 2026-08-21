# Phase 1 acceptance criteria

The normalization foundation is ready to merge when all of the following are true:

- every Markdown record under `experience/` parses successfully
- canonical `record_id` values remain unique after normalization
- policy/router/evidence classification is deterministic
- router and policy records are not ordinary embedding candidates
- non-reusable statuses are blocked from automatic reuse
- Markdown hierarchy is preserved as structural sections
- `ACH-*` references and relative Markdown links are captured without reinterpretation
- every normalized record has a deterministic content hash
- generated artifacts are tied to a source commit and remain outside the canonical source tree
- unit and repository-level integration tests pass in CI
- the existing `tools/validate_experience.py` validation still passes

Passing this phase does **not** imply that chunking, embeddings or retrieval are ready.
