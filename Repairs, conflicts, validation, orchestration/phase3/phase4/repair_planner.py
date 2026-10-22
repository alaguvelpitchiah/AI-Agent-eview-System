"""Plans a repair: generate -> validate each -> find conflicts -> search validated sets -> select.

Selection order: (1) cover every diagnosed stage, (2) fewest compensating (non-root-cause) repairs,
(3) smallest set. If no set validates, the outcome is "no_validated_fix" - never a guess."""
from __future__ import annotations
from itertools import combinations
from .models import RepairPlan
from .repair_generator import AdapterProposer
from .validation import RepairValidator, ValidationBudgetExceeded
from .conflict_analyzer import ConflictAnalyzer


class RepairPlanner:
    def __init__(self, adapter, proposer=None, max_set_size: int = 3, max_candidates: int = 10,
                 max_validations: int = 400):
        self.a = adapter
        self.proposer = proposer or AdapterProposer(adapter)
        self.max_set_size, self.max_candidates, self.max_validations = max_set_size, max_candidates, max_validations

    def plan(self, agent_id, diagnosis, target_cases, regression_cases, faults=()) -> RepairPlan:
        plan = RepairPlan(agent_id=agent_id, status="no_validated_fix")
        stages = self.a.stage_names(agent_id)
        if diagnosis.verdict not in ("single_root_cause", "joint_root_cause"):
            plan.rationale.append(f"Diagnosis verdict is '{diagnosis.verdict}'; no root cause to repair.")
            return plan
        susp = set(diagnosis.suspected_stages)
        cands = self.proposer.propose(agent_id, diagnosis, stages)[: self.max_candidates]
        if not cands:
            plan.rationale.append("No candidate repairs available for the diagnosed stages.")
            return plan
        role = {c.repair.repair_id: c.role for c in cands}
        by_id = {c.repair.repair_id: c.repair for c in cands}
        v = RepairValidator(self.a, agent_id, faults, target_cases, regression_cases, self.max_validations)
        try:
            valid_singles = []
            for c in cands:
                r = v.validate((c.repair,))
                plan.candidates.append(dict(repair_id=c.repair.repair_id, stage=c.repair.stage, role=c.role,
                                            valid=r.valid, target_failures=r.target_failures,
                                            regression_failures=r.regression_failures))
                if r.valid:
                    valid_singles.append(c.repair)
            plan.conflicts = ConflictAnalyzer(v).analyze(valid_singles)

            order = {s: i for i, s in enumerate(stages)}
            solutions = []
            for k in range(1, self.max_set_size + 1):
                for combo in combinations(cands, k):
                    if len({c.repair.stage for c in combo}) < k:
                        continue                       # at most one repair per stage
                    rs = tuple(c.repair for c in sorted(combo, key=lambda c: order[c.repair.stage]))
                    if v.validate(rs).valid:
                        solutions.append(rs)
        except ValidationBudgetExceeded:
            plan.warnings.append("Validation budget exhausted; the search was cut short.")
            solutions = [rs for rs in [tuple(by_id[i] for i in key) for key, res in v._cache.items() if res.valid]]
        plan.validations_used = v.count

        if not solutions:
            plan.rationale.append("No repair set fixes the target case without breaking a passing case.")
            return plan

        def key(rs):
            stg = {r.stage for r in rs}
            return (len(susp - stg), sum(r.stage not in susp for r in rs), len(rs), [r.repair_id for r in rs])
        best = min(solutions, key=key)
        plan.status, plan.selected = "validated_fix", [r.repair_id for r in best]
        plan.rationale.append("Selected the validated set that covers the most diagnosed stages with the "
                              "fewest compensating repairs.")
        sel = set(plan.selected)
        for c in plan.conflicts:
            if {c.repair_a, c.repair_b} & sel:
                other = c.repair_b if c.repair_a in sel else c.repair_a
                plan.warnings.append(f"{other} passes validation alone but conflicts with "
                                     f"{c.repair_a if other == c.repair_b else c.repair_b} "
                                     f"({c.kind}; fails {sorted(set(c.failed_cases))}). Do not apply both.")
        for r in valid_singles:
            if role[r.repair_id] == "downstream_compensation" and r.repair_id not in sel:
                plan.warnings.append(f"{r.repair_id} ({r.stage}) also passes the tests but only compensates "
                                     "downstream of the diagnosed fault; it was not selected.")
        return plan
