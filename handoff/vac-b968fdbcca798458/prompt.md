# Final CV review

Act as the final editor before this application is sent.

Your goal is not to regenerate the CV from scratch. Improve the existing proposal into the strongest accurate, credible and concise version for this vacancy.

## Read these first
1. `review_context.json`: why the automated CV did or did not pass, including quality, coverage, gaps and presentation diagnostics.
2. `vacancy.md` / `vacancy.json`: what the employer actually asks for.
3. `cv_proposed.json` and `cv_proposed.html`: the current content and rendered proposal.
4. `match_plan.json`: requirement-level supported / partial / unsupported coverage from the matching stage.
5. `evidence_snapshot.json`: public-safe evidence split into proposal refs and opportunity refs selected by matching, including constraints and claim boundaries.
6. `html_base.html.j2`: the visual/template baseline.
7. `public_identity.yaml`: identity fields that are safe to commit publicly.
8. `cover_letter_proposed.md`, when present, to keep the application narrative consistent.
9. The repository `experience/` evidence only when the snapshot is insufficient or a stronger factual angle is needed.

## Rules
- Use the vacancy to decide what deserves emphasis.
- Use real candidate evidence as the factual boundary.
- Never invent technologies, responsibilities, metrics, employers, titles, dates, achievements or contact details.
- Respect every evidence constraint/boundary in `evidence_snapshot.json`.
- Use `proposal_refs` to verify current claims and `opportunity_refs` to find stronger evidence the automated CV failed to surface.
- Transferable experience may be reframed when the connection is defensible, but never presented as direct experience when it is not.
- Prefer quantified evidence and concrete outcomes over adjectives.
- Remove true-but-distracting material when it weakens the application.
- Treat automated scores as diagnostics, not as instructions to mechanically optimize wording.
- Fix the specific weaknesses in `review_context.json` when evidence allows it; otherwise document the gap rather than hiding it.
- Preserve the base HTML system unless there is a clear usability, ATS, pagination or visual reason to change it.
- Keep the document self-contained, print-safe, Letter sized and ideally no more than two pages.
- Match the language of the vacancy.
- Do not add years of experience to the headline.
- Optimize for a senior recruiter reading the first 10–20 seconds.
- This repository is public. Use only `public_identity.yaml`; never add private email, phone or address to committed artifacts.

## Deliverables
Create:
- `final.html`: the final public-safe, self-contained CV ready to render.
- `review_notes.md`: a concise explanation of the most important changes, remaining gaps, evidence used, and any claim deliberately not made.

The automated quality KPI is advisory. A below-target proposal can still become the strongest honest application.
