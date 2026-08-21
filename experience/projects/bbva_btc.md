---
schema_version: 2
last_updated: 2026-08-20
status: populated
project_id: BBVA-BTC
organization: BBVA México
project_type: predictive_decisioning
public_safe: true
metric_policy: "Exact employer-internal uplift remains governed by achievements/metrics.md."
---

# BBVA — Best Time to Call (BTC)

## Executive summary

Predictive prioritization solution designed to improve the probability of successfully contacting customers by identifying more favorable contact windows from historical and behavioral signals.

## Business problem

Outbound commercial and service interactions lose efficiency when customers are contacted at low-probability moments. The project aimed to replace broad or static contact schedules with customer-level analytical prioritization.

## Objective

Estimate and operationalize the most promising contact timing for each customer so commercial teams could allocate outreach more effectively.

## José Carlos's ownership

- translated the contact-efficiency problem into a modeling and prioritization problem
- participated in data definition and feature engineering on large-scale banking information
- developed / validated predictive logic for customer contactability
- defined operational prioritization rules around model outputs
- supported production integration and business interpretation
- monitored effectiveness and model behavior after deployment
- communicated assumptions, limitations and results to business stakeholders

## Data / signal families

Project documentation supports the use of customer-level behavioral and historical interaction signals. Do not invent exact feature names unless recovered from a private implementation source.

Potential signal categories reflected in the analytical framing include:

- historical contact outcomes
- temporal patterns
- customer behavior
- operational availability / contact windows

## Methodological framing

- supervised predictive modeling / propensity-style estimation
- customer-level ranking / prioritization
- validation against operational baselines
- business-rule integration around model scores

## Production / operationalization

The value of BTC was not limited to offline model accuracy. The project required translating predictions into operational contact priorities usable by business teams.

This supports evidence of:

- model-to-decision translation
- production-oriented Data Science
- business-rule integration
- post-release monitoring

## Technologies

- Python
- PySpark / Spark
- SQL
- large-scale feature engineering
- model validation and monitoring

## Impact

A measurable improvement in contact effectiveness was achieved after implementation.

- **Exact metric:** governed by `../achievements/metrics.md` entry `ACH-BBVA-BTC-PRIVATE`
- **Public repository policy:** do not expose the exact internal uplift from this project file

## Skills evidenced

- predictive modeling
- propensity / contactability modeling
- ranking and prioritization
- feature engineering
- Spark / PySpark
- SQL
- productionization
- model monitoring
- stakeholder communication

## Approved CV wording

### Public-safe
> Developed and operationalized a Best Time to Call model that used customer behavioral and historical signals to improve outbound contact prioritization.

### Private-metric variant
Only hydrate the quantified uplift from a private source or explicit disclosure approval.

## Interview narrative

1. **Problem:** contact teams were not always reaching customers at high-probability moments.
2. **Approach:** estimate customer-level contactability by time window using historical/behavioral signals.
3. **Operational challenge:** predictions had to become usable prioritization rules, not just scores.
4. **Validation:** compare effectiveness against the existing approach and monitor post-release performance.
5. **Outcome:** improved contact effectiveness and created a reusable analytical component for broader decisioning.

## Related records

- [BBVA role](../roles/bbva.md)
- [Next Best Offer](bbva_next_best_offer.md)
- [Validated metrics](../achievements/metrics.md)
