---
schema_version: 3
record_id: project-movilidad-social-mx
record_type: project
status: validated_public_supporting
last_updated: 2026-08-20
confidence: medium
visibility: public
public_safe: true
project_type: analytical_public_app
source_repo: https://github.com/jcval94/movilidad_social_mx
primary_language: Python
source_refs:
  - SRC-GITHUB-JCVAL94-PUBLIC
  - SRC-GITHUB-PROFESSIONAL-CURATED-2026-04-19
---

# Movilidad Social en México

## Summary

A public Streamlit application for exploring social mobility in Mexico through cohort comparisons, transition views, probabilistic classification and interpretable recommendation patterns.

The strongest signal is analytical product design for mixed audiences: the repository explicitly separates value for technical users from clear explanations for the general public.

## Observable capabilities

- modular Streamlit application
- filters and base-versus-subgroup comparisons
- cohort/time evolution views
- probabilistic socioeconomic-class display
- KNN/descriptive-cluster recommendation patterns
- methodological interpretation guidance
- explicit warnings against causal overreach and small-sample conclusions
- public deployment and local setup instructions
- Gemini/OpenAI explanation layer configured through secrets
- container/Kubernetes deployment materials present in the repository

## Data and methods

The README identifies EMOVI 2017 data and describes model/data artifacts used by the application. Results are framed as probabilistic or descriptive rather than causal guarantees.

## Approved public narrative

> Developed a Streamlit experience for exploring social mobility in Mexico, combining cohort analysis, probabilistic classification, interpretable patterns and guidance for technical and non-technical audiences.

## Boundaries

- A public audit marks the repository as a fork; do not attribute the entire codebase as original work without a contribution-level comparison.
- Do not claim policy impact or user/adoption counts.
- Do not treat Docker/Kubernetes files as proof of operating a large production platform.
- Preserve the non-causal interpretation rules stated in the project.
