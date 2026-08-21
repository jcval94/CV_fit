---
schema_version: 3
record_id: project-r-statistical-tooling
record_type: project
last_updated: 2026-08-20
status: validated_public_supporting
confidence: high
visibility: public
public_safe: true
project_type: statistical_tooling_portfolio
source_repos:
  - https://github.com/jcval94/FitUltD
  - https://github.com/jcval94/shortcuts
  - https://github.com/jcval94/copypaste
  - https://github.com/jcval94/DataMiningTools
  - https://github.com/jcval94/FitUlt_V00
  - https://github.com/jcval94/Tesis
  - https://github.com/jcval94/Ensemble-Learning-for-Time-Series
  - https://github.com/jcval94/ShinyApps
primary_language: R
source_refs:
  - SRC-GITHUB-JCVAL94-PUBLIC
  - SRC-PORTFOLIO-PUBLIC-2026-08
---

# R Statistical Tooling & Early Quantitative Projects

## Summary

Public repositories and deployed apps from 2019 onward provide evidence that José Carlos's software/ML trajectory is grounded in **actuarial statistics, R package development, forecasting and analyst-productivity tooling**, rather than beginning only with recent Generative AI work.

FitUltD is strong enough to lead for statistical/actuarial roles. The remaining repositories should usually support newer projects rather than take prime CV space.

## FitUltD

FitUltD is a public CRAN package for fitting univariate data that is not well represented by ordinary single-density functions, including multimodal mixtures.

Observable repository/package evidence includes:

- released installation from CRAN
- mixture/cluster-based distribution fitting
- Anderson-Darling and Kolmogorov-Smirnov goodness-of-fit results
- reproducible examples and visual comparison of fitted components
- multi-year public maintenance

### Evidence value

- R/CRAN package ownership
- distribution fitting and statistical testing
- actuarial/risk modeling foundations
- translating research into reusable public software

## DataMiningTools

`DataMiningTools` is structured as a formal R package rather than a collection of loose scripts.

Public repository evidence includes:

- `DESCRIPTION`
- `NAMESPACE`
- `R/`
- `man/`
- R project metadata
- package dependencies

The public package metadata identifies José Carlos as author/maintainer and version `1.0.0`.

Dependencies include statistical/data-mining and visualization tools such as:

- `mclust`
- `ADGofTest`
- `tibble`
- `purrr`
- `ggplot2`
- `dplyr`
- base statistical methods

### Evidence value

- R package engineering
- statistical/data-mining tooling
- documentation structure
- dependency management
- reusable analytical software

## FitUlt_V00

Public R repository described as a `FitUlt package`, associated with José Carlos's distribution-fitting / actuarial modeling work.

### Evidence value

- statistical distribution fitting
- actuarial modeling
- R package development
- statistical research translated into reusable code

Use the thesis/research records for exact methodological or quantitative claims rather than inferring them solely from the repository name.

## Tesis

Public repository containing documents, files and code used in José Carlos's actuarial thesis.

### Evidence value

- reproducible research orientation
- statistical modeling
- actuarial / healthcare-risk context
- relationship between academic methodology and code

Canonical thesis metrics, if used, belong in `../achievements/metrics.md` and require methodology-aware wording.

## Ensemble-Learning-for-Time-Series

Public extension of an ensemble-learning approach for time-series forecasting in R.

The repository also references a deployed Shiny application.

### Evidence value

- time-series forecasting
- ensemble learning
- R
- interactive analytical delivery through Shiny

## shortcuts and copypaste

The `shortcuts` CRAN package and related `copypaste` work address recurring RStudio friction through add-ins and clipboard-oriented data import.

Observable capabilities include:

- importing copied browser/Excel/Sheets tables into R
- expanding function arguments into editable code
- running/installing libraries referenced in a script
- RStudio add-in integration
- CRAN distribution for `shortcuts`

### Evidence value

- developer experience and analyst-productivity design
- RStudio API/add-in development
- public package distribution
- solving small operational problems with reusable tooling

## SQL Reporting tool

The public portfolio and ShinyApps index document a tool that combined SQL queries and R code with Excel/Word/PDF outputs and real-time analysis.

Canonical impact is stored under `ACH-REPORTING-TIME-001` in the achievement registry.

### Evidence value

- SQL/R workflow integration
- automated reporting
- Office/PDF delivery
- measurable analyst time savings

## Skills evidenced across this project family

- R
- CRAN package publication
- RStudio add-ins
- statistical modeling
- probability/distribution fitting
- package development
- forecasting
- ensemble methods
- Shiny
- SQL/R reporting automation
- ggplot2 / analytical visualization
- reproducible quantitative research

## Portfolio narrative

A useful interview narrative is:

> My open-source work started from actuarial statistics and R tooling — distribution fitting, data-mining packages and forecasting — and later evolved toward Python ML libraries, cloud inference, data-quality tooling and Generative AI systems.

This is a stronger use of these repositories than presenting each older repository as an isolated current project.

## Usage constraints

- Do not infer current proficiency solely from repository age; current R proficiency is supported elsewhere in `skills.md`.
- Do not present an educational extension as original invention of the underlying published method.
- Do not auto-promote old course/research repositories over stronger recent open-source projects.
