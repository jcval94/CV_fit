# CV presentation, visual QA and Showcase V2

This package is the boundary between the evidence-grounded `CVDocument` and employer-facing HTML/PDF artifacts. It may select or omit already-approved content according to deterministic policy, but it never invents or rewrites candidate claims.

## Current architecture

```text
CVDocument (approved content)
        ↓
Candidate identity resolution
        ↓
CVPresentationModel
        ↓
Deterministic content fitter
        ↓
Page planner
        ↓
Technical Modern / Harvard Executive renderer
        ↓
Chromium physical-layout validator
        ↓
Objective visual-balance evaluator
        ↓
Metric-grounded Presentation Reviewer
        ↓
Application bundle + Showcase V2
```

Evidence references remain attached internally for auditability but are never printed in employer-facing templates.

## Senior editorial hierarchy

Presentation follows the stable content priority introduced by the agent policy:

1. Experience
2. Education
3. Selected Projects
4. Skills
5. Certifications

The fitter keeps Experience and Education authoritative, allows at most two selected projects and at most fifteen skills, keeps explicit GenAI capability, and protects the three mandatory certifications. Lower-priority content is removed before experience bullets when a tighter layout is required.

## Templates

### `technical_modern_v1`

Default primary template. Single-column, ATS-first and US Letter oriented. Verified employer branding is limited to headings, thin rules and small accents. It deliberately avoids dominant sidebars, charts, skill bars, photos and decorative iconography.

### `harvard_v1`

Alternate template. The visual system is locked to black/white Times-family academic styling and ignores employer branding. Its editorial flow still follows Experience -> Education -> Projects -> Skills -> Certifications. It omits the separate Professional Summary section by design.

## Dynamic pagination

The page planner no longer reserves page two for all lower-priority sections. It places the complete professional chronology first, then uses any remaining page-one capacity for Education, Projects, Skills and Certifications before opening page two. Experience items and projects are never split across pages.

## Physical layout validation

Chromium is authoritative for mechanical layout safety. `PhysicalLayoutReport` schema v2 records:

- DOM and PDF page counts;
- Letter page size;
- horizontal/vertical overflow;
- out-of-bounds elements;
- orphan headings;
- vertical utilization per page;
- rendered section areas;
- rendered item counts;
- empty rendered sections.

The PDF is exported only from the same measured HTML artifact.

## Objective visual balance

`visual_evals.py` applies explicit, versionable thresholds after Chromium rendering. It is designed to catch the problems visible in early production screenshots rather than relying on a subjective model opinion.

Current checks include:

- one- and two-page utilization floors;
- minimum Experience area;
- maximum Skills, Projects and Certifications area;
- Experience must visually dominate Skills;
- at most fifteen rendered skills;
- at most two rendered projects;
- minimum professional chronology, education and mandatory-certification counts;
- no empty rendered section.

A visual failure never becomes PASS through an LLM override.

## Presentation Reviewer

The Presentation Reviewer receives only deterministic measurements and factual template topology. It does **not** receive an image and therefore may not speculate about unsupported visual details. A physical or deterministic visual failure bypasses the model and returns `REVIEW_REQUIRED` directly.

For a primary Technical Modern CV, `ready_to_send=true` requires all of the following:

```text
content quality target
cover letter
verified design gate
physical layout PASS
visual balance PASS
presentation reviewer PASS
```

The Harvard alternate is reported independently and does not override a passing primary artifact.

## Showcase V2

The static showcase exposes, per vacancy:

- source fit and deterministic RAG coverage separately;
- Senior Headhunter score;
- factual/editorial/language validation;
- physical, visual and presentation-review status;
- page utilization;
- section-area ratios;
- rendered section counts;
- Technical Modern and Harvard HTML/PDF outputs;
- physical, visual and presentation-review reports;
- concise cover letter.

Human `SEND / REVISE / REJECT` annotations on detail pages are stored only in that browser's `localStorage`. They are not transmitted, committed or published.

## Identity boundary

Public-safe identity fields are `name`, `location`, `linkedin`, `github` and `website`. A public identity YAML may contain only those fields. Email and phone are private opt-in values and are refused for artifacts declared public.

This repository is public, so public automation and the Showcase must never publish private contact details.
