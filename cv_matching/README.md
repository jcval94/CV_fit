# Vacancy ↔ professional evidence matching

`cv_matching/` bridges the two derived corpora without merging their semantics:

- vacancy facts come from `vacancy_state/`;
- professional claims come from eligible chunks in `rag_state/`.

The matcher extracts structured requirements/capabilities from the canonical vacancy and retrieves supporting professional evidence for each item.

Coverage is intentionally conservative:

- `strong`: demonstrated proficiency/corroboration is sufficient for direct positioning;
- `partial`: relevant evidence exists but full requirement coverage is not proven;
- `weak`: limited/supporting evidence only;
- `unsupported`: no eligible evidence supports the requirement.

`unsupported` must remain visible to downstream agents. It is never permission to invent a candidate claim.

The output includes evidence chunk IDs, record IDs and source paths, so later strategy/CV decisions can be traced back to the original professional records.

Run for one canonical vacancy:

```bash
python -m cv_matching.match vac-... \
  --vacancy-state vacancy_state \
  --evidence-state rag_state
```
