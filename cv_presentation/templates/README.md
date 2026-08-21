# CV HTML template intake

The four v1 templates were normalized from user-supplied HTML prototypes before inclusion. No demo candidate facts from those prototypes are treated as evidence or copied into generated CV content.

| Template | Source prototype | Branding | Letter pagination | Intake changes |
| --- | --- | --- | --- | --- |
| `professional_sidebar_v1` | `cv_.html` | adaptive | 1–2 pages | hard-coded candidate/demo content removed; A4-like canvas normalized to US Letter; CSS tokens parameterized |
| `ai_engineer_sidebar_v1` | `cv_data_scientist_ai_engineer.html` | adaptive | 1–2 pages | hard-coded placeholders removed; Tailwind/Google Fonts/FontAwesome runtime dependencies removed; self-contained CSS |
| `executive_letter_v1` | `cv_data_scientist.html` | adaptive | 1–2 pages | original Letter intent retained; hard-coded page split replaced by deterministic page planning; demo content removed |
| `harvard_v1` | `cv_formato_harvard_ai_engineer.html` | **locked** | 1–2 pages | data object externalized into the shared presentation model; black/white Times-style visual system remains fixed |

## Parameter boundary

Templates receive only a fitted `CVPresentationModel`, localization labels, page plan, and (except Harvard) resolved design tokens. They do not retrieve professional evidence, call an LLM, infer candidate facts, or decide what claims belong in the CV.

## Pagination

All v1 HTML templates render fixed 8.5 × 11 inch US Letter page containers. The deterministic page planner creates one page when the fitted content is within the configured line budget and two pages when it is larger. It never rewrites claim text or splits a single experience item across pages.

This structural planner is a pre-render control. A future browser/PDF layout validator remains the final authority for physical overflow, orphan headings and clipping.

## Branding

Only verified/manual brand profiles may be described as institutional branding. Missing branding produces a neutral fallback. The design-review agent evaluates contrast, legibility, hierarchy, ATS/print safety and permitted usage of supplied tokens; it does not invent brand identity.

Harvard ignores every brand token and design substitution by contract.
