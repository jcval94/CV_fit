---
schema_version: 3
record_id: skills
record_type: skills
last_updated: 2026-08-20
status: canonical
confidence: high
visibility: public
public_safe: true
usage_policy: "Generated CVs must prefer demonstrated skills over inferred keywords and must preserve the exact core/working/familiarity level recorded here. Public GitHub repositories may be used as direct technical evidence when the capability is observable in code, packaging, tests, documentation or reproducible benchmarks."
source_refs:
  - SRC-USER-CONFIRMED-2026-08-20
  - SRC-TRAJECTORY-2021-2023-CURATED
  - SRC-TRAJECTORY-2024-2026-CURATED
  - SRC-GITHUB-JCVAL94-PUBLIC
---

# Skills

Canonical inventory of technical, analytical, business and leadership skills for José Carlos Del Valle.

This file is designed for RAG and CV generation, not keyword stuffing. It uses a strict three-level proficiency model so downstream systems do not have to interpret ambiguous labels.

## Proficiency model

- **core:** repeated professional use and/or substantial independently owned implementation with strong interview-level defensibility
- **working:** meaningful hands-on implementation, but not necessarily the primary specialization
- **familiarity:** exposure, training or limited implementation; never present as expert-level without additional evidence

Only these three values are allowed in `Level`. Recency, context and caveats belong in separate fields.

## Evidence hierarchy

1. production or professional role evidence
2. independently owned public software / open-source implementation
3. documented project implementation with tests or benchmarks
4. formal education / certification
5. training or conceptual exposure

A vacancy keyword is never evidence by itself.

---

# 1. Programming & Data

### Python
- **Level:** core
- **Evidence:** repeated professional Data Science/ML work plus independently authored Python libraries and systems including InsideForest, SheShe/DelDel, MetaCraft, narrative_dna and fraud/compliance tooling
- **Typical use:** modeling, statistical analysis, package development, pipelines, APIs, experimentation, automation, GenAI workflows, CLI tooling and validation

### SQL
- **Level:** core
- **Evidence:** repeated professional analytical, migration, segmentation, reporting and data-processing workflows
- **Typical use:** extraction, transformation, aggregation, analytical datasets, validation and feature preparation

### PySpark / Apache Spark
- **Level:** core
- **Evidence:** large-scale banking analytics and production-oriented distributed processing
- **Typical use:** distributed ETL, feature engineering, matching, large joins, analytical pipelines and production refactoring

### R
- **Level:** core
- **Evidence:** actuarial/statistical modeling, CRAN/public package development, thesis work, forecasting and reporting automation
- **Typical use:** statistical modeling, distributions, risk modeling, research, visualization and package development

### Pandas / NumPy
- **Level:** working
- **Evidence:** repeated use across public Python packages and analytical systems

### Git / GitHub
- **Level:** working
- **Evidence:** multi-year ownership of public repositories, versioned packages, documentation, tests and repository-driven workflows

### YAML / JSON / JSONL data contracts
- **Level:** working
- **Evidence:** MetaCraft schema tooling, narrative_dna JSON-first architecture and artifact-driven pipelines

---

# 2. Machine Learning & Statistics

### Supervised Machine Learning
- **Level:** core
- **Coverage:** classification, regression, feature engineering, model evaluation and business-oriented predictive modeling

### Tree-based Machine Learning / Random Forests
- **Level:** core
- **Coverage:** classification/regression, leaf/region extraction, feature importance and interpretable rule discovery
- **Repository evidence:** InsideForest and SheShe/DelDel

### Supervised Clustering & Region Discovery
- **Level:** core
- **Coverage:** target-guided region discovery, regional quality measurement, stable cluster assignment and human-readable decision regions
- **Repository evidence:** InsideForest and SheShe/DelDel

### Unsupervised / Anomaly Detection
- **Level:** core
- **Coverage:** anomaly detection, outlier analysis and hybrid rule + ML systems
- **Evidence:** banking fraud/malpractice analytics and public analytical tooling

### Statistical Modeling
- **Level:** core
- **Coverage:** probability distributions, hypothesis testing, model fitting, statistical validation, regression and risk modeling
- **Evidence:** actuarial education, thesis/research, R packages and professional analytics

### Model Evaluation & Validation
- **Level:** core
- **Coverage:** baselines, train/test or temporal validation, precision, recall, F1, lift, stability, clustering agreement, business validation and statistical fit

### Explainable / Interpretable Machine Learning
- **Level:** core
- **Coverage:** region-based explainability, low-dimensional rule extraction, subspace exploration, class diagnostics and model behavior translated into human-readable structures
- **Repository evidence:** InsideForest and SheShe/DelDel

