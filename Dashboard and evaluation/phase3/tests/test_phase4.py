from phase3.root_cause_engine import RootCauseEngine
from phase4.toy_repairs import ToyRepairAdapter, CATALOG
from phase4.validation import RepairValidator
from phase4.conflict_analyzer import ConflictAnalyzer
from phase4.interaction_analyzer import InteractionAnalyzer
from phase4.repair_planner import RepairPlanner
from phase4.baseline4 import baseline_fix
from phase4.evaluation4 import evaluate4
from phase4.storage4 import PlanStore
from phase4.demo4 import SCENARIOS, REG, R1, R4, R6, A

ad = ToyRepairAdapter()
RP = {r.repair_id: r for rs in CATALOG.values() for r in rs}


def _plan(scn):
    t = scn.target
    dx = RootCauseEngine(ad).diagnose(A, t.input, t.expected, scn.faults)
    return dx, RepairPlanner(ad).plan(A, dx, [t], scn.regression, scn.faults)


def test_validator_accepts_true_repair_rejects_wrong_one():
    v = RepairValidator(ad, A, ("TOY-F03",), [R6], REG)
    assert v.validate((RP["RP3"],)).valid
    assert v.validate((RP["RP4"],)).target_failures == ["R6"]       # does not fix the failure


def test_compensating_repair_passes_alone_but_conflicts_with_true_fix():
    v = RepairValidator(ad, A, ("TOY-F03",), [R6], REG)
    assert v.validate((RP["RP5"],)).valid                            # looks fine alone
    conf = ConflictAnalyzer(v).analyze([RP["RP3"], RP["RP5"]])
    assert len(conf) == 1 and conf[0].kind == "interaction" and conf[0].failed_cases == ["RX"]


def test_same_stage_repairs_both_valid_are_not_flagged():
    from phase4.models import Repair
    near = Repair("G1", "decide", "threshold 0.28", {"threshold": 0.28})    # also in the safe band (0.25, 0.33]
    v = RepairValidator(ad, A, ("TOY-F03",), [R6], REG)
    assert v.validate((RP["RP5"],)).valid and v.validate((near,)).valid
    assert v.validate((RP["RP5"], near)).valid and v.validate((near, RP["RP5"])).valid
    assert ConflictAnalyzer(v).analyze([RP["RP5"], near]) == []


def test_same_stage_overwrite_changes_outcome_by_order():
    v = RepairValidator(ad, A, ("TOY-F03",), [R6], REG)
    assert v.validate((RP["RP5"], RP["RP6"])).valid is False        # RP6 applied last -> target fails
    assert v.validate((RP["RP6"], RP["RP5"])).valid is True         # RP5 applied last -> passes


def test_planner_prefers_root_cause_over_compensation():
    dx, plan = _plan(SCENARIOS[0])
    assert plan.status == "validated_fix" and plan.selected == ["RP3"]
    assert any("RP5" in w and "conflicts" in w for w in plan.warnings)


def test_joint_fault_gets_full_repair_set_and_synergy():
    scn = SCENARIOS[1]
    dx, plan = _plan(scn)
    assert plan.selected == ["RP2", "RP3"]
    rep = InteractionAnalyzer(ad).analyze(A, R1.input, R1.expected, scn.faults, dx.suspected_stages)
    assert rep.summary == "synergistic" and rep.interactions[0].factors == ["extract_skills", "score"]
    assert rep.runs == 4                                              # 2^2


def test_independent_faults_not_flagged_as_interacting():
    for scn in SCENARIOS[2:]:
        dx, plan = _plan(scn)
        rep = InteractionAnalyzer(ad).analyze(A, scn.target.input, scn.target.expected, scn.faults, dx.suspected_stages)
        assert rep.summary == "none" and not any(p["interacts"] for p in rep.pairs)
        assert plan.status == "validated_fix"


def test_no_validated_fix_outcome():
    class NoRepairs(ToyRepairAdapter):
        def candidate_repairs(self, agent_id, stage):
            return []
    a2 = NoRepairs()
    dx = RootCauseEngine(a2).diagnose(A, R6.input, R6.expected, ("TOY-F03",))
    plan = RepairPlanner(a2).plan(A, dx, [R6], REG, ("TOY-F03",))
    assert plan.status == "no_validated_fix" and plan.selected == []


def test_only_bad_repairs_gives_no_validated_fix():
    class OnlyBad(ToyRepairAdapter):
        def candidate_repairs(self, agent_id, stage):
            return [RP["RP6"]] if stage == "decide" else []
    a2 = OnlyBad()
    dx = RootCauseEngine(a2).diagnose(A, R6.input, R6.expected, ("TOY-F03",))
    assert RepairPlanner(a2).plan(A, dx, [R6], REG, ("TOY-F03",)).status == "no_validated_fix"


def test_no_failure_diagnosis_is_not_repaired():
    dx = RootCauseEngine(ad).diagnose(A, R1.input, R1.expected, ())
    plan = RepairPlanner(ad).plan(A, dx, [R1], REG, ())
    assert plan.status == "no_validated_fix" and "no_failure" in plan.rationale[0]


def test_validation_budget_is_respected():
    dx = RootCauseEngine(ad).diagnose(A, R6.input, R6.expected, ("TOY-F03",))
    plan = RepairPlanner(ad, max_validations=2).plan(A, dx, [R6], REG, ("TOY-F03",))
    assert plan.validations_used <= 2 and any("budget" in w for w in plan.warnings)


def test_baseline_picks_the_compensating_repair():
    blamed, sel = baseline_fix(ad, A, R6, ("TOY-F03",))
    assert blamed == "decide" and sel == ["RP5"]


def test_evaluation_metrics():
    res = evaluate4(ad, SCENARIOS)
    assert res["planner_fix_rate"] == 1.0 and res["baseline_fix_rate"] == 0.0
    assert res["planner_hazard_rate"] == 0.0 and res["baseline_hazard_rate"] == 0.5
    assert res["interaction_recall"] == 1.0 and res["false_interaction_rate"] == 0.0
    assert res["conflict_recall"] == 1.0 and res["conflict_precision"] == 1.0


def test_plan_storage_roundtrip():
    dx, plan = _plan(SCENARIOS[0])
    s = PlanStore()
    i = s.save(plan)
    assert s.get(i)["plan"]["selected"] == ["RP3"] and s.list(A)[0]["status"] == "validated_fix"
