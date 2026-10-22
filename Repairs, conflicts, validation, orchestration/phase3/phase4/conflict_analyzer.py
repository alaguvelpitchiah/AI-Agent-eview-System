"""Repair-conflict detection: fix A passes, fix B passes, A+B fails.
Only pairs whose members each validate on their own are tested."""
from __future__ import annotations
from itertools import combinations
from .models import Conflict


class ConflictAnalyzer:
    def __init__(self, validator):
        self.v = validator

    def analyze(self, valid_repairs: list) -> list:
        conflicts = []
        for a, b in combinations(valid_repairs, 2):
            overlap = a.stage == b.stage and bool(set(a.patch) & set(b.patch))
            ab = self.v.validate((a, b))
            if overlap:
                ba = self.v.validate((b, a))
                if ab.valid != ba.valid:
                    conflicts.append(Conflict(a.repair_id, b.repair_id, "order_dependent",
                        ab.target_failures + ab.regression_failures + ba.target_failures + ba.regression_failures,
                        "result depends on which of the two writes to the same setting is applied last"))
                    continue
            if not ab.valid:
                conflicts.append(Conflict(a.repair_id, b.repair_id,
                    "overlapping_write" if overlap else "interaction",
                    ab.target_failures + ab.regression_failures,
                    f"each passes alone, together they fail: {ab.target_failures + ab.regression_failures}"))
        return conflicts
