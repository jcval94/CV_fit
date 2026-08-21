---
schema_version: 3
record_id: role-bbva
record_type: role
status: canonical
last_updated: 2026-08-20
confidence: high
visibility: public
public_safe: true
organization: BBVA México
period: 2021-present
source_refs:
  - SRC-USER-CONFIRMED-2026-08-20
  - SRC-LINKEDIN-PUBLIC
  - SRC-PORTFOLIO-PUBLIC-2026-08
  - SRC-TRAJECTORY-2021-2023-CURATED
  - SRC-TRAJECTORY-2024-2026-CURATED
---

# BBVA México

## Canonical employment record

- **Employment period:** May 2021 – present
- **Functional track:** Data Science / Advanced Analytics
- **Current corporate level:** Expert
- **Current market-facing title:** Senior Data Scientist
- **Primary domains:** banking operations, remote banking, commercial analytics, fraud, compliance, risk, data engineering and Generative AI

The corporate level **Expert** is retained for internal chronology. External career materials should normally use a market-readable title such as **Senior Data Scientist** or the user-approved general positioning **Líder de Data Science, Modelado e Inteligencia Artificial**.

## Role chronology

### Data Scientist — Analyst

- **Period:** May 2021 – April 2022
- **Primary scope:** analytical infrastructure, forecasting, ATM/branch strategy and operational automation
- **Observable contributions:**
  - evaluated and adapted ML models and ETL processes for forecasting cash demand
  - supported ATM/branch deployment and decommissioning decisions with clustering, market-potential analysis and visualization
  - contributed to predictive-maintenance, footprint and operational-dashboard work
  - built Python-based forecasting and recurring-data automation for infrastructure use cases
- **Canonical projects:** [ATM and physical-network analytics](../projects/bbva_atm_analytics.md)

### Data Scientist — Associate

- **Period:** May 2022 – March 2024
- **Primary scope:** remote banking, customer segmentation, contact optimization and recommendation strategy
- **Observable contributions:**
  - supported and refined geospatial/footprint analysis for remote ATMs
  - participated in contactability pilots and later operated recurring Best Time to Call releases
  - built population, segmentation and prioritization logic in SQL/PySpark for commercial workflows
  - contributed to CRMi/Next Best Offer releases and treatment/control evaluation
  - diagnosed sampling bias in an experimental control group and helped align commercial restrictions
  - developed prototypes that translated analytical recommendations into interactive business-facing experiences
- **Canonical projects:**
  - [Best Time to Call](../projects/bbva_btc.md)
  - [Next Best Offer / CRMi](../projects/bbva_next_best_offer.md)

### Data Scientist — Expert

- **Period:** April 2024 – present
- **Primary scope:** fraud and compliance analytics, production quality, data architecture and applied GenAI
- **Observable contributions:**
  - led and contributed to hybrid rule/ML systems for claim, malpractice and conduct-risk detection
  - translated investigation hypotheses into auditable analytical extractions and alert logic
  - calibrated alert thresholds and investigated false positives across transactional, HR and security data
  - worked on fuzzy identity matching, relational fraud analysis and external-data enrichment
  - reviewed production code and refactored distributed pipelines affected by deprecated inputs, temporal ambiguity or memory limits
  - helped productize data engines and design secure automation under corporate constraints
  - curated knowledge sources and measured operational impact for internal normative assistants
  - designed process/state/SLA architectures and GenAI-assisted workflows for regulatory operations
  - supported technical adoption of NotebookLM, Gemini, ChatGPT and Google Workspace automation
- **Canonical projects:**
  - [Fraud and inappropriate-practice detection](../projects/fraud_detection.md)
  - [Internal LLM tools](../projects/llm_internal_tools.md)
  - [Data quality, MLOps and analytical engines](../projects/bbva_data_quality_mlops.md)
  - [Supervisory Relations To-Be](../projects/bbva_supervisory_relations.md)

## End-to-end scope

Across the three levels, the role can defensibly include:

1. framing ambiguous business or control problems
2. extracting and validating data from multiple corporate sources
3. building analytical logic, statistical models or ML components
4. writing Python, PySpark and SQL
5. producing recurring pipelines, layouts, reports, dashboards or APIs
6. monitoring adoption, quality, drift and operational outcomes
7. coordinating with business, technology, compliance, legal/data and senior leadership
8. communicating trade-offs and impact to management

## Technologies with role evidence

- Python, PySpark, SQL and R
- Spark-based distributed processing
- Teradata and Oracle
- AWS analytical workloads
- Google Cloud and Google Workspace
- Apps Script, Google Sheets, Forms and Looker Studio
- Tableau and MicroStrategy/BI environments
- Git/Bitbucket/GitHub, code review and CI/CD practices
- OpenAI, Gemini and NotebookLM

Internal or deprecated platform names are not required in generated CVs.

## Stakeholders

Evidence supports work with:

- business and commercial teams
- risk, compliance and investigation teams
- technology and data teams
- legal/data/privacy stakeholders
- division, cell and senior-management leadership

Exact team sizes and reporting lines should not be inferred.

## Impact usage

Exact numerical claims must come from [the achievement registry](../achievements/metrics.md). Metrics from different projects, periods or alert populations must never be merged.

## Boundaries

- Do not present every initiative as individual ownership; the project files state whether the role was lead, contributor, operator or reviewer.
- Do not attribute the public fraud-detection improvement to the normative LLM assistant; these were separate workstreams.
- Do not claim platform engineering ownership for tools that were only used or reviewed.
- Preserve April 2024 as the current canonical Expert start date; the older public portfolio says March 2024 and is logged as a resolved discrepancy.
