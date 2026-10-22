import pytest
from phase3.models import Diagnosis
from phase3.root_cause_engine import RootCauseEngine
from phase4.toy_repairs import ToyRepairAdapter, CATALOG
from phase4.demo4 import SCENARIOS, REG, R6, R3, A, M
from phase5.demo5 import HELD, INCIDENTS, R7, payload
from phase5.db import Database
from phase5.gates import GateRunner, GateConfig
from phase5.approval import ApprovalQueue, InvalidTransition
from phase5.memory import FailureMemory, jaccard
from phase5.jobs import JobRunner
from phase5.orchestrator import ReviewOrchestrator
from phase5.evaluation5 import gate_effectiveness, memory_ablation

ad = ToyRepairAdapter()
RP = {r.repair_id: r for rs in CATALOG.values() for r in rs}
F03 = ("TOY-F03",)


def _dx(faults=F03, case=R6):
    return RootCauseEngine(ad).diagnose(A, case.input, case.expected, faults)


# ---------- gates
def test_true_fix_passes_every_gate():
    rep = GateRunner(ad).evaluate(A, F03, [R6], REG, HELD, _dx(), [RP["RP3"]])
    assert rep.passed and len(rep.results) == 8


def test_compensating_fix_is_blocked_by_heldout_coverage_and_scope():
    rep = GateRunner(ad).evaluate(A, F03, [R6], REG, HELD, _dx(), [RP["RP5"]])
    assert not rep.passed
    assert {"heldout_no_regression", "root_cause_coverage", "no_compensating"} <= set(rep.failed)
    assert "target_fixed" not in rep.failed and "no_regression" not in rep.failed   # looked fine to the usual tests


def test_missing_heldout_is_a_hard_failure_unless_configured():
    assert "heldout_no_regression" in GateRunner(ad).evaluate(A, F03, [R6], REG, [], _dx(), [RP["RP3"]]).failed
    ok = GateRunner(ad, GateConfig(require_heldout=False)).evaluate(A, F03, [R6], REG, [], _dx(), [RP["RP3"]])
    assert ok.passed


def test_low_confidence_diagnosis_blocked():
    d = Diagnosis(A, "single_root_cause", ["score"], "medium")
    assert "diagnosis_confirmed" in GateRunner(ad).evaluate(A, F03, [R6], REG, HELD, d, [RP["RP3"]]).failed


def test_unfixed_target_blocked():
    rep = GateRunner(ad).evaluate(A, F03, [R6], REG, HELD, _dx(), [RP["RP4"]])
    assert "target_fixed" in rep.failed


# ---------- approval
def test_approval_state_machine():
    q = ApprovalQueue(Database())
    i = q.create("r1", A, {"repairs": [{"repair_id": "RP3"}]})
    with pytest.raises(InvalidTransition):
        q.apply(i)                                   # cannot apply before approval
    with pytest.raises(InvalidTransition):
        q.approve(i, "  ")                           # reviewer must be named
    q.approve(i, "alice", "ok")
    with pytest.raises(InvalidTransition):
        q.approve(i, "bob")                          # no double decision
    with pytest.raises(InvalidTransition):
        q.reject(i, "bob")
    assert q.apply(i) == [{"repair_id": "RP3"}]
    assert q.get(i)["status"] == "applied" and q.get(i)["reviewer"] == "alice"
    with pytest.raises(InvalidTransition):
        q.apply(i)
    with pytest.raises(KeyError):
        q.approve(999, "alice")


def test_rejected_request_cannot_be_applied():
    q = ApprovalQueue(Database())
    i = q.create("r", A, {"repairs": []})
    q.reject(i, "alice", "no")
    with pytest.raises(InvalidTransition):
        q.apply(i)


