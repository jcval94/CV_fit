from __future__ import annotations

import json
import uuid
from typing import TypeVar

from pydantic import BaseModel


T = TypeVar("T", bound=BaseModel)


class AdkStructuredClient:
    """Small ADK adapter for stateless, schema-constrained generation steps.

    Imports ADK lazily so deterministic ingestion/retrieval tests do not require
    model credentials or even the ADK package. Live agent execution does.
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
        from google.adk.agents import LlmAgent
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai import types

        agent = LlmAgent(
            name=name,
            model=model,
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
