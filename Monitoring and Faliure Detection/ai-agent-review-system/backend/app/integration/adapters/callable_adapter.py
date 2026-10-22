"""Wrap any Python function as a reviewable agent (coding, data analysis, custom)."""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from ..base_adapter import AdapterOutput, AgentInfo, BaseAgentAdapter


class CallableAgentAdapter(BaseAgentAdapter):
    """Adapter for an in-process function ``fn(task_input, overrides) -> result``.

    ``fn`` may return an AdapterOutput (to supply events and usage) or any
    JSON-serialisable value, which becomes the output with no trace events.
    Declare override support in ``info.capabilities`` only if ``fn`` honours it.
    """

    def __init__(self, info: AgentInfo, fn: Callable[[Dict[str, Any], Optional[Dict[str, Any]]], Any]) -> None:
        self._info = info
        self._fn = fn

    def info(self) -> AgentInfo:
        return self._info

    def run(self, task_input: Dict[str, Any], overrides: Optional[Dict[str, Any]] = None) -> AdapterOutput:
        result = self._fn(task_input, overrides)
        if isinstance(result, AdapterOutput):
            if result.agent_version == "unknown":
                result.agent_version = self._info.version
            return result
        return AdapterOutput(output=result, agent_version=self._info.version)
