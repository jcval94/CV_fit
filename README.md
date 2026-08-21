# CV_fit

Fuente de verdad estructurada sobre la trayectoria profesional de José Carlos Del Valle y base incremental para transformar vacantes en insumos trazables de matching/RAG.

El repositorio mantiene **dos corpus separados**:

1. `experience/`: evidencia profesional canónica, gobernada y pública.
2. `GPTW/` + `Vacantes/`: entradas de vacantes, que se validan y normalizan hacia `vacancy_state/` sin modificar la evidencia profesional.

No se mezclan hechos profesionales con contenido de vacantes en una misma capa canónica.

## Evidencia profesional

- `experience/profile.md`: identidad y posicionamiento estables.
- `experience/roles/`: cronología, alcance y progresión profesional.
- `experience/roles/index.md`: índice de recuperación para seleccionar experiencias laborales sin duplicar evidencia.
- `experience/projects/`: problema, contribución personal, implementación, resultados y límites de uso.
- `experience/projects/index.md`: índice de recuperación por dominio, stack y señal de seniority.
- `experience/achievements/metrics.md`: registro único de afirmaciones numéricas y su semántica.
- `experience/skills.md`: capacidades con niveles estrictos `core | working | familiarity`.
- `experience/education.md` y `experience/certifications.md`: formación y credenciales.
- `experience/_meta/`: contrato de datos, fuentes, conflictos y preguntas abiertas.
- `rag/`: normalización determinista de `experience/` para etapas posteriores de recuperación.

## Vacantes incrementales

- `GPTW/**/*.json` y `Vacantes/**/*.json`: fuentes de entrada.
- `contracts/vacancies/`: schemas versionados de entrada y modelo canónico.
- `vacancy_pipeline/`: validación, adapters, normalización, deduplicación, chunking, indexación y recuperación léxica.
- `vacancy_state/`: estado derivado y versionado: manifiesto, snapshots, registros canónicos, chunks, índice, cuarentena y reportes.
- `.github/workflows/vacancy-ingest.yml`: automatización incremental cuando cambian las carpetas de entrada.

Cada archivo se identifica por SHA-256. Los archivos sin cambios no se reparsan; una modificación solo remezcla/rechunk/reindexa las vacantes afectadas. Los archivos inválidos se procesan de forma atómica y pasan a cuarentena.

## Reglas esenciales

- Todo registro Markdown bajo `experience/` cumple el esquema v3 descrito en `experience/_meta/data_contract.md`.
- Una métrica exacta se define semánticamente en `experience/achievements/metrics.md` y se reutiliza mediante su identificador `ACH-*`.
- Los conflictos no se sobrescriben silenciosamente: se documentan en `experience/_meta/conflicts.md`.
- La granularidad manda: project ownership > resumen de perfil, metric registry > cifra copiada, `skills.md` > lista plana de tecnologías.
- `vacancy_state/` es derivado; las correcciones de vacantes pertenecen a `GPTW/` o `Vacantes/`.
- Los scores/razonamientos de fit provenientes de una fuente se guardan en chunks separados de los hechos de la vacante.
- No se generan CVs todavía: esta etapa termina en insumos validados, chunked, indexados y trazables.

## Validación

```bash
python tools/validate_experience.py
python -m unittest discover -s tests -p 'test_*.py'
python -m rag.normalize --repo . --check
python -m vacancy_pipeline --repo . --state-dir /tmp/cv-fit-vacancy-state --full-rebuild --fail-on-quarantine
```

La validación se ejecuta en GitHub Actions. Para las vacantes, los PRs validan E2E en estado temporal; los pushes a `main` actualizan incrementalmente el estado versionado.
