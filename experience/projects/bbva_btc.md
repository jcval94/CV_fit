---
schema_version: 3
record_id: project-bbva-btc
record_type: project
status: canonical
last_updated: 2026-08-20
confidence: high
visibility: public
public_safe: true
organization: BBVA México
period: 2022-2024
source_refs:
  - SRC-USER-CONFIRMED-2026-08-20
  - SRC-PORTFOLIO-PUBLIC-2026-08
  - SRC-TRAJECTORY-2021-2023-CURATED
  - SRC-TRAJECTORY-2024-2026-CURATED
---

# BBVA — Best Time to Call (BTC)

## Summary

Best Time to Call is a remote-banking contact-prioritization workstream designed to identify useful days/time windows and order outbound activity using observed contact behavior rather than manual heuristics alone.

The evidence supports a progression from a 2022 contactability pilot to recurring operational releases and monitoring during 2023–2024.

## Business problem

Remote bankers faced low contactability, repeated unsuccessful calls and inefficient prioritization. The analytical need was to decide when to contact each customer, feed actionable outputs into the dialing workflow and measure whether users followed the recommendation.

## Contribution and ownership

### 2022 pilot

- participated in validation of a Bayesian/contactability pilot
- contributed to feature and population work
- supported demo and audit follow-up
- **Ownership boundary:** the final experimental result and sole authorship of the base model are not established

### 2023–2024 recurring operation

- operated recurring scoring/release workflows
- validated output quality and drift
- prepared operational layouts/bases for downstream contact systems
- monitored adherence, contactability and effectiveness
- analyzed first-call behavior, repeated-call penalties and cooling-time implications
- **Ownership boundary:** evidence is strongest for execution, monitoring, release and analytical improvement, not exclusive invention of the original algorithm

## Implementation evidence

- Python and PySpark
- Teradata and Oracle
- distributed analytical processing
- recurring CSV/layout releases
- quality-assurance notebooks
- Looker Studio / Google Sites reporting
- integration with commercial contact tooling

## Results

The project produced recurring operational recommendations and a measurable improvement in contact outcomes. Curated sources contain differing uplift values from different periods/definitions; exact internal values remain governed by `ACH-BBVA-BTC-PRIVATE` and are not published here.

## Approved public narratives

> Operated and monitored a recurring Best Time to Call pipeline for remote banking, validating outputs and releasing contact-prioritization recommendations into commercial workflows.

> Analyzed adherence, first-call success and repeated-call behavior to improve customer-contact prioritization.

## Boundaries

- Do not merge uplift values from different years.
- Do not state that the model was retrained weekly unless a primary artifact confirms it.
- Do not attribute full algorithm design or deployment ownership to one person.
- Do not expose customer or banker counts from restricted sources in public artifacts.
