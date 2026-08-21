from __future__ import annotations

import re
import unicodedata
from typing import Iterable


SUPPORTED_LANGUAGES = {"en", "es", "fr"}
EN_ROLE_TERMS = {
    "data scientist", "machine learning", "engineer", "scientist", "head of", "director", "lead", "manager",
    "analytics", "artificial intelligence", "ai ", "ml ", "researcher", "decision scientist",
}
ES_ROLE_TERMS = {
    "cientifico de datos", "científica de datos", "cientifico", "ingeniero", "ingeniera", "jefe de", "director de",
    "directora de", "lider", "líder", "analitica", "analítica", "inteligencia artificial", "aprendizaje automatico",
    "aprendizaje automático",
}
EN_MARKERS = {
    "the", "and", "with", "for", "you", "your", "will", "experience", "requirements", "responsibilities",
    "build", "develop", "design", "production", "team", "business", "data", "models", "role", "skills",
}
ES_MARKERS = {
    "el", "la", "los", "las", "y", "con", "para", "tu", "usted", "experiencia", "requisitos", "responsabilidades",
    "desarrollar", "diseñar", "produccion", "producción", "equipo", "negocio", "datos", "modelos", "puesto", "habilidades",
}


def _norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return value.casefold()


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-záéíóúñü]+", text.casefold())


def _explicit_language(value: str | None) -> str | None:
    if not value:
        return None
    key = value.strip().casefold().replace("_", "-")
    aliases = {
        "english": "en", "ingles": "en", "inglés": "en", "en-us": "en", "en-gb": "en",
        "spanish": "es", "espanol": "es", "español": "es", "es-mx": "es",
        "french": "fr", "frances": "fr", "francés": "fr",
    }
    code = aliases.get(key, key.split("-", 1)[0])
    return code if code in SUPPORTED_LANGUAGES else None


def infer_application_language(
    *,
    role_title: str,
    description: str | None = None,
    requirements: Iterable[str] = (),
    responsibilities: Iterable[str] = (),
    explicit_language: str | None = None,
) -> tuple[str, float, str]:
    """Infer application language without using source fit commentary.

    Priority is explicit source language, then substantive vacancy text, then
    the role title. Source-provided candidate fit reasoning is deliberately
    excluded so matching opinions cannot influence document language.
    """
    explicit = _explicit_language(explicit_language)
    if explicit:
        return explicit, 1.0, "explicit_source"

    body_parts = [description or "", *requirements, *responsibilities]
    body = " ".join(part for part in body_parts if part).strip()
    if body:
        words = _tokens(body)
        en = sum(word in EN_MARKERS for word in words)
        es = sum(word in ES_MARKERS for word in words)
        if en >= max(3, es + 2):
            return "en", min(0.98, 0.72 + 0.03 * en), "vacancy_text"
        if es >= max(3, en + 2):
            return "es", min(0.98, 0.72 + 0.03 * es), "vacancy_text"

    title_norm = _norm(role_title)
    en_role = sum(term in title_norm for term in EN_ROLE_TERMS)
    es_role = sum(_norm(term) in title_norm for term in ES_ROLE_TERMS)
    if en_role > es_role and en_role > 0:
        return "en", 0.86, "role_title"
    if es_role > en_role and es_role > 0:
        return "es", 0.9, "role_title"

    return "und", 0.0, "undetermined"
