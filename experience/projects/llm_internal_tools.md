---
schema_version: 3
record_id: project-bbva-llm-internal-tools
record_type: project
status: canonical
last_updated: 2026-08-20
confidence: high
visibility: public
public_safe: true
organization: BBVA México
period: 2023-present
source_refs:
  - SRC-USER-CONFIRMED-2026-08-20
  - SRC-LINKEDIN-PUBLIC
  - SRC-PORTFOLIO-PUBLIC-2026-08
  - SRC-TRAJECTORY-2021-2023-CURATED
  - SRC-TRAJECTORY-2024-2026-CURATED
---

# Internal LLM and Normative Knowledge Tools

## Summary

This project family covers the design, curation, evaluation and impact measurement of LLM-assisted tools that make internal knowledge easier to use in regulated workflows. The strongest documented case is **NorA**, a normative knowledge assistant for risk/operational users.

## Business problem

Internal normative questions required experts to search across many documents, producing slow and inconsistent response times. The challenge was not only answering with an LLM; it was curating the corpus, preventing semantic contamination, defining safe usage and proving operational value.

## NorA contribution

Evidence supports:

- curation and segregation of document corpora by domain/portfolio
- design of use cases and prompts for grounded normative questions
- operational follow-up and adoption analysis
- conversion of usage telemetry into time, capacity and FTE/ROI narratives
- definition of KPIs for reach, response speed and demand handling
- communication of results to management
- support for user enablement and responsible adoption

## Technologies and patterns

- NotebookLM
- Google Gemini
- ChatGPT / OpenAI-enabled workflows
- retrieval-grounded / RAG-style knowledge use
- source-constrained answering
- prompt engineering
- corpus curation and document segregation
- telemetry and KPI analysis
- Google Workspace and Apps Script
- structured workflows and human review

The exact vector database, embedding architecture and automated ingestion stack are not confirmed and must not be invented.

## Public outcomes

Canonical public metrics live in [the achievement registry](../achievements/metrics.md):

- `ACH-GENAI-NORA-001`: collaborator reach
- `ACH-GENAI-NORA-002`: consultation-handling speed
- `ACH-GENAI-NORA-003`: demand-capacity scaling

## Related GenAI work

- business-facing Streamlit prototype for recommendation/communication strategy
- process and state architecture for regulatory workflows using Gemini and Google Workspace
- participation in a technical GenAI community/champion program
- training, cases and practical guidance for NotebookLM, Gemini and ChatGPT
- exploration of AI-assisted code refactoring with deterministic formatting tools

These related items are not all equivalent to production deployment.

## Approved public narratives

> Curated and measured the impact of an AI-powered normative assistant, translating usage telemetry into reach, speed and capacity KPIs.

> Designed grounded knowledge workflows, corpus-segregation rules and adoption KPIs for GenAI use in a regulated environment.

## Boundaries

- Do not attribute fraud-detection rate improvements to NorA.
- Do not claim foundation-model training, fine-tuning or vector-database ownership.
- Preserve qualifiers such as `up to`.
- Treat prototypes, approved designs and deployed assistants as separate lifecycle states.
