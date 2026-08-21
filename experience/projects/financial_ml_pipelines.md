---
schema_version: 3
record_id: project-financial-ml-pipelines
record_type: project
status: validated_public_supporting
last_updated: 2026-08-20
confidence: high
visibility: public
public_safe: true
project_type: educational_financial_ml_pipelines
source_repos:
  - https://github.com/jcval94/floor
  - https://github.com/jcval94/yahoo
primary_language: Python
source_refs:
  - SRC-GITHUB-JCVAL94-PUBLIC
  - SRC-GITHUB-PROFESSIONAL-CURATED-2026-04-19
---

# Financial ML Pipelines — floor and yahoo

## Summary

Two public Python repositories demonstrate end-to-end thinking for financial data: ingestion, feature construction, model training, prediction, evaluation, portfolio/signaling logic, artifact persistence and static dashboard publication.

Their value is architectural and educational. They are not validated trading systems.

## yahoo

The repository documents a modular educational flow for selecting tickers, downloading market data, preprocessing, feature engineering, training, prediction, evaluation, portfolio optimization, configuration-driven execution, temporal validation and GitHub Pages publication.

## floor

The repository documents a more operations-oriented flow involving market-data ingestion, feature construction, champion/challenger artifacts, forecasts or signals, SQLite persistence, JSON/JSONL snapshots, GitHub Actions and static dashboard generation.

Its own documentation records incomplete or degraded components. That honesty is part of the evidence: the system must be described as implemented-and-audited, not as fully stable production infrastructure.

## Skills evidenced

- Python pipeline architecture
- time-series and market-data handling
- feature engineering and temporal validation
- training/evaluation separation
- artifact and snapshot contracts
- SQLite and JSON/JSONL
- GitHub Actions
- static dashboard delivery
- operational documentation and state transparency

## Approved public narrative

> Built and documented modular financial-ML pipelines from market-data ingestion through temporal validation, model artifacts and static dashboard publication using Python, GitHub Actions, SQLite and JSON contracts.

## Boundaries

- Do not claim real trading returns, production capital deployment or investment advice.
- Keep yahoo framed as educational.
- Preserve floor's documented partial/degraded state when discussing reliability.
- Dependency presence is not proof of deep expertise in every listed model family.
