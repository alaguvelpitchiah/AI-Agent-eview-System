"""End-to-end demo: background jobs -> pipeline -> hard gates -> human approval -> failure memory."""
from phase3.evaluation import Case
from phase4.toy_repairs import ToyRepairAdapter
from phase4.demo4 import REG, R6, R3, SCENARIOS, A, C, M, X
from .db import Database
from .jobs import JobRunner
from .orchestrator import ReviewOrchestrator
from .evaluation5 import gate_effectiveness, memory_ablation

RW = C("RW", "python sql", ["python", "sql", "java", "aws", "docker"], X)     # held-out: clean 0.4 -> reject
RV = C("RV", "python", ["python", "sql", "docker", "java"], X)                  # held-out: clean 0.25 -> reject
HELD = [RW, RV]
R7 = C("R7", "I know sql", ["python", "sql"], M)
R8 = C("R8", "sql", ["python", "sql"], M)
INCIDENTS = [(R6, ("TOY-F03",)), (R7, ("TOY-F03",)), (R3, ("TOY-F04",)), (R8, ("TOY-F03",))]


def payload(case, faults):
    d = lambda c: dict(case_id=c.case_id, input=c.input, expected=c.expected)
    return dict(agent_id=A, target=d(case), faults=list(faults), regression=[d(c) for c in REG], heldout=[d(c) for c in HELD])


if __name__ == "__main__":
    db, ad = Database(), ToyRepairAdapter()
    orch, runner = ReviewOrchestrator(ad, db), JobRunner(db)
    orch.register_with(runner)
    runner.start(2)
    for case, faults in INCIDENTS:
        job = runner.wait(runner.submit("review", payload(case, faults)))
        r = job["result"]
        print(f"\n{case.case_id} faults={faults} -> {r['outcome']}  selected={[x['repair_id'] for x in r['selected_repairs']]}")
        print("  steps:", [(s['step'], s['status']) for s in r["steps"]])
        if r["memory"]["rejected_hits"]:
            print("  memory hit rejected:", r["memory"]["rejected_hits"])
        if r["memory"]["reused_record"]:
            print("  reused memory record", r["memory"]["reused_record"])
        if r["approval_request_id"]:
            orch.approve(r["approval_request_id"], "alice", "looks right")
            print("  approved ->", [x["repair_id"] for x in orch.apply(r["approval_request_id"])], "applied")
    runner.stop()
    g = gate_effectiveness(ad, SCENARIOS, HELD)
    print("\nGate effectiveness:", {k: v for k, v in g.items() if k != "rows"})
    m = memory_ablation(ToyRepairAdapter, INCIDENTS, REG, HELD)
    for mode, v in m.items():
        print(f"memory={mode:15} runs={v['total_runs']:3} correct={v['correct_fixes']} wrong={v['wrong_fixes']} reuses={v['reuses']}")
