---
schema_version: 3
record_id: governance-conflict-log
record_type: conflict_log
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
---

# Conflict and Reconciliation Log

This log prevents silent overwrites when sources disagree. Open conflicts block automatic use of the disputed detail, not use of the entire record.

## CONFLICT-BBVA-EXPERT-START

- **Subject:** start of BBVA Expert level
- **User-confirmed value:** April 2024
- **Public portfolio value:** March 2024
- **Status:** resolved_for_current_use
- **Decision:** use April 2024 in canonical role chronology because current user confirmation outranks the older public self-description; retain the portfolio discrepancy here.

## CONFLICT-BTC-UPLIFT

- **Subject:** contactability/effectiveness uplift
- **Source discrepancy:** two restricted derivative sources report different uplift values and use different outcome labels
- **Status:** open_semantics
- **Decision:** treat as measurements from different periods or definitions. Never combine them into one value. Public CV automation uses only the separately approved metric record.

## CONFLICT-CRMI-METRICS

- **Subject:** commercial recommendation impact
- **Source discrepancy:** restricted derivative sources contain an uplift claim, a later treatment/control level comparison and an alignment measure
- **Status:** open_semantics
- **Decision:** preserve as separate measurements. The first is an uplift claim; the second is a level comparison in a later window. Do not rewrite either as percentage points without denominator evidence.

## CONFLICT-FRAUD-LLM-ATTRIBUTION

- **Subject:** attribution of the public detection-rate improvement
- **Current user-confirmed account:** hybrid business rules, anomaly detection and statistical validation drove the detection improvement; LLM tooling was a separate normative-use case.
- **Public portfolio wording:** places the metric immediately after the LLM sentence and can be read as causal attribution to LLM deployment.
- **Status:** resolved_for_current_use
- **Decision:** use the user-confirmed hybrid-detection attribution and keep the LLM impact separate. Do not claim the LLM caused the detection-rate change.

## CONFLICT-FRAUD-METRIC-FAMILIES

- **Subject:** public hybrid-detection metrics versus additional restricted alert-effectiveness, irregularity and disciplinary-action measures
- **Status:** resolved_as_distinct
- **Decision:** these belong to different models, alert populations, periods and denominators. Never present them as one continuous improvement series.

## CONFLICT-AIFE-DATE

- **Subject:** AIFE/Open Market execution period
- **Source values:** July 2022 and an internal annotation suggesting 2024
- **Status:** open
- **Decision:** keep AIFE as supporting evidence with medium/low confidence and do not use an exact date in a generated CV until a primary artifact resolves it.

## CONFLICT-INSIDEFOREST-SCOPE

- **Subject:** relationship between the 2023 internal methodology and the public open-source library
- **Status:** resolved_as_related_not_identical
- **Decision:** describe them as a related methodological line. Do not claim that the public package was deployed internally or that every internal component exists in the public library without direct evidence.

## CONFLICT-DEVF-END-DATE

- **Subject:** end of DEV.F teaching engagement
- **User-confirmed value:** January 2023
- **Curated trajectory value:** through February 2023
- **Status:** resolved_for_current_use
- **Decision:** use January 2023; retain the one-month discrepancy as a source-quality note.

## CONFLICT-EXPERIENCE-DURATION

- **Subject:** `9+ years` versus enumerated chronology
- **User-confirmed value:** 9+ years of professional experience
- **Enumerated roles currently documented:** October 2017 onward, including a 2019 pause
- **Status:** open_supporting_history
- **Decision:** retain the user-confirmed `9+ years` positioning, but do not invent an additional employer or role to close the arithmetic gap. Recover earlier primary evidence if exact continuous tenure is required.

## CONFLICT-PLATFORM-NAMING

- **Subject:** legacy/internal platform names versus external CV terminology
- **Status:** resolved_output_policy
- **Decision:** preserve the evidenced capability while preferring market-readable technology such as AWS, PySpark, Teradata and Oracle. Do not reintroduce deprecated/internal platform names in generated CVs unless explicitly requested.
