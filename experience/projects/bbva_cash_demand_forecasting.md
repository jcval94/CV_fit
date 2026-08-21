---
schema_version: 2
last_updated: 2026-08-20
status: populated
project_id: BBVA-CASH-FORECAST
organization: BBVA México
project_type: time_series_forecasting
public_safe: true
---

# BBVA — Cash Demand Forecasting

## Executive summary

Time-series / forecasting initiative designed to estimate seasonal cash demand and support branch cash-transfer planning with forward-looking operational signals.

## Business problem

Cash logistics require balancing availability with transfer and holding costs. Decisions based only on recent observations can miss seasonality and recurring temporal patterns.

## Objective

Model expected cash demand using historical and temporal behavior so operational teams could plan future cash-transfer capacity more effectively.

## José Carlos's ownership

- framed the operational demand problem as a forecasting task
- prepared and validated historical time-series data
- identified seasonal / temporal patterns relevant to planning
- compared forecasting behavior against operational expectations
- translated forecasts into capacity-planning recommendations
- communicated limitations and uncertainty to stakeholders

## Methodological themes

- time-series analysis
- seasonality
- temporal feature engineering
- forecasting
- backtesting / historical validation
- operational capacity planning

## Usage constraint on methods

Do not automatically claim ARIMA, SARIMA, Prophet or another specific forecasting family unless the project implementation source explicitly confirms it. The canonical evidence supports **forecasting and statistical time-series modeling**, not every named algorithm.

## Technologies

- Python
- PySpark / Spark
- SQL
- statistical analysis
- time-series feature engineering

## Skills evidenced

- forecasting
- seasonality analysis
- operational analytics
- temporal validation
- translating predictions into planning decisions
- stakeholder communication

## Approved CV wording

> Modeled seasonal cash demand to support branch cash-transfer planning, translating historical and temporal patterns into forward-looking operational capacity decisions.

## Interview narrative

1. **Problem:** operational cash planning required a forward-looking demand estimate.
2. **Approach:** structure historical demand as a time-series problem and capture seasonal patterns.
3. **Validation:** compare expected versus observed behavior over time rather than rely on random train/test splits.
4. **Business use:** turn forecasts into planning signals for cash-transfer capacity.

## Related records

- [BBVA role](../roles/bbva.md)
- [Skills](../skills.md)
