"""One command: build the benchmark, run pipeline + baseline, write results.json, benchmark.json, results.md, report.html.
    python -m phase6.run_benchmark --seed 7 --out phase6_results"""
from __future__ import annotations
import argparse, json, os, time
from .benchmark import build
from .runner import run_all
from .metrics import summarize
from phase5.gates import GateConfig


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default="phase6_results")
    ap.add_argument("--no-report", action="store_true")
    args = ap.parse_args(argv)
    t0 = time.time()
    adapter, pool, reg, held, hidden, scenarios = build(args.seed)
    rows = run_all(adapter, scenarios, reg, held, hidden)
    summary = summarize(rows)
    # post-hoc variant: optional residual-fault gate, added AFTER the first results were seen (reported separately)
    rows_ph = run_all(adapter, scenarios, reg, held, hidden, GateConfig(residual_check=True))
    summary_ph = summarize(rows_ph)
    meta = dict(seed=args.seed, pool=len(pool), reg=len(reg), held=len(held), hidden=len(hidden),
                scenarios=len(scenarios), seconds=round(time.time() - t0, 2))
    os.makedirs(args.out, exist_ok=True)
    dump = lambda name, obj: json.dump(obj, open(os.path.join(args.out, name), "w"), indent=2, default=str)
    dump("benchmark.json", dict(meta=meta, pool=pool, reg=[c["case_id"] for c in reg], held=[c["case_id"] for c in held],
                                hidden=[c["case_id"] for c in hidden], scenarios=[s.to_dict() for s in scenarios]))
    dump("results.json", dict(meta=meta, summary=summary, rows=rows, summary_posthoc=summary_ph, rows_posthoc=rows_ph))
    if not args.no_report:
        from .report import render_markdown, render_html
        md = render_markdown(meta, summary, rows, summary_ph, rows_ph)
        open(os.path.join(args.out, "results.md"), "w").write(md)
        open(os.path.join(args.out, "report.html"), "w").write(render_html(md))
    return meta, summary, rows, summary_ph


if __name__ == "__main__":
    meta, s, rows, ph = main()
    f = lambda d: f"{d['value']:.2f}" if d["value"] is not None else "n/a"
    print(f"{meta['scenarios']} scenarios in {meta['seconds']}s")
    for k in ("rca_exact", "blame_precision", "interaction_recall", "false_interaction_rate", "conflict_recall",
              "conflict_precision", "correct_fix", "unsafe_recommendation", "abstain", "regression_rate"):
        print(f"{k:24} pipeline={f(s[k]['pipeline'])} baseline={f(s[k]['baseline'])}")
    print("mean runs", s["mean_runs"]); print("paired", s["paired"])
    print("-- post-hoc variant (+ residual-fault gate, added after seeing results) --")
    for k in ("correct_fix", "unsafe_recommendation", "abstain", "regression_rate"):
        print(f"{k:24} pipeline={f(ph[k]['pipeline'])}")
    print("mean runs", ph["mean_runs"]["pipeline"])
