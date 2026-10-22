import json, os, tempfile
import pytest
from phase3.models import RunRecord
from phase5.gates import GateRunner, GateConfig
from phase5.db import Database
from phase5.orchestrator import ReviewOrchestrator
from phase3.evaluation import Case
from phase3.root_cause_engine import RootCauseEngine
from phase6.benchmark import build, make_pool, split_pool, SPARSE_IDS, TRAP_TARGET_IDS, AGENT
from phase6.bench_toy import BenchAdapter
from phase6.stats import wilson, sign_test
from phase6.metrics import summarize
from phase6.report import render_markdown, render_html, LIMITATIONS
from phase6 import dashboard_data as dd
from phase6.run_benchmark import main

ad = BenchAdapter()


@pytest.fixture(scope="module")
def bench():
    return build(7)


@pytest.fixture(scope="module")
def full_run():
    out = tempfile.mkdtemp()
    meta, summary, rows, ph = main(["--out", out, "--seed", "7"])
    return out, meta, summary, rows, ph


# ---------- benchmark construction
def test_pool_expected_values_come_from_the_spec_and_clean_agent_satisfies_them():
    pool = make_pool()
    assert len(pool) == 54 and len({c["case_id"] for c in pool}) == 54
    assert not [c["case_id"] for c in pool if ad.fails(c)]
    for c in pool:                                     # spec: match iff matched/required >= 0.5
        n, k = int(c["case_id"][3]), int(c["case_id"][5])
        assert c["expected"]["decision"] == ("match" if k / n >= 0.5 else "reject")


def test_splits_are_disjoint_and_sparse_suite_is_planning_only():
    pool = make_pool()
    reg, held, hidden = split_pool(pool, 7)
    ids = lambda xs: {c["case_id"] for c in xs}
    assert not (ids(reg) & ids(held)) and not (ids(reg) & ids(hidden)) and not (ids(held) & ids(hidden))
    assert ids(reg) | ids(held) | ids(hidden) == ids(pool)
    assert set(SPARSE_IDS) <= ids(reg) and set(TRAP_TARGET_IDS) <= ids(reg)


def test_benchmark_is_deterministic_and_seed_changes_splits(bench):
    again = build(7)
    assert [s.sid for s in again[5]] == [s.sid for s in bench[5]]
    assert [c["case_id"] for c in again[4]] == [c["case_id"] for c in bench[4]]
    assert [c["case_id"] for c in build(8)[4]] != [c["case_id"] for c in bench[4]]


def test_scenario_mix_matches_the_brief(bench):
    sc = bench[5]
    kinds = {k: sum(1 for s in sc if s.kind == k) for k in {s.kind for s in sc}}
    assert 30 <= len(sc) <= 50
    assert kinds["single_heldout"] == 9 and kinds["conflict_trap"] == 6
    assert kinds["double_synergistic"] >= 5 and kinds["double_independent"] >= 5       # decoys exist
    assert all(s.target["case_id"] not in {c["case_id"] for c in bench[4]} for s in sc)   # targets never come from hidden


def test_every_scenario_really_fails_and_synergy_labels_are_correct(bench):
    for s in bench[5]:
        assert ad.fails(s.target, s.faults)
        if s.kind == "double_synergistic":
            a, b = s.faults
            assert not ad.fails(s.target, (a,)) and not ad.fails(s.target, (b,))
            assert len(s.expected_interaction_pairs) == 1
        if s.kind == "double_independent":
            assert all(ad.fails(s.target, (f,)) for f in s.faults) and not s.expected_interaction_pairs


# ---------- oracle
def test_oracle_active_faults_and_fix_correctness():
    plain = dict(resume="experienced developer with python and sql", required=["python", "sql"])
    assert ad.active_faults(plain, ["TOY-F02"]) == ["TOY-F02"]
    assert ad.active_faults(dict(resume="developer with python", required=["python", "sql"]), ["TOY-F02"]) == []   # latent
    assert ad.active_faults(plain, ["TOY-F05"]) == []                                  # lowercase text: case-sensitivity inert
    assert ad.active_faults(dict(resume="5 years with python", required=["python"]), ["TOY-F07"]) == ["TOY-F07"]  # crash
    assert ad.fix_is_correct(("TOY-F03",), ["RP3"]) and ad.fix_is_correct(("TOY-F03",), ["RS-score"])
    assert not ad.fix_is_correct(("TOY-F03",), ["RP5"])                                # compensates, config differs
    assert not ad.fix_is_correct(("TOY-F06",), ["RP2"])                                # does not undo min_len
    assert ad.fix_is_correct(("TOY-F02", "TOY-F03"), ["RP2", "RP3"])


