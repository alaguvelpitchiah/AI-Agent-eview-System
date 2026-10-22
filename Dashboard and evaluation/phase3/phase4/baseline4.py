"""Baseline fixer: blame a stage with the Phase 3 baseline rules, then apply the first repair
for that stage that fixes the target case. No regression check, no conflict test."""
from __future__ import annotations
from phase3.baseline import baseline_blame


def baseline_fix(adapter, agent_id, target_case, faults=()):
    stages = adapter.stage_names(agent_id)
    failing = adapter.run(agent_id, target_case.input, faults=tuple(faults))
    blamed = baseline_blame(failing, stages)
    for r in adapter.candidate_repairs(agent_id, blamed):
        run = adapter.run(agent_id, target_case.input, faults=tuple(faults), repairs=(r,))
        if run.status == "success" and adapter.judge(agent_id, run, target_case.expected):
            return blamed, [r.repair_id]
    return blamed, []
