"""Markdown + HTML report generated from results (no live runs, fully reproducible from results.json)."""
from __future__ import annotations
import html, re

METRICS = [
    ("1", "Root-cause exact match", "rca_exact", "diagnosed stage set equals the oracle-active stage set"),
    ("2", "Blame precision", "blame_precision", "no stage blamed that is not a true cause"),
    ("3", "Interaction recall", "interaction_recall", "synergistic stage pairs flagged (baseline never tests)"),
    ("4", "False-interaction rate", "false_interaction_rate", "non-interacting pairs flagged (lower is better)"),
    ("5", "Conflict recall", "conflict_recall", "emergent repair conflicts found"),
    ("6", "Conflict precision", "conflict_precision", "reported conflicts that are real"),
    ("7", "Correct-fix rate", "correct_fix", "recommended fix restores the clean configuration (all scenarios)"),
    ("8", "Regression rate", "regression_rate", "recommended fixes breaking >=1 hidden case (lower is better)"),
]


def fmt(d) -> str:
    if d is None or d["value"] is None:
        return "n/a"
    lo, hi = d["ci95"]
    return f"{d['value']:.2f} [{lo:.2f}-{hi:.2f}] ({d['k']}/{d['n']})"


def _table(head, body) -> str:
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(map(str, r)) + " |" for r in body])


LIMITATIONS = [
    "**One toy agent.** A deterministic 4-stage resume matcher whose stages are pure functions and whose faults are "
    "configuration patches. Results show the method works on replayable, deterministic, stage-structured agents; they do not "
    "show it works on LLM agents, stochastic agents or code-level bugs.",
    "**I wrote everything the system is graded on.** Faults, the repair catalog, the case pool and the oracle are mine. The oracle "
    "is independent code (it calls the stage functions directly) but it encodes the same structural assumption as the engine "
    "(stage outputs replaced by reference values), so near-perfect root-cause accuracy here is expected, not impressive.",
    "**Held-out fault types are only partly held out.** Faults F05-F07 did not exist when Phases 3-5 were written, but the first "
    "full run was seen before this report was finalised. One weakness it exposed (residual faults passing the gates) led to a "
    "post-hoc change, which is why that variant is reported separately and should not be read as unbiased.",
    "**The generic rollback repair is strong.** Every fault is a config patch, so 'roll the stage back to its known-good config' "
    "always works. Real faults (prompt changes, tool bugs, data drift) usually have no such one-step undo.",
    "**Small samples.** 39 scenarios in five groups of 6-12; the 95% intervals are wide and group-level differences are "
    "anecdotal. The conflict counts (metrics 5-6) are inflated by repetition: the same two repair pairs recur across about ten scenarios, so 20/20 is closer to two distinct conflicts found repeatedly. The paired sign tests treat scenarios as independent, but several share a fault and differ only in the input.",
    "**Conflict ground truth depends on the suites.** 'Conflict' means emergent failure (A alone passes, B alone passes, A+B fails) "
    "for pairs that are valid on the reviewer's own suite. The six conflict-trap scenarios are seeded by construction with a "
    "deliberately sparse suite, so they test the mechanism, not the ability to find unknown conflicts.",
    "**Gates are only as strong as the suites.** A repair no test exercises passes. The shipped gates also checked coverage by "
    "stage name, not by effect, which is exactly how three wrong fixes got through (see 'Where the pipeline went wrong').",
    "**Cost.** The pipeline uses roughly two to three orders of magnitude more agent runs than the baseline because it validates "
    "many repair sets exhaustively. Cheap here, expensive for an LLM agent; pruning or sequential search is future work.",
    "**Not measured:** CPU/memory use, nondeterminism (no repeated trials were needed because the agent is deterministic), "
    "and any second-person test design (a single author wrote all cases).",
    "**Not verified against the real Phase 2 code.** The adapter to the real system is an unfilled template; the FastAPI routers "
    "and the Streamlit dashboard have never been run in this environment.",
]


