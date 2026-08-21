# Automatic CV generation state

This directory stores **sanitized, versioned generation metadata only**. Generated CV text is intentionally excluded from the public repository and is uploaded as a short-lived GitHub Actions artifact.

`manifest.json` is keyed by canonical `vacancy_id`. A generation fingerprint combines the vacancy semantic hash, the professional retrieval-state fingerprint, the retrieval mode, and the automatic-generation pipeline version.

Terminal states with an unchanged fingerprint are not regenerated automatically. `DEFERRED_CAP` entries are retried on the next eligible vacancy-ingest run. `FAILED_REVIEW_REQUIRED` is not retried automatically unless explicitly requested.

`ready_to_send: true` means the generated candidate passed the full deterministic + Senior Headhunter quality gate. A generated artifact with `COMPLETED_BELOW_TARGET` remains review-only.
