from __future__ import annotations

from typing import Any


def assert_vacancy_generation_ready(vacancy: dict[str, Any], *, allow_sparse_jd: bool = False) -> None:
    if vacancy.get("application_language") == "und":
        raise ValueError(
            f"vacancy {vacancy.get('vacancy_id')} has undetermined application_language; "
            "set an explicit source language before CV generation"
        )

    if vacancy.get("jd_generation_eligible"):
        return
    if allow_sparse_jd:
        return

    reasons = vacancy.get("jd_fidelity_reasons") or []
    detail = "; ".join(str(item) for item in reasons)
    raise ValueError(
        f"vacancy {vacancy.get('vacancy_id')} is not CV-generation eligible: "
        f"jd_fidelity={vacancy.get('jd_fidelity', 'unknown')} "
        f"score={vacancy.get('jd_fidelity_score', 'unknown')}. "
        "Preserve the employer's original description/requirements/responsibilities before spending model tokens. "
        f"Details: {detail}"
    )
