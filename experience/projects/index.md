---
schema_version: 1
last_updated: 2026-08-20
status: populated
purpose: project_retrieval_index
---

# Project Index

Canonical retrieval index for José Carlos Del Valle's professional and technical projects.

This file exists so downstream RAG / CV generation can select projects by **relevance, evidence strength, domain and disclosure policy** instead of retrieving every project equally.

## Retrieval priority

- **tier_1:** strongest evidence for senior Data Science / ML / GenAI applications
- **tier_2:** strong supporting evidence for specialized roles
- **tier_3:** historical / secondary evidence

---

# Professional projects — BBVA México

## Tier 1

### [Best Time to Call](bbva_btc.md)
- **Domains:** Predictive ML · Contactability · Ranking · Production Analytics
- **Best for:** Data Scientist · Applied Scientist · Decision Science
- **Evidence:** production-oriented professional project
- **Metrics:** private / controlled disclosure

### [Next Best Offer / CRMi](bbva_next_best_offer.md)
- **Domains:** Recommendation · Propensity · Ranking · Commercial Decisioning
- **Best for:** Senior Data Scientist · Recommender Systems · Decision Science
- **Evidence:** production-oriented multiproduct decision engine
- **Metrics:** private / controlled disclosure

### [Fraud and Inappropriate-Practice Detection](fraud_detection.md)
- **Domains:** Fraud · Anomaly Detection · Isolation Forest · Statistical Validation
- **Best for:** Fraud Data Science · Risk Analytics · Applied ML
- **Evidence:** hybrid rules + ML professional project
- **Metrics:** private / controlled disclosure

### [Internal LLM Tools / NorA](llm_internal_tools.md)
- **Domains:** GenAI · RAG · Grounding · Human-in-the-Loop
- **Best for:** GenAI · Applied AI · AI Product / Engineering
- **Evidence:** internal implementation + public-safe adoption metrics
- **Metrics:** selected public-safe metrics available

### [ATM Placement and Relocation Optimization](bbva_atm_optimization.md)
- **Domains:** Optimization · Geospatial Analytics · Decision Support
- **Best for:** Data Science · Optimization · Location Intelligence
- **Evidence:** professional optimization project
- **Metrics:** private / controlled disclosure

### [Customer Journey Reconstruction & Entity Matching](bbva_customer_journey_entity_matching.md)
- **Domains:** NLP · Entity Resolution · Investigation Analytics · Data Integration
- **Best for:** Applied ML · Fraud / Compliance Analytics · NLP
- **Evidence:** professional investigation analytics project
- **Metrics:** private / controlled disclosure

## Tier 2

### [Cash Demand Forecasting](bbva_cash_demand_forecasting.md)
- **Domains:** Forecasting · Time Series · Operations
- **Best for:** Forecasting · Supply / Operations Analytics · Data Science
- **Evidence:** professional forecasting project

### [AI-Enabled Model Lifecycle](bbva_ai_model_factory.md)
- **Domains:** GenAI · Agentic Workflows · Evaluation · ML Lifecycle
- **Best for:** GenAI · AI Engineering · MLOps / AI Enablement
- **Evidence:** governed internal workflow prototypes

### [Business Performance & Operating Model Analytics](bbva_business_performance_analytics.md)
- **Domains:** KPI Design · Business Analytics · Benchmarking · Executive Decision Support
- **Best for:** Lead Data Scientist · Decision Science · Analytics Leadership
- **Evidence:** recurring leadership-facing analytics
- **Metrics:** private / controlled disclosure

---

# Professional projects — Management Solutions

## Tier 1 / 2

### [Fraud / Risk Control Redesign](consulting_fraud_controls.md)
- **Domains:** Fraud · Risk · Operational Analytics · Consulting
- **Best for:** Fraud Data Science · Risk Analytics · Consulting-oriented roles
- **Evidence:** client-delivery professional project
- **Metrics:** private / controlled disclosure

### [Large-Scale Data Migration, Reconciliation & QA](consulting_data_migration.md)
- **Domains:** Data Quality · Migration · Reconciliation · Large-Scale Data
- **Best for:** Data Science with strong engineering / data-quality requirements
- **Evidence:** client-delivery professional project
- **Metrics:** exact scale private

---

# Public technical / open-source projects

## Tier 1

### [InsideForest](insideforest.md)
- **Domains:** Interpretable ML · Supervised Clustering · Python Package Engineering
- **Best for:** Senior Data Scientist · Applied Scientist · ML Engineer
- **Evidence:** public code, tests, documentation, package API and adoption

### [SheShe / DelDel](sheshe_deldel.md)
- **Domains:** Decision Surfaces · Rule Discovery · Optimization · XAI
- **Best for:** Applied Scientist · Research-oriented Data Science · XAI
- **Evidence:** public algorithms, reproducible benchmarks and package design

### [Narrative DNA](narrative_dna.md)
- **Domains:** GenAI · Structured Outputs · Pydantic · Evals · Adjudication
- **Best for:** GenAI Engineer · Applied AI · AI Reliability
- **Evidence:** public end-to-end architecture, tests and evaluation pipeline

### [MetaCraft](metacraft.md)
- **Domains:** Data Quality · Schema Drift · Metadata · OpenAI Integration
- **Best for:** Data / ML Platform · Data Quality · Senior Data Science
- **Evidence:** public Python package and documented capabilities

## Tier 2

### [MVP Agent Factory](mvp_agent_factory.md)
- **Domains:** Agentic Workflows · Skill Contracts · Evals · AI-Assisted SDLC
- **Best for:** Agentic AI · AI Product / Engineering

### [Cloud ML Recommender](cloud_ml_recommender.md)
- **Domains:** GCP · Cloud Functions · Keras · Transformers · Model Serving
- **Best for:** ML Engineering · Cloud ML · Applied ML

### [R / Statistical Tooling](r_statistical_tooling.md)
- **Domains:** R · Statistical Modeling · Package Development · Forecasting
- **Best for:** Quantitative / Statistical roles · historical depth

### [GitHub Portfolio Evidence Map](github_portfolio.md)
- **Purpose:** repository-level evidence inventory and relevance ranking

---

# Selection rules for CV generation

1. Retrieve at most **2–4 projects** for a standard one-page CV unless the target format explicitly allows more.
2. Prefer projects that jointly cover the vacancy's **problem domain + technical stack + seniority signal**.
3. Prefer **professional production projects** when the vacancy emphasizes business impact.
4. Prefer **public technical projects** when the vacancy requires concrete software / GenAI / package-engineering evidence.
5. Do not use two projects that communicate nearly the same capability unless both are central to the role.
6. Internal metrics must follow each project's disclosure policy.
7. Never synthesize a metric from one project into another.
8. A GitHub repository proves observable technical implementation; it does not automatically prove enterprise production usage.

# Suggested retrieval bundles

## Senior Data Scientist
- Next Best Offer
- Fraud Detection or BTC
- InsideForest
- one domain-relevant supporting project

## GenAI / AI Engineer
- NorA / Internal LLM Tools
- Narrative DNA
- AI-Enabled Model Lifecycle
- MVP Agent Factory or MetaCraft

## ML Engineer
- InsideForest
- Cloud ML Recommender
- Next Best Offer or BTC
- MetaCraft

## Fraud / Risk Data Science
- Fraud Detection
- Consulting Fraud Controls
- Customer Journey / Entity Matching
- InsideForest

## Decision Science / Optimization
- ATM Optimization
- Next Best Offer
- BTC
- Business Performance Analytics

## Forecasting / Operations
- Cash Demand Forecasting
- ATM Optimization
- Business Performance Analytics
- R / Statistical Tooling
