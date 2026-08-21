---
schema_version: 3
record_id: project-bbva-fraud-detection
record_type: project
status: canonical
last_updated: 2026-08-20
confidence: high
visibility: public
public_safe: true
organization: BBVA México
period: 2024-present
source_refs:
  - SRC-USER-CONFIRMED-2026-08-20
  - SRC-PORTFOLIO-PUBLIC-2026-08
  - SRC-TRAJECTORY-2024-2026-CURATED
---

# Fraud, Malpractice and Conduct-Risk Detection

## Summary

This record consolidates a family of related but non-identical fraud/compliance workstreams. The common pattern is translating ambiguous investigation or policy concerns into auditable data logic, prioritization models, calibrated alerts and operational review workflows.

## 1. Hybrid claim and malpractice prioritization

### Problem

Manual review pools were too broad and business rules alone generated avoidable false positives.

### Contribution

- led/co-developed a hybrid approach combining expert rules, supervised/unsupervised modeling, anomaly detection and statistical validation
- used techniques including Isolation Forest, distribution/goodness-of-fit reasoning and Benford-oriented checks where appropriate
- created claim-probability/prioritization logic and identified factors associated with higher risk
- translated model outputs into an investigation workflow rather than treating scoring as the final deliverable

### Public results

- `ACH-BBVA-FRAUD-REVIEW-001`: review-pool reduction
- `ACH-BBVA-FRAUD-DETECTION-001`: detection-rate improvement

The detection-rate improvement is attributed to the hybrid detection workstream, not to the separate normative LLM assistant.

## 2. Conduct and operational-risk alert calibration

Evidence supports:

- recurring monitoring of alert effectiveness
- root-cause analysis of false positives
- threshold and rule calibration
- contextual joins across transactional, HR and security data
- stronger evidence packages for investigators

Internal alert-effectiveness figures from different populations are not published or merged with the hybrid model metrics.

## 3. Insurance-sales malpractice / PyMAN

The multi-year workstream includes:

- analytical reconciliation across policy, subscription, incentive and transactional sources
- logic for tied sales, early cancellation and other irregular commercial patterns
- recurring reports and forensic KPIs
- evidence packages for control and disciplinary follow-up

The analytical role does not imply ownership of final HR or disciplinary decisions.

## 4. Identity, network and fuzzy-matching analysis

Supporting initiatives include:

- fuzzy name matching against regulatory/watch lists using distributed processing and Levenshtein-style similarity
- extraction of entities and relationships from claim narratives and operational metadata
- cross-checking phone numbers, identities and representatives to identify possible collusion
- transformation of investigation hypotheses into targeted relational/transactional queries

Specific graph libraries, matching thresholds and production precision must not be inferred.

## 5. Credential misuse and channel-security redesign

Evidence supports:

- invalidating a noisy multi-login heuristic through exploratory analysis
- designing more contextual signals using role, time, location and HR status
- exploring impossible-travel and credential-lending patterns
- producing parameters/manuals for operational analysts

The final production effectiveness of this workstream is not yet a public approved metric.

## Technologies and methods

- Python, PySpark and SQL
- distributed ETL and large-scale joins
- Isolation Forest and supervised/unsupervised models
- anomaly and outlier detection
- descriptive statistics and goodness-of-fit reasoning
- fuzzy matching / identity resolution
- relational analysis and text-derived signals
- dashboards, recurring reports and investigation support
- code review and reproducible pipeline practices

## Approved public narratives

> Led hybrid fraud/compliance analytics combining expert rules, anomaly detection and statistical validation, materially narrowing the review pool and improving detection.

> Translated sensitive investigation hypotheses into auditable analytical extractions, calibrated alerts and prioritized review workflows.

## Boundaries

- Do not combine metrics across alert populations, periods or workstreams.
- Do not claim final disciplinary decisions as the analytical team's result.
- Do not present inferred NLP/graph libraries as confirmed implementation facts.
- Do not attribute the detection-rate improvement to LLM deployment.