### scikit-learn ecosystem
- **Level:** core
- **Evidence:** professional ML usage plus independently authored estimator-style APIs with `fit`, `predict`, `transform`, scoring, persistence and parameter interfaces

### Fuzzy Matching / Identity Resolution
- **Level:** working
- **Coverage:** name normalization, edit-distance similarity, candidate review and distributed matching against regulatory/watch lists

### Time Series & Forecasting
- **Level:** working
- **Coverage:** forecasting, trend analysis, seasonality, temporal validation and ensemble-learning concepts
- **Evidence:** professional demand/operations forecasting plus public time-series work
- **Usage note:** do not claim specialization in ARIMA, SARIMA, Prophet or another named family without project-specific evidence

### Geospatial Analytics
- **Level:** working
- **Coverage:** coordinate aggregation, footprint analysis, ATM/branch location strategy, geolocation and spatial-temporal analytical features

### Optimization / Decision Modeling
- **Level:** working
- **Coverage:** prioritization, low-dimensional rule search, greedy/beam search patterns, decision support and analytical allocation problems
- **Usage note:** do not claim deep mixed-integer programming specialization without project-specific evidence

### TensorFlow / Keras
- **Level:** working
- **Evidence:** public Google Cloud model-serving implementation using Keras artifacts

### Hugging Face Transformers / BERT-family models
- **Level:** working
- **Evidence:** public cloud recommender using Transformer tokenizers/models and BERT-style embeddings

### Semantic Similarity / Embeddings
- **Level:** working
- **Evidence:** cosine-similarity recommendation and semantic-auditing implementations

### Approximate Nearest-Neighbor Search
- **Level:** working
- **Evidence:** hnswlib used in public ML tooling

### LightGBM
- **Level:** familiarity
- **Evidence:** optional/public project ecosystem exposure

### SHAP
- **Level:** familiarity
- **Evidence:** optional/public project ecosystem exposure

### InterpretML
- **Level:** familiarity
- **Evidence:** optional/public project ecosystem exposure

---

# 3. Generative AI & LLM Systems

### LLM Application Design
- **Level:** core
- **Coverage:** business use-case design, grounded workflows, structured generation, validation, deterministic fallbacks and integration into analytical processes
- **Evidence:** internal knowledge tooling plus public narrative_dna, MetaCraft and agent-oriented projects

### Retrieval-Augmented / Retrieval-Grounded Generation
- **Level:** core
- **Coverage:** source-based answering, knowledge-base design, corpus curation, context control and hallucination mitigation
- **Boundary:** application-level RAG/retrieval grounding is supported; do not infer ownership of a specific vector database or ingestion platform unless a project confirms it

### Prompt Engineering
- **Level:** core
- **Coverage:** task decomposition, structured outputs, extraction, summarization, evaluation, adjudication and reusable workflow prompts

### Structured LLM Outputs
- **Level:** working
- **Coverage:** JSON Schema constrained outputs, typed validation and deterministic post-generation checks
- **Repository evidence:** narrative_dna

### Agentic Workflows
- **Level:** working
- **Coverage:** multi-step agent workflows, skill/role contracts, task delegation, evaluation and iterative quality gates
- **Repository evidence:** mvp-agent-factory, narrative_dna and AI-assisted open-source development

### LLM Evaluation / Evals
- **Level:** working
- **Coverage:** rubrics, regression cases, reviewer aggregation, synthetic-gold workflows, deterministic validation and quality gates

### LLM Safety / Hallucination Mitigation
- **Level:** working
- **Coverage:** grounding, conservative adjudication, schema constraints, validation, source constraints, confidence gates and fallback behavior

### OpenAI API / Responses API
- **Level:** working
- **Evidence:** public structured-output, embedding and LLM workflow implementations

### Google Gemini
- **Level:** working
- **Evidence:** professional/internal workflow use and Google Workspace AI initiatives

### NotebookLM
- **Level:** working
- **Evidence:** internal normative/knowledge workflows and adoption analysis

### Google Workspace AI workflows
- **Level:** working
- **Evidence:** Apps Script/Workspace automation, Gemini/NotebookLM use cases and workflow design

## GenAI boundary

Do not convert application-level GenAI experience into claims of foundation-model pretraining, large-scale GPU training, custom model fine-tuning infrastructure or autonomous decision making unless a project provides direct evidence.

---

# 4. Data Engineering, Data Quality, MLOps & Production

### ETL & Data Quality
- **Level:** core
- **Coverage:** extraction, transformation, integration, validation, reconciliation, data-quality controls and analytical dataset construction

### Productionization of Data Science Solutions
- **Level:** core
- **Coverage:** moving analytical logic from exploration to repeatable business processes, recurring releases, APIs, packages, operational integration and monitoring

