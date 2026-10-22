"""End-to-end review pipeline: monitor -> memory -> diagnose -> interact -> plan -> HARD GATES -> approval.

Outcomes: no_failure | inconclusive | no_validated_fix | approval_pending.
Nothing is applied automatically. A fix needs every gate AND a named human reviewer.
Adapter needs (beyond Phases 3-4): get_repair(agent_id, repair_id) and, optionally, agent_version(agent_id)."""
from __future__ import annotations
import json, time, uuid
from dataclasses import dataclass, field, replace
from phase3.evaluation import Case
from phase3.models import Diagnosis
from phase3.root_cause_engine import RootCauseEngine
from phase4.interaction_analyzer import InteractionAnalyzer
from phase4.repair_planner import RepairPlanner
from .db import Database
from .gates import GateConfig, GateRunner
from .memory import FailureMemory, symptom_features
from .approval import ApprovalQueue


@dataclass
class ReviewResult:
    review_id: str
    agent_id: str
    outcome: str = "pending"
    steps: list = field(default_factory=list)
    diagnosis: dict = None
    interaction: dict = None
    plan: dict = None
    gates: dict = None
    selected_repairs: list = field(default_factory=list)
    approval_request_id: int = None
    memory: dict = field(default_factory=lambda: dict(hits=[], rejected_hits=[], reused_record=None))
    notes: list = field(default_factory=list)

    def to_dict(self):
        return dict(self.__dict__)


class ReviewStore:
    def __init__(self, db: Database):
        self.db = db
        db.execute("CREATE TABLE IF NOT EXISTS reviews(review_id TEXT PRIMARY KEY, agent_id TEXT, outcome TEXT, "
                   "payload TEXT, created_at REAL)")

    def save(self, res: ReviewResult):
        self.db.execute("INSERT OR REPLACE INTO reviews VALUES (?,?,?,?,?)",
                        (res.review_id, res.agent_id, res.outcome, json.dumps(res.to_dict(), default=str), time.time()))

    def get(self, review_id):
        r = self.db.query("SELECT payload FROM reviews WHERE review_id=?", (review_id,))
        return json.loads(r[0][0]) if r else None


def case_from_dict(agent_id, d) -> Case:
    return Case(d["case_id"], agent_id, d["input"], d["expected"])


