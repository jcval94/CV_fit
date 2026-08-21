---
schema_version: 1
last_updated: 2026-08-20
status: validated_public
public_safe: true
project_type: open_source_library
source_repo: https://github.com/jcval94/InsideForest
primary_language: Python
license: MIT
---

# InsideForest

## Summary

InsideForest is an independently authored open-source Python library for discovering **interpretable regions in tabular data through supervised clustering**. Random forests are used as generators of candidate leaves; the library then selects, scores, describes and assigns observations to useful human-readable regions.

The project is strong evidence of José Carlos's ability to move beyond model consumption into **algorithm design, reusable library engineering, evaluation and public API ownership**.

## Public repository facts

- Repository created: February 2023
- Publicly maintained through at least July 2026
- Current release documented in repository: `0.4.3`
- Primary language: Python
- License: MIT
- Installable with `pip`
- Includes documentation site, API/migration docs, changelog, examples, benchmarks and pytest suite

## Canonical estimators

- `InsideForestRegionClusterer` — general categorical targets
- `InsideForestClassRegionClusterer` — class-aware regions retaining class distributions and diagnostics
- `InsideForestContinuousRegionClusterer` — continuous targets

## Public API / engineering evidence

Canonical estimators expose:

- `fit`
- `fit_predict`
- `predict`
- `transform`
- `score`
- `get_params`
- `set_params`
- `save`
- `load`
- region assignment and explanation methods
- quality-reporting methods

The library also maintains migration aliases with deprecation behavior, demonstrating awareness of backward compatibility and API evolution.

## ML / statistical concepts demonstrated

### Categorical targets

Quality reporting includes:

- adjusted mutual information (AMI)
- coverage / unmatched rate
- NMI
- ARI
- homogeneity
- completeness
- purity
- lift
- entropy
- class-level diagnostics

### Continuous targets

Regions preserve statistics such as:

- support / coverage
- mean / median
- standard deviation
- IQR / range
- target shift
- dispersion reduction
- separation
- region score

The canonical continuous score is η², measuring the fraction of target variance explained by the returned clusters.

## Validation engineering

The repository contains reproducible benchmark scripts for:

- class-region quality
- coverage
- unmatched rate
- clustering agreement
- regional quality
- stability
- runtime
- memory
- regression-region quality
- dispersion reduction
- assignment/geometric stability
- branch compression

A complete pytest suite is also documented.

## Skills evidenced

- Python package engineering
- scikit-learn-style estimator design
- Random Forests
- supervised clustering
- interpretable / explainable ML
- classification and continuous-target analysis
- statistical metrics
- benchmarking
- model validation
- testing with pytest
- API design
- persistence / serialization
- backward compatibility
- technical documentation
- open-source maintenance

## Quantified public outcomes

Use `../achievements/metrics.md` as the canonical source for numeric claims.

Currently approved public metrics include:

- `30,000+ pip installs`
- adoption across `50+ countries`
- `3+ years` of public maintenance/evolution

Do not infer current download counts from GitHub itself; the adoption numbers originate from José Carlos's public professional statements.

## Strong CV narratives

### General Data Science / ML

> Built and maintained InsideForest, an open-source Python library for interpretable supervised clustering and rule-region discovery in tabular ML, with 30,000+ pip installs across 50+ countries.

### ML Engineering

> Designed a reusable scikit-learn-style ML library with stable estimator APIs, persistence, pytest coverage, benchmark suites, documentation and backward-compatible API migration.

### Applied Scientist / XAI

> Developed supervised region-discovery methods over tree-generated candidate spaces, with class/continuous-target diagnostics, stability evaluation and human-readable region explanations.

## Usage constraints

- Do not describe InsideForest as a replacement for Random Forest prediction; its canonical estimators return region-cluster IDs.
- Do not claim external academic peer review unless independently verified.
- Do not convert package downloads into active users.
- Do not use lines of code as a primary quality metric.
