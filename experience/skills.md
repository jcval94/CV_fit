---
schema_version: 3
record_id: skills
record_type: skills
last_updated: 2026-08-20
status: canonical
confidence: high
visibility: public
public_safe: true
usage_policy: "Generated CVs must prefer demonstrated skills over inferred keywords and must not upgrade familiarity into expert proficiency. Public GitHub repositories may be used as direct technical evidence when the capability is observable in code, packaging, tests, documentation, or reproducible benchmarks."
source_refs:
  - SRC-USER-CONFIRMED-2026-08-20
  - SRC-TRAJECTORY-2021-2023-CURATED
  - SRC-TRAJECTORY-2024-2026-CURATED
  - SRC-GITHUB-JCVAL94-PUBLIC
---

# Skills

Canonical inventory of technical, analytical, business and leadership skills for José Carlos Del Valle.

This file intentionally separates **demonstrated/core capability**, **practical working experience**, and **familiarity/exposure**. It is designed for RAG and CV generation, not for keyword stuffing.

## Proficiency model

- **core:** repeated professional use and/or substantial independently owned implementation with strong interview-level defensibility
- **working:** meaningful hands-on implementation, but not necessarily the primary specialization
- **familiarity:** exposure, training or limited implementation experience; never present as expert-level without additional evidence

## Evidence hierarchy

1. production or professional role evidence
2. independently owned public software / open-source implementation
3. documented project implementation with tests or benchmarks
4. formal education / certification
5. training or conceptual exposure

A vacancy keyword is never evidence by itself.

---

# 1. Programming & Data

## Core

### Python
- **Level:** core
- **Evidence:** professional Data Science/ML work plus independently authored Python packages and systems including InsideForest, SheShe/DelDel, MetaCraft, narrative_dna and agent-oriented tooling
- **Typical use:** modeling, statistical analysis, package development, pipelines, APIs, experimentation, automation, GenAI workflows, CLI tooling and validation

### SQL
- **Level:** core
- **Evidence:** professional analytical and data-processing workflows
- **Typical use:** extraction, transformation, aggregation, analytical datasets, validation and feature preparation

### PySpark / Apache Spark
- **Level:** core
- **Evidence:** large-scale banking analytics and production-oriented data processing
- **Typical use:** distributed ETL, feature engineering, large datasets and analytical pipelines

### R
- **Level:** core
- **Evidence:** actuarial/statistical modeling and public R package development dating back to 2019
- **Typical use:** statistical modeling, distributions, risk modeling, research, visualization and package development
- **Repository evidence:** `FitUlt_V00`, `DataMiningTools`, time-series projects and thesis code

## Working

### Pandas / NumPy
- **Level:** working-to-core
- **Evidence:** core dependencies across public Python packages and analytical systems
- **Typical use:** tabular transformations, numerical operations, validation, experimentation and reporting

### Git / GitHub
- **Level:** working-to-core
- **Evidence:** multi-year ownership of public repositories, versioned packages, documentation sites, test suites and agent-assisted software workflows
- **Typical use:** version control, package maintenance, issue-driven development, experimentation, reproducible documentation and automation

### YAML / JSON / JSONL data contracts
- **Level:** working-to-core
- **Evidence:** MetaCraft schema tooling and narrative_dna JSON-first architecture
- **Typical use:** schemas, configuration, versioned contracts, structured outputs and auditable pipelines

---

# 2. Machine Learning & Statistics

## Core

### Supervised Machine Learning
- **Level:** core
- **Coverage:** classification, regression, tree-based methods, model evaluation and feature engineering
- **Repository evidence:** InsideForest, SheShe/DelDel and cloud ML recommender

### Tree-based Machine Learning / Random Forests
- **Level:** core
- **Coverage:** classification/regression, leaf/region extraction, feature importance and interpretable rule discovery
- **Repository evidence:** InsideForest and SheShe/DelDel

### Supervised Clustering & Region Discovery
- **Level:** core
- **Coverage:** discovering human-readable regions guided by target information, regional quality measurement and stable cluster assignment
- **Repository evidence:** InsideForest canonical clusterers for categorical and continuous targets; SheShe/DelDel subspace exploration

