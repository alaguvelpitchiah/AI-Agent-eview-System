"""Exceptions raised by the integration layer."""
from __future__ import annotations

from typing import Any, List, Optional


class AgentIntegrationError(Exception):
    """Base class for all integration-layer errors."""


class AgentNotFoundError(AgentIntegrationError):
    def __init__(self, agent_id: str):
        super().__init__(f"Agent '{agent_id}' is not registered")
        self.agent_id = agent_id


class DuplicateAgentError(AgentIntegrationError):
    def __init__(self, agent_id: str):
        super().__init__(f"Agent '{agent_id}' is already registered")
        self.agent_id = agent_id


class AdapterConfigError(AgentIntegrationError):
    """An agent entry in the agents configuration file is invalid."""


class TaskValidationError(AgentIntegrationError):
    """The submitted input does not match the agent's input schema."""

    def __init__(self, errors: List[str]):
        super().__init__("; ".join(errors))
        self.errors = list(errors)


class OverrideError(TaskValidationError):
    """The submitted overrides are not supported or are malformed."""


class AgentRunError(AgentIntegrationError):
    """A failure inside an agent run that keeps the trace gathered so far.

    Adapters raise this (instead of a bare exception) so the executor can store
    the events recorded before the failure; they are the evidence the
    root-cause engine needs.
    """

    def __init__(self, message: str, events: Optional[List[Any]] = None, error_type: str = "AgentRunError"):
        super().__init__(message)
        self.events = list(events or [])
        self.error_type = error_type
