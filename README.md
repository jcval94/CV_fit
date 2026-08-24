# CV_fit

Sistema incremental, trazable y evidence-grounded para convertir vacantes en CVs personalizados **sin inventar experiencia**.

CV_fit combina una fuente de verdad profesional gobernada, ingestión incremental de vacantes, Retrieval/RAG, matching determinista, un workflow de generación y revisión con Google ADK + OpenAI, validación factual, presentación HTML/PDF, observabilidad, control de costos y publicación de resultados en GitHub Pages.

> **Principio rector:** una vacante puede pedir cualquier cosa; el CV solo puede afirmar lo que esté respaldado por evidencia profesional autorizada.

## Índice

- [Qué hace el sistema](#qué-hace-el-sistema)
- [Showcase público](#showcase-público)
- [Invariantes de diseño](#invariantes-de-diseño)
- [Arquitectura](#arquitectura)
- [Mapa del repositorio](#mapa-del-repositorio)
- [Flujo E2E diario](#flujo-e2e-diario)
- [Instalación local](#instalación-local)
- [Configuración, secretos y variables](#configuración-secretos-y-variables)
- [Fuente de verdad profesional](#fuente-de-verdad-profesional)
- [Vacantes: entrada, validación y enriquecimiento](#vacantes-entrada-validación-y-enriquecimiento)
- [Retrieval y matching](#retrieval-y-matching)
- [Generación del CV](#generación-del-cv)
- [Cover letter](#cover-letter)
- [Presentación HTML/PDF](#presentación-htmlpdf)
- [Automatización incremental](#automatización-incremental)
- [Idempotencia y reintentos](#idempotencia-y-reintentos)
- [Observabilidad y artifacts](#observabilidad-y-artifacts)
- [GitHub Actions](#github-actions)
- [Production canary](#production-canary)
- [GitHub Pages](#github-pages)
- [WhatsApp](#whatsapp)
- [Costos y política de modelos](#costos-y-política-de-modelos)
- [Validación y tests](#validación-y-tests)
- [Troubleshooting](#troubleshooting)
- [Procedimiento seguro de cambio y release](#procedimiento-seguro-de-cambio-y-release)
- [Definition of Done](#definition-of-done)
- [Límites deliberados](#límites-deliberados)

---

## Qué hace el sistema

A alto nivel:

```text
experiencia profesional gobernada
            +
      vacante nueva JSON
            ↓
validación + normalización + deduplicación
            ↓
       JD fidelity gate
            ↓
 professional Retrieval / RAG
            ↓
 vacancy ↔ evidence matching
            ↓
   CV Strategist / Writer
            ↓
   Senior Headhunter review
            ↓
 deterministic factual gates
            ↓
 grounded cover letter
            ↓
 Technical Modern + Harvard
            ↓
 HTML + Chromium/PDF + QA
            ↓
 GitHub Pages review feed
            ↓
 optional WhatsApp notification
```

El repositorio no es solo un generador de texto. Está diseñado para preservar cuatro propiedades durante todo el flujo:

1. **Grounding:** todo claim sustantivo debe estar respaldado.
2. **Trazabilidad:** debe poder rastrearse desde el CV hasta la evidencia original.
3. **Idempotencia:** una misma entrada sin cambios no debe volver a generar trabajo/costo innecesario.
4. **Fail closed:** cuando falta evidencia, el JD es insuficiente o un gate falla, el sistema debe bloquear o marcar revisión en lugar de rellenar huecos creativamente.

---

## Showcase público

**[Abrir CV_fit Daily Showcase](https://jcval94.github.io/CV_fit/)**

La página pública permite revisar las vacantes procesadas, sus enlaces originales y el estado de generación. Cuando una candidatura pasa los gates correspondientes, puede mostrar previews HTML/PDF del CV principal y del formato Harvard.

Reglas de publicación:

- solo se utiliza identidad `public_safe`;
- los secretos y datos privados no deben publicarse en Pages;
- `source fit` y cobertura RAG son métricas diferentes;
- un CV no se considera listo solo porque exista un archivo PDF;
- `ready_to_send=true` depende de contenido, grounding y presentación.

---

## Invariantes de diseño

Estas reglas deben mantenerse aunque cambie la implementación:

### 1. Las vacantes no son evidencia profesional

`GPTW/` y `Vacantes/` describen oportunidades. Nunca deben convertirse en claims sobre el candidato.

### 2. Source fit no es RAG coverage

- **Source fit:** señal que viene del proceso de discovery/origen de la vacante.
- **RAG coverage:** cuánto de lo que pide la vacante puede respaldarse realmente con evidencia profesional recuperada.

No deben mezclarse ni utilizarse uno como sustituto del otro.

### 3. `unsupported` es una salida válida

Si un requirement no tiene evidencia suficiente, se conserva como gap. El sistema no debe inventar experiencia para mejorar artificialmente el ajuste.

### 4. La proficiency no puede inflarse

Una skill `familiarity` no puede convertirse en `working`, `core`, `advanced` o `expert` porque una vacante lo solicite.

### 5. El source of truth no se retroalimenta desde un CV generado

```text
SOURCE OF TRUTH
      ↓
retrieval
      ↓
derived CV
```

Nunca:

```text
generated CV
      ↓
SOURCE OF TRUTH
```

### 6. Los artifacts públicos son derivados

HTML, PDF, cover letters, previews y showcase son resultados derivados. La evidencia profesional gobernada sigue siendo la fuente de verdad.

---

## Arquitectura

CV_fit mantiene dos corpus canónicos separados y varias capas derivadas.

```text
experience/                     GPTW/ + Vacantes/
    │                                  │
    ▼                                  ▼
rag/                             vacancy_pipeline/
    │                                  │
    ▼                                  ▼
rag_state/                       vacancy_state/
    └──────────────┬───────────────────┘
                   ▼
              cv_matching/
                   ▼
               cv_agent/
                   ▼
                cv_auto/
                   ▼
            cv_presentation/
                   ▼
       outputs/ + generation_state/
                   ▼
          GitHub Pages / WhatsApp
```

### Separación de responsabilidades

- **RAG recupera hechos.**
- **Matching decide qué evidencia cubre qué requirement.**
- **Writer redacta.**
- **Senior Headhunter juzga calidad y ajuste.**
- **Validadores deterministas verifican claims.**
- **Presentation transforma el contenido aprobado en artifacts de envío.**
- **Observability registra qué ocurrió, cuánto costó y por qué falló o pasó.**

---

## Mapa del repositorio

| Ruta | Responsabilidad |
|---|---|
| `experience/` | Fuente de verdad profesional gobernada |
| `experience/_meta/` | Contratos, fuentes, conflictos y preguntas abiertas |
| `GPTW/` | Vacantes provenientes del canal GPTW |
| `Vacantes/` | Vacantes provenientes de otros canales |
| `contracts/vacancies/` | Schemas versionados del input y modelo canónico |
| `vacancy_pipeline/` | Validación, normalización, dedupe, fidelity, chunking, indexing y retrieval de vacantes |
| `vacancy_state/` | Estado derivado/versionado de vacantes |
| `rag/` | Normalización, chunking e indexación de evidencia profesional |
| `rag_state/` | Estado derivado/versionado del Retrieval profesional |
| `cv_matching/` | Matching requirement ↔ evidencia |
| `cv_agent/` | ADK workflow, policy, revisión, factual validation y cover letters |
| `cv_auto/` | Orquestación automática/idempotente de generación por lotes |
| `cv_presentation/` | Templates, branding, HTML, PDF, visual QA y showcase |
| `cv_observability/` | Eventos, stage reports, pipeline summary y diagnósticos |
| `cv_notifications/` | Integración opcional de notificaciones |
| `generation_state/` | Fingerprints y estado idempotente de generación/notificación |
| `outputs/` | Artifacts live locales/CI; no es source of truth |
| `evals/` | Evaluaciones y datasets de calidad |
| `docs/` | Runbooks especializados |
| `.github/workflows/` | CI/CD, ingest, canaries, Pages y experimentos controlados |

---

## Flujo E2E diario

Cuando entra una vacante nueva o cambia una existente:

```text
1. JSON llega a GPTW/** o Vacantes/**
2. GitHub detecta el cambio
3. vacancy_pipeline valida el envelope
4. se calcula SHA-256 del source
5. se normaliza al Canonical Vacancy
6. se deduplica contra el estado actual
7. se calcula idioma + JD fidelity
8. sparse => no genera CV live
9. full/partial => puede continuar
10. Retrieval recupera evidencia profesional
11. matching clasifica coverage por requirement
12. cv_auto decide si hace falta generar/regenerar
13. ADK genera y revisa el CV
14. validadores deterministas verifican claims
15. se genera cover letter grounded
16. se construyen HTML/PDF
17. pasan gates físicos/visuales
18. se escribe observabilidad E2E
19. se construye el Daily Showcase
20. se persiste solo el estado versionable/sanitizado
21. Pages publica el resultado
22. WhatsApp puede notificar únicamente si está habilitado y ready_to_send=true
```

---

## Instalación local

### Requisitos

- Python **>= 3.11**. CI usa Python 3.12.
- Git.
- Chromium vía Playwright para validación/render de PDF.
- Credencial OpenAI únicamente para pasos live.

### Setup recomendado

```bash
git clone https://github.com/jcval94/CV_fit.git
cd CV_fit

python -m venv .venv
source .venv/bin/activate       # Linux/macOS
# .venv\Scripts\activate        # Windows

python -m pip install --upgrade pip
python -m pip install -e .
python -m playwright install --with-deps chromium
```

Dependencias principales declaradas en `pyproject.toml`:

- Google ADK
- Jinja2
- LiteLLM
- OpenAI SDK
- Playwright
- Pydantic
- PyPDF
- PyYAML

### Smoke test inicial

```bash
python tools/validate_experience.py
python -m unittest discover -s tests -p 'test_*.py'
python -m rag.normalize --repo . --check
```

No se requiere una API key para las validaciones deterministas.

---

## Configuración, secretos y variables

### OpenAI

El repositorio utiliza como **Actions secret canónico**:

```text
OPENAI_APY_KEY
```

El nombre conserva deliberadamente `APY` porque ése es el contrato actual del repositorio. El runtime puede reflejarlo internamente a `OPENAI_API_KEY` cuando una librería externa exige el nombre convencional.

No deben añadirse fallbacks silenciosos a otros proveedores.

### Modelos

Variables opcionales:

```text
CV_FIT_MODEL_ECONOMY
CV_FIT_MODEL_BALANCED
CV_FIT_MODEL_PREMIUM
```

Defaults actuales:

```text
economy  = gpt-5.6-luna
balanced = gpt-5.6-terra
premium  = gpt-5.6-sol
```

El runtime valida que el modelo pertenezca a la familia OpenAI permitida.

### Observabilidad

Variables utilizadas por workflows:

```text
CVFIT_EVENT_LOG
CVFIT_RUN_ID
```

Los eventos generados para artifacts de CI deben permanecer redacted/sanitized.

### Recuperación automática

El comportamiento de recuperación de fallos transitorios puede controlarse con:

```text
CVFIT_AUTO_RECOVER_TRANSIENT=true
CVFIT_MAX_RECOVERY_CANDIDATES=3
```

No se deben usar reintentos automáticos para errores de grounding, schema, lógica o calidad determinista.

### WhatsApp

Secrets:

```text
WHATSAPP_ACCESS_TOKEN
WHATSAPP_PHONE_NUMBER_ID
WHATSAPP_RECIPIENT
```

Variables:

```text
WHATSAPP_NOTIFICATIONS_ENABLED
WHATSAPP_TEMPLATE_NAME
WHATSAPP_TEMPLATE_LANGUAGE
WHATSAPP_GRAPH_VERSION
```

La integración debe permanecer deshabilitada hasta completar el go-live descrito más adelante.

---

## Fuente de verdad profesional

La evidencia profesional vive en `experience/`.

### Estructura

- `experience/profile.md`: identidad y posicionamiento estables.
- `experience/roles/`: cronología, scope y progresión.
- `experience/projects/`: problema, ownership, implementación, resultados y límites.
- `experience/achievements/metrics.md`: claims numéricos gobernados por IDs `ACH-*`.
- `experience/skills.md`: proficiency `core | working | familiarity`.
- `experience/education.md`: formación.
- `experience/certifications.md`: credenciales.
- `experience/_meta/`: contrato, provenance, conflictos y preguntas abiertas.

### Reglas de mantenimiento

Antes de añadir una afirmación profesional:

1. debe existir una fuente o fundamento identificable;
2. una métrica debe mantener su unidad, alcance y calificadores;
3. no se deben duplicar dos claims incompatibles sobre el mismo hecho;
4. los límites de ownership deben conservarse;
5. una reformulación estilística no debe convertirse en un hecho nuevo.

### Canonical CV backbone

Cronología, empleadores, educación y otros elementos estructurales no compiten contra proyectos/skills en un top-k semántico. Se incorporan como backbone canónico para evitar que una vacante técnica haga desaparecer información profesional básica ya documentada.

### Validar el source of truth

```bash
python tools/validate_experience.py
python -m rag.normalize --repo . --check
```

Construcción completa del estado profesional:

```bash
python -m rag.evidence \
  --repo . \
  --state-dir /tmp/rag_state \
  --run-id local-rag \
  --full-rebuild
```

---

## Vacantes: entrada, validación y enriquecimiento

### Dónde colocar una vacante

Los inputs canónicos entran en:

```text
GPTW/**/*.json
Vacantes/**/*.json
```

Respeta el schema versionado de `contracts/vacancies/`. No adaptes el pipeline a mano para un JSON mal formado si el source puede corregirse de forma determinista.

### Qué ocurre al ingerir

Cada source se identifica por SHA-256.

- source nuevo → se procesa;
- source modificado → se reprocesan solo las vacantes impactadas;
- source sin cambios → no-op;
- source inválido → cuarentena;
- modificación que no cambia una vacante canónica → no debe provocar generación innecesaria.

### Ingest local completo

```bash
python -m vacancy_pipeline \
  --repo . \
  --state-dir /tmp/vacancy_state \
  --run-id local-validation \
  --full-rebuild \
  --fail-on-quarantine
```

### Probar idempotencia

Ejecuta inmediatamente una segunda vez sobre el mismo estado:

```bash
python -m vacancy_pipeline \
  --repo . \
  --state-dir /tmp/vacancy_state \
  --run-id local-validation-noop \
  --fail-on-quarantine
```

El resultado esperado es:

```text
new = 0
modified = 0
impacted = 0
reindexed = 0
```

### Retrieval smoke test de vacantes

```bash
python -m vacancy_pipeline.retrieve \
  "machine learning" \
  --state-dir /tmp/vacancy_state \
  --top-k 3
```

### JD fidelity

Canonical Vacancy v2 expone:

```text
jd_fidelity: full | partial | sparse
jd_fidelity_score
jd_fidelity_reasons
jd_generation_eligible
application_language
```

Solo contenido real de JD como `description`, `requirements` y `responsibilities` cuenta para fidelity. `fit_score`, razonamiento de ajuste o tech stack inferido no pueden utilizarse para fabricar un JD.

Regla de generación:

```text
full/partial + idioma resuelto => puede ser elegible
sparse o application_language=und => generación live bloqueada
```

### Employer JD enrichment

`.github/workflows/auto-enrich-jd.yml` intenta enriquecer vacantes sparse cuando existe una URL suficientemente específica y puede recuperar un `JobPosting` verificable.

El proceso:

- no reescribe el JSON diario original;
- escribe derivados en `GPTW/enriched/auto/` o `Vacantes/enriched/auto/`;
- exige coincidencia razonable de rol/empresa;
- falla de forma segura si la página bloquea automatización, es genérica o no expone un JobPosting confiable;
- deja la vacante como `sparse` si no puede demostrarse fidelidad.

---

## Retrieval y matching

### Professional Retrieval

`rag/` transforma la evidencia profesional en unidades recuperables y trazables.

Propiedades importantes:

- métricas `ACH-*` se mantienen atómicas;
- proficiency viaja como metadata;
- boundaries de ownership/uso se propagan;
- el estado derivado queda en `rag_state/`;
- Retrieval no tiene permiso para convertir una inferencia en evidencia.

### Vacancy ↔ Evidence matching

`cv_matching/` descompone requirements y clasifica la cobertura como:

```text
strong
partial
weak
unsupported
```

La cobertura determinista es una señal de grounding. No es equivalente al fit original de la vacante.

### Retrieval V2

El production canary valida que el estado de Retrieval contenga, entre otros, los artifacts requeridos:

```text
manifest.json
lexical_index.json
dense_index.json
relations.json
```

Una ausencia de estos artifacts debe tratarse como estado incompleto, no como una búsqueda vacía válida.

---

## Generación del CV

### Pipeline conceptual

```text
canonical vacancy
+ canonical CV backbone
+ grounded vacancy-specific evidence
        ↓
JD/language preflight
        ↓
CV Strategist
        ↓
CV Writer
        ↓
Senior Headhunter
        ↓
CV Reviser, si hace falta
        ↓
máximo 5 reviews
        ↓
deterministic validators
        ↓
cv_final + evidence trace + run report
```

### Ejecución live manual

Primero construye estados aislados:

```bash
python -m vacancy_pipeline \
  --repo . \
  --state-dir /tmp/vacancy_state \
  --run-id manual-live \
  --full-rebuild \
  --fail-on-quarantine

python -m rag.evidence \
  --repo . \
  --state-dir /tmp/rag_state \
  --run-id manual-live \
  --full-rebuild
```

Después:

```bash
export OPENAI_APY_KEY="..."

python -m cv_agent.run \
  --vacancy-id vac-... \
  --vacancy-state /tmp/vacancy_state \
  --evidence-state /tmp/rag_state \
  --outputs outputs \
  --run-id manual-live
```

No ejecutes una generación live para una vacante con `jd_generation_eligible=false`.

### Headhunter loop

Máximo exacto: **5 reviews**.

Policy default:

```text
reviews 1-2 → economy
reviews 3-4 → balanced
review 5     → premium
```

Si la quinta review no alcanza el target, el sistema debe devolver el mejor candidato realmente evaluado y registrar:

```text
COMPLETED_BELOW_TARGET
quality_target_reached=false
best_review_iteration=<n>
```

No se debe insertar una advertencia interna en el CV que verá el empleador.

### Factual safety

Un PASS del Headhunter no sustituye los validadores.

Los gates deterministas deben detectar, entre otros:

- evidence refs inexistentes/no autorizados;
- métricas no aprobadas;
- números que no aparecen en evidencia;
- pérdida de calificadores como `hasta`, `up to` o `aproximadamente`;
- inflación de tenure;
- people management no respaldado;
- escalation de proficiency;
- specializations bloqueadas por boundaries;
- idioma incorrecto.

---

## Cover letter

La cover letter es un artifact derivado del mismo contexto grounded. No debe introducir logros o experiencia que no exista en la evidencia autorizada.

Batch automático:

```bash
python -m cv_agent.cover_letter_batch \
  --batch-report outputs/auto/_batch/<run-id>/generation_run_report.json \
  --outputs outputs/auto \
  --vacancy-state vacancy_state
```

El workflow productivo aplica además un budget explícito de costo.

---

## Presentación HTML/PDF

La capa de presentación está separada de la generación de contenido.

### Formatos

- `Technical Modern`: artifact principal/branded.
- `Harvard`: alternativa deliberadamente estable.

Un brand profile específico es una mejora, no un requisito. Si no existe un perfil verificado, se utiliza un fallback neutral ATS-safe con `brand_verified=false`.

Nunca describas branding no verificado como branding oficial del empleador.

### Batch bundle

```bash
python -m cv_presentation.batch_bundle \
  --batch-report outputs/auto/_batch/<run-id>/generation_run_report.json \
  --outputs outputs/auto \
  --vacancy-state vacancy_state \
  --generation-state generation_state \
  --identity-public cv_presentation/identity.public.yaml \
  --brand-profiles-dir cv_presentation/brands
```

### Qué valida Chromium

- US Letter / MediaBox correcto;
- overflow;
- clipping;
- headings huérfanos;
- páginas extra inesperadas;
- balance visual;
- legibilidad física del layout.

`ready_to_send=true` requiere más que un render exitoso: también depende de los gates de contenido y del bundle completo.

---

## Automatización incremental

El workflow central es `.github/workflows/vacancy-ingest.yml`.

En `main`:

1. sincroniza el commit más reciente;
2. ingiere incrementalmente;
3. captura vacantes impactadas;
4. repite ingest para demostrar no-op idempotente;
5. ejecuta un retrieval smoke test;
6. instala la capa de generación/presentación;
7. genera CVs para cambios elegibles o lógica obsoleta;
8. genera cover letters;
9. construye application bundles;
10. escribe observabilidad E2E;
11. construye el showcase;
12. sube artifacts temporales;
13. versiona `vacancy_state/` y `generation_state/` sanitizados.

### Límites actuales del batch automático

El workflow productivo aplica budgets y límites explícitos, por ejemplo:

```text
max vacancies per run: 6
CV generation budget: 2.0 USD estimados
cover-letter batch budget: 3.0 USD estimados
presentation budget: 3.0 USD estimados
```

Estos límites son guards de costo, no garantías de facturación exacta del proveedor.

---

## Idempotencia y reintentos

### Fingerprint de generación

La generación automática utiliza un fingerprint derivado de insumos relevantes como vacante, RAG y versión lógica del generador.

Objetivo:

```text
mismo input + misma lógica => no gastar otra vez
input/lógica materialmente diferente => regeneración controlada
```

### No-op obligatorio

Los workflows de evidence y vacancy ingest ejecutan una segunda corrida y esperan cero cambios. Si la segunda corrida reindexa o marca nuevas fuentes sin razón, existe un bug de idempotencia.

### Recuperación de fallos transitorios

Pueden reintentarse de forma controlada errores claramente transitorios, por ejemplo:

- provider quota/balance recuperable después de recarga;
- rate limit;
- timeout;
- connection error;
- provider unavailable;
- 502/503/504.

No deben entrar automáticamente al retry pool:

- errores de schema;
- grounding failures;
- deterministic validation failures;
- quality failures no transitorios;
- errores desconocidos.

---

## Observabilidad y artifacts

### Niveles de observabilidad

1. **Eventos:** `CVFIT_EVENT_LOG`.
2. **Stage reports:** generación, cover letter, presentación.
3. **Pipeline summary:** visión E2E.
4. **Run reports por candidatura:** calidad, costos, cobertura y estado.
5. **GitHub artifacts:** outputs temporales y eventos redacted.
6. **State versionado:** metadata necesaria para idempotencia/auditoría.

### No confundir process outcome con semantic outcome

Un proceso puede terminar con exit code 0 y aun así producir un estado funcional no válido.

El production canary separa:

```text
process_outcomes
stage_outcomes
```

Ejemplo:

```text
proceso de generación = success
semantic generation = FAILED_REVIEW_REQUIRED
```

Eso **no** debe considerarse una generación sana ni permitir que etapas downstream se reporten falsamente como exitosas.

### Artifacts importantes

Según la etapa pueden existir:

```text
cv_final.json / cv_final.md
cover_letter_final.md
evidence_trace.json
run_report.json
usage_report.json
cv_primary.html
cv_primary.pdf
application_bundle_report.json
generation_run_report.json
cover_letter_batch_report.json
application_bundle_batch_report.json
```

Los nombres exactos que exige el production canary son la referencia operacional para readiness.

---

## GitHub Actions

| Workflow | Propósito |
|---|---|
| `validate-experience.yml` | Valida source of truth y suite general |
| `evidence-rag.yml` | Construye/valida estado profesional RAG |
| `vacancy-ingest.yml` | Ingest incremental + generación + bundle + estado |
| `auto-enrich-jd.yml` | Intenta enriquecer JDs sparse con fuente del empleador |
| `cv-agent.yml` | Valida workflow ADK, presentation y contratos de generación |
| `retrieval-v2-eval.yml` | Evalúa Retrieval V2 |
| `cv-cost-ab.yml` | Experimentos A/B de costo bajo gates controlados |
| `production-canary.yml` | Prueba E2E live manual de readiness; nunca envía WhatsApp |
| `production-canary-contract.yml` | Evita regresiones en el contrato del canary |
| `daily-showcase-pages.yml` | Publica el Daily Showcase en Pages |
| `restore-ab-pages.yml` | Recuperación/control de Pages para experimentos autorizados |
| `live-canary-once.yml` | Canary histórico de Konfío; solo manual y no es la ruta productiva recomendada |

La ruta recomendada de readiness es **`Production readiness canary`**, no el canary histórico.

---

## Production canary

Antes de habilitar notificaciones outbound o declarar un cambio productivo sano, utiliza `.github/workflows/production-canary.yml`.

### Seguridad

El production canary es **manual (`workflow_dispatch`)**.

No debe existir un trigger público por issue, comentario o PR capaz de llegar a un job con acceso a `OPENAI_APY_KEY`.

La concurrency single-flight evita dos canaries pagados simultáneos.

### Qué prueba

1. rebuild aislado de vacancies;
2. rebuild/refresh de Retrieval V2;
3. credencial OpenAI live;
4. una generación real;
5. Headhunter loop;
6. cover letter grounded;
7. bundle HTML/PDF;
8. physical/visual/presentation gates;
9. semantic stage outcomes;
10. artifacts requeridos;
11. costo/estado observable;
12. `canary_healthy` final.

### Cómo ejecutarlo

En GitHub:

```text
Actions
→ Production readiness canary
→ Run workflow
→ vacancy_id = <canonical vacancy id>
```

No abras un issue para dispararlo.

### Criterio de éxito

El canary solo es sano cuando:

```text
canary_healthy = true
```

y existe el conjunto de artifacts finales requerido.

Una etapa técnicamente ejecutada pero semánticamente fallida no cuenta como PASS.

El production canary **nunca envía WhatsApp**.

---

## GitHub Pages

El showcase público se deriva de artifacts sanitizados.

Reglas:

- no publicar secretos;
- no publicar identidad privada;
- mantener links a la vacante original;
- conservar el estado de generación;
- no hacer pasar un artifact `REVIEW_REQUIRED` como listo;
- preservar artifacts existentes cuando una corrida incremental no los regenera, sin heredar metadata obsoleta.

URL actual:

```text
https://jcval94.github.io/CV_fit/
```

---

## WhatsApp

La integración usa Meta WhatsApp Cloud API y está feature-flagged.

### Gate principal

```text
WHATSAPP_NOTIFICATIONS_ENABLED=true
```

Si falta o tiene otro valor, no debe enviar.

### Solo se notifica cuando

- Pages ya desplegó;
- la candidatura tiene `ready_to_send=true`;
- existe CV HTML público;
- el fingerprint no fue reservado previamente.

### Semántica at-most-once

El estado se reserva **antes** de llamar a Meta para reducir el riesgo de duplicados.

Estados:

```text
RESERVED
ACCEPTED
FAILED
UNKNOWN_DELIVERY
```

`ACCEPTED` significa que Meta aceptó la petición; no prueba entrega al handset.

`FAILED` y `UNKNOWN_DELIVERY` no se reintentan automáticamente.

### Template esperado

Default:

```text
name: cv_fit_opportunity_ready
language: es_MX
```

Siete variables de body, en orden:

1. Company
2. Role title
3. Source fit
4. Headhunter score
5. RAG coverage
6. Published primary-CV HTML URL
7. Original vacancy/application URL

Runbook detallado: [`docs/whatsapp_notifications.md`](docs/whatsapp_notifications.md).

---

## Costos y política de modelos

### Escalation policy

Producción utiliza una escalación por review:

| Iteración | Tier | Default |
|---:|---|---|
| 1 | economy | `gpt-5.6-luna` |
| 2 | economy | `gpt-5.6-luna` |
| 3 | balanced | `gpt-5.6-terra` |
| 4 | balanced | `gpt-5.6-terra` |
| 5 | premium | `gpt-5.6-sol` |

El tier premium aparece tarde para evitar pagar un modelo más costoso antes de saber si hace falta.

### Experimentos de costo

`cv-cost-ab.yml` y el código experimental deben usarse para demostrar ahorro antes de promover una policy distinta.

Regla de ingeniería:

```text
no cambiar producción solo porque una estimación offline parece mejor
```

Antes de promover una optimización de costo, exigir:

- misma entrada;
- mismo contrato de calidad;
- ausencia de regresión factual;
- evidencia de ahorro live cuando aplique;
- CI verde;
- rollback simple.

---

## Validación y tests

### Suite general

```bash
python tools/validate_experience.py
python -m unittest discover -s tests -p 'test_*.py'
python -m rag.normalize --repo . --check
```

### Rebuild profesional

```bash
python -m rag.evidence \
  --repo . \
  --state-dir /tmp/rag_state \
  --run-id validation \
  --full-rebuild
```

### Rebuild de vacantes

```bash
python -m vacancy_pipeline \
  --repo . \
  --state-dir /tmp/vacancy_state \
  --run-id validation \
  --full-rebuild \
  --fail-on-quarantine
```

### Antes de mergear cambios de pipeline

Como mínimo deben pasar:

```text
source-of-truth validation
unit/integration tests
vacancy ingest
idempotence/no-op proof
ADK contracts
presentation gates cuando aplique
production-canary contract si se toca readiness
```

Un test verde que no cubre la ruta modificada no es evidencia suficiente por sí solo.

---

## Troubleshooting

### `OPENAI_APY_KEY` missing

**Síntoma:** generación/canary no realiza llamada live.

**Acción:** configurar el secret del repositorio. No hardcodear la key ni añadirla a `.env` versionado.

---

### `429`, `insufficient_quota` o `credit_balance_exhausted`

**Qué significa:** el provider no puede completar la llamada por límite/cuota/crédito.

**No hacer:** repetir automáticamente muchas veces un error permanente de balance.

**Hacer:** recuperar cuota/crédito y ejecutar de nuevo de forma controlada. El diagnóstico debe conservar el error real y no marcar etapas downstream como exitosas.

---

### Vacante `sparse`

**Síntoma:** matching funciona pero generación live queda bloqueada.

**Es correcto.**

Revisar:

- si existe un JD más completo;
- si `auto-enrich-jd` puede obtener JobPosting del empleador;
- si la URL es una página genérica o bloquea automatización.

Nunca rellenar requirements desde `fit_score` o inferencias.

---

### Vacante en cuarentena

**Síntoma:** `--fail-on-quarantine` rompe la validación.

Revisar el source original y el contrato en `contracts/vacancies/`. Corregir el input o adapter; no desactivar el gate para hacer pasar el archivo.

---

### Segunda corrida vuelve a procesar lo mismo

**Síntoma:** no-op reporta `new`, `modified`, `impacted` o `reindexed` > 0 sin cambios reales.

**Interpretación:** posible bug de hashing, normalización, manifest o fingerprint.

No aceptar como comportamiento esperado: la idempotencia es parte del contrato E2E.

---

### Headhunter pasa pero validación falla

**Es esperado que pueda ocurrir.**

Los jueces LLM evalúan calidad; los validadores deterministas tienen la última palabra sobre factualidad/contrato.

Corregir la generación o evidencia. No relajar el validator para acomodar el texto generado salvo que el contrato sea demostrablemente incorrecto.

---

### HTML se ve bien pero PDF falla

Ejecutar los gates de Playwright/Chromium y revisar:

- overflow;
- clipping;
- tamaños físicos;
- page breaks;
- headings;
- MediaBox.

La captura visual no sustituye la validación física del PDF.

---

### `ready_to_send=false`

No asumir que es un error de infraestructura. Revisar el bundle report para determinar si el bloqueo proviene de:

- contenido;
- Headhunter;
- grounding;
- cover letter;
- presentation;
- artifacts faltantes.

---

## Procedimiento seguro de cambio y release

### 1. Antes de cambiar código

Identifica qué contrato estás modificando:

```text
source of truth
vacancy contract
retrieval
matching
generation
presentation
observability
cost policy
notification
```

### 2. Haz el cambio mínimo

Evita refactors simultáneos sin beneficio demostrable. Una corrección debe poder atribuirse a un problema concreto.

### 3. Añade un test que hubiera fallado antes

Para bugs, el test debe reproducir el fallo o su condición lógica.

### 4. Corre validación determinista

```bash
python tools/validate_experience.py
python -m unittest discover -s tests -p 'test_*.py'
```

### 5. Reproduce el flujo afectado

Ejemplo:

```text
vacancy bug     → ingest + no-op
retrieval bug   → rebuild + retrieval eval
generation bug  → agent tests + canary cuando corresponda
layout bug      → Chromium/PDF gates
cost change     → A/B
```

### 6. PR pequeño y auditable

El PR debe explicar:

- problema;
- evidencia;
- cambio;
- riesgo;
- validación;
- rollback.

### 7. No promover un cambio live con CI rojo

Fallo de CI/test tiene prioridad sobre mejoras posteriores.

### 8. Canary para cambios productivos relevantes

Si el cambio afecta el camino live de generación, credenciales, Retrieval, artifacts o gates, ejecutar `Production readiness canary` antes de declarar readiness.

### 9. Observar las primeras corridas reales

Verificar:

- generación;
- costos;
- stage outcomes;
- artifacts;
- Pages;
- notificaciones si están habilitadas.

### 10. Cerrar trabajo experimental

Cuando una dirección gana:

- promover una sola ruta;
- cerrar PRs superseded;
- eliminar duplicación cuando sea seguro;
- conservar evidencia histórica necesaria;
- actualizar este README si cambia el contrato operativo.

---

## Definition of Done

Un cambio relevante en CV_fit está terminado cuando, según aplique:

```text
[ ] source of truth sigue consistente
[ ] schema/contrato sigue válido
[ ] tests relevantes están verdes
[ ] ingest funciona
[ ] segunda corrida es no-op
[ ] sparse/invalid sigue bloqueándose correctamente
[ ] retrieval conserva provenance
[ ] unsupported sigue siendo una salida válida
[ ] claims del CV siguen grounded
[ ] no hay proficiency/tenure inflation
[ ] artifacts esperados existen
[ ] HTML/PDF pasan gates físicos
[ ] semantic stage outcomes son coherentes
[ ] observabilidad explica éxito/fallo
[ ] costo queda limitado/registrado
[ ] no se expusieron secretos/PII
[ ] rollback es claro
```

Para production readiness completo, añadir:

```text
[ ] Production readiness canary = canary_healthy=true
```

---

## Límites deliberados

CV_fit deliberadamente **no** intenta:

- inventar experiencia faltante;
- convertir vacantes en evidencia profesional;
- ocultar gaps reales;
- usar múltiples proveedores LLM como fallback silencioso;
- publicar datos privados en Pages;
- considerar un PDF bonito equivalente a un CV válido;
- reintentar indefinidamente fallos desconocidos;
- disparar canaries pagados desde eventos públicos no autorizados;
- convertir cada optimización de costo en producción sin evidencia.

Cuando el sistema no tiene suficiente evidencia, la salida correcta puede ser **no generar**, **marcar unsupported**, **quarantine**, **REVIEW_REQUIRED** o **COMPLETED_BELOW_TARGET**.

Eso es una propiedad del sistema, no un defecto.

---

## Referencias operativas

- Go-live: [`docs/production_go_live.md`](docs/production_go_live.md)
- WhatsApp: [`docs/whatsapp_notifications.md`](docs/whatsapp_notifications.md)
- Agent internals: [`cv_agent/README.md`](cv_agent/README.md)
- Schemas de vacantes: [`contracts/vacancies/`](contracts/vacancies/)
- Showcase: <https://jcval94.github.io/CV_fit/>

Si este README y la implementación entran en conflicto, la prioridad es **corregir la contradicción**: el manual debe describir el comportamiento verificable del código y los workflows actuales, no una intención histórica.