### Python Package Engineering
- **Level:** core
- **Coverage:** package layouts, dependency management, public APIs, backward compatibility, documentation, release/version management and distribution
- **Repository evidence:** InsideForest, SheShe/DelDel and MetaCraft

### Schema Engineering / Metadata Management
- **Level:** working
- **Coverage:** YAML schemas, schema enrichment, drift detection, conversion and contract-driven validation
- **Repository evidence:** MetaCraft

### Data Sketches / Approximate Statistics
- **Level:** working
- **Coverage:** t-digest and HyperLogLog-based metadata/statistical sketches

### Great Expectations
- **Level:** working
- **Coverage:** expectation-suite generation from metadata/schema definitions

### API / CLI Design
- **Level:** working
- **Coverage:** HTTP endpoints, command-line workflows and stable callable APIs

### Automated Testing / Regression Testing
- **Level:** working
- **Coverage:** pytest suites, golden regression, deterministic validation and experiment protocols

### Code Review / Production QA
- **Level:** working
- **Coverage:** pull-request review, forensic debugging, source-to-report lineage, schema normalization and false-positive remediation

### CI/CD
- **Level:** working
- **Coverage:** repository-driven testing/deployment practices and automated delivery concepts

### Docker
- **Level:** working
- **Coverage:** containerization and reproducible deployment environments

### MLflow
- **Level:** working
- **Coverage:** experiment tracking and model-lifecycle workflows

### Airflow
- **Level:** working
- **Coverage:** workflow orchestration and scheduled analytical pipelines

### RPA / Web Automation
- **Level:** working
- **Coverage:** browser automation, retries, logs, batch execution and secure local processing
- **Evidence:** Python/Selenium provider-validation workflow

### Kubernetes
- **Level:** familiarity
- **Usage note:** suitable as supporting MLOps knowledge; do not position as Kubernetes platform engineering expertise

### Kubeflow
- **Level:** familiarity
- **Usage note:** mention only where orchestration/MLOps context is relevant and avoid implying deep production ownership

### Kafka
- **Level:** familiarity
- **Usage note:** do not present as a core streaming specialization without stronger project evidence

---

# 5. Cloud & Data Platforms

### AWS
- **Level:** working
- **Evidence:** professional AWS/EMR/PySpark analytical workloads plus SageMaker-related formal training
- **Usage note:** do not claim AWS architecture certification

### Google Cloud
- **Level:** working
- **Evidence:** Cloud Functions Gen2, Cloud Storage, HTTP model serving and cloud-hosted model artifacts in public code

### Google Workspace ecosystem
- **Level:** working
- **Coverage:** Apps Script, Sheets, Forms, Looker Studio, Gemini, NotebookLM and AI-enabled workflows

### Teradata
- **Level:** working
- **Evidence:** professional analytical and operational workflows

### Oracle
- **Level:** working
- **Evidence:** professional analytical/operational data workflows

---

# 6. Visualization & Business Intelligence

### Tableau
- **Level:** working
- **Evidence:** Tableau Desktop Specialist credential and professional reporting

### Power BI
- **Level:** working

### Looker Studio
- **Level:** working

### Matplotlib / Plotly / Analytical Visualization
- **Level:** working
- **Evidence:** analytical and model/rule visualization work

### Shiny
- **Level:** working
- **Recency:** historical
- **Evidence:** public time-series/analytical applications

### Streamlit
- **Level:** working
- **Evidence:** public analytical apps and professional prototypes

### Data Storytelling
- **Level:** core
- **Coverage:** translating analytical outputs into business decisions, executive communication and visual narratives

---

# 7. Software Engineering & Open Source

### Library / Framework Design
- **Level:** core
- **Evidence:** independently authored reusable Python and R libraries rather than only notebooks or one-off scripts

### Open-Source Ownership
- **Level:** core
- **Evidence:** public repositories and packages spanning statistical tooling, interpretable ML, data quality, GenAI evaluation and agent architecture across multiple years

### Backward Compatibility & API Migration
- **Level:** working
- **Evidence:** public API migration/deprecation patterns in InsideForest

### R / RStudio Add-in Engineering
- **Level:** working
- **Evidence:** CRAN-published FitUltD/shortcuts ecosystem and analyst-productivity utilities

### Documentation & Developer Experience
- **Level:** working
- **Evidence:** README quickstarts, API/migration docs, operating guides, Colab examples and technical documentation across public projects

### Reproducible Experiment Design
- **Level:** working
- **Evidence:** multi-seed benchmarks, experiment protocols and golden-regression fixtures

---

# 8. Business & Domain Skills

### Banking Analytics
- **Level:** core
- **Coverage:** remote banking, commercial analytics, contactability, product recommendation, operational analytics, profitability/productivity measurement and physical-network analytics

