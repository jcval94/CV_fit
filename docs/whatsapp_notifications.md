# WhatsApp notifications

CV_fit can send a WhatsApp alert **after GitHub Pages has deployed successfully** and only for vacancies whose application bundle has `ready_to_send=true`.

The integration uses Meta WhatsApp Cloud API template messages. This is deliberate: automated business-initiated messages may run outside the 24-hour customer-service window, where a pre-approved template is required.

## Expected template

Default template name: `cv_fit_opportunity_ready`

Default language: `es_MX`

Create and approve a template with **7 body variables in this exact order**:

```text
CV_fit: candidatura lista para revisar.

{{1}} — {{2}}
Fit: {{3}} | Headhunter: {{4}} | RAG: {{5}}

CV: {{6}}
Vacante: {{7}}
```

Variables:

1. Company
2. Role title
3. Source fit
4. Headhunter score
5. RAG coverage
6. Published primary-CV HTML URL
7. Original vacancy/application URL

Template category is intentionally not hard-coded in the repository; use the category Meta approves for the notification use case.

## GitHub configuration

Set these **Actions secrets**:

- `WHATSAPP_ACCESS_TOKEN`: Meta system-user access token with `whatsapp_business_messaging` permission.
- `WHATSAPP_PHONE_NUMBER_ID`: sender Phone Number ID from the WhatsApp Business Platform.
- `WHATSAPP_RECIPIENT`: WhatsApp recipient accepted by Cloud API. Keep it in Secrets; the repository state stores only a one-way hash.

Set these **Actions variables**:

- `WHATSAPP_NOTIFICATIONS_ENABLED=true` to activate delivery. Missing or any other value keeps the integration off.
- `WHATSAPP_TEMPLATE_NAME=cv_fit_opportunity_ready` (optional; this is the default).
- `WHATSAPP_TEMPLATE_LANGUAGE=es_MX` (optional; this is the default).
- `WHATSAPP_GRAPH_VERSION=v23.0` (optional; override when you intentionally move API versions).

Do not store access tokens, sender IDs intended to be private, or recipient numbers in repository files.

## Delivery semantics

1. GitHub Pages deploys successfully.
2. CV_fit reads the deployed `showcase.json` and reserves only `ready_to_send=true` vacancies that have a published primary HTML CV.
3. The reservation is committed to `generation_state/whatsapp_notifications.json` **before** calling Meta.
4. The approved template is sent through `POST /{PHONE_NUMBER_ID}/messages`.
5. The provider message ID and final state are committed afterward.

The fingerprint includes vacancy ID, primary CV SHA-256, original vacancy URL, recipient hash, template name and template language. The same artifact cannot be sent twice by normal reruns. A materially changed CV gets a new fingerprint and can generate a new alert.

States:

- `RESERVED`: delivery was reserved before the API call.
- `SENT`: Meta accepted the request and returned a message ID.
- `FAILED`: a definite send error was recorded.
- `UNKNOWN_DELIVERY`: a network/timeout error occurred and Meta may have accepted the request.

`FAILED` and `UNKNOWN_DELIVERY` are **not automatically retried**. This is an at-most-once bias chosen to prevent duplicate WhatsApp spam. Reconciliation/retry should be explicit.

## Message links

The notification contains two direct links:

- the published primary CV HTML on GitHub Pages;
- the original vacancy/application URL.

The full review page remains available at `.../vacancies/{vacancy_id}/index.html`, and its URL is also persisted in notification state for auditability.
