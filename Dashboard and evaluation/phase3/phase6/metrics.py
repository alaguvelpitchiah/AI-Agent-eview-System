"""Aggregates per-scenario rows into the nine headline metrics (+ slices, intervals, paired tests).

Headline metrics (pipeline vs baseline reviewer)
 1 root-cause exact match      diagnosed stage set == oracle-active stage set
 2 blame precision             no stage is blamed that is not a true cause
 3 interaction recall          synergistic stage pairs flagged (baseline never tests, so 0 by design)
 4 false-interaction rate      non-interacting stage pairs flagged as interacting
 5 conflict recall             emergent conflicts found among those visible to the reviewer's suite
 6 conflict precision          reported conflicts that are real
 7 correct-fix rate            recommended fix restores the clean configuration (over ALL scenarios)
 8 regression rate             recommended fixes that break >=1 hidden case that passed before
 9 mean agent runs per scenario"""
from __future__ import annotations
from collections import defaultdict
from .stats import wilson, sign_test


def _rate(k, n):
    lo, hi = wilson(k, n)
    return dict(k=k, n=n, value=(k / n if n else None), ci95=[lo, hi])


def summarize(rows: list) -> dict:
    N = len(rows)
    out = dict(n_scenarios=N)
    # 1, 2
    pe = [set(r["dx_stages"]) == set(r["truth_stages"]) for r in rows]
    be = [{r["base_blamed"]} == set(r["truth_stages"]) for r in rows]
    pp = [bool(r["dx_stages"]) and set(r["dx_stages"]) <= set(r["truth_stages"]) for r in rows]
    bp = [r["base_blamed"] in r["truth_stages"] for r in rows]
    out["rca_exact"] = dict(pipeline=_rate(sum(pe), N), baseline=_rate(sum(be), N))
    out["blame_precision"] = dict(pipeline=_rate(sum(pp), N), baseline=_rate(sum(bp), N))
    # 3, 4 (pair level)
    tp = fn = fp = tn = 0
    for r in rows:
        exp = {frozenset(p) for p in r["expected_pairs"]}
        flagged = {frozenset(p["pair"]) for p in r["pred_pairs"] if p["interacts"]}
        seen = {frozenset(p["pair"]) for p in r["pred_pairs"]}
        tp += len(exp & flagged); fn += len(exp - flagged)
        fp += len(flagged - exp); tn += len(seen - flagged - exp)
    out["interaction_recall"] = dict(pipeline=_rate(tp, tp + fn), baseline=_rate(0, tp + fn))
    out["false_interaction_rate"] = dict(pipeline=_rate(fp, fp + tn), baseline=_rate(0, 0))
    # 5, 6
    ctp = cfn = cfp = 0
    for r in rows:
        o = {tuple(x) for x in r["oracle_conflicts"]}; p = {tuple(x) for x in r["pred_conflicts"]}
        ctp += len(o & p); cfn += len(o - p); cfp += len(p - o)
    out["conflict_recall"] = dict(pipeline=_rate(ctp, ctp + cfn), baseline=_rate(0, ctp + cfn))
    out["conflict_precision"] = dict(pipeline=_rate(ctp, ctp + cfp), baseline=_rate(0, 0))
    # 7
    pc = [r["pipe_correct"] is True for r in rows]
    bc = [r["base_correct"] is True for r in rows]
    out["correct_fix"] = dict(pipeline=_rate(sum(pc), N), baseline=_rate(sum(bc), N))
    prec = [r for r in rows if r["pipe_sel"]]
    brec = [r for r in rows if r["base_sel"]]
    out["unsafe_recommendation"] = dict(pipeline=_rate(sum(1 for r in prec if not r["pipe_correct"]), N),
                                        baseline=_rate(sum(1 for r in brec if not r["base_correct"]), N))
    out["abstain"] = dict(pipeline=_rate(N - len(prec), N), baseline=_rate(N - len(brec), N))
    # 8
    out["regression_rate"] = dict(
        pipeline=_rate(sum(1 for r in prec if r["pipe_broke"] > 0), len(prec)),
        baseline=_rate(sum(1 for r in brec if r["base_broke"] > 0), len(brec)))
    # 9
    out["mean_runs"] = dict(pipeline=sum(r["pipe_runs"] for r in rows) / N, baseline=sum(r["base_runs"] for r in rows) / N)
    # paired tests (exact sign test on discordant scenarios)
    def paired(a, b):
        oa = sum(1 for x, y in zip(a, b) if x and not y); ob = sum(1 for x, y in zip(a, b) if y and not x)
        return dict(pipeline_only=oa, baseline_only=ob, p_value=sign_test(oa, ob))
    out["paired"] = dict(rca_exact=paired(pe, be), correct_fix=paired(pc, bc))
    # slices
    sl = defaultdict(list)
    for r in rows:
        sl[r["kind"]].append(r)
    out["slices"] = {}
    for k, rs in sorted(sl.items()):
        n = len(rs)
        out["slices"][k] = dict(
            n=n,
            rca_exact=dict(pipeline=sum(set(r["dx_stages"]) == set(r["truth_stages"]) for r in rs),
                           baseline=sum({r["base_blamed"]} == set(r["truth_stages"]) for r in rs)),
            correct_fix=dict(pipeline=sum(r["pipe_correct"] is True for r in rs), baseline=sum(r["base_correct"] is True for r in rs)),
            unsafe=dict(pipeline=sum(1 for r in rs if r["pipe_sel"] and not r["pipe_correct"]),
                        baseline=sum(1 for r in rs if r["base_sel"] and not r["base_correct"])),
            abstained=sum(1 for r in rs if not r["pipe_sel"]))
    # where the pipeline went wrong (for the report)
    out["pipeline_misses"] = [dict(sid=r["sid"], truth=r["truth_stages"], diagnosed=r["dx_stages"], outcome=r["outcome"],
                                   selected=r["pipe_sel"], correct=r["pipe_correct"], gate_failed=r["gate_failed"])
                              for r in rows if not (set(r["dx_stages"]) == set(r["truth_stages"]) and r["pipe_correct"] is True)]
    return out