### Unsupervised / Anomaly Detection
- **Level:** core
- **Coverage:** anomaly detection, outlier analysis and hybrid rule + ML approaches
- **Evidence:** banking fraud / malpractice detection using rules and Isolation Forest

### Fuzzy Matching / Identity Resolution
- **Level:** working-to-core
- **Coverage:** name normalization, edit-distance similarity, probabilistic candidate review and distributed matching against regulatory/watch lists
- **Evidence:** professional compliance analytics plus public COI/fraud tooling

### Statistical Modeling
- **Level:** core
- **Coverage:** probability distributions, hypothesis testing, model fitting, statistical validation and risk modeling
- **Evidence:** actuarial education, thesis/research work, R packages and professional analytics

### Model Evaluation & Validation
- **Level:** core
- **Coverage:** train/test evaluation, baselines, F1, precision, recall, lift, clustering agreement, stability, business validation and statistical fit
- **Repository evidence:** InsideForest validation suites; DelDel experiment protocol; narrative_dna evaluation/regression framework

### Explainable / Interpretable Machine Learning
- **Level:** core
- **Coverage:** region-based explainability, low-dimensional rule extraction, subspace exploration, class diagnostics and model behavior translated into human-readable structures
- **Repository evidence:** InsideForest and SheShe/DelDel

### Time Series & Forecasting
- **Level:** working-to-core
- **Coverage:** forecasting, trend analysis, statistical models and ensemble learning for time series
- **Evidence:** professional demand-forecasting initiatives plus public `Ensemble-Learning-for-Time-Series` implementation and Shiny app
- **Usage note:** avoid claiming specialization in a specific forecasting family unless the target CV has matching project evidence

### Geospatial Analytics
- **Level:** working
- **Coverage:** coordinate aggregation, footprint analysis, ATM/branch location strategy, customer/debtor geolocation and spatial-temporal alert features
- **Evidence:** BBVA ATM analytics, geolocation engines and public social-mobility/analytical apps

### Optimization / Decision Modeling
- **Level:** working
- **Coverage:** prioritization, rule search, beam/greedy search patterns, decision support and analytical allocation problems
- **Repository evidence:** DelDel low-dimensional rule search and pruning strategies
- **Usage note:** do not automatically claim deep mixed-integer programming specialization without project-specific evidence

## Working

### scikit-learn estimator ecosystem
- **Level:** working-to-core
- **Evidence:** InsideForest exposes estimator-style `fit`, `fit_predict`, `predict`, `transform`, `score`, `get_params`, `set_params`, persistence and fitted attributes

### TensorFlow / Keras
- **Level:** working
- **Evidence:** public Google Cloud Function loads and serves Keras models as part of an ML recommendation pipeline

### Hugging Face Transformers / BERT-family models
- **Level:** working
- **Evidence:** public cloud recommender uses Transformer tokenizers/models and TinyBERT/BERT-style embeddings for text representation

### Semantic similarity / embeddings
- **Level:** working-to-core
- **Evidence:** cosine-similarity recommender and narrative_dna semantic-similarity auditor with configurable local/OpenAI embeddings

### Approximate nearest-neighbor search
- **Level:** working
- **Evidence:** `hnswlib` used as a main dependency in SheShe for fast nearest-neighbor search

## Ecosystem exposure — do not auto-promote

- LightGBM
- SHAP
- InterpretML

These appear in public project ecosystems but should not be presented as core expertise solely from optional dependency presence.

---

# 3. Generative AI & LLM Systems

## Core

### LLM Application Design
- **Level:** core
- **Coverage:** business use-case design, structured LLM workflows, grounding, output validation, deterministic fallbacks and integration into analytical processes
- **Evidence:** internal normative assistant plus public narrative_dna, MetaCraft and agent-factory repositories

### Retrieval-Augmented Generation (RAG)
- **Level:** core
- **Coverage:** retrieval-grounded assistants, source-based answering, knowledge-base design and hallucination mitigation
- **Evidence:** internal knowledge / normative tooling

### Prompt Engineering
- **Level:** core
- **Coverage:** task decomposition, structured outputs, extraction, summarization, evaluation, adjudication and reusable workflow prompts

### Structured LLM Outputs
- **Level:** working-to-core
- **Coverage:** JSON Schema constrained outputs, strict validation, typed models and post-generation deterministic checks
- **Repository evidence:** narrative_dna uses OpenAI Responses API structured outputs with strict JSON Schema and Pydantic validation

