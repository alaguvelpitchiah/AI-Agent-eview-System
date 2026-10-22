"""Scores the engine and the baseline against ground-truth fault components."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Case:
    case_id: str
    agent_id: str
    input: dict
    expected: dict
    faults: tuple = ()


def evaluate(adapter, engine, cases: list) -> dict:
    from .baseline import baseline_blame
    rows, not_failing = [], 0
    for c in cases:
        truth = {adapter.fault_component(c.agent_id, f) for f in c.faults}
        failing = adapter.run(c.agent_id, c.input, faults=c.faults)
        dx = engine.diagnose(c.agent_id, c.input, c.expected, c.faults, failing_run=failing)
        if dx.verdict == "no_failure":
            not_failing += 1
            continue
        base = baseline_blame(failing, adapter.stage_names(c.agent_id))
        rows.append(dict(case=c.case_id, faults=list(c.faults), truth=sorted(truth),
                         verdict=dx.verdict, engine=dx.suspected_stages, baseline=base,
                         pattern=dx.interaction_pattern, confidence=dx.confidence,
                         experiments=len(dx.experiments),
                         engine_exact=set(dx.suspected_stages) == truth,
                         baseline_exact=(truth == {base}),
                         baseline_hit=base in truth))
    n = len(rows) or 1
    multi = [r for r in rows if len(r["truth"]) > 1]
    return dict(
        evaluated=len(rows), not_failing=not_failing,
        engine_exact_rate=sum(r["engine_exact"] for r in rows) / n,
        baseline_exact_rate=sum(r["baseline_exact"] for r in rows) / n,
        baseline_hit_rate=sum(r["baseline_hit"] for r in rows) / n,
        joint_detection_rate=(sum(r["verdict"] == "joint_root_cause" for r in multi) / len(multi)) if multi else None,
        mean_experiments=sum(r["experiments"] for r in rows) / n,
        rows=rows)
