"""Validates a set of repairs: it must fix the target case(s) and must not break any
case that currently passes (no-regression rule)."""
from __future__ import annotations
from .models import ValidationResult


class ValidationBudgetExceeded(Exception):
    pass


class RepairValidator:
    def __init__(self, adapter, agent_id, faults, target_cases, regression_cases, max_validations=400):
        self.a, self.agent_id, self.faults = adapter, agent_id, tuple(faults)
        self.targets = list(target_cases)
        tids = {c.case_id for c in self.targets}
        self.regression = [c for c in regression_cases if c.case_id not in tids]
        self.max_validations, self.count, self._cache = max_validations, 0, {}
        self.currently_passing = {c.case_id for c in self.regression if self._passes(c, ())}
        self.regression = [c for c in self.regression if c.case_id in self.currently_passing]

    def _passes(self, case, repairs) -> bool:
        run = self.a.run(self.agent_id, case.input, faults=self.faults, repairs=tuple(repairs))
        return run.status == "success" and self.a.judge(self.agent_id, run, case.expected)

    def validate(self, repairs) -> ValidationResult:
        key = tuple(r.repair_id for r in repairs)
        if key in self._cache:
            return self._cache[key]
        if self.count >= self.max_validations:
            raise ValidationBudgetExceeded()
        self.count += 1
        res = ValidationResult(key,
            target_failures=[c.case_id for c in self.targets if not self._passes(c, repairs)],
            regression_failures=[c.case_id for c in self.regression if not self._passes(c, repairs)])
        self._cache[key] = res
        return res