### Agentic Workflows
- **Level:** working-to-core
- **Coverage:** multi-step agent workflows, agent-assisted development, role/skill contracts, task delegation, evaluation and iterative quality gates
- **Repository evidence:** `mvp-agent-factory`; agent-assisted open-source development; narrative_dna synthetic review/adjudication workflow

### LLM Evaluation / Evals
- **Level:** working-to-core
- **Coverage:** rubrics, regression cases, reviewer aggregation, high-confidence synthetic gold, deterministic validation and quality gates
- **Repository evidence:** narrative_dna and mvp-agent-factory

### LLM Safety / Hallucination Mitigation
- **Level:** working-to-core
- **Coverage:** grounding, conservative adjudication, schema constraints, validation, source constraints, rejected labels, confidence gates and fallback behavior
- **Repository evidence:** narrative_dna JSON-first architecture and internal grounded assistants

## Tools / Platforms with demonstrated use

- OpenAI API
- OpenAI Responses API
- OpenAI Structured Outputs / JSON Schema patterns
- ChatGPT / Codex-assisted development
- Google Gemini
- NotebookLM
- Google Workspace AI workflows

## Working implementation patterns

- Pydantic validation
- retries and controlled failure modes
- versioned prompts/configuration
- cache-by-hash patterns
- embeddings and semantic auditing
- synthetic reviewer committees / adjudication
- JSON/JSONL traceability

## Usage note

Do not convert LLM application experience into claims of foundation-model pretraining, large-scale GPU training or fine-tuning infrastructure ownership unless a specific project provides evidence.

---

# 4. Data Engineering, Data Quality, MLOps & Production

## Core / Working

### ETL & Data Quality
- **Level:** core
- **Coverage:** extraction, transformation, integration, validation, data-quality controls and analytical dataset construction
- **Repository evidence:** MetaCraft validates types, ranges and nulls; detects schema drift; transforms datasets to schema; produces quality reports

### Schema Engineering / Metadata Management
- **Level:** working-to-core
- **Coverage:** YAML schemas, schema enrichment, drift detection, schema conversion and contract-driven validation
- **Repository evidence:** MetaCraft

### Data Sketches / Approximate Statistics
- **Level:** working
- **Coverage:** t-digest and HyperLogLog-based metadata/statistical sketches
- **Repository evidence:** MetaCraft

### Great Expectations
- **Level:** working
- **Coverage:** generation of expectation suites from metadata/schema definitions
- **Repository evidence:** MetaCraft

### Productionization of Data Science Solutions
- **Level:** core
- **Coverage:** moving analytical logic from exploration to repeatable business processes, APIs, packages, operational integration and monitoring
- **Repository evidence:** PyPI-style packages, Cloud Functions deployment, CLIs and end-to-end pipelines

### Python Package Engineering
- **Level:** working-to-core
- **Coverage:** `pyproject`/package layouts, editable installs, dependency management, public APIs, backward compatibility, documentation, release/version management and PyPI distribution
- **Repository evidence:** InsideForest, SheShe/DelDel and MetaCraft

### API / CLI Design
- **Level:** working
- **Coverage:** HTTP function endpoints, command-line workflows and stable callable APIs
- **Repository evidence:** cloud ML recommender, narrative_dna CLI and package APIs

### Automated Testing / Regression Testing
- **Level:** working-to-core
- **Coverage:** pytest suites, golden regression, deterministic validation and experiment protocols
- **Repository evidence:** InsideForest, SheShe/DelDel and narrative_dna

### Code Review / Production QA
- **Level:** working-to-core
- **Coverage:** pull-request review, forensic debugging, source-to-report lineage, schema normalization and false-positive remediation
- **Evidence:** professional review of critical analytical repositories and production data-quality incidents

### CI/CD
- **Level:** working
- **Coverage:** automated testing/deployment concepts and repository-driven delivery

### Docker
- **Level:** working
- **Coverage:** containerization and reproducible deployment environments

### MLflow
- **Level:** working
- **Coverage:** experiment tracking / model lifecycle concepts and practical MLOps workflows

### Airflow
- **Level:** working
- **Coverage:** workflow orchestration and scheduled analytical pipelines

