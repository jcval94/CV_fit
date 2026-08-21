from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from cv_agent.schemas import CVDocument
from cv_presentation.schemas import (
    CVPresentationModel,
    CandidateIdentity,
    PresentationConfig,
    PresentationExperienceItem,
    PresentationLine,
    PresentationProjectItem,
)


def _stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_cv_document(path: Path) -> CVDocument:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("cv"), dict):
        payload = payload["cv"]
    return CVDocument.model_validate(payload)


def load_presentation_config(path: Path | None = None) -> PresentationConfig:
    if path is None:
        return PresentationConfig()
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return PresentationConfig.model_validate(payload)


def _line(value) -> PresentationLine:
    return PresentationLine(text=value.text, evidence_refs=list(value.evidence_refs))


def build_presentation_model(
    cv: CVDocument,
    *,
    candidate: CandidateIdentity,
    config: PresentationConfig,
) -> CVPresentationModel:
    source_cv_hash = _stable_hash(cv.model_dump(mode="json"))
    config_hash = _stable_hash(config.model_dump(mode="json"))
    return CVPresentationModel(
        source_cv_hash=source_cv_hash,
        config_hash=config_hash,
        candidate=candidate,
        language=cv.language,
        target_role=cv.target_role,
        headline=_line(cv.headline),
        summary=_line(cv.summary),
        experience=[
            PresentationExperienceItem(
                organization=item.organization,
                title=item.title,
                period=item.period,
                evidence_refs=list(item.evidence_refs),
                bullets=[_line(bullet) for bullet in item.bullets],
            )
            for item in cv.experience
        ],
        projects=[
            PresentationProjectItem(
                name=item.name,
                evidence_refs=list(item.evidence_refs),
                bullets=[_line(bullet) for bullet in item.bullets],
            )
            for item in cv.projects
        ],
        skills=[_line(item) for item in cv.skills],
        education=[_line(item) for item in cv.education],
        certifications=[_line(item) for item in cv.certifications],
        document=config.document,
        layout=config.layout,
        density=config.density,
    )
