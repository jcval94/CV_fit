from __future__ import annotations

import os
import re


PUBLIC_KEY_ENV = "OPENAI_APY_KEY"
INTERNAL_OPENAI_KEY_ENV = "OPENAI_API_KEY"
OPENAI_MODEL_RE = re.compile(r"^gpt-[a-z0-9][a-z0-9.\-]*$", re.IGNORECASE)


def prepare_openai_environment(*, required: bool) -> str | None:
    """Expose the repo's single configured credential to ADK/LiteLLM in-process.

    The repository contract intentionally uses OPENAI_APY_KEY. ADK Python reaches
    OpenAI through LiteLLM, which expects OPENAI_API_KEY. We therefore mirror the
    value only inside the current process. No Google/Gemini credential is read.
    """

    value = os.getenv(PUBLIC_KEY_ENV)
    if not value:
        if required:
            raise RuntimeError(
                f"Missing {PUBLIC_KEY_ENV}. CV_fit uses OpenAI as its only model provider."
            )
        return None

    os.environ[INTERNAL_OPENAI_KEY_ENV] = value
    return value


def validate_openai_model_id(model_id: str) -> str:
    model_id = model_id.strip()
    if not OPENAI_MODEL_RE.fullmatch(model_id):
        raise ValueError(
            f"Unsupported model id {model_id!r}; CV_fit allows OpenAI GPT models only."
        )
    return model_id


def adk_openai_model(model_id: str):
    """Return ADK's documented Python OpenAI connector, locked to OpenAI.

    `include_usage` is requested explicitly so ADK events can expose prompt,
    cached-input, response and total token counts for the run artifact.
    """

    from google.adk.models.lite_llm import LiteLlm

    model_id = validate_openai_model_id(model_id)
    return LiteLlm(
        model=f"openai/{model_id}",
        stream_options={"include_usage": True},
    )
