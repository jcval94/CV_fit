"""Google ADK application for evidence-grounded CV adaptation."""

try:
    from cv_agent.agent import app
except ImportError:
    # Deterministic repository tooling can run without the optional ADK runtime
    # installed. Live agent execution requires the project dependencies.
    app = None

__all__ = ["app"]
