"""Hard validation gates. ALL gates must pass; there is no weighted score and no override.
A failing gate means the outcome is "No validated fix found" and nothing reaches the approval queue.

Gates (each re-runs the agent itself, independent of the planner's cached results):
  diagnosis_confirmed   diagnosis is a root cause with at least the required confidence
  target_fixed          every target case passes with the repairs applied
  no_regression         every currently-passing regression case still passes
  heldout_no_regression same rule on held-out cases the planner never saw
  root_cause_coverage   every diagnosed stage has a repair
  no_compensating       no repair on a stage that was not diagnosed (unless allowed)
  pair_safe             order of application does not matter and no repair pair breaks a passing case
  stable                repeated runs give identical results (determinism)
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from itertools import combinations
from phase3.evidence_analyzer import values_equal

CONF = {"none": 0, "low": 1, "medium": 2, "high": 3}


@dataclass
class GateConfig:
    min_confidence: str = "high"
    allow_compensating: bool = False
    require_heldout: bool = True
    repeats: int = 2
    residual_check: bool = False     # optional 9th gate: no stage may still deviate from the reference after repair


@dataclass
class GateResult:
    name: str
    passed: bool
    detail: str


@dataclass
class GateReport:
    results: list = field(default_factory=list)
    runs: int = 0

    @property
    def passed(self) -> bool:
        return bool(self.results) and all(r.passed for r in self.results)

    @property
    def failed(self) -> list:
        return [r.name for r in self.results if not r.passed]

    def to_dict(self):
        return dict(passed=self.passed, failed=self.failed, runs=self.runs, results=[asdict(r) for r in self.results])


class GateRunner:
    def __init__(self, adapter, config: GateConfig = None):
        self.a, self.cfg, self.runs = adapter, config or GateConfig(), 0

    def _pass(self, agent_id, faults, case, repairs) -> bool:
        self.runs += 1
        run = self.a.run(agent_id, case.input, faults=tuple(faults), repairs=tuple(repairs))
        return run.status == "success" and self.a.judge(agent_id, run, case.expected)

    def _residual_stages(self, agent_id, faults, target, repairs) -> list:
        """Stage-isolation test with the repairs applied: stages that still depart from the clean reference."""
        ref = self.a.run(agent_id, target.input, faults=())
        if ref.status != "success":
            return []
        stages, bad = self.a.stage_names(agent_id), []
        for i, st in enumerate(stages):
            ov = {p: ref.event(p).output for p in stages[:i]}
            self.runs += 1
            ev = self.a.run(agent_id, target.input, faults=tuple(faults), overrides=ov, repairs=tuple(repairs)).event(st)
            if ev is None or ev.error or not values_equal(ev.output, ref.event(st).output):
                bad.append(st)
        return bad

    def evaluate(self, agent_id, faults, targets, regression, heldout, diagnosis, repairs) -> GateReport:
        self.runs = 0
        repairs = list(repairs)
        tids = {c.case_id for c in targets}
        reg_cp = [c for c in regression if c.case_id not in tids and self._pass(agent_id, faults, c, ())]
        held_cp = [c for c in heldout if c.case_id not in tids and self._pass(agent_id, faults, c, ())]
        groups = [("t", targets), ("r", reg_cp), ("h", held_cp)]
        index = [(g, c.case_id) for g, cs in groups for c in cs]

        def vec(rs):
            return tuple(self._pass(agent_id, faults, c, rs) for _, cs in groups for c in cs)

        out = GateReport()
        add = lambda n, ok, d: out.results.append(GateResult(n, bool(ok), d))

        ok = diagnosis.verdict in ("single_root_cause", "joint_root_cause") and \
            CONF.get(diagnosis.confidence, 0) >= CONF[self.cfg.min_confidence]
        add("diagnosis_confirmed", ok, f"verdict={diagnosis.verdict}, confidence={diagnosis.confidence}, "
            f"required>={self.cfg.min_confidence}")

        vs = [vec(repairs) for _ in range(max(1, self.cfg.repeats))]
        v0 = vs[0]
        fails = lambda g: [cid for (gg, cid), p in zip(index, v0) if gg == g and not p]
        add("target_fixed", not fails("t"), f"still failing: {fails('t')}" if fails("t") else "all targets pass")
        add("no_regression", not fails("r"), f"broken: {fails('r')}" if fails("r") else f"{len(reg_cp)} passing cases intact")
        if not heldout and self.cfg.require_heldout:
            add("heldout_no_regression", False, "no held-out cases supplied (required)")
        else:
            add("heldout_no_regression", not fails("h"),
                f"broken: {fails('h')}" if fails("h") else f"{len(held_cp)} held-out cases intact")

        diag, rstages = set(diagnosis.suspected_stages), {r.stage for r in repairs}
        add("root_cause_coverage", diag <= rstages, f"diagnosed {sorted(diag)}, repaired {sorted(rstages)}")
        extra = sorted(rstages - diag)
        add("no_compensating", self.cfg.allow_compensating or not extra,
            f"repairs on undiagnosed stages: {extra}" if extra else "all repairs target diagnosed stages")

        bad = []
        n_t = len(targets)
        for a, b in combinations(repairs, 2):
            ab, ba = vec((a, b)), vec((b, a))
            if ab != ba:
                bad.append(f"{a.repair_id}/{b.repair_id}: order-dependent")
            elif not all(ab[n_t:]):
                bad.append(f"{a.repair_id}+{b.repair_id}: breaks a passing case")
        add("pair_safe", not bad, "; ".join(bad) if bad else ("single repair" if len(repairs) < 2 else "pairs safe in both orders"))
        add("stable", all(v == v0 for v in vs), f"{len(vs)} identical repeats" if all(v == v0 for v in vs) else "results differ between repeats")
        if self.cfg.residual_check:
            resid = sorted({st for t in targets for st in self._residual_stages(agent_id, faults, t, repairs)})
            add("no_residual_fault", not resid, f"stages still deviating from the reference after repair: {resid}" if resid
                else "every stage matches the reference once repaired")
        out.runs = self.runs
        return out
