---
schema_version: 2
last_updated: 2026-08-20
status: populated
project_id: BBVA-NBO-CRMI
organization: BBVA México
project_type: recommendation_decisioning
public_safe: true
metric_policy: "Exact commercial uplift remains governed by achievements/metrics.md."
---

# BBVA — Next Best Offer (CRMi)

## Executive summary

Multiproduct recommendation / decisioning engine designed to prioritize the most relevant commercial offer for each customer across major banking and financial-product categories.

## Product scope

Known product families include:

- insurance
- investment funds / investments
- credit cards
- personal loans
- mortgages

## Business problem

Commercial teams needed a more systematic way to decide which product to prioritize for each customer rather than relying on broad campaigns or independent product scores.

## Objective

Combine customer signals and product-level propensity information into a unified recommendation layer that could rank alternatives and support commercial decisioning.

## José Carlos's ownership

- framed the multiproduct recommendation problem
- built and validated analytical logic on large-scale banking data
- performed feature engineering in Python / PySpark / SQL
- integrated product scores and business decision rules
- supported productionization and operational use
- defined evaluation / comparison logic
- monitored model performance and stability
- translated model results into business-facing recommendations

## Decisioning context

The broader decision framework distinguished among separate concepts that should not be conflated:

- **contactability:** whether / when the customer can effectively be reached
- **purchase propensity:** likelihood or commercial relevance of an offer
- **eligibility / approval constraints:** rules controlled by Risk or product policy

This separation is important. CRMi supported commercial prioritization and should not be represented as an autonomous credit-approval engine.

## Analytical approach

- multiproduct propensity / recommendation
- customer-level ranking
- feature engineering on large-scale banking data
- product comparison and prioritization
- integration of analytical scores with business rules
- benchmark-based evaluation

## Technologies

- Python
- PySpark / Apache Spark
- SQL
- large-scale feature engineering
- model monitoring / validation

## Impact

The productionized engine produced a measurable improvement in conversion versus the comparison benchmark.

- **Exact metric:** governed by `ACH-BBVA-NBO-PRIVATE` in `../achievements/metrics.md`
- **Public repository policy:** exact conversion / uplift values are not automatically disclosed here

## Skills evidenced

- recommender systems
- propensity modeling
- ranking / decision engines
- feature engineering
- PySpark / Spark
- SQL
- experimentation / benchmark comparison
- model monitoring
- business-rule integration
- commercial analytics

## Approved CV wording

### Public-safe
> Built and productionized a multiproduct Next Best Offer engine across cards, loans, mortgages, insurance and investments, combining large-scale feature engineering with customer-level recommendation and business decision rules.

### Private-metric variant
Quantified conversion performance may be hydrated only from an approved private metric source.

## Interview narrative

1. **Problem:** independent commercial signals did not provide one clear customer-level product priority.
2. **Approach:** create a multiproduct recommendation layer using customer and product signals.
3. **Architecture:** keep contactability, propensity and Risk-approved eligibility conceptually separate.
4. **Operationalization:** translate scores into prioritization logic usable by commercial channels.
5. **Evaluation:** compare conversion against an established benchmark and monitor stability.

## Related records

- [BBVA role](../roles/bbva.md)
- [Best Time to Call](bbva_btc.md)
- [Validated metrics](../achievements/metrics.md)
