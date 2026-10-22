"""Common interface that every reviewable agent must implement.

The reviewer core talks to agents only through this interface. Connecting a
new kind of agent (chatbot, coding, research, data analysis, anything else)
means writing, or configuring, one adapter and nothing else.

Adapters declare their *capabilities*. Later phases pick diagnostic
experiments from these: a black-box HTTP agent supports only input-level
tests, while an instrumented in-process agent can also support stage, tool
and configuration overrides.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from .errors import OverrideError

# Override groups an adapter may support.
OVERRIDE_STAGE = "stage_overrides"    # replace one stage's output (counterfactual tests)
OVERRIDE_TOOL = "tool_overrides"      # replace one tool's result (mocked tool)
OVERRIDE_CONFIG = "config_overrides"  # change a copy of the agent configuration

# How much of the run the reviewer can observe.
TRACE_NONE = "none"      # final output only
TRACE_IO = "io"          # input, output, latency
TRACE_EVENTS = "events"  # per-step events (stages, tool calls, LLM calls...)


@dataclass
class TraceEvent:
    """One observable step of an agent run."""

    kind: str   # stage | tool_call | llm_call | retrieval | message | error
    name: str
    input: Any = None
    output: Any = None
    duration_ms: float = 0.0
    overridden: bool = False        # True when an experiment replaced this step's output
    component_version: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentCapabilities:
    trace_level: str = TRACE_IO
    supports_stage_overrides: bool = False
    supports_tool_overrides: bool = False
    supports_config_overrides: bool = False
    deterministic: bool = False  # same input always gives the same output

    def supported_override_keys(self) -> List[str]:
        keys = []
        if self.supports_stage_overrides:
            keys.append(OVERRIDE_STAGE)
        if self.supports_tool_overrides:
            keys.append(OVERRIDE_TOOL)
        if self.supports_config_overrides:
            keys.append(OVERRIDE_CONFIG)
        return keys


@dataclass
class AdapterOutput:
    """What an adapter returns from a successful run."""

    output: Any
    events: List[TraceEvent] = field(default_factory=list)
    agent_version: str = "unknown"
    usage: Dict[str, Any] = field(default_factory=dict)  # tokens, cost, ... when known


@dataclass
class AgentInfo:
    """Static description of a registered agent."""

    agent_id: str
    name: str
    agent_type: str  # chatbot | coding | research | data_analysis | recruitment | custom | ...
    version: str
    description: str
    input_schema: Dict[str, Any]
    capabilities: AgentCapabilities = field(default_factory=AgentCapabilities)
    supported_stages: List[str] = field(default_factory=list)
    supported_tools: List[str] = field(default_factory=list)
    example_inputs: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["supported_overrides"] = self.capabilities.supported_override_keys()
        return data


@dataclass
class AgentResult:
    """Standard result format returned for every execution, success or failure."""

    execution_id: str
    agent_id: str
    agent_version: str
    status: str  # "success" | "error"
    started_at: str
    duration_ms: float
    input: Dict[str, Any]
    overrides: Optional[Dict[str, Any]] = None
    expected: Optional[Dict[str, Any]] = None   # expected outcome, evaluated from Phase 2
    metadata: Optional[Dict[str, Any]] = None
    output: Any = None
    events: List[TraceEvent] = field(default_factory=list)
    usage: Dict[str, Any] = field(default_factory=dict)
    error: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BaseAgentAdapter(ABC):
    """Interface between the reviewer and one target agent."""

    @abstractmethod
    def info(self) -> AgentInfo:
        """Describe the agent, its input schema and its capabilities."""

    @abstractmethod
    def run(self, task_input: Dict[str, Any], overrides: Optional[Dict[str, Any]] = None) -> AdapterOutput:
        """Run one validated input. Raise on failure; the executor records it.

        Raise AgentRunError (with events) to keep the partial trace.
        """

    @property
    def agent_id(self) -> str:
        return self.info().agent_id

    def extra_override_errors(self, overrides: Dict[str, Any]) -> List[str]:
        """Hook for agent-specific checks (valid config keys, output shapes)."""
        return []

    def validate_overrides(self, overrides: Optional[Dict[str, Any]]) -> None:
        """Reject overrides the agent has not declared support for."""
        if not overrides:
            return
        if not isinstance(overrides, dict):
            raise OverrideError(["Overrides must be a JSON object"])

        info = self.info()
        allowed = info.capabilities.supported_override_keys()
        errors: List[str] = []
        for key in overrides:
            if key not in allowed:
                shown = ", ".join(allowed) if allowed else "none"
                errors.append(f"Unsupported override '{key}' for agent '{info.agent_id}' (supported: {shown})")

        checks = ((OVERRIDE_STAGE, info.supported_stages, "stage"), (OVERRIDE_TOOL, info.supported_tools, "tool"))
        for key, valid_names, label in checks:
            if key in allowed and key in overrides:
                value = overrides[key]
                if not isinstance(value, dict):
                    errors.append(f"'{key}' must be an object")
                else:
                    errors += [f"Unknown {label} '{n}'" for n in value if n not in valid_names]
        if OVERRIDE_CONFIG in allowed and OVERRIDE_CONFIG in overrides and not isinstance(overrides[OVERRIDE_CONFIG], dict):
            errors.append(f"'{OVERRIDE_CONFIG}' must be an object")

        if not errors:
            errors = self.extra_override_errors(overrides)
        if errors:
            raise OverrideError(errors)

    def health_check(self) -> bool:
        return True