class ReviewOrchestrator:
    def __init__(self, adapter, db: Database = None, gate_config: GateConfig = None,
                 memory_mode: str = "validated", min_similarity: float = 0.85, max_experiments: int = 40):
        assert memory_mode in ("validated", "off", "blind_ablation")   # blind_ablation exists only to measure the risk
        self.a, self.db = adapter, db or Database()
        self.cfg, self.memory_mode, self.min_similarity = gate_config or GateConfig(), memory_mode, min_similarity
        self.engine, self.inter = RootCauseEngine(adapter, max_experiments), InteractionAnalyzer(adapter)
        self.planner = RepairPlanner(adapter)
        self.memory, self.approvals, self.reviews = FailureMemory(self.db), ApprovalQueue(self.db), ReviewStore(self.db)

    # ---------- helpers
    def _version(self, agent_id):
        return self.a.agent_version(agent_id) if hasattr(self.a, "agent_version") else "unknown"

    @staticmethod
    def _log(res, name, t0, status="ok", detail=""):
        res.steps.append(dict(step=name, status=status, ms=round((time.perf_counter() - t0) * 1000, 2), detail=detail))

    def _confirm(self, agent_id, target, faults, stages):
        """Cheap sufficiency check for a remembered root cause: replacing those stages' outputs with the
        reference values must make the target pass."""
        ref = self.a.run(agent_id, target.input, faults=())
        if ref.status != "success" or not self.a.judge(agent_id, ref, target.expected):
            return False, "reference run does not pass this case"
        if any(ref.event(s) is None for s in stages):
            return False, "remembered stage not present in this agent"
        run = self.a.run(agent_id, target.input, faults=tuple(faults), overrides={s: ref.event(s).output for s in stages})
        ok = run.status == "success" and self.a.judge(agent_id, run, target.expected)
        return ok, ("remembered stages are sufficient to fix this case" if ok
                    else "replacing the remembered stages does NOT fix this case (different cause)")

    # ---------- main entry
    def review(self, agent_id, target: Case, faults=(), regression=(), heldout=(), use_memory=True,
               review_id=None, ctx=None) -> ReviewResult:
        faults, regression, heldout = tuple(faults), list(regression), list(heldout)
        res = ReviewResult(review_id or uuid.uuid4().hex[:12], agent_id)
        say = (lambda m: ctx.progress(m)) if ctx else (lambda m: None)
        version = self._version(agent_id)

        t0 = time.perf_counter(); say("monitoring")
        failing = self.a.run(agent_id, target.input, faults=faults)
        if failing.status == "success" and self.a.judge(agent_id, failing, target.expected):
            self._log(res, "monitor", t0, detail="run passes")
            res.outcome = "no_failure"
            self.reviews.save(res)
            return res
        self._log(res, "monitor", t0, "failed", f"status={failing.status}")
        feats = symptom_features(agent_id, target, failing)

        selected = dx = gate_report = reused = None
        if use_memory and self.memory_mode != "off":
            t0 = time.perf_counter(); say("memory lookup")
            hits = self.memory.lookup(agent_id, version, feats, self.min_similarity)
            res.memory["hits"] = [dict(id=h["record"]["id"], similarity=h["similarity"]) for h in hits]
            self._log(res, "memory_lookup", t0, detail=f"{len(hits)} similar past failure(s)")
            for h in hits:
                rec = h["record"]
                repairs = [self.a.get_repair(agent_id, i) for i in rec["repair_ids"]]
                stages = rec["suspected_stages"]
                dxm = Diagnosis(agent_id, "single_root_cause" if len(stages) == 1 else "joint_root_cause",
                                list(stages), "medium", evidence=[f"suggested by failure memory #{rec['id']}; "
                                "sufficiency confirmed, not independently diagnosed"])
                if self.memory_mode == "blind_ablation":
                    selected, dx, reused = repairs, dxm, rec
                    res.notes.append("ABLATION: memory fix used without re-validation")
                    break
                t0 = time.perf_counter(); say(f"re-validating memory #{rec['id']}")
                ok, why = self._confirm(agent_id, target, faults, stages)
                if not ok:
                    res.memory["rejected_hits"].append(dict(id=rec["id"], reason=why))
                    self._log(res, "memory_confirm", t0, "rejected", why)
                    continue
                rep = GateRunner(self.a, replace(self.cfg, min_confidence="medium")).evaluate(
                    agent_id, faults, [target], regression, heldout, dxm, repairs)
                if not rep.passed:
                    res.memory["rejected_hits"].append(dict(id=rec["id"], reason="gates failed: " + ", ".join(rep.failed)))
                    self._log(res, "memory_confirm", t0, "rejected", "gates failed: " + ", ".join(rep.failed))
                    continue
                self._log(res, "memory_confirm", t0, "ok", why)
                selected, dx, gate_report, reused = repairs, dxm, rep, rec
                break
            if reused:
                res.memory["reused_record"] = reused["id"]

        if selected is None:
            t0 = time.perf_counter(); say("diagnosing")
            dx = self.engine.diagnose(agent_id, target.input, target.expected, faults, failing_run=failing)
            self._log(res, "diagnose", t0, detail=f"{dx.verdict} {dx.suspected_stages} ({dx.confidence}), {len(dx.experiments)} experiments")
            res.diagnosis = dx.to_dict()
            if dx.verdict not in ("single_root_cause", "joint_root_cause"):
                res.outcome = "inconclusive"
                res.notes += dx.evidence
                self.reviews.save(res)
                return res
            t0 = time.perf_counter(); say("interaction analysis")
            rep_i = self.inter.analyze(agent_id, target.input, target.expected, faults, dx.suspected_stages)
            res.interaction = rep_i.to_dict()
            self._log(res, "interaction", t0, detail=f"{rep_i.summary}, {rep_i.runs} runs")
            t0 = time.perf_counter(); say("planning repair")
            plan = self.planner.plan(agent_id, dx, [target], regression, faults)
            res.plan = plan.to_dict()
            self._log(res, "plan", t0, plan.status, f"selected={plan.selected}, {plan.validations_used} validations")
            if plan.status != "validated_fix":
                res.outcome = "no_validated_fix"
                res.notes += plan.rationale
                self.reviews.save(res)
                return res
            selected = [self.a.get_repair(agent_id, i) for i in plan.selected]
            t0 = time.perf_counter(); say("running hard gates")
            gate_report = GateRunner(self.a, self.cfg).evaluate(agent_id, faults, [target], regression, heldout, dx, selected)
            self._log(res, "gates", t0, "ok" if gate_report.passed else "blocked",
                      "all gates passed" if gate_report.passed else "failed: " + ", ".join(gate_report.failed))
        elif res.diagnosis is None:
            res.diagnosis = dx.to_dict()

        res.selected_repairs = [dict(repair_id=r.repair_id, stage=r.stage, description=r.description, patch=r.patch) for r in selected]
        if gate_report is not None:
            res.gates = gate_report.to_dict()
            if not gate_report.passed:
                res.outcome = "no_validated_fix"
                res.notes.append("Blocked by hard gates: " + ", ".join(gate_report.failed))
                self.reviews.save(res)
                return res
        res.approval_request_id = self.approvals.create(res.review_id, agent_id, dict(
            review_id=res.review_id, agent_version=version, faults=list(faults), target_case_id=target.case_id,
            repairs=res.selected_repairs, suspected_stages=list(dx.suspected_stages), features=sorted(feats),
            memory_record_id=reused["id"] if reused else None, gates_passed=gate_report is not None))
        res.outcome = "approval_pending"
        self.reviews.save(res)
        return res

    # ---------- human decisions
    def approve(self, request_id, reviewer, note=""):
        req = self.approvals.approve(request_id, reviewer, note)
        p = req["payload"]
        if p.get("memory_record_id"):
            self.memory.mark_reuse(p["memory_record_id"], True)
        else:
            self.memory.record(req["agent_id"], p["agent_version"], set(p["features"]), p["suspected_stages"],
                               [r["repair_id"] for r in p["repairs"]], "approved", p["review_id"])
        return req

    def reject(self, request_id, reviewer, note=""):
        req = self.approvals.reject(request_id, reviewer, note)
        p = req["payload"]
        if p.get("memory_record_id"):
            self.memory.mark_reuse(p["memory_record_id"], False)
        else:
            self.memory.record(req["agent_id"], p["agent_version"], set(p["features"]), p["suspected_stages"],
                               [r["repair_id"] for r in p["repairs"]], "rejected", p["review_id"])
        return req

    def apply(self, request_id):
        return self.approvals.apply(request_id)

    # ---------- background jobs
    def job_handler(self, payload, ctx):
        a = payload["agent_id"]
        res = self.review(a, case_from_dict(a, payload["target"]), payload.get("faults", ()),
                          [case_from_dict(a, c) for c in payload.get("regression", [])],
                          [case_from_dict(a, c) for c in payload.get("heldout", [])],
                          payload.get("use_memory", True), ctx=ctx)
        return res.to_dict()

    def register_with(self, runner):
        runner.register("review", self.job_handler)
