"""Data layer for the dashboard (no UI imports, so it is testable)."""
from __future__ import annotations
import json, os
from phase3.evaluation import Case
from phase5.db import Database
from phase5.gates import GateConfig
from phase5.orchestrator import ReviewOrchestrator
from .benchmark import build, AGENT
from .metrics import summarize
from .report import METRICS, fmt


def load_results(out_dir: str) -> dict:
    return json.load(open(os.path.join(out_dir, "results.json")))


def metric_table(summary: dict) -> list:
    rows = [dict(metric=f"{n}. {name}", pipeline=fmt(summary[key]["pipeline"]), baseline=fmt(summary[key]["baseline"]))
            for n, name, key, _ in METRICS]
    rows.append(dict(metric="9. Mean agent runs", pipeline=f"{summary['mean_runs']['pipeline']:.0f}",
                     baseline=f"{summary['mean_runs']['baseline']:.1f}"))
    return rows


def slice_table(summary: dict) -> list:
    return [dict(group=k, n=v["n"], rca_pipeline=v["rca_exact"]["pipeline"], rca_baseline=v["rca_exact"]["baseline"],
                 fix_pipeline=v["correct_fix"]["pipeline"], fix_baseline=v["correct_fix"]["baseline"],
                 wrong_pipeline=v["unsafe"]["pipeline"], wrong_baseline=v["unsafe"]["baseline"]) for k, v in summary["slices"].items()]


def scenario_ids(seed: int = 7) -> list:
    return [s.sid for s in build(seed)[5]]


def walkthrough(sid: str, seed: int = 7, residual_check: bool = False) -> dict:
    """Runs one scenario live through the full pipeline and returns every intermediate artefact."""
    adapter, pool, reg, held, hidden, scenarios = build(seed)
    scn = next(s for s in scenarios if s.sid == sid)
    mk = lambda d: Case(d["case_id"], AGENT, d["input"], d["expected"])
    suite = [c for c in reg if c["case_id"] in scn.suite_ids] if scn.suite_ids else reg
    orch = ReviewOrchestrator(adapter, Database(), gate_config=GateConfig(residual_check=residual_check), memory_mode="off")
    res = orch.review(AGENT, mk(scn.target), tuple(scn.faults), [mk(c) for c in suite], [mk(c) for c in held], use_memory=False)
    d = res.to_dict()
    d["scenario"] = scn.to_dict()
    d["approval"] = orch.approvals.get(res.approval_request_id) if res.approval_request_id else None
    return d
