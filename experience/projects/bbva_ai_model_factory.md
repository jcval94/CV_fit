---
schema_version: 2
last_updated: 2026-08-20
status: populated
project_id: BBVA-AI-MODEL-LIFECYCLE
organization: BBVA México
project_type: genai_mlops_enablement
public_safe: true
---

# BBVA — AI-Enabled Model Lifecycle / Analytical Model Factory

## Executive summary

Governed GenAI / agentic workflow prototypes for accelerating parts of the analytical model lifecycle while preserving structured outputs, validation, testing, documentation and human review.

## Business problem

Data Science delivery includes substantial repeatable work beyond modeling itself: exploration, code scaffolding, testing, documentation, reporting, validation and handoff. Uncontrolled LLM usage can speed up individual tasks but create traceability, reliability and governance risks.

## Objective

Explore how LLM and agentic workflows could accelerate repeatable analytical tasks without bypassing model-quality, documentation or human-control requirements.

## José Carlos's ownership

- identified high-friction stages of the analytical lifecycle suitable for AI assistance
- designed RAG / LLM / agentic workflow patterns
- structured inputs and outputs so generated work could be validated
- used controlled code generation and task decomposition
- incorporated testing / evaluation checks
- preserved human review before acceptance
- connected AI-generated artifacts with documentation and reporting workflows

## Workflow areas

- exploratory support
- controlled code generation
- testing
- documentation
- analytical reporting
- structured output generation
- knowledge retrieval / RAG
- agent-assisted task decomposition

## Reliability principles

- explicit task boundaries
- structured output contracts
- deterministic or programmatic checks where possible
- human review for consequential outputs
- source grounding where knowledge retrieval is involved
- reproducibility and traceability over one-off prompting

## Technical themes

- LLM applications
- agentic workflows
- RAG
- structured outputs
- evaluation / validation
- AI-assisted software development
- model lifecycle automation
- human-in-the-loop systems

## Skills evidenced

- GenAI workflow architecture
- agent design / orchestration patterns
- prompt engineering
- evaluation-driven AI development
- responsible AI implementation
- MLOps / model-lifecycle thinking
- technical workflow automation

## Approved CV wording

> Prototyped governed GenAI and agentic workflows for the analytical model lifecycle, accelerating exploration, controlled code generation, testing, documentation and reporting with structured outputs, evaluation checks and human review.

## Usage constraints

- Do not claim autonomous model development.
- Do not claim a specific orchestration framework unless project evidence confirms it.
- Do not imply that generated code bypassed testing, review or governance.
- This project supports agentic / GenAI workflow experience, not foundation-model training.

## Related records

- [Internal LLM tools / NorA](llm_internal_tools.md)
- [Narrative DNA](narrative_dna.md)
- [MVP Agent Factory](mvp_agent_factory.md)
- [BBVA role](../roles/bbva.md)