# ---------- memory
def test_memory_similarity_version_and_status_rules():
    m = FailureMemory(Database())
    f = {"a", "b", "c", "d"}
    mid = m.record(A, "1.0.0", f, ["score"], ["RP3"])
    assert m.lookup(A, "1.0.0", f)[0]["record"]["id"] == mid
    assert m.lookup(A, "1.0.0", {"a", "b", "c", "z"}, 0.85) == []        # similarity 0.6 < 0.85
    assert m.lookup(A, "2.0.0", f) == []                                  # other agent version
    assert m.lookup("other", "1.0.0", f) == []
    assert m.record(A, "1.0.0", f, ["score"], ["RP3"]) == mid             # dedupe
    assert m.get(mid)["confirmations"] == 2
    m.record(A, "1.0.0", {"x", "y"}, ["decide"], ["RP4"], "rejected")
    assert m.lookup(A, "1.0.0", {"x", "y"}) == []                         # rejected never suggested
    m.mark_reuse(mid, False); m.mark_reuse(mid, False)
    assert m.lookup(A, "1.0.0", f) == []                                  # humans rejected it more than accepted
    assert jaccard({1}, {1}) == 1.0


# ---------- orchestrator
def test_full_pipeline_reaches_approval_and_learns():
    o = ReviewOrchestrator(ad, Database())
    r = o.review(A, R6, F03, REG, HELD)
    assert r.outcome == "approval_pending" and [x["repair_id"] for x in r.selected_repairs] == ["RP3"]
    assert [s["step"] for s in r.steps] == ["monitor", "memory_lookup", "diagnose", "interaction", "plan", "gates"]
    assert r.gates["passed"] and r.memory["reused_record"] is None
    assert o.memory.lookup(A, "1.0.0", set(o.approvals.get(r.approval_request_id)["payload"]["features"])) == []  # not learned yet
    o.approve(r.approval_request_id, "alice")
    assert len(o.memory.lookup(A, "1.0.0", set(o.approvals.get(r.approval_request_id)["payload"]["features"]))) == 1
    assert o.reviews.get(r.review_id)["outcome"] == "approval_pending"


def test_memory_reuse_is_cheaper_and_still_gated():
    from phase5.counting import CountingAdapter
    c = CountingAdapter(ToyRepairAdapter())
    o = ReviewOrchestrator(c, Database())
    r1 = o.review(A, R6, F03, REG, HELD); o.approve(r1.approval_request_id, "alice")
    full = c.runs
    c.runs = 0
    r2 = o.review(A, R7, F03, REG, HELD)
    assert r2.memory["reused_record"] and r2.outcome == "approval_pending" and r2.gates["passed"]
    assert c.runs < full
    assert [s["step"] for s in r2.steps] == ["monitor", "memory_lookup", "memory_confirm"]   # diagnosis skipped, gates ran


def test_lookalike_failure_with_different_cause_is_not_fooled_by_memory():
    o = ReviewOrchestrator(ad, Database())
    r1 = o.review(A, R6, F03, REG, HELD); o.approve(r1.approval_request_id, "alice")
    r3 = o.review(A, R3, ("TOY-F04",), REG, HELD)
    assert r3.memory["hits"] and r3.memory["rejected_hits"] and r3.memory["reused_record"] is None
    assert [x["repair_id"] for x in r3.selected_repairs] == ["RP4"]


def test_blind_memory_applies_the_wrong_fix():
    o = ReviewOrchestrator(ad, Database(), memory_mode="blind_ablation")
    r1 = o.review(A, R6, F03, REG, HELD); o.approve(r1.approval_request_id, "alice")
    r3 = o.review(A, R3, ("TOY-F04",), REG, HELD)
    assert [x["repair_id"] for x in r3.selected_repairs] == ["RP3"]          # wrong cause, wrong fix


def test_no_failure_and_inconclusive_outcomes():
    o = ReviewOrchestrator(ad, Database())
    assert o.review(A, R6, (), REG, HELD).outcome == "no_failure"
    bad = type(R6)("Z", A, R6.input, {"decision": "reject"})   # even the clean agent fails this expectation
    r = o.review(A, bad, (), REG, HELD)
    assert r.outcome == "inconclusive" and r.approval_request_id is None and any("Reference" in n for n in r.notes)


def test_no_validated_fix_never_creates_an_approval_request():
    class NoRepairs(ToyRepairAdapter):
        def candidate_repairs(self, agent_id, stage):
            return []
    o = ReviewOrchestrator(NoRepairs(), Database())
    r = o.review(A, R6, F03, REG, HELD)
    assert r.outcome == "no_validated_fix" and r.approval_request_id is None and o.approvals.list() == []


