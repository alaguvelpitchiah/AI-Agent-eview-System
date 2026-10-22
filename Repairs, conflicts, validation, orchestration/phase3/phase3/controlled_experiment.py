"""Runs counterfactual experiments against the agent, within a budget."""
from __future__ import annotations
from typing import Optional
from .models import Experiment, RunRecord
from .evidence_analyzer import values_equal


class BudgetExhausted(Exception):
    pass


class ExperimentRunner:
    def __init__(self, adapter, agent_id: str, input: dict, expected: dict,
                 faults: tuple, reference: RunRecord, failing: RunRecord,
                 stages: list, budget: int):
        self.a, self.agent_id, self.input, self.expected = adapter, agent_id, input, expected
        self.faults, self.ref, self.failing = faults, reference, failing
        self.stages, self.budget = stages, budget
        self.log: list = []

    def _record(self, kind, target, outcome, detail=""):
        self.log.append(Experiment(len(self.log) + 1, kind, tuple(target), outcome, detail))

    def _run(self, overrides: dict) -> RunRecord:
        if len(self.log) >= self.budget:
            raise BudgetExhausted()
        return self.a.run(self.agent_id, self.input, faults=self.faults, overrides=overrides)

    def stage_is_faulty(self, stage: str) -> bool:
        """Give `stage` the reference outputs of every earlier stage, then check
        whether its own output still departs from the reference."""
        if len(self.log) >= self.budget:
            raise BudgetExhausted()
        idx = self.stages.index(stage)
        ref_ev = self.ref.event(stage)
        if idx == 0:
            obs = self.failing.event(stage)           # already observed, no new run needed
            run = None
        else:
            overrides = {s: self.ref.event(s).output for s in self.stages[:idx]}
            run = self._run(overrides)
            obs = run.event(stage)
        faulty = obs is None or obs.error is not None or not values_equal(obs.output, ref_ev.output)
        self._record("stage_isolation", [stage], faulty,
                     "with clean upstream inputs the stage output "
                     + ("differs from" if faulty else "matches") + " the reference"
                     + ("" if run is not None else " (read from the original failing run)"))
        return faulty

    def repair_passes(self, subset: tuple) -> bool:
        """Replace only `subset` stages with reference outputs; others stay as in the failing run."""
        run = self._run({s: self.ref.event(s).output for s in subset})
        ok = run.status == "success" and self.a.judge(self.agent_id, run, self.expected)
        self._record("repair", subset, ok,
                     "run passes" if ok else "run still fails")
        return ok
