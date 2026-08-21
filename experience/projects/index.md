---
schema_version: 3
record_id: project-retrieval-index
record_type: governance
status: canonical
last_updated: 2026-08-20
confidence: high
visibility: public
public_safe: true
source_refs: []
---

# Project Retrieval Index

Routing layer for RAG and CV generation. This index does not create new evidence; it ranks canonical project records by relevance and evidence strength.

## Retrieval rules

1. Retrieve **2–4 projects** for a standard one-page CV unless the requested format allows more.
2. Prefer projects that jointly match the vacancy's **problem domain + technical stack + seniority signal**.
3. Prefer professional projects for business-impact claims and public projects for directly observable engineering evidence.
4. Project ownership comes from the project file, not from this index.
5. Exact metrics come only from `../achievements/metrics.md` by `ACH-*` ID.
6. Avoid selecting two projects that communicate essentially the same capability unless both are central to the target role.

---

# Professional projects — BBVA México

## Tier 1

### [Fraud, Malpractice and Conduct-Risk Detection](fraud_detection.md)
- **Signals:** fraud analytics · anomaly detection · Isolation Forest · statistical validation · fuzzy matching · investigation workflows
- **Best for:** Senior Data Scientist · Fraud/Risk DS · Applied ML · Compliance Analytics

### [Internal LLM and Normative Knowledge Tools](llm_internal_tools.md)
- **Signals:** GenAI · retrieval-grounded knowledge · prompt design · corpus curation · adoption/impact measurement
- **Best for:** GenAI · Applied AI · AI Product · regulated AI workflows

### [Best Time to Call](bbva_btc.md)
- **Signals:** contactability · predictive prioritization · recurring scoring/release · monitoring · operational analytics
- **Best for:** Senior Data Scientist · Decision Science · Customer Analytics

### [Next Best Offer / CRMi](bbva_next_best_offer.md)
- **Signals:** segmentation · recommendation · propensity · eligibility logic · treatment/control evaluation
- **Best for:** Senior Data Scientist · Recommender/Decision Science · Commercial Analytics

### [Data Quality, MLOps and Analytical Engines](bbva_data_quality_mlops.md)
- **Signals:** PySpark · production QA · code review · pipeline refactoring · AWS · data lineage · resilient automation
- **Best for:** ML Engineering · Production Data Science · Data Quality · MLOps-oriented roles

## Tier 2

### [ATM and Physical-Network Analytics](bbva_atm_analytics.md)
- **Signals:** forecasting · clustering · geospatial analytics · ETL · infrastructure decision support

### [Supervisory Relations To-Be Architecture](bbva_supervisory_relations.md)
- **Signals:** workflow architecture · state models · SLAs · RACI · Google Workspace · proposed Gemini assistance
- **Lifecycle boundary:** approved phased design; projected improvements are not production outcomes

---

# Professional projects — Management Solutions

## Tier 1 / 2

### [Clarification Prioritization](consulting_clarification_prioritization.md)
- **Signals:** PySpark · ML prioritization · operational capacity · MicroStrategy · domain-expert integration
- **Best for:** Data Science · Fraud/Risk Analytics · Operational Analytics

### [Insurance Fraud Monitoring](consulting_insurance_fraud_monitoring.md)
- **Signals:** PCA · outlier detection · unsupervised analytics · R · KPI/control design
- **Best for:** Fraud/Risk DS · Statistical Analytics · Consulting

### [Data Migration, Reconciliation & QA](consulting_data_migration.md)
- **Signals:** data migration · reconciliation · schema/layout design · QA · A/B testing · Salesforce context
- **Best for:** Data Quality · Analytics Engineering · Data/ML roles with migration ownership

---

# Public technical / open-source projects

## Tier 1

### [InsideForest](insideforest.md)
- **Signals:** interpretable ML · supervised clustering · Python package engineering · estimator APIs · tests · benchmarks · public adoption
- **Best for:** Senior Data Scientist · Applied Scientist · ML Engineer · XAI

### [narrative_dna / ADNarrativa](narrative_dna.md)
- **Signals:** OpenAI Responses API · Structured Outputs · Pydantic · evals · adjudication · semantic audit · regression testing
- **Best for:** GenAI Engineer · Applied AI · AI Reliability

### [MetaCraft](metacraft.md)
- **Signals:** data quality · metadata/schema engineering · drift · Great Expectations · OpenAI integration
- **Best for:** Data/ML Platform · Data Quality · Senior Data Science

### [SheShe / DelDel](sheshe_deldel.md)
- **Signals:** interpretable ML · rule discovery · numerical search · reproducible synthetic benchmarks
- **Best for:** Applied Scientist · Research-oriented DS · XAI

### [COI / Fraud Analysis Toolkit](coi_fraud_toolkit.md)
- **Signals:** public fraud/compliance tooling · transaction patterns · text signals · interpretable case exports
- **Best for:** Fraud Analytics · Compliance Analytics · analytical-tooling roles

## Tier 2

### [Cloud ML Recommender](cloud_ml_recommender.md)
- **Signals:** GCP Cloud Functions · Keras · Transformers · embeddings · HTTP model serving

### [MVP Agent Factory](mvp_agent_factory.md)
- **Signals:** agent architecture · skill contracts · eval rubrics · PRDs · AI-assisted SDLC

### [Financial ML Pipelines](financial_ml_pipelines.md)
- **Signals:** temporal validation · GitHub Actions · SQLite/JSON artifacts · static dashboards
- **Boundary:** educational/partially degraded; not validated trading production

### [R Statistical Tooling](r_statistical_tooling.md)
- **Signals:** CRAN · R packages · distribution fitting · forecasting · RStudio add-ins · reporting automation

### [Movilidad Social en México](movilidad_social_mx.md)
- **Signals:** Streamlit · analytical storytelling · probabilistic interpretation
- **Boundary:** fork/contribution scope must be preserved

### [GitHub Portfolio Evidence Map](github_portfolio.md)
- **Purpose:** repository-level evidence inventory and evidence-strength routing

---

# Suggested retrieval bundles

## Senior Data Scientist
- Fraud Detection or Next Best Offer
- Best Time to Call or Data Quality/MLOps
- InsideForest
- one domain-relevant supporting project

## GenAI / Applied AI
- Internal LLM Tools
- narrative_dna
- MVP Agent Factory or MetaCraft
- one professional production/analytics project

## ML Engineer / Production DS
- Data Quality/MLOps
- InsideForest
- Cloud ML Recommender
- BTC or NBO for enterprise operationalization evidence

## Fraud / Risk Data Science
- Fraud Detection
- Clarification Prioritization
- Insurance Fraud Monitoring
- COI or InsideForest

## Decision Science / Customer Analytics
- Next Best Offer
- Best Time to Call
- ATM Analytics
- InsideForest

## Data Quality / Analytics Engineering
- Data Quality/MLOps
- Management Solutions Data Migration
- MetaCraft
- one business-facing professional project
