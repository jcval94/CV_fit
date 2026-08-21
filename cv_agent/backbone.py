from __future__ import annotations

from typing import Any


PROFILE_RECORD_ID = "professional-profile"
ROLE_RECORD_IDS = ("role-bbva", "role-management-solutions")
EDUCATION_RECORD_ID = "education"

PROFILE_TITLES = (
    "Professional positioning",
    "Professional-experience basis",
    "Canonical summary",
)
EDUCATION_TITLES = (
    "Master's Degree in Data Science",
    "Bachelor's Degree in Actuarial Science",
)


def _is_public_cv_evidence(chunk: dict[str, Any]) -> bool:
    return bool(chunk.get("cv_eligible")) and bool(chunk.get("public_safe"))


def is_canonical_backbone_chunk(chunk: dict[str, Any]) -> bool:
    """Return True for stable chronology/education/profile facts every CV may rely on.

    These chunks do not compete with vacancy-specific retrieval. They are the
    canonical structural backbone that prevents a semantic top-k from dropping
    dates, employers, role progression, formal education or the governed tenure
    basis. Project/skill evidence remains vacancy-specific.
    """
    if not _is_public_cv_evidence(chunk):
        return False

    record_id = str(chunk.get("record_id") or "")
    title = str(chunk.get("title") or "")
    heading_path = [str(value) for value in chunk.get("heading_path", [])]

    if record_id == PROFILE_RECORD_ID:
        return title in PROFILE_TITLES

    if record_id in ROLE_RECORD_IDS:
        if title == "Canonical employment record":
            return True
        return "Role chronology" in heading_path

    if record_id == EDUCATION_RECORD_ID:
        return title in EDUCATION_TITLES

    return False


def _priority(chunk: dict[str, Any]) -> tuple[int, int, str]:
    record_id = str(chunk.get("record_id") or "")
    title = str(chunk.get("title") or "")
    if record_id == PROFILE_RECORD_ID:
        return (0, PROFILE_TITLES.index(title) if title in PROFILE_TITLES else 99, str(chunk.get("chunk_id") or ""))
    if record_id == "role-bbva":
        return (1, 0 if title == "Canonical employment record" else 1, str(chunk.get("chunk_id") or ""))
    if record_id == "role-management-solutions":
        return (2, 0 if title == "Canonical employment record" else 1, str(chunk.get("chunk_id") or ""))
    if record_id == EDUCATION_RECORD_ID:
        return (3, EDUCATION_TITLES.index(title) if title in EDUCATION_TITLES else 99, str(chunk.get("chunk_id") or ""))
    return (99, 99, str(chunk.get("chunk_id") or ""))


def select_canonical_backbone(catalog: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    selected = [chunk for chunk in catalog.values() if is_canonical_backbone_chunk(chunk)]
    selected.sort(key=_priority)
    return selected
