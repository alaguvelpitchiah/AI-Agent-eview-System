"""The only seam between Phase 3 and the agents / Phase 2 code.

Implement these four methods for your real system (see phase2_adapter.py).
Contract:
  * run(...) executes the agent. `faults` is the failing run's fault/config
    identifiers (tuple of ids; () means the clean, known-good configuration).
    `overrides` maps stage name -> value. An overridden stage is NOT executed;
    its output is set to the value and the event is marked overridden.
  * Every stage must record an event with its name, the inputs it consumed
    (explicit dict) and its output, in pipeline order.
  * Runs must be deterministic for the same (input, faults, overrides).
"""
from __future__ import annotations
from typing import Protocol, Optional
from .models import RunRecord


class AgentAdapter(Protocol):
    def stage_names(self, agent_id: str) -> list: ...

    def run(self, agent_id: str, input: dict, *, faults: tuple = (),
            overrides: Optional[dict] = None) -> RunRecord: ...

    def judge(self, agent_id: str, run: RunRecord, expected: dict) -> bool:
        """True if the run satisfies `expected` (Phase 2 outcome_evaluator)."""

    def fault_component(self, agent_id: str, fault_id: str) -> str:
        """Ground-truth stage a fault breaks (Phase 2 fault_injector). Used only for evaluation."""
