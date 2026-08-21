from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping

import yaml

from cv_presentation.schemas import CandidateIdentity, IdentityResolution


PUBLIC_FIELDS = ("name", "location", "linkedin", "github", "website")
PRIVATE_FIELDS = ("email", "phone")
ENV_KEYS = {
    "name": "CV_IDENTITY_NAME",
    "location": "CV_IDENTITY_LOCATION",
    "linkedin": "CV_IDENTITY_LINKEDIN",
    "github": "CV_IDENTITY_GITHUB",
    "website": "CV_IDENTITY_WEBSITE",
    "email": "CV_IDENTITY_EMAIL",
    "phone": "CV_IDENTITY_PHONE",
}


def _load_public_yaml(path: Path | None) -> dict[str, str | None]:
    if path is None:
        return {}
    if not path.exists():
        raise FileNotFoundError(path)
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError("public identity YAML must contain a mapping")
    forbidden = sorted(field for field in PRIVATE_FIELDS if payload.get(field))
    if forbidden:
        raise ValueError(
            "private contact fields are not allowed in the public identity file; "
            f"use environment variables instead: {forbidden}"
        )
    unknown = sorted(set(payload) - set(PUBLIC_FIELDS))
    if unknown:
        raise ValueError(f"unknown public identity fields: {unknown}")
    return {field: payload.get(field) for field in PUBLIC_FIELDS}


def resolve_candidate_identity(
    *,
    public_identity_path: Path | None = None,
    env: Mapping[str, str] | None = None,
    include_private_contact: bool = False,
    artifact_visibility: str = "public",
    allow_private_in_public_artifact: bool = False,
) -> IdentityResolution:
    if artifact_visibility not in {"public", "private"}:
        raise ValueError("artifact_visibility must be 'public' or 'private'")
    if include_private_contact and artifact_visibility == "public" and not allow_private_in_public_artifact:
        raise ValueError(
            "refusing to include private contact data in a public artifact; use a private render path or explicit override"
        )

    values = _load_public_yaml(public_identity_path)
    field_sources: dict[str, str] = {
        field: "public_file" for field in PUBLIC_FIELDS if values.get(field)
    }
    source_env = env if env is not None else os.environ

    for field in PUBLIC_FIELDS:
        env_value = source_env.get(ENV_KEYS[field])
        if env_value and env_value.strip():
            values[field] = env_value.strip()
            field_sources[field] = "environment"

    private_fields_included: list[str] = []
    if include_private_contact:
        for field in PRIVATE_FIELDS:
            env_value = source_env.get(ENV_KEYS[field])
            if env_value and env_value.strip():
                values[field] = env_value.strip()
                field_sources[field] = "environment"
                private_fields_included.append(field)

    identity = CandidateIdentity(**values)
    return IdentityResolution(
        identity=identity,
        field_sources=field_sources,
        private_fields_included=private_fields_included,
        artifact_visibility=artifact_visibility,
    )