# ---------- statistics
def test_wilson_and_sign_test():
    lo, hi = wilson(0, 10)
    assert lo == 0.0 and abs(hi - 0.2775) < 1e-3
    assert wilson(0, 0) == (None, None)
    lo, hi = wilson(10, 10)
    assert hi == 1.0 and abs(lo - 0.7225) < 1e-3
    assert sign_test(10, 0) == pytest.approx(2 / 1024)
    assert sign_test(5, 5) == 1.0 and sign_test(0, 0) == 1.0
    assert 0 < sign_test(7, 2) < 0.2


def _row(**kw):
    base = dict(sid="s", kind="k", faults=[], truth_stages=["a"], dx_stages=["a"], pred_pairs=[], expected_pairs=[],
                pred_conflicts=[], oracle_conflicts=[], pipe_sel=["R"], pipe_correct=True, pipe_broke=0, pipe_runs=10,
                base_blamed="a", base_sel=["R"], base_correct=True, base_broke=0, base_runs=2, outcome="approval_pending",
                gate_failed=[], dx_verdict="single_root_cause", dx_confidence="high")
    base.update(kw)
    return base


def test_metric_math_on_hand_built_rows():
    rows = [_row(),
            _row(dx_stages=["b"], pipe_correct=False, base_blamed="b", base_correct=False, base_broke=2),
            _row(truth_stages=["a", "c"], dx_stages=["a", "c"], expected_pairs=[["a", "c"]],
                 pred_pairs=[{"pair": ["a", "c"], "interacts": True}], oracle_conflicts=[["R1", "R2"]], pred_conflicts=[["R1", "R2"], ["R3", "R4"]]),
            _row(pipe_sel=[], pipe_correct=None, outcome="no_validated_fix", dx_stages=[])]
    s = summarize(rows)
    assert s["rca_exact"]["pipeline"]["k"] == 2 and s["rca_exact"]["baseline"]["k"] == 2   # rows 1 and 4 for the baseline
    assert s["blame_precision"]["pipeline"]["k"] == 2              # row 2 blames a wrong stage, row 4 blames nothing
    assert s["interaction_recall"]["pipeline"]["k"] == 1 and s["interaction_recall"]["pipeline"]["n"] == 1
    assert (s["conflict_recall"]["pipeline"]["k"], s["conflict_recall"]["pipeline"]["n"]) == (1, 1)
    assert (s["conflict_precision"]["pipeline"]["k"], s["conflict_precision"]["pipeline"]["n"]) == (1, 2)
    assert s["correct_fix"]["pipeline"]["k"] == 2 and s["abstain"]["pipeline"]["k"] == 1
    assert s["regression_rate"]["baseline"]["k"] == 1 and s["regression_rate"]["baseline"]["n"] == 4
    assert s["unsafe_recommendation"]["pipeline"]["k"] == 1


# ---------- residual gate + ranked fallback (post-hoc additions)
def test_residual_gate_catches_a_fix_that_leaves_a_fault_behind(bench):
    reg = bench[2]
    scn = next(s for s in bench[5] if s.faults == ["TOY-F03", "TOY-F06"])
    t = Case(scn.target["case_id"], AGENT, scn.target["input"], scn.target["expected"])
    dx = RootCauseEngine(ad).diagnose(AGENT, t.input, t.expected, tuple(scn.faults))
    repairs = [ad.get_repair(AGENT, i) for i in ("RP2", "RP3")]
    mk = lambda cs: [Case(c["case_id"], AGENT, c["input"], c["expected"]) for c in cs]
    base = GateRunner(ad).evaluate(AGENT, scn.faults, [t], mk(bench[2]), mk(bench[3]), dx, repairs)
    strict = GateRunner(ad, GateConfig(residual_check=True)).evaluate(AGENT, scn.faults, [t], mk(bench[2]), mk(bench[3]), dx, repairs)
    assert base.passed and not strict.passed and strict.failed == ["no_residual_fault"]


def test_orchestrator_falls_back_to_next_ranked_repair_set(bench):
    scn = next(s for s in bench[5] if s.faults == ["TOY-F03", "TOY-F06"])
    w = dd.walkthrough(scn.sid, residual_check=True)
    assert w["outcome"] == "approval_pending" and len(w["gate_attempts"]) >= 2
    assert w["gate_attempts"][0]["passed"] is False and w["gate_attempts"][-1]["passed"] is True
    assert ad.fix_is_correct(scn.faults, [r["repair_id"] for r in w["selected_repairs"]])


