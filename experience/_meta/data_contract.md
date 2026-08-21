---
schema_version: 3
record_id: governance-data-contract
record_type: governance
status: canonical
last_updated: 2026-08-20
confidence: high
visibility: public
public_safe: true
source_refs: []
---

# Experience Data Contract

This repository is a canonical evidence base for career artifacts. It stores broad, traceable facts; generated CVs and applications select only the approved subset relevant to a target role.

## Required frontmatter

Every Markdown file under `experience/` must declare:

```yaml
schema_version: 3
record_id: unique-kebab-case-id
record_type: profile | education | certifications | skills | role | project | achievement_registry | governance | conflict_log
status: draft | needs_reconciliation | canonical | validated_public | validated_public_supporting | deprecated
last_updated: YYYY-MM-DD
confidence: high | medium | low
visibility: public
public_safe: true
source_refs:
  - SRC-REGISTERED-ID
```

This repository is public. Canonical records committed here must use `visibility: public` and `public_safe: true`. Internal or restricted evidence may be named in the source registry, but its raw content and sensitive values must not be committed.

## Source priority

When two sources disagree, use this order:

1. current user confirmation
2. primary artifact or official credential
3. observable public repository or code
4. current public professional profile
5. curated derivative document
6. inference

Recency breaks ties only between sources with comparable authority. Never average conflicting metrics.

## Confidence

- `high`: direct primary evidence or multiple consistent sources
- `medium`: coherent and interview-defensible, but incomplete or derivative
- `low`: recovery lead only; not eligible for automatic CV use

Confidence measures evidence strength, not project importance.

## Ownership vocabulary

Use the strongest term supported by evidence:

- `owned` / `designed` / `built`: individual implementation and decisions are evidenced
- `led`: accountable direction and delivery are evidenced
- `co-developed` / `collaborated`: shared design or implementation
- `contributed`: a bounded personal contribution is observable
- `operated` / `maintained`: recurring execution, monitoring or release
- `reviewed`: code or quality-gate responsibility
- `exposure`: topic is visible but no substantive action is evidenced; do not turn it into a CV bullet

## Canonical routing

- `profile.md`: stable identity and positioning
- `roles/`: chronology, scope and progression by employer or teaching engagement
- `projects/`: problem, personal contribution, implementation, result and usage boundaries
- `achievements/metrics.md`: the only canonical home for exact numerical claims
- `skills.md`: proficiency backed by roles, projects or public code
- `education.md` and `certifications.md`: exact academic or credential records
- `_meta/sources.yaml`: source provenance and permitted use
- `_meta/conflicts.md`: open and resolved contradictions

Project files reference metric IDs instead of copying values. A repeated value must preserve the same metric ID, qualifier, unit and comparison.

## Metric semantics

Every metric must identify, when known:

- baseline and comparator
- period and population
- absolute value, relative percent or percentage points
- achieved result, target, projection or technical benchmark
- attribution boundary
- public-safety and CV-use status
- approved wording and forbidden rewrites

Targets are never reported as achieved results. Synthetic benchmarks are never reported as business outcomes.

## Privacy and confidentiality

- Do not commit raw employer documents, emails, screenshots, credentials or datasets.
- Do not expose account identifiers, credential IDs containing contact data, internal paths or PII.
- A source marked internal/restricted may support public wording only when that wording is independently public or explicitly approved.
- Redacted values must never be restored from memory by an automated process.
- Use market-readable titles externally while preserving internal levels as metadata.

## Ingestion workflow

1. Register the source in `_meta/sources.yaml`.
2. Extract atomic claims and label period, confidence, visibility and ownership.
3. Search for an existing canonical home before creating a file.
4. Reconcile conflicts or add them to `_meta/conflicts.md`.
5. Update the relevant role/project/metric/skill record.
6. Run `python tools/validate_experience.py`.
7. Review the diff for overclaiming and privacy before publishing.

## Output policy

Generated public CVs may use only public-safe records and metrics whose CV usage is approved or whose conditional requirement has been satisfied. Preserve qualifiers such as `up to`, `approximately`, `pilot`, `projected` and `synthetic benchmark`.
