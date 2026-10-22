"""Generates candidate repairs from a Phase 3 diagnosis.

Root-cause candidates target the diagnosed stages. Downstream candidates target later
stages and can only *compensate* for an upstream fault; they are kept as candidates
because they often look correct on tests, and the conflict analyzer exists to catch them.
Plug an LLM in by implementing RepairProposer.propose(...) -> list[Candidate]."""
from __future__ import annotations
from typing import Protocol
from .models import Candidate


class RepairProposer(Protocol):
    def propose(self, agent_id: str, diagnosis, stages: list) -> list: ...


class AdapterProposer:
    """Uses adapter.candidate_repairs(agent_id, stage) -> list[Repair]."""
    def __init__(self, adapter, include_downstream: bool = True):
        self.a, self.include_downstream = adapter, include_downstream

    def propose(self, agent_id, diagnosis, stages):
        susp = [s for s in stages if s in set(diagnosis.suspected_stages)]
        out = [Candidate(r, "root_cause") for s in susp for r in self.a.candidate_repairs(agent_id, s)]
        if self.include_downstream and susp:
            first = stages.index(susp[0])
            for s in stages[first + 1:]:
                if s not in susp:
                    out += [Candidate(r, "downstream_compensation") for r in self.a.candidate_repairs(agent_id, s)]
        return out
