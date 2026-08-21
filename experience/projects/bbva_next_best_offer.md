---
schema_version: 3
record_id: project-bbva-next-best-offer
record_type: project
status: canonical
last_updated: 2026-08-20
confidence: high
visibility: public
public_safe: true
organization: BBVA México
period: 2023-2024
source_refs:
  - SRC-USER-CONFIRMED-2026-08-20
  - SRC-PORTFOLIO-PUBLIC-2026-08
  - SRC-TRAJECTORY-2021-2023-CURATED
  - SRC-TRAJECTORY-2024-2026-CURATED
---

# BBVA — Next Best Offer / CRMi

## Summary

CRMi/Next Best Offer is a multiproduct recommendation and population-prioritization workstream for remote banking. It combined customer segmentation, recurring recommendation labels, commercial restrictions and experimental measurement to make outreach more relevant and auditable.

## Business problem

The channel needed to prioritize customer/product combinations without relying exclusively on banker intuition or increasing customer fatigue. A second problem was methodological: the team needed to determine whether recommendation-aligned sales were incremental rather than natural customer demand.

## Contribution and ownership

Evidence supports:

- construction of SQL/PySpark population and segmentation logic
- preparation and recurring release of analytical labels/layouts
- integration of propensities and commercial eligibility rules
- support for campaigns and prioritization across several financial product families
- design/implementation of treatment-control evaluation for a weekly optimized label
- diagnosis of sampling bias caused by non-homogeneous commercial restrictions
- alignment of treatment/placebo filters before interpreting uplift
- contribution to recarterization logic that removed ineligible customers and prioritized stronger prospects

The evidence does not support exclusive ownership of every underlying propensity model or the complete recommendation engine.

## Implementation evidence

- SQL and PySpark
- Teradata
- distributed analytical workflows
- treatment/control and placebo logic
- customer segmentation and eligibility rules
- recurring operational layouts
- business dashboards and campaign monitoring
- interactive Streamlit/LLM prototype for explaining recommendations

## Results

- measurable commercial improvement is recorded in the private metric registry under `ACH-BBVA-NBO-PRIVATE`
- the current public portfolio separately documents a high-value versus low-value customer-segment comparison; its exact interpretation belongs in the achievement registry
- the experimental work produced a more reliable evaluation design by identifying and correcting control-group bias

## Approved public narratives

> Built segmentation and eligibility logic for recurring Next Best Offer recommendations in remote banking, integrating model outputs with commercial restrictions and operational delivery.

> Designed treatment/control evaluation for a recommendation workflow and diagnosed sampling bias caused by inconsistent eligibility filters.

## Boundaries

- Keep overall CRMi strategy and the specific causal experiment related but distinct.
- Do not convert effectiveness levels into uplift or percentage points without denominator evidence.
- Do not claim the recommendation engine alone caused all downstream sales.
- Do not list specific internal tables, paths or campaign identifiers in public artifacts.
