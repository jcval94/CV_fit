# CV Editorial Style Contract v1

This contract separates **content judgment** from **resume-writing mechanics** so CV_fit does not spend Senior Headhunter calls detecting deterministic copy defects.

## Canonical resume voice

Employer-facing CV narrative uses **implied first person**.

Good English:
- `Built and deployed ML models that improved contact effectiveness by 6%.`

Avoid:
- `He built and deployed...`
- `I built and deployed...`
- `Responsible for building and deploying...`

Good Spanish:
- `Desarrollé e implementé modelos de ML que incrementaron la efectividad de contacto en 6%.`

Avoid:
- `El candidato desarrolló...`
- `Yo desarrollé...`
- `Responsable del desarrollo...`

The Spanish verb form may encode first person; the rule is to omit the explicit pronoun, not to force infinitive fragments.

## Ownership

| Concern | Primary owner | Deterministic gate | Repair owner | Headhunter role |
| --- | --- | --- | --- | --- |
| Third-person candidate voice | Writer | Yes | Reviser | Do not spend review budget rediscovering it |
| Explicit personal pronouns | Writer | Yes | Reviser | Do not spend review budget rediscovering it |
| Weak responsibility openers | Writer | Yes | Reviser | Judge impact after repair |
| Summary > 70 words | Writer | Yes | Reviser | Judge positioning, not word count |
| Bullet > 38 words | Writer | Yes | Reviser | Judge prioritization, not mechanical length |
| Mixed bullet punctuation | Writer | Yes | Reviser | No special role |
| Repeated leading verbs | Writer | Advisory | Reviser | Judge whether repetition hurts persuasion |
| Strongest evidence first | Strategist | No | Reviser | Judge content priority |
| Narrative redundancy | Writer | Advisory | Reviser | Judge whether repetition weakens the application |
| Keyword stuffing | Strategist | Advisory | Reviser | Judge natural vacancy alignment |
| Stable professional identity | Strategist | Existing editorial gate | Reviser | Judge seniority/fit |
| Factual scope and evidence | Writer | Existing factual gate | Reviser | Never reward unsupported coverage |

## Pipeline

```text
Evidence + vacancy
      |
      v
 Strategist        <- owns story, selection, ordering and gaps
      |
      v
   Writer          <- owns resume voice and first-pass copy
      |
      v
Style preflight    <- deterministic; zero model cost when clean
      |
      +-- PASS ------------------------------+
      |                                      |
      +-- FAIL -> economy Style Reviser -----+
                    |
                    +-> style + factual + language re-validation
      |
      v
Senior Headhunter  <- owns hiring judgment, persuasion and prioritization
      |
      v
General Reviser    <- fixes Headhunter + deterministic validation feedback
      |
      v
Final factual/language/structure/editorial gates
```

The Style Reviser is **conditional**, not a new mandatory agent. A clean Writer output incurs no additional LLM call.

## Hard deterministic rules

The current contract blocks:

1. Third-person candidate references at the beginning of summary/bullets.
2. Explicit first-person pronouns at the beginning of summary/bullets.
3. Weak responsibility/participation bullet openers.
4. Summary above 70 words.
5. Experience/project bullets above 38 words.
6. Mixed terminal-period conventions inside one role/project block.

Hard rules intentionally stay high-confidence. Subjective choices such as verb variety, redundancy, keyword stuffing and content order remain advisory or Headhunter judgment rather than brittle regex blockers.

## Safety of conditional repair

A pre-Headhunter style repair is accepted only when all three checks pass afterwards:

- deterministic resume-style contract;
- factual/evidence validation;
- application-language validation.

If the repair changes factual scope or remains stylistically invalid, generation fails rather than silently sending the changed CV to a Senior Headhunter.

## Testing strategy

Mutation tests intentionally inject:

- English and Spanish third-person voice;
- explicit first person;
- weak responsibility openers;
- overlong summary;
- overlong bullet;
- inconsistent punctuation;
- repeated leading verbs.

The workflow tests also prove that:

- a clean CV does **not** call the Style Reviser;
- a hard style violation invokes the Style Reviser before `senior_headhunter_1`;
- the conditional repair uses the economy model by default;
- repair telemetry is written to `style_preflight.json` and `run_report.json`.
