from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from vacancy_pipeline import CANONICAL_VACANCY_SCHEMA_VERSION
from vacancy_pipeline.language import infer_application_language
from vacancy_pipeline.models import ProvenanceRef, VacancyRecord


class VacancyValidationError(ValueError):
    """Raised when an input file cannot be accepted atomically."""

    def __init__(self, source_path: str, errors: list[str]):
        self.source_path = source_path
        self.errors = errors
        super().__init__(f"{source_path}: " + "; ".join(errors))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _norm_key(value: str | None) -> str:
    if not value:
        return ""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.casefold().strip()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def _clean_string(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return str(value).strip() or None
    value = value.strip()
    return value or None


def _clean_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _clean_string(item)
        if not text:
            continue
        key = text.casefold()
        if key not in seen:
            seen.add(key)
            out.append(text)
    return out


def extract_url(value: Any) -> str | None:
    text = _clean_string(value)
    if not text:
        return None
    match = re.search(r"https?://[^\s)\]]+", text)
    if not match:
        return None
    raw = match.group(0)
    parts = urlsplit(raw)
    query = [
        (key, val)
        for key, val in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
        and key.lower() not in {"trk", "trackingid", "ref", "refid"}
    ]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ""))


def normalize_work_model(value: Any) -> str | None:
    text = _clean_string(value)
    if not text:
        return None
    key = _norm_key(text)
    if key in {"remote", "remoto", "remota", "100 remoto", "100 remote"}:
        return "Remote"
    if key in {"hybrid", "hibrido", "hibrida"}:
        return "Hybrid"
    if key in {"onsite", "on site", "presencial"}:
        return "On-site"
    return text


def normalize_posted_date(value: Any) -> tuple[str | None, str | None]:
    raw = _clean_string(value)
    if not raw:
        return None, None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return raw, raw
    return None, raw


def stable_identity(company: str, role_title: str, location_raw: str | None, url: str | None) -> tuple[str, str]:
    base = "|".join((_norm_key(company), _norm_key(role_title), _norm_key(location_raw)))
    if not _norm_key(location_raw) and url:
        base += "|" + _norm_key(url)
    digest = hashlib.sha256(base.encode("utf-8")).hexdigest()
    return f"vac-{digest[:16]}", digest


def semantic_hash(payload: dict[str, Any]) -> str:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def detect_source_format(data: Any) -> str:
    if not isinstance(data, dict):
        return "unknown"
    if isinstance(data.get("vacancies"), list):
        return "gptw_v1"
    if isinstance(data.get("vacantes"), list):
        return "vacantes_v1"
    return "unknown"


def _validate_score(value: Any, label: str, errors: list[str]) -> None:
    if value is None:
        return
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= float(value) <= 100:
        errors.append(f"{label} must be a number between 0 and 100")


def _validate_optional_language(value: Any, label: str, errors: list[str]) -> None:
    if value is not None and not isinstance(value, str):
        errors.append(f"{label} must be a string when provided")


