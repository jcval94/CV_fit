# CV_fit

Fuente de verdad profesional estructurada y sistema incremental para convertir vacantes en CVs personalizados, trazables y verificables sin inventar experiencia.

## Live vacancy showcase

**[Abrir CV_fit Daily Showcase](https://jcval94.github.io/CV_fit/)**

La página pública muestra las vacantes de la corrida diaria, su enlace original, el estado de generación y, cuando pasan los gates correspondientes, previews HTML/PDF del CV institucional y del formato Harvard. Solo usa identidad profesional `public_safe`; datos privados de contacto no se publican en GitHub Pages.

`source fit` y la cobertura determinista del RAG son métricas distintas: la primera proviene de la fuente de discovery y la segunda mide evidencia profesional realmente respaldada.

El repositorio mantiene **dos corpus canónicos separados** y varias capas derivadas:

1. `experience/`: evidencia profesional gobernada y pública.
2. `GPTW/` + `Vacantes/`: entradas de vacantes.
3. `rag_state/`: evidencia profesional normalizada/chunked/indexada para recuperación.
4. `vacancy_state/`: vacantes normalizadas/chunked/indexadas.
5. `cv_matching/`: unión determinista vacante ↔ evidencia.
6. `cv_agent/`: workflow Google ADK para estrategia, redacción, revisión Senior Headhunter y validación final, usando OpenAI como único proveedor LLM.
7. `cv_presentation/`: presentación parametrizada, branding verificado, fitting, HTML, Chromium/PDF y gates físicos.
8. `generation_state/`: estado idempotente de generación automática.

Una vacante nunca se convierte en evidencia sobre el candidato y una opinión previa de fit nunca se trata como hecho de la vacante.

## Evidencia profesional

- `experience/profile.md`: identidad y posicionamiento estables.
- `experience/roles/`: cronología, alcance y progresión profesional.
- `experience/projects/`: problema, contribución personal, implementación, resultados y límites de uso.
- `experience/achievements/metrics.md`: registro único de afirmaciones numéricas `ACH-*`.
- `experience/skills.md`: capacidades con niveles estrictos `core | working | familiarity`.
- `experience/education.md` y `experience/certifications.md`: formación y credenciales.
- `experience/_meta/`: contrato de datos, fuentes, conflictos y preguntas abiertas.
- `rag/`: normalización, semantic chunking, relations e indexación profesional incremental.
- `rag_state/`: estado derivado/versionado de retrieval profesional.

Las métricas se chunkifican de forma atómica por `ACH-*`; los skills conservan su proficiency como metadata y los límites de ownership/uso se propagan a los chunks que puedan alimentar un CV.

La cronología profesional, el fundamento de tenure y la educación forman además un **canonical CV backbone**: siguen estando gobernados por el mismo source of truth, pero no compiten contra proyectos/skills por un top-k semántico. Esto evita que una vacante altamente técnica haga desaparecer fechas, empleadores o instituciones que ya están documentados.

## Vacantes incrementales

- `GPTW/**/*.json` y `Vacantes/**/*.json`: fuentes de entrada.
- `contracts/vacancies/`: schemas versionados de entrada y modelo canónico.
- `vacancy_pipeline/`: validación, adapters, idioma, fidelidad del JD, normalización, deduplicación, chunking, indexación y recuperación.
- `vacancy_state/`: manifiesto, snapshots, registros canónicos, chunks, índice, cuarentena y reportes.
- `.github/workflows/vacancy-ingest.yml`: automatización incremental.

Cada archivo se identifica por SHA-256. Los archivos sin cambios no se reparsan; una modificación solo afecta las vacantes correspondientes. Los archivos inválidos se procesan de forma atómica y pasan a cuarentena.

Canonical Vacancy v2 incluye `application_language` y también una evaluación determinista de fidelidad del Job Description:

- `jd_fidelity`: `full | partial | sparse`
- `jd_fidelity_score`: score transparente de detalle preservado
- `jd_fidelity_reasons`: señales que justifican la clasificación
- `jd_generation_eligible`: solo `true` para `partial` o `full`

Solo `description`, `requirements` y `responsibilities` originales cuentan para fidelidad. El `fit_score`, el razonamiento de ajuste y el `tech_stack` inferido no sustituyen el JD del empleador. Una vacante `sparse` puede seguir usándose para discovery/matching, pero `cv_agent` bloquea generación live antes de gastar tokens.

La inferencia de idioma prioriza idioma explícito, después texto sustantivo de la vacante y finalmente el título. Si queda `und`, la generación automática del CV también se bloquea.

## Vacancy ↔ Evidence matching

`cv_matching/` descompone la vacante en señales estructuradas y busca evidencia profesional elegible. Cada requirement queda clasificado como:

- `strong`
- `partial`
- `weak`
- `unsupported`

`unsupported` es una salida válida y necesaria: el sistema no fabrica experiencia para cerrar gaps. Una skill `familiarity` tampoco puede convertirse en `working`, `core`, expert o advanced solo porque la vacante lo pida.

## Google ADK + OpenAI CV workflow

`cv_agent/` implementa:

```text
canonical vacancy + canonical CV backbone + grounded vacancy-specific evidence
        ↓
JD/language preflight
        ↓
CV Strategist
        ↓
CV Writer
        ↓
Senior Headhunter review
        ↓ if needed
CV Reviser
        ↓
maximum 5 Headhunter reviews
        ↓
deterministic claim/language/structure validation
        ↓
cv_final.md + evidence_trace.json + run_report.json
```

El CV se redacta directamente en `application_language`.

ADK es el framework de orquestación, pero **OpenAI es el único proveedor de modelos permitido**. El único secreto del repositorio para inferencia es `OPENAI_APY_KEY`. Internamente se refleja temporalmente a `OPENAI_API_KEY` porque el conector OpenAI de ADK/LiteLLM espera el nombre convencional; no existe fallback a Gemini, Claude u otro proveedor.

### Cost-aware model escalation

Por defecto:

- revisiones 1–2: `gpt-5.6-luna`
- revisiones 3–4: `gpt-5.6-terra`
- revisión 5: `gpt-5.6-sol`

Los IDs son configurables por variables de entorno, pero el runtime rechaza cualquier ID que no sea un modelo `gpt-*` de OpenAI. El modelo premium solo se llama si las primeras cuatro revisiones no alcanzan el quality gate.

El máximo es exactamente **5 revisiones**. Si la quinta tampoco alcanza la calidad objetivo, se devuelve el mejor CV efectivamente evaluado y `run_report.json` registra `COMPLETED_BELOW_TARGET`, `quality_target_reached=false` y `best_review_iteration`. Esa advertencia no se inserta en el CV destinado al empleador.

### Factual safety

Un `PASS` del Headhunter no basta. Cada línea sustantiva del CV conserva `evidence_refs` y después pasa por validadores deterministas para detectar, entre otras cosas:

- referencias no autorizadas;
- métricas sin `ACH-*` aprobado;
- valores numéricos que no existen en la evidencia;
- pérdida de calificadores como `hasta/up to` o `aproximadamente`;
- inflación de años de experiencia;
- formal people management no respaldado;
- escalamiento de proficiency;
- specializations bloqueadas por boundaries;
- idioma incorrecto.

## Presentación y artifacts

El CV aprobado pasa a una capa separada de presentación. El formato branded de envío usa por defecto `executive_letter_v1`, de lectura lineal y branding institucional verificado; `harvard_v1` se conserva como alternativa visualmente inmutable. Los formatos con sidebar permanecen disponibles como variantes visuales, pero no son el artifact ATS primario.

Chromium valida el layout físico y exporta PDF US Letter. El gate detecta overflow, clipping, headings huérfanos, páginas extra y MediaBox incorrecto. `ready_to_send=true` requiere además cover letter, calidad de contenido y los gates de presentación.

## Automatización y garantías E2E

- `.github/workflows/validate-experience.yml`: integridad general del source of truth y tests.
- `.github/workflows/evidence-rag.yml`: estado profesional RAG incremental.
- `.github/workflows/vacancy-ingest.yml`: estado de vacantes, generación automática y application bundles.
- `.github/workflows/cv-agent.yml`: validación determinista del agente tanto en PR como después del merge a `main`.
- `.github/workflows/daily-showcase-pages.yml`: despliegue del artifact público a GitHub Pages.

Los workflows de vacantes y evidencia realizan una segunda corrida inmediata después de su procesamiento y exigen un no-op real: cero fuentes nuevas/modificadas, cero registros/vacantes impactados y cero reindexaciones. La idempotencia queda así validada E2E, no solo por unit tests.

La generación automática usa `OPENAI_APY_KEY`, mantiene un fingerprint de vacante + RAG + versión lógica del generador y solo vuelve a gastar cuando cambia un insumo relevante o cuando una nueva versión lógica requiere una regeneración controlada. Los CVs/HTML/PDF se publican como artifacts temporales; el repositorio solo persiste metadata sanitizada.

## Validación local

```bash
python tools/validate_experience.py
python -m unittest discover -s tests -p 'test_*.py'
python -m rag.normalize --repo . --check
python -m rag.evidence --repo . --state-dir /tmp/rag_state --run-id validation --full-rebuild
python -m vacancy_pipeline --repo . --state-dir /tmp/vacancy_state --run-id validation --full-rebuild --fail-on-quarantine
```

Para una ejecución ADK real, la vacante debe ser `jd_generation_eligible=true`:

```bash
python -m pip install -e .
python -m cv_agent.run \
  --vacancy-id vac-... \
  --vacancy-state vacancy_state \
  --evidence-state rag_state
```

Los outputs live se guardan bajo `outputs/` y están excluidos de Git.