### RPA / Web Automation
- **Level:** working
- **Coverage:** browser automation, retries, logs, batch execution and secure local processing under InfoSec constraints
- **Evidence:** Python/Selenium provider-validation workflow

## Familiarity / bounded experience

### Kubernetes
- **Level:** familiarity-to-working
- **Usage rule:** suitable as supporting MLOps knowledge; do not position as a Kubernetes platform engineer

### Kubeflow
- **Level:** familiarity
- **Usage rule:** mention only where orchestration/MLOps tooling is relevant and avoid implying deep production ownership without project evidence

### Kafka
- **Level:** familiarity
- **Usage rule:** do not present as a core streaming specialization without stronger project evidence

---

# 5. Cloud & Platforms

## Working

### Google Cloud
- **Level:** working
- **Demonstrated capabilities:** Cloud Functions Gen2, Cloud Storage, HTTP-triggered model serving, runtime/resource configuration and cloud-hosted model artifact loading
- **Repository evidence:** public `cloud_function` ML recommender

### Google Workspace ecosystem
- **Level:** working
- **Relevant exposure:** Gemini, Apps Script/Workspace automation, Sheets/Forms workflow design, APIs and AI-enabled processes

### AWS
- **Level:** working
- **Relevant exposure:** cloud-based analytical workloads, AWS EMR/PySpark delivery and SageMaker-related formal training
- **Usage note:** do not claim AWS architecture certification unless verified in `certifications.md`

---

# 6. Visualization & Business Intelligence

## Core / Working

### Tableau
- **Level:** core-to-working
- **Evidence:** Tableau Desktop Specialist credential and professional analytical reporting

### Power BI
- **Level:** working

### Looker Studio
- **Level:** working

### Matplotlib / Plotly / analytical visualization
- **Level:** working
- **Repository evidence:** model/rule visualization utilities and cloud recommendation tooling

### Shiny
- **Level:** working / historical
- **Evidence:** public ensemble time-series forecasting application

### Streamlit
- **Level:** working
- **Evidence:** public analytical apps and professional prototypes translating model/recommendation outputs into interactive experiences

### Data Storytelling
- **Level:** core
- **Coverage:** translating analytical outputs into business decisions, executive communication and visual narratives

---

# 7. Software Engineering & Open Source

## Independently demonstrated

### Library / Framework Design
- **Level:** working-to-core
- **Evidence:** authored reusable Python and R libraries rather than only standalone notebooks
- **Examples:** InsideForest, SheShe/DelDel, MetaCraft, DataMiningTools, FitUlt

### Backward Compatibility & API Migration
- **Level:** working
- **Evidence:** InsideForest maintains deprecated compatibility aliases while moving users toward canonical estimator contracts

### R / RStudio Add-in Engineering
- **Level:** working
- **Evidence:** CRAN-published FitUltD and shortcuts packages, clipboard/add-in utilities and SQL/R reporting tools

### Documentation & Developer Experience
- **Level:** working-to-core
- **Evidence:** documentation sites, README quickstarts, Colab examples, operating guides, API guides and migration documentation across public projects

### Reproducible Experiment Design
- **Level:** working-to-core
- **Evidence:** DelDel mandatory experiment protocol; InsideForest benchmark scripts; narrative_dna golden-regression fixtures

### Open-source ownership
- **Level:** core differentiator
- **Evidence:** public repositories spanning statistical tooling, ML interpretability, data quality, GenAI evaluation and agent architecture, with projects maintained across multiple years

---

# 8. Business & Domain Skills

## Core

### Banking Analytics
- remote banking
- commercial analytics
- product propensity / offer optimization
- operational analytics
- fraud / malpractice detection
- customer behavior
- profitability and productivity measurement

### Risk & Fraud Analytics
- statistical anomaly detection
- hybrid business-rule + ML approaches
- monitoring and prioritization
- interpretability and investigation support

### Insurance / Actuarial Reasoning
- probability
- risk modeling
- statistical distributions
- quantitative decision making

### Healthcare / Risk Modeling
- statistical modeling and distribution fitting applied to medical/risk contexts

---

# 9. Leadership & Delivery

## Core

