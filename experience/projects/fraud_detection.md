---
schema_version: 2
last_updated: 2026-08-20
status: populated
project_id: BBVA-FRAUD-HYBRID
organization: BBVA México
project_type: fraud_anomaly_detection
public_safe: true
metric_policy: "Review-efficiency and detection-rate values remain private unless explicitly approved."
---

# Fraud and Inappropriate-Practice Detection

## Executive summary

Hybrid fraud / malpractice detection system combining deterministic business rules, Isolation Forest anomaly detection and statistical validation to improve investigation prioritization and reduce inefficient manual review.

## Business problem

Traditional monitoring generated large review volumes with limited prioritization. Analysts needed a way to surface cases with stronger evidence of anomalous or inappropriate behavior while preserving interpretability and operational control.

## Objective

Increase the concentration of relevant cases in the review queue and reduce the amount of manual effort required to find meaningful anomalies.

## José Carlos's ownership

- translated investigation patterns and business concerns into analytical detection logic
- designed hybrid rules + machine-learning workflows
- implemented anomaly detection using Isolation Forest
- evaluated candidate rules / signals using statistical tests and empirical distributions
- compared alternative thresholds and prioritization strategies
- helped redesign the review workflow around risk / anomaly signals
- communicated detection logic in interpretable terms for business and investigation stakeholders
- supported validation and operational monitoring

## Analytical approach

### Layer 1 — deterministic signals
Business rules captured known patterns, process violations or suspicious combinations that required explicit interpretability.

### Layer 2 — anomaly detection
Isolation Forest was used to identify unusual observations that might not be captured by deterministic rules alone.

### Layer 3 — statistical validation
Candidate signals and thresholds were tested against observed distributions / statistical behavior to reduce arbitrary rule selection.

### Layer 4 — prioritization
Rule and anomaly outputs were transformed into an investigation queue designed to increase analytical efficiency rather than simply maximize alert volume.

## Technical themes

- anomaly detection
- Isolation Forest
- rule-based detection
- statistical hypothesis / distribution analysis
- ranking and prioritization
- explainability
- operational fraud analytics
- human-in-the-loop investigation

## Technologies

- Python
- PySpark / Spark
- SQL
- scikit-learn style anomaly-detection workflows
- statistical analysis

## Impact

The project materially improved both review efficiency and relevant-case detection versus the prior process.

- **Review-efficiency metric:** `ACH-BBVA-FRAUD-PRIVATE`
- **Detection-rate metric:** `ACH-BBVA-FRAUD-PRIVATE`
- **Disclosure:** exact before/after values are intentionally redacted in this public repository

## Skills evidenced

- fraud analytics
- anomaly detection
- Isolation Forest
- hybrid rules + ML systems
- statistical validation
- model / rule explainability
- investigation prioritization
- production-oriented analytics
- cross-functional work with operational / control stakeholders

## Approved CV wording

### Public-safe
> Designed a hybrid fraud and inappropriate-practice detection framework combining business rules, Isolation Forest and statistical validation to improve investigation prioritization and reduce inefficient manual review.

### Private-metric variant
Use exact review-efficiency and detection-rate improvements only when sourced from an approved private metric registry.

## Interview narrative

1. **Problem:** analysts were reviewing too many low-signal cases.
2. **Constraint:** fraud controls needed interpretability; a black-box score alone was insufficient.
3. **Approach:** combine explainable rules with unsupervised anomaly detection.
4. **Validation:** test signal behavior statistically and compare alternative thresholds.
5. **Operationalization:** use outputs for prioritization, keeping investigators in the loop.
6. **Result:** higher review efficiency and stronger concentration of relevant cases.

## Related records

- [BBVA role](../roles/bbva.md)
- [Customer journey / entity matching](bbva_customer_journey_entity_matching.md)
- [Validated metrics](../achievements/metrics.md)