def render_markdown(meta, summary, rows, summary_ph=None, rows_ph=None) -> str:
    L = []
    add = L.append
    kinds = {}
    for r in rows:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    add("# AI Agent Review System - Final Evaluation\n")
    add(f"Seed {meta['seed']}; case pool {meta['pool']} (planning {meta['reg']}, gate held-out {meta['held']}, hidden {meta['hidden']}); "
        f"{meta['scenarios']} scenarios ({', '.join(f'{k}: {v}' for k, v in sorted(kinds.items()))}). "
        "Pipeline = monitor, diagnose, interaction test, repair plan, hard gates (memory off). "
        "Baseline = blame by trace rules, first repair on that stage that fixes the target, no validation.\n")
    add("## Headline results\n")
    body = [(n, name, fmt(summary[key]["pipeline"]), fmt(summary[key]["baseline"]), note) for n, name, key, note in METRICS]
    body.append(("9", "Mean agent runs per scenario", f"{summary['mean_runs']['pipeline']:.0f}", f"{summary['mean_runs']['baseline']:.1f}", "cost"))
    add(_table(["#", "Metric", "Pipeline", "Baseline", "Meaning"], body))
    add("\nRates show value [95% Wilson interval] (k/n). The baseline never tests interactions or conflicts, so metrics 3, 5 are 0 by "
        "design and 4, 6 are undefined for it.\n")
    add("### Other outcomes\n")
    add(_table(["Outcome", "Pipeline", "Baseline"], [
        ("Recommended a fix that is not correct", fmt(summary["unsafe_recommendation"]["pipeline"]), fmt(summary["unsafe_recommendation"]["baseline"])),
        ("Abstained (no fix recommended)", fmt(summary["abstain"]["pipeline"]), fmt(summary["abstain"]["baseline"]))]))
    pr = summary["paired"]
    add("\n### Paired comparison (exact sign test on discordant scenarios)\n")
    add(_table(["Outcome", "Pipeline only", "Baseline only", "p"], [
        ("Root-cause exact", pr["rca_exact"]["pipeline_only"], pr["rca_exact"]["baseline_only"], f"{pr['rca_exact']['p_value']:.1e}"),
        ("Correct fix", pr["correct_fix"]["pipeline_only"], pr["correct_fix"]["baseline_only"], f"{pr['correct_fix']['p_value']:.1e}")]))
    add("\n## Results by scenario group\n")
    add(_table(["Group", "n", "RCA exact (pipe / base)", "Correct fix (pipe / base)", "Wrong fix recommended (pipe / base)", "Abstained (pipe)"],
               [(k, v["n"], f"{v['rca_exact']['pipeline']} / {v['rca_exact']['baseline']}",
                 f"{v['correct_fix']['pipeline']} / {v['correct_fix']['baseline']}",
                 f"{v['unsafe']['pipeline']} / {v['unsafe']['baseline']}", v["abstained"]) for k, v in summary["slices"].items()]))
    add("\n`single_heldout` uses fault types never seen in Phases 3-5; `conflict_trap` is seeded by construction (sparse planning suite).\n")

    def show(title, r):
        add(f"### {title}\n")
        add(f"- Scenario `{r['sid']}`; injected faults {r['faults']}; oracle root-cause stages {r['truth_stages']}.")
        add(f"- Pipeline diagnosis: {r['dx_stages']} ({r['dx_verdict']}, confidence {r['dx_confidence']}).")
        fl = [p["pair"] for p in r["pred_pairs"] if p["interacts"]]
        add(f"- Interaction test: {'flagged ' + str(fl) if fl else 'no interaction flagged'}; expected {r['expected_pairs'] or 'none'}.")
        add(f"- Conflicts reported {r['pred_conflicts'] or 'none'}; oracle {r['oracle_conflicts'] or 'none'}.")
        add(f"- Pipeline recommends {r['pipe_sel'] or 'nothing'} (correct: {r['pipe_correct']}); baseline blamed `{r['base_blamed']}` and "
            f"applied {r['base_sel'] or 'nothing'} (correct: {r['base_correct']}; breaks {r['base_broke']} of {r['base_hidden_before']} hidden cases).\n")

    add("## Two worked cases\n")
    syn = next((r for r in rows if r["kind"] == "double_synergistic"), None)
    trap = next((r for r in rows if r["kind"] == "conflict_trap"), None)
    if syn:
        show("Interacting faults (each alone passes, together they fail)", syn)
    if trap:
        show("Repair conflict (fix A and fix B each pass, A+B fails)", trap)

    add("## Where the pipeline went wrong (as shipped)\n")
    miss = summary["pipeline_misses"]
    if not miss:
        add("No misses.\n")
    else:
        add(_table(["Scenario", "Oracle stages", "Diagnosed", "Recommended", "Correct", "Gates failed"],
                   [(m["sid"], m["truth"], m["diagnosed"], m["selected"], m["correct"], m["gate_failed"]) for m in miss]))
        add("\nThe recommended repairs pass every shipped gate yet leave a fault in place: `RP2` clears only the `drop` setting, so "
            "it does nothing for the held-out `min_len` fault, and the coverage gate checks stage names, not effects.\n")
    if summary_ph:
        add("## Post-hoc variant (NOT a clean result)\n")
        add("After seeing the misses above I added an optional gate that re-runs stage isolation with the repairs applied (no stage may "
            "still deviate from the reference) and made the orchestrator fall back to the next-ranked repair set when one is blocked. "
            "These changes were designed with knowledge of this benchmark, so the numbers below are optimistic and need fresh faults.\n")
        add(_table(["Metric", "As shipped", "Post-hoc"], [
            ("Correct-fix rate", fmt(summary["correct_fix"]["pipeline"]), fmt(summary_ph["correct_fix"]["pipeline"])),
            ("Wrong fix recommended", fmt(summary["unsafe_recommendation"]["pipeline"]), fmt(summary_ph["unsafe_recommendation"]["pipeline"])),
            ("Abstained", fmt(summary["abstain"]["pipeline"]), fmt(summary_ph["abstain"]["pipeline"])),
            ("Regression rate", fmt(summary["regression_rate"]["pipeline"]), fmt(summary_ph["regression_rate"]["pipeline"])),
            ("Mean agent runs", f"{summary['mean_runs']['pipeline']:.0f}", f"{summary_ph['mean_runs']['pipeline']:.0f}")]))
        add("")
    add("## Limitations\n")
    for t in LIMITATIONS:
        add(f"- {t}")
    add("\n## Reproduce\n")
    add("`python -m phase6.run_benchmark --seed 7 --out phase6_results` rebuilds the benchmark and regenerates every file here "
        "(`benchmark.json`, `results.json`, `results.md`, `report.html`).")
    return "\n".join(L) + "\n"


