# Final CV review

Act as the final editor before this application is sent.

Your goal is not to regenerate the CV from scratch. Improve the existing proposal into the strongest accurate, credible and concise version for this vacancy.

## Sources of truth
1. `vacancy.md` / `vacancy.json`: what the employer actually asks for.
2. `cv_proposed.json`: the current content proposal.
3. `cv_proposed.html`: the current rendered CV.
4. `html_base.html.j2`: the visual/template baseline.
5. The repository `experience/` evidence: the candidate's factual professional history.

## Rules
- Use the vacancy to decide what deserves emphasis.
- Use real candidate evidence as the factual boundary.
- Never invent technologies, responsibilities, metrics, employers, titles, dates or achievements.
- Transferable experience may be reframed when the connection is defensible, but never presented as direct experience when it is not.
- Prefer quantified evidence and concrete outcomes over adjectives.
- Remove true-but-distracting material when it weakens the application.
- Preserve the base HTML system unless there is a clear usability, ATS, pagination or visual reason to change it.
- Keep the document self-contained, print-safe, Letter sized and ideally no more than two pages.
- Match the language of the vacancy.
- Do not add years of experience to the headline.
- Optimize for a senior recruiter reading the first 10–20 seconds.

## Deliverables
Create:
- `final.html`: the final self-contained CV ready to render and send.
- `review_notes.md`: a concise explanation of the most important changes, remaining gaps and any claim that was deliberately not made.

The automated quality KPI is advisory. A below-target proposal can still become the final sendable CV.
