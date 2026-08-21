# CV presentation contract and content fitting

This package is the boundary between the evidence-grounded `CVDocument` and future HTML/PDF rendering.

It intentionally does **not** render HTML, CSS or PDF. The next rendering layer should consume the fitted `CVPresentationModel` instead of reading agent output directly.

## Architecture

```text
CVDocument (approved content)
        ↓
Candidate Identity resolution
        ↓
CVPresentationModel
        ↓
Deterministic Content Fitter
        ↓
fitted_presentation.json + fit_report.json
        ↓
[future] HTML template / PDF / layout validator
```

The presentation layer never changes factual claims. Evidence references remain attached internally for auditability, even though a future employer-facing template should not display them.

## Identity boundary

Public-safe identity fields are:

- `name`
- `location`
- `linkedin`
- `github`
- `website`

A public identity YAML may contain only those fields. `email` and `phone` are rejected if they are placed in that file.

Environment variables:

- `CV_IDENTITY_NAME`
- `CV_IDENTITY_LOCATION`
- `CV_IDENTITY_LINKEDIN`
- `CV_IDENTITY_GITHUB`
- `CV_IDENTITY_WEBSITE`
- `CV_IDENTITY_EMAIL`
- `CV_IDENTITY_PHONE`

Private contact is opt-in. By default the resolver refuses to put private contact into an artifact declared `public`. This is important because this repository itself is public; private contact should eventually be rendered through a private/local delivery path rather than committed or exposed through public automation artifacts.

## Presentation contract

`presentation.default.yaml` reserves the initial delivery target:

- Letter page size
- target maximum of 2 pages
- one-column ATS-oriented future template id `ats_classic_v1`
- summary and experience always present
- projects and certifications optional/auto
- deterministic content-density limits

The template id is only a contract in this stage. There is no HTML template yet.

## Content fitting

The fitter assumes the agent returns bullets/projects/skills/certifications in descending vacancy relevance. It then:

1. applies configured hard caps;
2. removes disabled sections;
3. estimates pre-render line usage;
4. if needed, removes optional content in this order: certifications, project detail/projects, optional skills, then lower-priority experience bullets;
5. never removes an experience role and never reduces a role below `min_role_bullets`;
6. never truncates or rewrites claim text.

If the content still exceeds the estimated budget, or the summary is longer than the configured limit, the result is `NEEDS_REVISION`. Rewriting must happen upstream because presentation fitting is not allowed to invent or mutate claims.

The line estimator is deliberately a heuristic. The future HTML/PDF layout validator will be authoritative for actual physical page count, overflow and clipping.

## CLI

```bash
python -m cv_presentation \
  --cv outputs/<vacancy>/<run>/cv_final.json \
  --config cv_presentation/presentation.default.yaml \
  --identity-public /path/to/public_identity.yaml \
  --output outputs/<vacancy>/<run>/presentation.json \
  --fit-report outputs/<vacancy>/<run>/fit_report.json
```

For a private render path, contact can be injected from environment variables with `--include-private-contact --artifact-visibility private`.
