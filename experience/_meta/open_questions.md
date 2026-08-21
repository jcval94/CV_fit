---
schema_version: 3
record_id: governance-open-questions
record_type: governance
status: canonical
last_updated: 2026-08-20
confidence: high
visibility: public
public_safe: true
source_refs:
  - SRC-USER-CONFIRMED-2026-08-20
  - SRC-PORTFOLIO-PUBLIC-2026-08
  - SRC-TRAJECTORY-2021-2023-CURATED
  - SRC-TRAJECTORY-2024-2026-CURATED
  - SRC-GITHUB-PROFESSIONAL-CURATED-2026-04-19
---

# Open Evidence Questions

This backlog turns uncertainty into explicit collection work. An open item does not invalidate related records; it limits only the unsupported detail.

## Priority 1 — blocks strong CV claims

### Q-BBVA-BTC-METRIC-SEMANTICS

- **Need:** period, population, denominator and outcome definition for each BTC/contactability uplift value found in restricted sources.
- **Why:** derivative sources appear to describe different windows or success measures.
- **Best evidence:** approved dashboard definition, experiment readout or public artifact.
- **Close when:** each value has its own comparison, unit, period and attribution boundary, or is intentionally excluded.

### Q-BBVA-CRMI-METRIC-SEMANTICS

- **Need:** separate definitions for uplift, treatment/control level comparison and alignment measurement.
- **Why:** combining them would create a false continuous improvement series.
- **Best evidence:** experiment specification, measurement note or approved public statement.
- **Close when:** every value is mapped to a distinct metric record or intentionally excluded.

### Q-MS-MIGRATION-SCALE

- **Need:** confirm the public portfolio wording about migration scale and its unit.
- **Why:** the current phrasing is unusually large and is not safe to normalize by inference.
- **Best evidence:** project scope document or explicit user confirmation.
- **Close when:** exact wording is verified; until then, use only the approved qualitative description.

## Priority 2 — improves ownership and project depth

### Q-BBVA-PROJECT-OWNERSHIP

- **Need:** personal contribution and lifecycle stage for AIFE, selected internal GenAI/model-lifecycle prototypes, credential-misuse analytics and the internal InsideForest-related methodology.
- **Why:** the curated material mixes individual, team and reconstructed authorship.
- **Best evidence:** dated code, design document, review record or concise user confirmation per project.
- **Close when:** each project can use a supported ownership verb and delivery stage.

### Q-GENAI-PRODUCTION-BOUNDARIES

- **Need:** deployment state, active-user scope and measurable outcomes for internal assistants and agentic tools beyond the already public NorA adoption metrics.
- **Why:** prototypes, pilots and production services require different CV wording.
- **Best evidence:** release note, usage report, approved architecture artifact or public demonstration.
- **Close when:** each tool is labeled prototype, pilot, production or discontinued with a dated scope.

### Q-OPEN-SOURCE-ADOPTION

- **Need:** stronger external-usage or maintenance evidence for public projects that currently prove implementation but not broad adoption, especially COI and smaller R/RStudio utilities.
- **Why:** repository existence supports implementation, but not production adoption or active external use.
- **Best evidence:** package registry, releases, citations, dependent repositories or analytics.
- **Close when:** adoption claims are evidence-backed or intentionally omitted.

## Priority 3 — completeness

### Q-CREDENTIAL-METADATA

- **Need:** issuer, completion date, status and credential URL for the remaining pending **Applied Generative AI** and **Universidad Carlos III de Madrid Machine Learning** entries.
- **Why:** incomplete credentials are excluded from automatic CV generation.
- **Best evidence:** official badge, certificate or issuer verification page.
- **Close when:** every field is verified or the entry is deprecated.

### Q-ORIGINAL-ARTIFACTS

- **Need:** primary artifacts for high-value claims currently supported only by curated derivative documents.
- **Why:** primary evidence increases confidence and permits more precise attribution.
- **Best evidence:** public repository, redacted deliverable, official credential, approved performance record or dated publication.
- **Close when:** each high-value derivative claim has a primary reference or remains explicitly supporting-only.

## Resolved items removed from this backlog

- Professional-experience duration is now intentionally calibrated to **8+ years** based on formal chronology; university teaching/service and IMEF leadership remain supporting experience rather than employment tenure.
- The fraud review-efficiency ratio is normalized as **450 -> 34 cases reviewed per relevant finding** and is no longer an open wording question.

## Intake rule

New material should close or refine an existing question whenever possible. If it introduces a new claim, register the source first, record conflicts before selecting a value and route the result to the canonical file defined by the data contract.
