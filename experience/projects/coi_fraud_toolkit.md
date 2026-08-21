---
schema_version: 3
record_id: project-coi-fraud-toolkit
record_type: project
status: validated_public
last_updated: 2026-08-20
confidence: high
visibility: public
public_safe: true
project_type: fraud_compliance_toolkit
source_repo: https://github.com/jcval94/coi
primary_language: Python
source_refs:
  - SRC-GITHUB-JCVAL94-PUBLIC
  - SRC-GITHUB-PROFESSIONAL-CURATED-2026-04-19
---

# COI / Fraud Analysis Toolkit

## Summary

A public Python toolkit for analyzing transaction histories, detecting suspicious patterns and producing interpretable reports for conflict-of-interest and fraud review.

The project is strong public evidence that José Carlos can translate sensitive fraud/compliance questions into reusable analytical software without relying on confidential employer code.

## Observable capabilities

- CSV/DataFrame input and reusable package installation
- person-, pair- and transaction-level summaries
- monthly and multi-window analysis
- suspicious text/concept matching in transaction descriptions
- imbalance, repeated-reference, centralizer and quid-pro-quo style patterns
- guided Q&A tables with plain-language interpretability fields
- Seaborn/Matplotlib visualizations
- export of case-specific outputs to CSV
- reproducible Google Colab workflow
- synthetic data generation for demonstrations

## Technologies

- Python
- Pandas and NumPy
- scikit-learn and SciPy where optional analytical components are used
- Seaborn and Matplotlib
- package installation / editable development
- Google Colab
- NLP-style text categorization and interpretable rules

## Engineering evidence

The README documents local and Colab installation, package imports, a callable pipeline, automated/manual paths, explicit input columns, interpretation guidance, output conventions and safe synthetic data.

## Approved public narrative

> Built a reusable Python toolkit for conflict-of-interest and fraud analysis, combining transaction-pattern detection, text signals, guided Q&A, visual reporting and interpretable case exports.

## Boundaries

- Do not claim production use or employer adoption from the public repository alone.
- Do not publish real sensitive transaction data.
- Do not infer model precision or business impact without an evaluated dataset.
- Describe optional embeddings/NLP components only to the level implemented in the repository.
