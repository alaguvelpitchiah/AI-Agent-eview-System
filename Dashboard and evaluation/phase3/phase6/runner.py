"""Runs the full pipeline and the baseline reviewer on every scenario and returns one row per scenario."""
from __future__ import annotations
from phase3.baseline import baseline_blame
from phase3.evaluation import Case
from phase4.baseline4 import baseline_fix
from phase5.counting import CountingAdapter
from phase5.db import Database
from phase5.orchestrator import ReviewOrchestrator
from .benchmark import AGENT


def _case(d) -> Case:
    return Case(d["case_id"], AGENT, d["input"], d["expected"])


def _broke(adapter, hidden, faults, repair_ids) -> tuple:
    """(#hidden cases passing before the fix, #of those broken by it)."""
    repairs = [adapter.get_repair(AGENT, i) for i in repair_ids]
    before = [c for c in hidden if not adapter.fails(c, faults)]
    return len(before), sum(1 for c in before if adapter.fails(c, faults, repairs))


def run_scenario(adapter, scn, reg, held, hidden, gate_config=None) -> dict:
    faults, target = tuple(scn.faults), _case(scn.target)
    if scn.suite_ids:
        by_id = {c['case_id']: c for c in reg}
        reg = [by_id[i] for i in scn.suite_ids]
    # ---- full pipeline (memory off: every scenario is judged on its own)
    ca = CountingAdapter(adapter)
    orch = ReviewOrchestrator(ca, Database(), gate_config=gate_config, memory_mode="off")
    res = orch.review(AGENT, target, faults, [_case(c) for c in reg], [_case(c) for c in held], use_memory=False)
    sel = [r["repair_id"] for r in res.selected_repairs] if res.outcome == "approval_pending" else []
    dx = res.diagnosis or {}
    n_before, n_broke = _broke(adapter, hidden, faults, sel) if sel else (0, 0)
    # ---- baseline reviewer (blame by trace rules, first repair on that stage that fixes the target)
    cb = CountingAdapter(adapter)
    blamed, bsel = baseline_fix(cb, AGENT, target, faults)
    bn_before, bn_broke = _broke(adapter, hidden, faults, bsel) if bsel else (0, 0)
    return dict(
        sid=scn.sid, kind=scn.kind, faults=list(faults), truth_stages=scn.truth_stages,
        outcome=res.outcome, dx_verdict=dx.get("verdict"), dx_confidence=dx.get("confidence"),
        dx_stages=dx.get("suspected_stages", []),
        pred_pairs=(res.interaction or {}).get("pairs", []), expected_pairs=scn.expected_interaction_pairs,
        pred_conflicts=sorted(sorted([c["repair_a"], c["repair_b"]]) for c in (res.plan or {}).get("conflicts", [])),
        oracle_conflicts=scn.oracle_conflicts,
        pipe_sel=sel, pipe_correct=(adapter.fix_is_correct(faults, sel) if sel else None),
        pipe_hidden_before=n_before, pipe_broke=n_broke, pipe_runs=ca.runs,
        gate_failed=(res.gates or {}).get("failed", []), notes=res.notes,
        base_blamed=blamed, base_sel=bsel, base_correct=(adapter.fix_is_correct(faults, bsel) if bsel else None),
        base_hidden_before=bn_before, base_broke=bn_broke, base_runs=cb.runs)


def run_all(adapter, scenarios, reg, held, hidden, gate_config=None) -> list:
    return [run_scenario(adapter, s, reg, held, hidden, gate_config) for s in scenarios]
