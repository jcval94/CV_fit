---
schema_version: 3
record_id: project-mvp-agent-factory
record_type: project
last_updated: 2026-08-20
status: validated_public
confidence: high
visibility: public
public_safe: true
project_type: agent_architecture_methodology
source_repo: https://github.com/jcval94/mvp-agent-factory
source_refs:
  - SRC-GITHUB-JCVAL94-PUBLIC
---

# mvp-agent-factory

## Summary

`mvp-agent-factory` is a versioned documentation and architecture system for converting vague MVP ideas into development-ready packages for coding agents such as Codex, Claude Code, Cursor or human engineering teams.

Its strongest professional signal is not an end-user app; it demonstrates **agent-system design, scope control, skill contracts, eval design and repeatable AI-assisted software development methodology**.

## Problem addressed

The repository explicitly targets common failure modes in agent-assisted product development:

- unclear target users
- inflated MVP scope
- ambiguous success criteria
- agents without clear boundaries
- non-repeatable prompts
- premature coding before product/architecture decisions

## Canonical workflow

1. capture idea
2. generate structured product/technical documents
3. validate against evals
4. define a small vertical slice
5. build the MVP
6. iterate

## Artifacts generated / designed

- Product Brief
- PRD
- Agent Operating Spec
- Skill Map
- Skill Contracts
- Eval Suite
- Harness Spec
- Project Structure
- Implementation Plan
- Codex / Claude prompts

## Agent skill methodology

Skills are treated as explicit contracts defining:

- activation conditions
- inputs
- outputs
- acceptance criteria
- boundaries / prohibited behavior

This is stronger evidence than merely stating “agentic workflows”: it shows a systematic approach to making agent behavior reusable and reviewable.

## Evaluation methodology

The repo includes:

- rubrics
- checklists
- regression cases
- explicit Definition of Ready
- quality gates before product coding

A documented readiness criterion requires the eval rubric to reach an average score of `4+`; this is a **methodological threshold**, not a measured business KPI.

## Developer tooling

A Python scaffold script can create a minimal new MVP project structure with idea, documentation, eval, skill, example and application directories.

The repo explicitly supports workflows with:

- OpenAI Codex
- Claude Code
- Cursor
- human engineering teams

## Skills evidenced

- agent architecture
- AI-assisted SDLC design
- skill / tool contract design
- evaluation rubric design
- prompt engineering
- requirements engineering
- PRD design
- scope control
- vertical-slice planning
- technical documentation
- software scaffolding
- regression-thinking for agent outputs

## CV positioning

### Agentic AI / AI Engineer

> Designed a reusable agent-development framework with explicit skill contracts, eval rubrics, operating specs and quality gates for converting ambiguous MVP ideas into development-ready vertical slices.

### Technical Leadership / AI Product

> Built a documentation-first methodology for coordinating AI coding agents and human teams around PRDs, architecture decisions, acceptance criteria and regression-oriented evals.

## Usage constraints

- Do not present the repository as a deployed SaaS product.
- The `4+` rubric threshold is a Definition-of-Ready rule, not a measured product outcome.
- Use this project primarily as evidence of agent-system thinking, product/engineering structure and evaluation methodology.
