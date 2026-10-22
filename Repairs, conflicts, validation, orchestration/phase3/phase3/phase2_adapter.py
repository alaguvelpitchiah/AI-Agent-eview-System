"""TEMPLATE: wire Phase 3 to your real Phase 2 code.

I could not see the Phase 2 zip, so these bodies are intentionally unfilled.
Map each method to the matching Phase 2 call (names below are guesses):
"""
from __future__ import annotations
from .models import RunRecord, StageEvent


class Phase2Adapter:
    def __init__(self, registry, evaluator, fault_injector):
        self.registry, self.evaluator, self.faults = registry, evaluator, fault_injector

    def stage_names(self, agent_id):
        # ordered stage list from the agent's declared capabilities
        raise NotImplementedError

    def run(self, agent_id, input, *, faults=(), overrides=None):
        # 1. get the agent, apply Phase 2 fault overrides for each id in `faults`
        # 2. execute with stage overrides (skip stage, use given output)
        # 3. convert the Phase 2 trace to RunRecord([StageEvent(name, input, output, error)])
        raise NotImplementedError

    def judge(self, agent_id, run, expected):
        # call Phase 2 outcome_evaluator on run.output with `expected`; return verdict == "pass"
        raise NotImplementedError

    def fault_component(self, agent_id, fault_id):
        # read fault_component from data/fault_scenarios/<agent_id>/faults.json
        raise NotImplementedError
