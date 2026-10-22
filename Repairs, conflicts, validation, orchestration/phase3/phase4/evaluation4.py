"""Scores Phase 4 against seeded ground truth and against the baseline fixer."""
from __future__ import annotations
from dataclasses import dataclass, field
from phase3.root_cause_engine import RootCauseEngine
from .interaction_analyzer import InteractionAnalyzer
from .repair_planner import RepairPlanner
from .baseline4 import baseline_fix


@dataclass
class Scenario:
    name: str
    agent_id: str
    target: object                 # phase3.evaluation.Case that fails under `faults`
    faults: tuple
    regression: list
    seeded_conflicts: set = field(default_factory=set)       # {frozenset({"RP3","RP5"})}
    expected_interactions: set = field(default_factory=set)  # {frozenset({"extract_skills","score"})}


def evaluate4(adapter, scenarios) -> dict:
    eng, ia, planner = RootCauseEngine(adapter), InteractionAnalyzer(adapter), RepairPlanner(adapter)
    rows = []
    tp = fp = fn = tn = 0
    c_tp = c_fp = c_fn = 0
    for s in scenarios:
        t = s.target
        dx = eng.diagnose(s.agent_id, t.input, t.expected, s.faults)
        rep = ia.analyze(s.agent_id, t.input, t.expected, s.faults, dx.suspected_stages)
        plan = planner.plan(s.agent_id, dx, [t], s.regression, s.faults)
        blamed, bsel = baseline_fix(adapter, s.agent_id, t, s.faults)
        truth = {adapter.true_repair(s.agent_id, f) for f in s.faults}
        for p in rep.pairs:
            key, exp = frozenset(p["pair"]), frozenset(p["pair"]) in s.expected_interactions
            tp += p["interacts"] and exp; fp += p["interacts"] and not exp
            fn += (not p["interacts"]) and exp; tn += (not p["interacts"]) and not exp
        pred = {frozenset((c.repair_a, c.repair_b)) for c in plan.conflicts}
        c_tp += len(pred & s.seeded_conflicts); c_fp += len(pred - s.seeded_conflicts)
        c_fn += len(s.seeded_conflicts - pred)

        def hazard(sel):   # selection contains a repair seeded as conflicting with a true repair
            return any(frozenset((x, y)) in s.seeded_conflicts for x in sel for y in truth if x != y)
        rows.append(dict(scenario=s.name, faults=list(s.faults), truth=sorted(truth),
                         diagnosis=dx.suspected_stages, interaction=rep.summary,
                         plan_status=plan.status, planner=plan.selected, baseline_blamed=blamed,
                         baseline=bsel, planner_correct=set(plan.selected) == truth,
                         baseline_correct=set(bsel) == truth,
                         planner_hazard=hazard(plan.selected), baseline_hazard=hazard(bsel),
                         conflicts=[sorted([c.repair_a, c.repair_b]) for c in plan.conflicts],
                         warnings=plan.warnings, validations=plan.validations_used))
    n = len(rows) or 1
    div = lambda a, b: (a / b) if b else None
    return dict(
        scenarios=len(rows),
        planner_fix_rate=sum(r["planner_correct"] for r in rows) / n,
        baseline_fix_rate=sum(r["baseline_correct"] for r in rows) / n,
        planner_hazard_rate=sum(r["planner_hazard"] for r in rows) / n,
        baseline_hazard_rate=sum(r["baseline_hazard"] for r in rows) / n,
        interaction_recall=div(tp, tp + fn), interaction_precision=div(tp, tp + fp),
        false_interaction_rate=div(fp, fp + tn),
        conflict_recall=div(c_tp, c_tp + c_fn), conflict_precision=div(c_tp, c_tp + c_fp),
        rows=rows)