# ---------- end-to-end benchmark
def test_full_run_writes_all_files_and_headline_invariants(full_run):
    out, meta, s, rows, ph = full_run
    assert {"benchmark.json", "results.json", "results.md", "report.html"} <= set(os.listdir(out))
    assert meta["scenarios"] == len(rows) == s["n_scenarios"]
    assert s["rca_exact"]["pipeline"]["value"] > s["rca_exact"]["baseline"]["value"]
    assert s["correct_fix"]["pipeline"]["value"] > s["correct_fix"]["baseline"]["value"]
    assert s["regression_rate"]["pipeline"]["value"] == 0 and s["regression_rate"]["baseline"]["value"] > 0
    assert s["mean_runs"]["pipeline"] > 100 * s["mean_runs"]["baseline"]               # the cost is real and reported
    # no recommended fix ever failed the target case it was meant to fix
    targets = {sc.sid: sc.target for sc in build(7)[5]}
    for r in rows:
        if r["pipe_sel"]:
            assert not ad.fails(targets[r["sid"]], r["faults"], [ad.get_repair(AGENT, i) for i in r["pipe_sel"]]), r["sid"]


def test_documented_failure_is_reproduced(full_run):
    _, _, s, rows, ph = full_run
    misses = s["pipeline_misses"]
    assert len(misses) == 3 and all("F03+F06" in m["sid"] for m in misses)            # residual-fault weakness
    assert all(m["diagnosed"] == m["truth"] and m["correct"] is False for m in misses)
    assert ph["pipeline_misses"] == [] and ph["correct_fix"]["pipeline"]["k"] == ph["n_scenarios"]


def test_baseline_never_beats_pipeline_on_diagnosis(full_run):
    _, _, s, rows, ph = full_run
    assert s["paired"]["rca_exact"]["baseline_only"] < s["paired"]["rca_exact"]["pipeline_only"]
    held = s["slices"]["single_heldout"]
    assert held["rca_exact"]["pipeline"] >= held["rca_exact"]["baseline"]


def test_run_is_reproducible(full_run):
    out, *_ = full_run
    a = json.load(open(os.path.join(out, "results.json")))
    meta2, s2, rows2, ph2 = main(["--out", tempfile.mkdtemp(), "--seed", "7", "--no-report"])
    assert a["summary"] == json.loads(json.dumps(s2, default=str)) and a["rows"] == json.loads(json.dumps(rows2, default=str))


# ---------- report and dashboard data
def test_report_contents_and_html(full_run):
    out, meta, s, rows, ph = full_run
    md = open(os.path.join(out, "results.md")).read()
    for h in ("## Headline results", "## Results by scenario group", "## Two worked cases", "## Where the pipeline went wrong",
              "## Post-hoc variant (NOT a clean result)", "## Limitations", "## Reproduce"):
        assert h in md
    assert md.count("\n- **") >= len(LIMITATIONS) - 1 and "Interacting faults" in md and "Repair conflict" in md
    page = open(os.path.join(out, "report.html")).read()
    assert page.startswith("<!doctype html>") and page.count("<table>") >= 5 and "prefers-color-scheme" in page
    assert "<script" not in page
    assert "<b>" in render_html("**x** <y>") and "&lt;y&gt;" in render_html("**x** <y>")


def test_dashboard_data_layer(full_run, bench):
    out, meta, s, rows, ph = full_run
    res = dd.load_results(out)
    assert len(dd.metric_table(res["summary"])) == 9 and len(dd.slice_table(res["summary"])) == 5
    sid = next(x.sid for x in bench[5] if x.kind == "double_synergistic")
    w = dd.walkthrough(sid)
    assert w["interaction"]["summary"] == "synergistic" and w["scenario"]["sid"] == sid
    assert [x["step"] for x in w["steps"]] == ["monitor", "diagnose", "interaction", "plan", "gates"]
    trap = next(x.sid for x in bench[5] if x.kind == "conflict_trap")
    wt = dd.walkthrough(trap)
    assert any({c["repair_a"], c["repair_b"]} == {"RP3", "RP5"} for c in wt["plan"]["conflicts"])
    assert wt["approval"]["status"] == "pending"
    assert len(dd.scenario_ids(7)) == len(bench[5])


def test_dashboard_script_compiles():
    import py_compile
    py_compile.compile(os.path.join(os.path.dirname(__file__), "..", "phase6", "dashboard.py"), doraise=True)
