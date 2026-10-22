"""Adapter for the example tool-using calculator agent."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ...config import Settings
from ...integration.base_adapter import (
    OVERRIDE_CONFIG,
    OVERRIDE_STAGE,
    OVERRIDE_TOOL,
    TRACE_EVENTS,
    AdapterOutput,
    AgentCapabilities,
    AgentInfo,
    BaseAgentAdapter,
)
from ...integration.config_utils import apply_overrides
from ...integration.errors import AgentRunError
from ...integration.tracing import EventRecorder
from .calculator_agent import STAGES, TOOLS, CalculatorAgent


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


class CalculatorAdapter(BaseAgentAdapter):
    AGENT_ID = "calculator-agent"

    def __init__(self, agent: Optional[CalculatorAgent] = None) -> None:
        self.agent = agent or CalculatorAgent()

    def info(self) -> AgentInfo:
        return AgentInfo(
            agent_id=self.AGENT_ID,
            name="Calculator Agent (example)",
            agent_type="tool_using",
            version=self.agent.version,
            description="Turns a math question into an expression, calls a calculator tool and answers.",
            input_schema={
                "fields": {"question": {"type": "str", "required": True, "min_length": 3, "max_length": 500}},
                "allow_extra": False,
            },
            capabilities=AgentCapabilities(
                trace_level=TRACE_EVENTS,
                supports_stage_overrides=True,
                supports_tool_overrides=True,
                supports_config_overrides=True,
                deterministic=True,
            ),
            supported_stages=list(STAGES),
            supported_tools=list(TOOLS),
            example_inputs=[{"question": "What is 12 plus 30 times 2?"}],
        )

    def extra_override_errors(self, overrides: Dict[str, Any]) -> List[str]:
        errors: List[str] = []
        stages = overrides.get(OVERRIDE_STAGE) or {}
        if "plan" in stages and not (isinstance(stages["plan"], dict) and "expression" in stages["plan"]):
            errors.append("Override for 'plan' must be an object containing 'expression'")
        if "respond" in stages and not (isinstance(stages["respond"], dict) and "answer" in stages["respond"]):
            errors.append("Override for 'respond' must be an object containing 'answer'")
        for name, value in (overrides.get(OVERRIDE_TOOL) or {}).items():
            if not _is_number(value):
                errors.append(f"Override for tool '{name}' must be a number")
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
                tool_overrides=overrides.get(OVERRIDE_TOOL),
                config_overrides=overrides.get(OVERRIDE_CONFIG),
                recorder=recorder,
            )
        except Exception as exc:
            raise AgentRunError(str(exc), events=recorder.events, error_type=type(exc).__name__) from exc
        return AdapterOutput(output=output, events=recorder.events, agent_version=output["config_version"])


def create_adapter(settings: Settings, **options: Any) -> CalculatorAdapter:
    """Factory referenced from agents.yaml."""
    return CalculatorAdapter()
