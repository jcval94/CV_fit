---
schema_version: 2
last_updated: 2026-08-20
status: populated
project_id: BBVA-NORA-LLM
organization: BBVA México
project_type: genai_rag_knowledge_assistant
public_safe: true
---

# Internal LLM Tools / NorA

## Executive summary

Internal GenAI knowledge-assistant initiative designed to make complex normative and procedural information easier to retrieve and use without forcing analysts to manually navigate large collections of documentation.

The strongest public project representation is **NorA**, an internal normative AI assistant.

## Business problem

Analysts and collaborators frequently needed answers buried across many manuals, norms and procedural documents. Manual search increased response time and made knowledge access dependent on familiarity with the documentation structure.

## Objective

Create a controlled AI-assisted workflow that retrieves relevant source context and produces useful answers while reducing hallucination risk and preserving human oversight.

## José Carlos's ownership

- identified / shaped the knowledge-access use case
- structured source knowledge for retrieval-oriented usage
- designed prompt and answer-generation workflows
- implemented RAG / controlled-context patterns
- added validation and source constraints
- incorporated human review for sensitive or uncertain outputs
- iterated on usability and operational adoption
- communicated safe-use boundaries to users / stakeholders

## Architectural principles

### Retrieval-grounded answering
Answers should be generated from retrieved internal source context rather than unconstrained model memory.

### Controlled context
The model receives bounded, relevant documentation instead of indiscriminate access to all available text.

### Validation
Generated answers are subject to checks before being treated as reliable operational guidance.

### Human oversight
The system supports analysts rather than silently replacing accountable human decision making.

## Technical themes

- LLM applications
- retrieval-augmented generation (RAG)
- prompt engineering
- knowledge-base design
- grounding
- context management
- hallucination mitigation
- validation / guardrails
- human-in-the-loop review
- internal AI adoption

## Impact

Publicly reusable metrics are registered in `../achievements/metrics.md`:

- `ACH-GENAI-NORA-001` — 200+ collaborators reached
- `ACH-GENAI-NORA-002` — up to 15x faster consultation handling
- `ACH-GENAI-NORA-003` — capacity to absorb up to 13x higher consultation demand

These metrics may be used only with their original qualifiers (`200+`, `up to`).

## Skills evidenced

- GenAI product / use-case design
- RAG
- prompt engineering
- knowledge retrieval
- LLM guardrails
- hallucination mitigation
- human-in-the-loop AI
- AI adoption
- stakeholder enablement

## Approved CV wording

### Standard
> Built an internal RAG-based normative knowledge assistant that grounded LLM responses in controlled source context, incorporated validation and human review, and scaled access to complex procedural knowledge.

### Quantified public variant
> Implemented an AI-powered normative knowledge assistant serving 200+ collaborators and accelerating consultation handling by up to 15x through retrieval-grounded answers, validation and controlled context.

## Usage constraints

- Do not claim foundation-model training or fine-tuning unless a separate source proves it.
- Do not present the assistant as an autonomous compliance decision maker.
- Preserve `up to` qualifiers for speed and demand-capacity metrics.
- Do not expose internal source documents, prompts or normative content.

## Related records

- [BBVA role](../roles/bbva.md)
- [AI-enabled model lifecycle](bbva_ai_model_factory.md)
- [Narrative DNA public GenAI evidence](narrative_dna.md)
- [Validated metrics](../achievements/metrics.md)