def validate_source_document(data: Any, source_path: str) -> str:
    errors: list[str] = []
    source_format = detect_source_format(data)
    if source_format == "unknown":
        raise VacancyValidationError(source_path, ["unsupported JSON envelope; expected vacancies[] or vacantes[]"])

    if source_format == "gptw_v1":
        entries = data["vacancies"]
        declared = data.get("total_results")
        if declared is not None and declared != len(entries):
            errors.append(f"total_results={declared!r} does not match vacancies length={len(entries)}")
        for idx, item in enumerate(entries):
            prefix = f"vacancies[{idx}]"
            if not isinstance(item, dict):
                errors.append(f"{prefix} must be an object")
                continue
            if not _clean_string(item.get("company")):
                errors.append(f"{prefix}.company is required")
            if not _clean_string(item.get("role_title")):
                errors.append(f"{prefix}.role_title is required")
            if item.get("tech_stack") is not None and not isinstance(item.get("tech_stack"), list):
                errors.append(f"{prefix}.tech_stack must be an array")
            if item.get("location") is not None and not isinstance(item.get("location"), dict):
                errors.append(f"{prefix}.location must be an object")
            _validate_score(item.get("fit_score"), f"{prefix}.fit_score", errors)
            _validate_optional_language(item.get("application_language", item.get("language")), f"{prefix}.application_language", errors)
    else:
        entries = data["vacantes"]
        metadata = data.get("metadata") or {}
        if metadata is not None and not isinstance(metadata, dict):
            errors.append("metadata must be an object")
            metadata = {}
        declared = metadata.get("total_vacantes_encontradas") if isinstance(metadata, dict) else None
        if declared is not None and declared != len(entries):
            errors.append(f"metadata.total_vacantes_encontradas={declared!r} does not match vacantes length={len(entries)}")
        for idx, item in enumerate(entries):
            prefix = f"vacantes[{idx}]"
            if not isinstance(item, dict):
                errors.append(f"{prefix} must be an object")
                continue
            if not _clean_string(item.get("empresa")):
                errors.append(f"{prefix}.empresa is required")
            if not _clean_string(item.get("puesto")):
                errors.append(f"{prefix}.puesto is required")
            if item.get("stack_clave_detectado") is not None and not isinstance(item.get("stack_clave_detectado"), list):
                errors.append(f"{prefix}.stack_clave_detectado must be an array")
            if item.get("razon_ajuste") is not None and not isinstance(item.get("razon_ajuste"), dict):
                errors.append(f"{prefix}.razon_ajuste must be an object")
            _validate_score(item.get("porcentaje_ajuste"), f"{prefix}.porcentaje_ajuste", errors)
            _validate_optional_language(item.get("idioma_postulacion", item.get("application_language")), f"{prefix}.idioma_postulacion", errors)

    if errors:
        raise VacancyValidationError(source_path, errors)
    return source_format


def _record_payload_without_hash(**kwargs: Any) -> dict[str, Any]:
    return {key: value for key, value in kwargs.items() if key not in {"content_hash", "provenance"}}


