# CV_fit ADK application

This package turns a validated canonical vacancy plus eligible professional evidence into a vacancy-specific CV. It does **not** mutate `experience/`, `GPTW/`, or `Vacantes/`.

Google ADK remains the orchestration/runtime framework, but **OpenAI is the only LLM provider** used by this repository. ADK Python reaches OpenAI through its documented LiteLLM connector. The only repository credential is `OPENAI_APY_KEY`; the runtime mirrors it in-process to the conventional `OPENAI_API_KEY` name required by the connector. No Gemini/Google model credential is read or supported.

## Flow

```text
canonical vacancy
      +
rag_state evidence
      ↓
deterministic vacancy↔evidence match
      ↓
CV Strategist (ADK + OpenAI)
      ↓
CV Writer (ADK + OpenAI)
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

Default OpenAI policy:

| Review | Tier | Default model |
|---:|---|---|
| 1 | economy | `gpt-5.6-luna` |
| 2 | economy | `gpt-5.6-luna` |
| 3 | balanced | `gpt-5.6-terra` |
| 4 | balanced | `gpt-5.6-terra` |
| 5 | premium | `gpt-5.6-sol` |

The premium model is used only if the first four reviews fail the quality gate. If an earlier review passes, later calls are skipped.

Model IDs are runtime configuration, but the provider is not: every configured model must remain an OpenAI GPT model.

- `CV_FIT_MODEL_ECONOMY`
- `CV_FIT_MODEL_BALANCED`
- `CV_FIT_MODEL_PREMIUM`
- `CV_FIT_MODEL_STRATEGIST`
- `CV_FIT_MODEL_WRITER`

## Credential contract

The repository secret/environment variable is intentionally named exactly:

```text
OPENAI_APY_KEY
```

Although `OPENAI_API_KEY` is the conventional OpenAI/LiteLLM variable name, repository configuration must use `OPENAI_APY_KEY`. The application copies the value to `OPENAI_API_KEY` only inside the live Python process so ADK's OpenAI connector can authenticate. The secret is never written into generated artifacts.

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
  "best_review_iteration": 3,
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

Install the project, configure `OPENAI_APY_KEY`, and run:

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

A GitHub Actions `workflow_dispatch` entry point is also available. It expects the repository secret `OPENAI_APY_KEY`, rebuilds isolated current state, and uploads the resulting application directory as a workflow artifact rather than committing generated CVs.

Automatic CV generation on every new vacancy is intentionally **not enabled yet**. It should be activated only after live ADK evals demonstrate adequate grounding, hallucination resistance, language quality, and task success.