### Risk & Fraud Analytics
- **Level:** core
- **Coverage:** statistical anomaly detection, hybrid rule + ML approaches, monitoring, prioritization, interpretability and investigation support

### Insurance / Actuarial Reasoning
- **Level:** core
- **Coverage:** probability, risk modeling, statistical distributions and quantitative decision making

### Healthcare / Risk Modeling
- **Level:** working
- **Coverage:** statistical modeling and distribution fitting applied to medical/risk contexts

---

# 9. Leadership & Delivery

### End-to-End Technical Ownership
- **Level:** core
- **Coverage:** problem framing, data contracts, modeling, validation, implementation, productionization, monitoring and business communication

### Stakeholder Management
- **Level:** core
- **Coverage:** collaboration with business, technology, compliance, data/legal, risk and senior leadership stakeholders

### Technical / Project Leadership
- **Level:** core
- **Coverage:** project direction, solution architecture, quality/evaluation criteria, mentoring, technical presentations and cross-functional coordination
- **Boundary:** project/technical leadership must not be converted into formal people-management claims without direct evidence

### Process / Workflow Architecture
- **Level:** working
- **Coverage:** As-Is/To-Be mapping, state models, SLAs, escalation, RACI and phased automation design

### Teaching & Knowledge Transfer
- **Level:** working
- **Coverage:** Python instruction, technical mentoring, AI/GenAI workshops, internal talks, documentation and examples

### Agile Delivery
- **Level:** working
- **Coverage:** Scrum principles, iterative development and cross-functional coordination

---

# 10. Languages

### Spanish
- **Proficiency:** native

### English
- **Proficiency:** C1 / advanced professional
- **Evidence:** professional and academic use plus international experience in Dublin

### French
- **Proficiency:** A2

---

# 11. GitHub-backed evidence map

| Repository | Strongest evidence |
|---|---|
| `InsideForest` | Python package engineering, estimator APIs, supervised clustering, interpretable ML, validation, pytest, persistence, documentation |
| `SheShe` / `PureSheShe` | decision-surface exploration, low-dimensional rule discovery, numerical search, experiment design and packaging |
| `MetaCraft` | data quality, schema drift, YAML metadata, Great Expectations, sketches and OpenAI integration |
| `ADNarrativa` / `narrative_dna` | OpenAI Responses API, Structured Outputs, Pydantic, JSON Schema, embeddings, LLM evals, adjudication and golden regression |
| `mvp-agent-factory` | agent architecture, skill contracts, eval rubrics, PRDs and AI-assisted SDLC structure |
| `cloud_function` | GCP Cloud Functions Gen2, Cloud Storage, Keras, Transformers, embeddings and HTTP model serving |
| `coi` | transaction-pattern analysis, fraud/compliance tooling, text signals, visual reporting and interpretable case exports |
| `floor` / `yahoo` | financial-data pipelines, temporal validation, GitHub Actions, SQLite/JSON artifacts and static dashboards |
| `FitUltD` / `shortcuts` | CRAN package engineering, distribution fitting, statistical tests, RStudio add-ins and analyst productivity |
| `movilidad_social_mx` | Streamlit analytical product and probabilistic storytelling; fork boundary applies |
| `DataMiningTools` / `FitUlt_V00` | R package development and statistical tooling |
| `Ensemble-Learning-for-Time-Series` | R time-series ensemble forecasting and Shiny delivery |

---

# 12. CV generation rules

1. A vacancy keyword alone is never enough to promote a skill into the CV.
2. Prefer skills with direct evidence in `projects/`, `roles/`, `achievements/` or observable public repositories.
3. Preserve the exact `core`, `working` or `familiarity` value; never upgrade it for ATS matching.
4. Never infer a hybrid level. If evidence grows, update the canonical level explicitly.
5. Optional dependency presence is weaker evidence than code/API ownership.
6. For senior Data Science roles, lead with Python, SQL, PySpark/Spark, ML, statistics, interpretable ML, GenAI/LLMs and end-to-end ownership when relevant.
7. For ML Engineering/MLOps roles, add package engineering, tests, APIs, cloud model serving, Docker, CI/CD and lifecycle tools while keeping Kubernetes/Kubeflow/Kafka at familiarity unless new evidence is added.
8. For GenAI roles, emphasize Structured Outputs, validation, evals, RAG, prompting, adjudication, agentic workflows and auditable system design rather than unsupported foundation-model training claims.
9. For data-quality/platform roles, MetaCraft and professional production-quality work provide evidence for schema contracts, drift detection, metadata, QA and reconciliation.
10. For explainable-ML roles, InsideForest and SheShe/DelDel are primary evidence.
11. For leadership roles, combine technical/project leadership with measurable outcomes; do not invent formal people-management scope.
