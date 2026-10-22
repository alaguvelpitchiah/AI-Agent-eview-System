"""Phase 5 evaluation: (A) do the hard gates catch unsafe fixes that a target-only check accepts?
(B) memory ablation: no memory vs validated memory vs blind memory (cost and wrong fixes)."""
from __future__ import annotations
from itertools import combinations
from phase3.root_cause_engine import RootCauseEngine
from .gates import GateRunner
from .counting import CountingAdapter
from .db import Database
from .orchestrator import ReviewOrchestrator


def _all_repairs(adapter, agent_id):
    return [r for s in adapter.stage_names(agent_id) for r in adapter.candidate_repairs(agent_id, s)]


def gate_effectiveness(adapter, scenarios, heldout) -> dict:
    eng, gr = RootCauseEngine(adapter), GateRunner(adapter)
    cat = _all_repairs(adapter, scenarios[0].agent_id)
    rows, naive_n = [], 0
    for s in scenarios:
        t = s.target
        dx = eng.diagnose(s.agent_id, t.input, t.expected, s.faults)
        truth = {adapter.true_repair(s.agent_id, f) for f in s.faults}
        for k in (1, 2):
            for combo in combinations(cat, k):
                if len({r.stage for r in combo}) < k:
                    continue
                run_ok = all(adapter.judge(s.agent_id, (rr := adapter.run(s.agent_id, t.input, faults=s.faults, repairs=combo)), t.expected)
                             and rr.status == "success" for _ in [0])
                if not run_ok:
                    continue                                       # a target-only check would reject it anyway
                naive_n += 1
                rep = gr.evaluate(s.agent_id, s.faults, [t], s.regression, heldout, dx, combo)
                rows.append(dict(scenario=s.name, repairs=[r.repair_id for r in combo], safe={r.repair_id for r in combo} == truth,
                                 gate_passed=rep.passed, failed=rep.failed))
    unsafe = [r for r in rows if not r["safe"]]
    safe = [r for r in rows if r["safe"]]
    return dict(proposals_accepted_by_target_check=len(rows), unsafe=len(unsafe), safe=len(safe),
                unsafe_passed_by_gates=sum(r["gate_passed"] for r in unsafe),
                unsafe_blocked_by_gates=sum(not r["gate_passed"] for r in unsafe),
                safe_blocked_by_gates=sum(not r["gate_passed"] for r in safe),
                rows=rows)


def memory_ablation(adapter_factory, incidents, regression, heldout) -> dict:
    """incidents: list of (Case, faults). Each strategy sees them in order; fixes are auto-approved
    (reviewer='eval') so memory can learn. Wrong fix = selected repairs != ground-truth repairs."""
    out = {}
    for mode in ("off", "validated", "blind_ablation"):
        ad = CountingAdapter(adapter_factory())
        orch = ReviewOrchestrator(ad, Database(), memory_mode=mode)
        rows = []
        for case, faults in incidents:
            before = ad.runs
            res = orch.review(case.agent_id, case, faults, regression, heldout)
            truth = {ad.true_repair(case.agent_id, f) for f in faults}
            sel = {r["repair_id"] for r in res.selected_repairs}
            rows.append(dict(case=case.case_id, outcome=res.outcome, selected=sorted(sel), correct=sel == truth,
                             runs=ad.runs - before, memory_reused=res.memory["reused_record"],
                             rejected_hits=len(res.memory["rejected_hits"])))
            if res.approval_request_id:
                orch.approve(res.approval_request_id, "eval")
        out[mode] = dict(total_runs=ad.runs, wrong_fixes=sum(1 for r in rows if r["selected"] and not r["correct"]),
                         correct_fixes=sum(r["correct"] for r in rows), reuses=sum(1 for r in rows if r["memory_reused"]),
                         rows=rows)
    return out
