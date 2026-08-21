from __future__ import annotations

import json
import uuid
from typing import TypeVar

from pydantic import BaseModel

from cv_agent.openai_provider import adk_openai_model, prepare_openai_environment


T = TypeVar("T", bound=BaseModel)


class AdkStructuredClient:
    """ADK adapter for stateless schema-constrained OpenAI generation steps.

    CV_fit uses OpenAI as its only model provider. ADK Python connects to OpenAI
    through its documented LiteLLM model connector; the repo-level credential is
    OPENAI_APY_KEY and is mirrored in-process only when a live call is made.
    """

    def __init__(self, app_name: str = "cv_fit_pipeline", user_id: str = "cv_fit") -> None:
        self.app_name = app_name
        self.user_id = user_id

    async def call(
        self,
        *,
        name: str,
        model: str,
        instruction: str,
        payload: dict,
        output_schema: type[T],
        max_output_tokens: int = 6000,
    ) -> T:
        prepare_openai_environment(required=True)

        from google.adk.agents import LlmAgent
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai import types

        agent = LlmAgent(
            name=name,
            model=adk_openai_model(model),
            include_contents="none",
            instruction=instruction,
            output_schema=output_schema,
            generate_content_config=types.GenerateContentConfig(max_output_tokens=max_output_tokens),
        )
        session_service = InMemorySessionService()
        session_id = f"{name}-{uuid.uuid4().hex[:12]}"
        await session_service.create_session(
            app_name=self.app_name,
            user_id=self.user_id,
            session_id=session_id,
        )
        runner = Runner(agent=agent, app_name=self.app_name, session_service=session_service)
        message = types.Content(
            role="user",
            parts=[types.Part(text=json.dumps(payload, ensure_ascii=False, sort_keys=True))],
        )
        final_text: str | None = None
        async for event in runner.run_async(
            user_id=self.user_id,
            session_id=session_id,
            new_message=message,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final_text = event.content.parts[0].text
        if not final_text:
            raise RuntimeError(f"ADK agent {name!r} returned no final structured response")
        return output_schema.model_validate_json(final_text)
