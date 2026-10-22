"""Adapter for the example FAQ chatbot agent."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ...config import Settings
from ...integration.base_adapter import (
    OVERRIDE_CONFIG,
    OVERRIDE_STAGE,
    TRACE_EVENTS,
    AdapterOutput,
    AgentCapabilities,
    AgentInfo,
    BaseAgentAdapter,
)
from ...integration.config_utils import apply_overrides
from ...integration.errors import AgentRunError
from ...integration.tracing import EventRecorder
from .faq_agent import STAGES, FaqAgent

_SHAPES = {"intent_detection": str, "retrieval": list, "response_generation": dict}


class FaqAdapter(BaseAgentAdapter):
    AGENT_ID = "faq-chatbot"

    def __init__(self, agent: Optional[FaqAgent] = None) -> None:
        self.agent = agent or FaqAgent()

    def info(self) -> AgentInfo:
        return AgentInfo(
            agent_id=self.AGENT_ID,
            name="FAQ Chatbot (example)",
            agent_type="chatbot",
            version=self.agent.version,
            description="Answers customer questions about a fictional cloud storage service from a small FAQ.",
            input_schema={
                "fields": {"question": {"type": "str", "required": True, "min_length": 2, "max_length": 500}},
                "allow_extra": False,
            },
            capabilities=AgentCapabilities(
                trace_level=TRACE_EVENTS,
                supports_stage_overrides=True,
                supports_config_overrides=True,
                deterministic=True,
            ),
            supported_stages=list(STAGES),
            example_inputs=[{"question": "How do I reset my password?"}],
        )

    def extra_override_errors(self, overrides: Dict[str, Any]) -> List[str]:
        errors: List[str] = []
        for name, value in (overrides.get(OVERRIDE_STAGE) or {}).items():
            if not isinstance(value, _SHAPES[name]):
                errors.append(f"Override for '{name}' must be a {_SHAPES[name].__name__}")
            elif name == "response_generation" and "answer" not in value:
                errors.append("Override for 'response_generation' must contain 'answer'")
        if overrides.get(OVERRIDE_CONFIG):
            try:
                apply_overrides(self.agent.config, overrides[OVERRIDE_CONFIG])
            except ValueError as exc:
                errors.append(str(exc))
        return errors

    def run(self, task_input: Dict[str, Any], overrides: Optional[Dict[str, Any]] = None) -> AdapterOutput:
        overrides = overrides or {}
        recorder = EventRecorder()
        try:
            output = self.agent.run(
                task_input["question"],
                stage_overrides=overrides.get(OVERRIDE_STAGE),
                config_overrides=overrides.get(OVERRIDE_CONFIG),
                recorder=recorder,
            )
        except Exception as exc:
            raise AgentRunError(str(exc), events=recorder.events, error_type=type(exc).__name__) from exc
        return AdapterOutput(output=output, events=recorder.events, agent_version=output["config_version"])


def create_adapter(settings: Settings, **options: Any) -> FaqAdapter:
    """Factory referenced from agents.yaml."""
    return FaqAdapter()