### End-to-End Technical Ownership
- translate business problems into analytical solutions
- define data and output contracts
- build and validate models
- design reusable software interfaces
- productionize analytical logic
- monitor/evaluate outputs
- communicate business impact

### Stakeholder Management
- interaction with business, technology, compliance, data/legal and senior leadership stakeholders
- executive-level communication of analytical findings

### Technical Leadership
- project direction
- solution architecture
- quality/evaluation criteria
- mentoring / knowledge sharing
- technical presentations and workshops

### Process / Workflow Architecture
- **Level:** working-to-core
- **Coverage:** As-Is/To-Be mapping, state models, SLAs, escalation, RACI and phased automation design
- **Evidence:** regulatory-process architecture with Google Workspace and proposed LLM assistance

### Teaching & Knowledge Transfer
- Python instruction
- AI / GenAI workshops
- internal technical talks and labs
- public documentation and examples

### Agile Delivery
- Scrum principles
- iterative development
- cross-functional coordination

---

# 10. Languages

### Spanish
- **Level:** native

### English
- **Level:** C1 / advanced professional proficiency
- **Evidence:** professional and academic use; international experience in Dublin

### French
- **Level:** A2

---

# 11. GitHub-backed skill evidence map

| Repository | Strongest evidence |
|---|---|
| `InsideForest` | Python package engineering, scikit-learn-style APIs, supervised clustering, interpretable ML, validation, pytest, persistence, documentation |
| `SheShe` / `PureSheShe` | decision-surface exploration, low-dimensional rule discovery, classification/regression, numerical search, experiment design, PyPI packaging |
| `MetaCraft` | data quality, schema drift, YAML metadata, Great Expectations, t-digest, HyperLogLog, OpenAI integration |
| `ADNarrativa` / `narrative_dna` | OpenAI Responses API, strict Structured Outputs, Pydantic, JSON Schema, embeddings, LLM evals, adjudication, synthetic review, CLI, golden regression |
| `mvp-agent-factory` | agent architecture, skill contracts, eval rubrics, PRDs, vertical slices, Codex/Claude/Cursor workflows |
| `cloud_function` | GCP Cloud Functions Gen2, Cloud Storage, TensorFlow/Keras, Transformers, embeddings, HTTP model serving, OpenAI integration |
| `coi` | transaction-pattern analysis, public fraud/compliance tooling, guided Q&A, text signals, visual reporting, interpretable case exports |
| `floor` / `yahoo` | financial-data pipelines, temporal validation, GitHub Actions, SQLite/JSON artifacts, static dashboards |
| `FitUltD` / `shortcuts` | CRAN package engineering, distribution fitting, statistical tests, RStudio add-ins and analyst productivity |
| `movilidad_social_mx` | Streamlit analytical product, mixed-audience storytelling and probabilistic interpretation; fork boundary applies |
| `DataMiningTools` / `FitUlt_V00` | R package development, statistical tooling, distribution/modeling ecosystem |
| `Ensemble-Learning-for-Time-Series` | R time-series ensemble forecasting and Shiny delivery |

---

# 12. CV generation rules

1. A vacancy keyword alone is never enough to promote a skill into the CV.
2. Prefer skills with direct evidence in `projects/`, `roles/`, `achievements/` or observable public repositories.
3. Never change `familiarity` into `core` simply to improve ATS matching.
4. A dependency listed as optional is weaker evidence than code/API ownership; do not overclaim it.
5. For senior Data Science roles, lead with Python, SQL, PySpark/Spark, ML, statistics, interpretable ML, GenAI/LLMs and end-to-end ownership when relevant.
6. For ML Engineering/MLOps roles, add package engineering, tests, APIs, cloud model serving, Docker, CI/CD and lifecycle tools while preserving bounded labels for Kubernetes/Kubeflow/Kafka.
7. For GenAI roles, emphasize Structured Outputs, validation, evals, RAG, prompting, adjudication, agentic workflows and auditable system design rather than unsupported foundation-model training claims.
8. For data-quality/platform roles, MetaCraft provides direct evidence for schema contracts, drift detection, metadata and expectation generation.
9. For explainable-ML roles, InsideForest and SheShe/DelDel are primary evidence and should be preferred over generic XAI claims.
10. For leadership roles, combine technical architecture/ownership with measurable business outcomes rather than replacing technical depth with generic management language.
