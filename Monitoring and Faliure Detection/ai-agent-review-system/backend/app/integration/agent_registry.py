"""Registry of the agents the reviewer can connect to."""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from ..config import Settings, get_settings
from .base_adapter import AgentInfo, BaseAgentAdapter
from .errors import AgentNotFoundError, DuplicateAgentError


class AgentRegistry:
    def __init__(self) -> None:
        self._adapters: Dict[str, BaseAgentAdapter] = {}
        self._lock = threading.Lock()

    def register(self, adapter: BaseAgentAdapter) -> None:
        agent_id = adapter.agent_id
        with self._lock:
            if agent_id in self._adapters:
                raise DuplicateAgentError(agent_id)
            self._adapters[agent_id] = adapter

    def unregister(self, agent_id: str) -> None:
        with self._lock:
            if agent_id not in self._adapters:
                raise AgentNotFoundError(agent_id)
            del self._adapters[agent_id]

    def get(self, agent_id: str) -> BaseAgentAdapter:
        with self._lock:
            adapter = self._adapters.get(agent_id)
        if adapter is None:
            raise AgentNotFoundError(agent_id)
        return adapter

    def list_info(self) -> List[AgentInfo]:
        with self._lock:
            adapters = list(self._adapters.values())
        return [a.info() for a in adapters]

    def __contains__(self, agent_id: str) -> bool:
        with self._lock:
            return agent_id in self._adapters

    def __len__(self) -> int:
        with self._lock:
            return len(self._adapters)


def build_default_registry(settings: Optional[Settings] = None) -> AgentRegistry:
    """Build the registry from the agents configuration file (agents.yaml)."""
    from .adapter_loader import load_registry  # local import: loader pulls in adapters

    return load_registry(settings or get_settings())
