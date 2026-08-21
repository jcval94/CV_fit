from __future__ import annotations

import json
import time
import uuid
from typing import TypeVar

from pydantic import BaseModel

from cv_agent.openai_provider import adk_openai_model, prepare_openai_environment
from cv_agent.telemetry import LLMCallUsage, PRICING_BASIS, PRICING_SNAPSHOT_DATE, estimate_cost_usd, summarize_usage


T = TypeVar("T", bound=BaseModel)


class AdkStructuredClient:
    """ADK adapter for stateless schema-constrained OpenAI generation steps.

    CV_fit uses OpenAI as its only model provider. ADK Python connects to OpenAI
    through its documented LiteLLM model connector; the repo-level credential is
    OPENAI_APY_KEY and is mirrored in-process only when a live call is made.

    Every live call records ADK usage metadata. A cumulative estimated-cost guard
    can stop additional calls after the configured budget has been reached. The
    guard is intentionally conservative: a single in-flight call may put the run
    slightly above the threshold, but no subsequent model call will be started.
    """

    def __init__(
        self,
        app_name: str = "cv_fit_pipeline",
        user_id: str = "cv_fit",
        max_estimated_cost_usd: float | None = None,
    ) -> None:
        self.app_name = app_name
        self.user_id = user_id
        self.max_estimated_cost_usd = max_estimated_cost_usd
        self._usage: list[LLMCallUsage] = []

    def telemetry_snapshot(self) -> dict:
        summary = summarize_usage(list(self._usage))
        summary["max_estimated_cost_usd"] = self.max_estimated_cost_usd
        return summary

    def _assert_budget_available(self) -> None:
        if self.max_estimated_cost_usd is None:
            return
        spent = float(self.telemetry_snapshot().get("known_estimated_cost_usd") or 0.0)
        if spent >= self.max_estimated_cost_usd:
            raise RuntimeError(
                f"OpenAI live-run estimated-cost guard reached: ${spent:.4f} >= "
                f"${self.max_estimated_cost_usd:.4f}. No additional model call was started."
            )

    def _record_usage(
        self,
        *,
        name: str,
        model: str,
        prompt_tokens: int,
        cached_input_tokens: int,
        candidate_tokens: int,
        reasoning_tokens: int,
        total_tokens: int,
        started: float,
        error: str | None = None,
    ) -> None:
        self._usage.append(LLMCallUsage(
            name=name,
            model=model,
            prompt_tokens=prompt_tokens,
            cached_input_tokens=cached_input_tokens,
            candidate_tokens=candidate_tokens,
            reasoning_tokens=reasoning_tokens,
            total_tokens=total_tokens,
            duration_ms=round((time.perf_counter() - started) * 1000),
            estimated_cost_usd=estimate_cost_usd(
                model,
                prompt_tokens=prompt_tokens,
                cached_input_tokens=cached_input_tokens,
                candidate_tokens=candidate_tokens,
                reasoning_tokens=reasoning_tokens,
            ),
            pricing_snapshot_date=PRICING_SNAPSHOT_DATE,
            pricing_basis=PRICING_BASIS,
            error=error,
        ))

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
        self._assert_budget_available()
        prepare_openai_environment(required=True)

        from google.adk.agents import LlmAgent
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai import types

        started = time.perf_counter()
        prompt_tokens = 0
        cached_input_tokens = 0
        candidate_tokens = 0
        reasoning_tokens = 0
        total_tokens = 0

        try:
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
                usage = getattr(event, "usage_metadata", None)
                if usage:
                    prompt_tokens += int(getattr(usage, "prompt_token_count", 0) or 0)
                    cached_input_tokens += int(getattr(usage, "cached_content_token_count", 0) or 0)
                    candidate_tokens += int(getattr(usage, "candidates_token_count", 0) or 0)
                    reasoning_tokens += int(getattr(usage, "thoughts_token_count", 0) or 0)
                    total_tokens += int(getattr(usage, "total_token_count", 0) or 0)
                if event.is_final_response() and event.content and event.content.parts:
                    final_text = event.content.parts[0].text
            if not final_text:
                raise RuntimeError(f"ADK agent {name!r} returned no final structured response")
            result = output_schema.model_validate_json(final_text)
        except Exception as exc:
            self._record_usage(
                name=name,
                model=model,
                prompt_tokens=prompt_tokens,
                cached_input_tokens=cached_input_tokens,
                candidate_tokens=candidate_tokens,
                reasoning_tokens=reasoning_tokens,
                total_tokens=total_tokens,
                started=started,
                error=f"{type(exc).__name__}: {exc}",
            )
            raise

        self._record_usage(
            name=name,
            model=model,
            prompt_tokens=prompt_tokens,
            cached_input_tokens=cached_input_tokens,
            candidate_tokens=candidate_tokens,
            reasoning_tokens=reasoning_tokens,
            total_tokens=total_tokens,
            started=started,
        )
        self._assert_budget_available()
        return result
