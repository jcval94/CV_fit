from __future__ import annotations

from google.adk.agents import Agent
from google.adk.apps import App

from cv_agent.model_policy import escalation_plan, model_ids
from cv_agent.openai_provider import adk_openai_model, prepare_openai_environment
from cv_agent.prompts import ROOT_AGENT_INSTRUCTION


# Keep import-time validation credential-free for CI, but if the repo-level key
# is already present make it available to ADK/LiteLLM inside this process.
prepare_openai_environment(required=False)
MODEL = model_ids()["balanced"]


def get_review_policy() -> dict:
    """Return the bounded review policy and per-iteration OpenAI model tiers."""
    return {
        "provider": "openai",
        "credential_env": "OPENAI_APY_KEY",
        "max_review_iterations": 5,
        "quality_target": "Senior Headhunter gate plus factual/language/structure validators",
        "on_limit": "return best evaluated CV with COMPLETED_BELOW_TARGET metadata",
        "model_escalation": [item.to_dict() for item in escalation_plan()],
    }


root_agent = Agent(
    name="root_agent",
    model=adk_openai_model(MODEL),
    instruction=ROOT_AGENT_INSTRUCTION,
    tools=[get_review_policy],
)

app = App(root_agent=root_agent, name="cv_agent")
