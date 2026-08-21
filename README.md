# CV_fit

Fuente de verdad estructurada sobre la trayectoria profesional, formación, certificaciones, habilidades, proyectos y logros de José Carlos Del Valle.

La información canónica vive bajo `experience/` y alimenta CVs, perfiles profesionales, cartas de presentación y procesos de adaptación a vacantes. El repositorio separa evidencia, interpretación y redacción final para evitar contradicciones, sobreatribución y exposición de información sensible.

## Estructura

- `experience/profile.md`: identidad y posicionamiento estables.
- `experience/roles/`: cronología, alcance y progresión profesional.
- `experience/roles/index.md`: índice de recuperación para seleccionar experiencias laborales sin duplicar evidencia.
- `experience/projects/`: problema, contribución personal, implementación, resultados y límites de uso.
- `experience/projects/index.md`: índice de recuperación para seleccionar proyectos por dominio, stack y señal de seniority.
- `experience/achievements/metrics.md`: registro único de afirmaciones numéricas y su semántica.
- `experience/skills.md`: capacidades respaldadas por roles, proyectos o código público, con niveles estrictos `core | working | familiarity`.
- `experience/education.md` y `experience/certifications.md`: formación y credenciales.
- `experience/_meta/`: contrato de datos, fuentes, conflictos y preguntas abiertas.

## Reglas esenciales

- Todo registro Markdown bajo `experience/` cumple el esquema v3 descrito en `experience/_meta/data_contract.md`.
- Una métrica exacta se define semánticamente en `experience/achievements/metrics.md` y se reutiliza mediante su identificador `ACH-*`.
- Los conflictos no se sobrescriben silenciosamente: se documentan en `experience/_meta/conflicts.md`.
- El contenido publicado debe ser `public_safe`; las fuentes restringidas se registran sin incluir archivos o valores sensibles.
- La redacción preserva calificadores como `hasta`, `aproximadamente`, `piloto`, `proyectado` y `benchmark sintético`.
- La antigüedad profesional se calcula con la cronología laboral formal; docencia universitaria, servicio social y liderazgo estudiantil se conservan como experiencia complementaria.
- La granularidad manda: project ownership > resumen de perfil, metric registry > cifra copiada, `skills.md` > lista plana de tecnologías.

## Validación

```bash
python tools/validate_experience.py
```

La validación comprueba esquema, IDs, fuentes, enlaces, referencias de métricas y niveles de proficiency. La misma comprobación se ejecuta automáticamente sobre cambios y propuestas mediante GitHub Actions.