def _inline(t: str) -> str:
    t = html.escape(t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    return re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)


def render_html(md: str) -> str:
    out, lines, i = [], md.split("\n"), 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("|"):
            blk = []
            while i < len(lines) and lines[i].startswith("|"):
                blk.append(lines[i]); i += 1
            rows = [[c.strip() for c in b.strip().strip("|").split("|")] for b in blk if not set(b.replace("|", "").strip()) <= {"-"}]
            out.append("<div class='scroll'><table><thead><tr>" + "".join(f"<th>{_inline(c)}</th>" for c in rows[0]) + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>" for r in rows[1:]) + "</tbody></table></div>")
            continue
        m = re.match(r"(#+) (.*)", ln)
        if m:
            out.append(f"<h{len(m.group(1))}>{_inline(m.group(2))}</h{len(m.group(1))}>")
        elif ln.startswith("- "):
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(f"<li>{_inline(lines[i][2:])}</li>"); i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue
        elif ln.strip():
            out.append(f"<p>{_inline(ln)}</p>")
        i += 1
    css = ("body{font:15px/1.5 system-ui,sans-serif;max-width:1000px;margin:2rem auto;padding:0 1rem;color:#1b1b1b;background:#fff}"
           "table{border-collapse:collapse;font-size:13px}td,th{border:1px solid #ccc;padding:4px 8px;text-align:left}th{background:#f2f2f2}"
           "code{background:#f2f2f2;padding:1px 4px;border-radius:3px}.scroll{overflow-x:auto;margin:.5rem 0}"
           "@media(prefers-color-scheme:dark){body{color:#e6e6e6;background:#161616}th{background:#2a2a2a}td,th{border-color:#444}code{background:#2a2a2a}}")
    return ("<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>Final Evaluation</title><style>{css}</style></head><body>" + "\n".join(out) + "</body></html>")
