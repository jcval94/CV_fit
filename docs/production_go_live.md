# CV_fit production operating contract

## Daily path

New vacancy JSON files may arrive every day under `GPTW/**` and `Vacantes/**`.

The production path is:

```text
new daily JSON
  -> validate source envelope
  -> attempt employer-JD enrichment when original JD is sparse
  -> canonicalize + deduplicate
  -> JD fidelity gate
  -> RAG / evidence match
  -> CV generation + Headhunter review
  -> grounded cover letter
  -> Technical Modern + Harvard presentation gates
  -> GitHub Pages review feed
  -> WhatsApp only when ready_to_send=true and notifications are enabled
```

## Employer JD enrichment

`Auto-enrich daily vacancy JDs` runs on new/changed JSON files in `main`.

It never rewrites the incoming daily file. For a sparse vacancy with a specific application URL, it attempts to retrieve employer-authored `JobPosting` JSON-LD and writes a deterministic derived file under:

- `GPTW/enriched/auto/`
- `Vacantes/enriched/auto/`

The original role/company must match the retrieved JobPosting. If the page cannot be fetched, is a generic careers landing page, blocks automation, or does not expose a matching JobPosting, the vacancy remains `sparse` and CV generation stays blocked. Source-fit text and inferred stack are never promoted into employer requirements.

The enrichment commit intentionally triggers the normal vacancy-ingest workflow again, so the derived JD is incorporated using the existing canonical deduplication path.

## Daily priority and recoverable failures

Fresh vacancies from the current ingest always get generation capacity before prior failures.

After today's candidates are planned, CV_fit may use remaining capacity for up to three prior `FAILED_REVIEW_REQUIRED` entries only when the recorded error is clearly recoverable, including:

- provider quota / credit balance exhaustion;
- HTTP 429 / rate limiting;
- timeouts or connection failures;
- temporary provider unavailability;
- HTTP 502/503/504 style provider failures.

Unknown, schema, grounding, quality or deterministic failures do not enter the automatic retry pool. They still require an explicit retry or code/data correction.

This recovery behavior is controlled by:

- `CVFIT_AUTO_RECOVER_TRANSIENT=true` (default)
- `CVFIT_MAX_RECOVERY_CANDIDATES=3` (default)

## New employers and presentation

A company-specific brand YAML is an enhancement, not a prerequisite.

If a verified profile exists, Technical Modern uses the verified tokens. If no profile exists, the existing neutral ATS-safe fallback is used with `brand_verified=false`. Deterministic contrast, ATS, print, physical-layout, visual-balance and presentation-review gates still apply.

No unverified fallback is described as official employer branding.

## Production canary

Before enabling outbound WhatsApp, run `Production readiness canary` manually from GitHub Actions.

The canary:

1. rebuilds isolated vacancy and professional-evidence states;
2. requires the live `OPENAI_APY_KEY` secret;
3. runs one real vacancy through CV generation and the Headhunter loop;
4. generates the grounded cover letter;
5. builds HTML/PDF Technical Modern and Harvard bundles;
6. runs physical, visual and presentation gates;
7. records process outcomes separately from semantic stage outcomes;
8. requires the expected final artifacts before `canary_healthy=true`;
9. records stage costs and the final ready/review state;
10. never sends WhatsApp.

The production canary is `workflow_dispatch` only. Do **not** use an issue, pull request or other public event to trigger a paid readiness run.

Run it from:

```text
GitHub -> Actions -> Production readiness canary -> Run workflow
```

A successful infrastructure/readiness result requires `canary_healthy=true`. A shell command that exits successfully is not enough if generation, cover or presentation has a failed semantic status.

The historical `live-canary-once.yml` Konfío workflow is retained only as a manual diagnostic path and is not the recommended production-readiness entrypoint.

## WhatsApp go-live

WhatsApp remains feature-flagged with `WHATSAPP_NOTIFICATIONS_ENABLED`.

Only enable it after:

- the production canary succeeds with live OpenAI billing;
- Meta secrets are present;
- the approved template matches the documented seven variables;
- the first reservation plan has been inspected so existing READY CVs do not create an unexpected notification burst.

`ACCEPTED` means Meta accepted the API request. It does not mean handset delivery. `DELIVERED`/`READ` require webhook status events and remain outside the current at-most-once notification contract.
