---
schema_version: 1
last_updated: 2026-08-20
status: validated_public
public_safe: true
project_type: open_source_ml_research
source_repos:
  - https://github.com/jcval94/SheShe
  - https://github.com/jcval94/PureSheShe
primary_language: Python
---

# SheShe / DelDel

## Summary

SheShe (**Smart High-dimensional Edge Segmentation & Hyperboundary Explorer**) and its experimental DelDel/PureSheShe work form a public research-oriented toolkit for turning probabilistic models into guided explorers of decision surfaces and discovering **human-readable rules in low-dimensional subspaces**.

This project family is direct evidence of algorithmic experimentation, model interpretation, numerical search and reproducible benchmark design.

## SheShe capabilities

- supervised clustering for classification and regression
- rule extraction
- subspace exploration
- decision-surface exploration via local probability/predicted-value maxima
- 2D/3D visualization
- integration with InsideForest
- reusable package installation from PyPI
- pytest-based development workflow

## Mathematical / algorithmic ideas

The public documentation describes an optimization view based on approximating `max_x f(x)` through gradient-ascent paths toward local maxima and delineating neighborhoods around those maxima.

Related implementation patterns include:

- boundary / frontier plane discovery
- rule pruning and orientation
- low-dimensional conjunction search
- AND / OR / DNF rule search
- greedy, beam, random and diversity-oriented search strategies
- F1 / precision / recall / lift-based regional evaluation
- Pareto-style rule ranking

## DelDel experimental discipline

The PureSheShe/DelDel repository defines a mandatory experiment protocol. Experiments record metrics including:

- F1
- precision / recall
- precision lift
- runtime
- per-class and global summaries

The project also defines a composite `compass_score` based on the geometric mean of F1, lift precision and minimum class lift for selected regions.

## Public benchmark evidence

The repository documents multi-seed experiments on synthetic datasets with:

- `30,000` samples
- `25` informative variables
- seeds `11`, `17`, `23`

Across the documented runs, the low-dimensional search stage completed in approximately `6.97–8.32 s`.

Documented best 2D results span roughly:

- F1: `0.619–0.684`
- precision: `0.802–0.967`

These are **synthetic technical benchmarks**, not production/business performance.

## Dependencies / ecosystem demonstrated

Primary repository dependencies include:

- NumPy
- Pandas
- scikit-learn
- Matplotlib
- hnswlib

Optional ecosystem integrations include LightGBM, SHAP and InterpretML. Optional dependency presence alone must not be treated as expert-level evidence.

## Skills evidenced

- algorithm design
- high-dimensional ML
- interpretable ML / XAI
- classification / regression
- supervised clustering
- numerical optimization/search
- rule extraction
- beam / greedy search patterns
- feature/subspace exploration
- benchmark design
- reproducible experimentation
- Python package engineering
- pytest
- developer documentation

## CV positioning

### Applied Scientist / Research DS

> Designed interpretable rule-discovery and decision-surface exploration methods for classification/regression, with reproducible multi-seed benchmarks on 30k × 25 synthetic datasets.

### Explainable ML

> Built Python tooling that transforms complex model decision surfaces into low-dimensional, human-readable regions evaluated by precision, recall, F1 and lift.

## Usage constraints

- Always label the 30k × 25 metrics as synthetic benchmarks.
- Do not describe optional LightGBM/SHAP/Interpret dependencies as core expertise without separate evidence.
- Prefer InsideForest adoption metrics for standard CVs; use SheShe/DelDel when the target role rewards algorithmic/research depth.