def test_gate_failure_blocks_even_when_planner_found_a_fix():
    o = ReviewOrchestrator(ad, Database())
    r = o.review(A, R6, F03, REG, [])                                         # no held-out cases -> hard gate fails
    assert r.outcome == "no_validated_fix" and "heldout_no_regression" in r.gates["failed"]
    assert r.approval_request_id is None


def test_rejection_is_recorded_and_not_suggested_again():
    o = ReviewOrchestrator(ad, Database())
    r1 = o.review(A, R6, F03, REG, HELD)
    o.reject(r1.approval_request_id, "alice", "no")
    r2 = o.review(A, R7, F03, REG, HELD)
    assert r2.memory["hits"] == [] and r2.outcome == "approval_pending"       # rejected fix not recalled, fresh diagnosis
    with pytest.raises(InvalidTransition):
        o.apply(r1.approval_request_id)


# ---------- jobs
def test_job_success_progress_and_listing():
    db = Database(); o = ReviewOrchestrator(ad, db); jr = JobRunner(db); o.register_with(jr)
    jid = jr.submit("review", payload(R6, F03))
    assert jr.get(jid)["status"] == "queued"
    assert jr.run_pending() == 1
    j = jr.get(jid)
    assert j["status"] == "succeeded" and j["result"]["outcome"] == "approval_pending"
    assert "running hard gates" in j["progress"] and len(jr.list("succeeded")) == 1


def test_job_retry_then_fail_and_cancel():
    db = Database(); jr = JobRunner(db, max_retries=2)
    calls = []
    jr.register("boom", lambda p, c: calls.append(1) or (_ for _ in ()).throw(RuntimeError("nope")))
    jid = jr.submit("boom", {})
    jr.run_pending()
    j = jr.get(jid)
    assert j["status"] == "failed" and j["attempts"] == 3 and len(calls) == 3 and "RuntimeError" in j["error"]
    j2 = jr.submit("boom", {})
    assert jr.cancel(j2) and jr.get(j2)["status"] == "cancelled" and jr.run_pending() == 0
    with pytest.raises(ValueError):
        jr.submit("unknown", {})


def test_job_that_succeeds_on_retry():
    db = Database(); jr = JobRunner(db, max_retries=1)
    state = {"n": 0}
    def flaky(p, c):
        state["n"] += 1
        if state["n"] == 1:
            raise RuntimeError("transient")
        return {"ok": True}
    jr.register("flaky", flaky)
    jid = jr.submit("flaky", {}); jr.run_pending()
    assert jr.get(jid)["status"] == "succeeded" and jr.get(jid)["attempts"] == 2


def test_background_workers_process_jobs_concurrently():
    db = Database(); o = ReviewOrchestrator(ad, db); jr = JobRunner(db); o.register_with(jr)
    jr.start(3)
    try:
        ids = [jr.submit("review", payload(R6, F03)) for _ in range(4)]
        done = [jr.wait(i, 20) for i in ids]
    finally:
        jr.stop()
    assert all(d["status"] == "succeeded" and d["attempts"] == 1 for d in done)
    assert len(o.approvals.list("pending")) == 4


def test_job_with_bad_fault_id_fails_cleanly():
    db = Database(); o = ReviewOrchestrator(ad, db); jr = JobRunner(db, max_retries=0); o.register_with(jr)
    jid = jr.submit("review", payload(R6, ("NOPE",)))
    jr.run_pending()
    assert jr.get(jid)["status"] == "failed" and "KeyError" in jr.get(jid)["error"]


# ---------- evaluation
def test_gate_effectiveness_numbers():
    g = gate_effectiveness(ad, SCENARIOS, HELD)
    assert g["safe_blocked_by_gates"] == 0
    assert g["unsafe_blocked_by_gates"] > g["unsafe_passed_by_gates"]
    assert g["unsafe_passed_by_gates"] == 1                                   # RP1+RP6: indistinguishable by any test


def test_memory_ablation_numbers():
    m = memory_ablation(ToyRepairAdapter, INCIDENTS, REG, HELD)
    assert m["off"]["wrong_fixes"] == 0 and m["validated"]["wrong_fixes"] == 0
    assert m["blind_ablation"]["wrong_fixes"] == 1
    assert m["validated"]["total_runs"] < m["off"]["total_runs"]
    assert m["validated"]["reuses"] == 2 and m["validated"]["correct_fixes"] == 4
