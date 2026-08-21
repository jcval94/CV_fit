# CV_fit ADK application

This package turns a validated canonical vacancy plus eligible professional evidence into a vacancy-specific CV. It does **not** mutate `experience/`, `GPTW/`, or `Vacantes/`.

## Flow

```text
canonical vacancy
      +
rag_state evidence
      ↓
deterministic vacancy↔evidence match
      ↓
CV Strategist (ADK)
      ↓
CV Writer (ADK)
      ↓
Senior Headhunter review #1
      ↓ if needed
CV Reviser
      ↓
... at most five Headhunter reviews ...
      ↓
factual + language + structure gates
      ↓
cv_final.md + trace + run_report.json
```

The application language is a hard input constraint derived during vacancy normalization. If the language remains `und`, live CV generation is blocked until the source declares it explicitly.

## Five-review limit and model escalation

The review count is hard-capped at five. A sixth review is never hidden behind the workflow.

Default policy:

| Review | Tier | Default model |
|---:|---|---|
| 1 | economy | `gemini-3.5-flash-lite` |
| 2 | economy | `gemini-3.5-flash-lite` |
| 3 | balanced | `gemini-3.6-flash` |
| 4 | balanced | `gemini-3.6-flash` |
| 5 | premium | `gemini-3.1-pro-preview` |

The premium model is used only if the first four reviews fail the quality gate. If an earlier review passes, later calls are skipped.

Model IDs are runtime configuration, not architectural constants:

- `CV_FIT_MODEL_ECONOMY`
- `CV_FIT_MODEL_BALANCED`
- `CV_FIT_MODEL_PREMIUM`
- `CV_FIT_MODEL_STRATEGIST`
- `CV_FIT_MODEL_WRITER`

This is particularly important for the premium default because it is a preview model and should be replaceable without a code change.

## Quality gate

A Headhunter `PASS` alone is insufficient. All of the following are required:

- overall score >= 92
- vacancy alignment >= 90
- evidence strength >= 95
- language quality >= 95
- no blocking Headhunter issues
- factual validator PASS
- language validator PASS
- structure validator PASS

If the fifth review still does not pass, the workflow returns the best **evaluated** CV and records:

```json
{
  "status": "COMPLETED_BELOW_TARGET",
  "quality_target_reached": false,
  "quality_note": "Maximum of 5 Senior Headhunter review iterations reached ..."
}
```

The warning belongs in `run_report.json` and `cv_final.json` metadata, **not** in the CV body sent to the employer.

## Evidence safety

Every substantive CV line carries `evidence_refs`. Deterministic validation rejects or flags:

- unknown or non-selected evidence
- non-public/non-eligible evidence
- quantified claims without approved `ACH-*` evidence
- numerical values not present in the referenced metric
- dropped metric qualifiers such as `up to` / `approximately`
- inflated years-of-experience claims
- unsupported formal people-management claims
- proficiency escalation
- selected unsupported specializations
- wrong application language

The Headhunter can request better framing; it cannot authorize new facts.

## Live run

Install the project and provide Gemini credentials supported by ADK/Google GenAI, then run:

```bash
python -m cv_agent.run \
  --vacancy-id vac-... \
  --vacancy-state vacancy_state \
  --evidence-state rag_state
```

Outputs are local/gitignored under:

```text
outputs/<vacancy_id>/<run_id>/
├── match_plan.json
├── strategy.json
├── drafts/
├── reviews/
├── cv_final.json
├── cv_final.md
├── evidence_trace.json
└── run_report.json
```

A GitHub Actions `workflow_dispatch` entry point is also available. It rebuilds isolated current state and uploads the resulting application directory as a workflow artifact rather than committing generated CVs.

Automatic CV generation on every new vacancy is intentionally **not enabled yet**. It should be activated only after live ADK evals demonstrate adequate grounding, hallucination resistance, language quality, and task success.