def adapt_source_document(
    data: dict[str, Any],
    source_path: str,
    source_hash: str,
    source_commit: str | None = None,
) -> list[VacancyRecord]:
    source_format = validate_source_document(data, source_path)
    records: list[VacancyRecord] = []

    if source_format == "gptw_v1":
        entries = data["vacancies"]
        file_updated = _clean_string(data.get("last_updated"))
        for idx, item in enumerate(entries):
            location = item.get("location") or {}
            company = _clean_string(item.get("company")) or ""
            role = _clean_string(item.get("role_title")) or ""
            city = _clean_string(location.get("city"))
            work_model = normalize_work_model(location.get("work_model"))
            location_raw = city
            posted_date, posted_raw = normalize_posted_date(item.get("posted_date"))
            url = extract_url(item.get("url"))
            vacancy_id, identity_key = stable_identity(company, role, location_raw, url)
            tech_stack = _clean_list(item.get("tech_stack"))
            requirements = _clean_list(item.get("requirements"))
            responsibilities = _clean_list(item.get("responsibilities"))
            description = _clean_string(item.get("description"))
            language, language_confidence, language_source = infer_application_language(
                role_title=role,
                description=description,
                requirements=requirements,
                responsibilities=responsibilities,
                explicit_language=_clean_string(item.get("application_language", item.get("language"))),
            )
            kwargs = dict(
                schema_version=CANONICAL_VACANCY_SCHEMA_VERSION,
                vacancy_id=vacancy_id,
                company=company,
                role_title=role,
                seniority=_clean_string(item.get("seniority")),
                company_category=_clean_string(item.get("company_category")),
                location_raw=location_raw,
                city=city,
                work_model=work_model,
                posted_date=posted_date,
                posted_date_raw=posted_raw,
                url=url,
                salary=_clean_string(item.get("salary")),
                tech_stack=tech_stack,
                requirements=requirements,
                responsibilities=responsibilities,
                description=description,
                application_language=language,
                language_confidence=language_confidence,
                language_source=language_source,
                fit_score=float(item["fit_score"]) if item.get("fit_score") is not None else None,
                fit_summary=_clean_string(item.get("fit_evaluation")),
                fit_strengths=_clean_list(item.get("fit_strengths")),
                fit_gaps=_clean_list(item.get("fit_gaps")),
                identity_key=identity_key,
            )
            content_hash = semantic_hash(_record_payload_without_hash(**kwargs))
            provenance = [ProvenanceRef(
                source_path=source_path,
                source_hash=source_hash,
                source_format=source_format,
                source_entry_index=idx,
                source_native_id=_clean_string(item.get("id")),
                source_commit=source_commit,
                source_updated_at=file_updated,
                source_search_date=None,
            )]
            records.append(VacancyRecord(**kwargs, content_hash=content_hash, provenance=provenance))
    else:
        entries = data["vacantes"]
        metadata = data.get("metadata") or {}
        search_date = _clean_string(metadata.get("fecha_busqueda"))
        for idx, item in enumerate(entries):
            reason = item.get("razon_ajuste") or {}
            company = _clean_string(item.get("empresa")) or ""
            role = _clean_string(item.get("puesto")) or ""
            location_raw = _clean_string(item.get("ubicacion"))
            posted_date, posted_raw = normalize_posted_date(item.get("fecha_publicacion"))
            url = extract_url(item.get("url_postulacion"))
            vacancy_id, identity_key = stable_identity(company, role, location_raw, url)
            tech_stack = _clean_list(item.get("stack_clave_detectado"))
            requirements = _clean_list(item.get("requirements"))
            responsibilities = _clean_list(item.get("responsibilities"))
            description = _clean_string(item.get("description"))
            language, language_confidence, language_source = infer_application_language(
                role_title=role,
                description=description,
                requirements=requirements,
                responsibilities=responsibilities,
                explicit_language=_clean_string(item.get("idioma_postulacion", item.get("application_language"))),
            )
            kwargs = dict(
                schema_version=CANONICAL_VACANCY_SCHEMA_VERSION,
                vacancy_id=vacancy_id,
                company=company,
                role_title=role,
                seniority=_clean_string(item.get("seniority")),
                company_category=_clean_string(item.get("categoria_empresa")),
                location_raw=location_raw,
                city=location_raw,
                work_model=normalize_work_model(item.get("modalidad")),
                posted_date=posted_date,
                posted_date_raw=posted_raw,
                url=url,
                salary=_clean_string(item.get("rango_salarial")),
                tech_stack=tech_stack,
                requirements=requirements,
                responsibilities=responsibilities,
                description=description,
                application_language=language,
                language_confidence=language_confidence,
                language_source=language_source,
                fit_score=float(item["porcentaje_ajuste"]) if item.get("porcentaje_ajuste") is not None else None,
                fit_summary=_clean_string(reason.get("resumen")),
                fit_strengths=_clean_list(reason.get("puntos_fuertes")),
                fit_gaps=_clean_list(reason.get("posibles_gaps")),
                identity_key=identity_key,
            )
            content_hash = semantic_hash(_record_payload_without_hash(**kwargs))
            provenance = [ProvenanceRef(
                source_path=source_path,
                source_hash=source_hash,
                source_format=source_format,
                source_entry_index=idx,
                source_native_id=_clean_string(item.get("id_vacante")),
                source_commit=source_commit,
                source_updated_at=None,
                source_search_date=search_date,
            )]
            records.append(VacancyRecord(**kwargs, content_hash=content_hash, provenance=provenance))
    return records


def load_and_adapt(
    path: Path,
    repo_root: Path,
    source_commit: str | None = None,
) -> tuple[str, list[VacancyRecord]]:
    source_path = path.relative_to(repo_root).as_posix()
    raw = path.read_bytes()
    source_hash = sha256_bytes(raw)
    try:
        data = json.loads(raw.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise VacancyValidationError(source_path, [f"file is not valid UTF-8: {exc}"]) from exc
    except json.JSONDecodeError as exc:
        raise VacancyValidationError(source_path, [f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"]) from exc
    return source_hash, adapt_source_document(data, source_path, source_hash, source_commit)
