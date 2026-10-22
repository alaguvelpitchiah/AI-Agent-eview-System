"""Known, named faults used to create controlled failures (single faults).

A fault is a set of overrides (config, stage or tool) that makes a healthy agent
misbehave in a specific, known way. Because the faulty component is declared,
later phases can measure how often root-cause diagnosis finds it.

Definitions live in ``data/fault_scenarios/<agent_id>/faults.json``::

    {"agent_id": "...", "faults": [
        {"fault_id": "...", "name": "...", "description": "...",
         "component": "resume_parser", "overrides": {"config_overrides": {...}}}]}
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..integration.agent_executor import AgentExecutor
from ..integration.agent_registry import AgentRegistry
from ..integration.base_adapter import AgentResult
from ..integration.errors import AgentIntegrationError, OverrideError, TaskValidationError


class FaultConfigError(AgentIntegrationError):
    """A fault definition is malformed or not supported by its agent."""


class FaultNotFoundError(AgentIntegrationError):
    def __init__(self, agent_id: str, fault_id: str):
        super().__init__(f"Fault '{fault_id}' is not defined for agent '{agent_id}'")


@dataclass
class Fault:
    fault_id: str
    agent_id: str
    name: str
    description: str
    component: str  # ground truth: where the fault lives
    overrides: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FaultInjector:
    def __init__(self, data_dir: Path, registry: AgentRegistry) -> None:
        self.data_dir = Path(data_dir)
        self.registry = registry
        self._cache: Dict[str, List[Fault]] = {}

    def list_faults(self, agent_id: str) -> List[Fault]:
        adapter = self.registry.get(agent_id)  # AgentNotFoundError
        if agent_id in self._cache:
            return self._cache[agent_id]

        path = self.data_dir / "fault_scenarios" / agent_id / "faults.json"
        if not path.exists():
            self._cache[agent_id] = []
            return []
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise FaultConfigError(f"{path}: invalid JSON ({exc})") from exc

        faults, seen = [], set()
        for item in document.get("faults", []):
            missing = {"fault_id", "name", "component", "overrides"} - set(item)
            if missing:
                raise FaultConfigError(f"{path}: fault {item.get('fault_id', '?')} is missing {sorted(missing)}")
            if item["fault_id"] in seen:
                raise FaultConfigError(f"{path}: duplicate fault_id {item['fault_id']}")
            seen.add(item["fault_id"])
            try:
                adapter.validate_overrides(item["overrides"])
            except OverrideError as exc:
                raise FaultConfigError(f"{path}: fault {item['fault_id']} is not supported by '{agent_id}': {exc}") from exc
            faults.append(Fault(item["fault_id"], agent_id, item["name"], item.get("description", ""), item["component"], item["overrides"]))
        self._cache[agent_id] = faults
        return faults

    def get_fault(self, agent_id: str, fault_id: str) -> Fault:
        for fault in self.list_faults(agent_id):
            if fault.fault_id == fault_id:
                return fault
        raise FaultNotFoundError(agent_id, fault_id)

    def run_with_fault(
        self,
        executor: AgentExecutor,
        agent_id: str,
        task_input: Dict[str, Any],
        fault_id: str,
        expected: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        fault = self.get_fault(agent_id, fault_id)
        meta = {**(metadata or {}), "fault_id": fault.fault_id, "fault_component": fault.component}
        return executor.execute(agent_id, task_input, overrides=fault.overrides, expected=expected, metadata=meta)
