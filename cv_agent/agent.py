from __future__ import annotations

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from cv_agent.model_policy import escalation_plan, model_ids
from cv_agent.prompts import ROOT_AGENT_INSTRUCTION


MODEL = model_ids()["balanced"]


def get_review_policy() -> dict:
    """Return the bounded review policy and per-iteration model tiers used by CV_fit."""
    return {
        "max_review_iterations": 5,
        "quality_target": "Senior Headhunter gate plus factual/language/structure validators",
        "on_limit": "return best evaluated CV with COMPLETED_BELOW_TARGET metadata",
        "model_escalation": [item.to_dict() for item in escalation_plan()],
    }


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=2),
    ),
    instruction=ROOT_AGENT_INSTRUCTION,
    tools=[get_review_policy],
)

app = App(root_agent=root_agent, name="cv_agent")
