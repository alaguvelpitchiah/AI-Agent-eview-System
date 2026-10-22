import pytest
from phase3.toy_agent import ToyAdapter
from phase3.root_cause_engine import RootCauseEngine
from phase3.evaluation import evaluate
from phase3.storage import DiagnosisStore
from phase3.baseline import baseline_blame
from phase3.demo import CASES, R1, R2, R3, R4, M, A

ad = ToyAdapter()
eng = RootCauseEngine(ad)


def test_clean_agent_passes_all_cases():
    for c in CASES:
        assert ad.judge(A, ad.run(A, c.input), c.expected)


def test_no_failure_verdict():
    assert eng.diagnose(A, R1, M, ()).verdict == "no_failure"


@pytest.mark.parametrize("fault,inp,stage", [
    ("TOY-F01", R2, "tokenize"), ("TOY-F02", R3, "extract_skills"), ("TOY-F04", R3, "decide")])
def test_single_fault_found_and_confirmed(fault, inp, stage):
    dx = eng.diagnose(A, inp, M, (fault,))
    assert dx.verdict == "single_root_cause" and dx.root_stage == stage
    assert dx.confidence == "high" and dx.minimal_fix_sets == [[stage]]


def test_interaction_detected():
    dx = eng.diagnose(A, R1, M, ("TOY-F02", "TOY-F03"))
    assert dx.verdict == "joint_root_cause"
    assert dx.suspected_stages == ["extract_skills", "score"]
    assert dx.interaction_pattern == "failure_requires_all_faults"
    assert sorted(dx.minimal_fix_sets) == [["extract_skills"], ["score"]]


def test_two_active_faults_both_found_even_if_masked():
    dx = eng.diagnose(A, R4, M, ("TOY-F01", "TOY-F04"))
    assert dx.suspected_stages == ["tokenize", "decide"]
    assert dx.verdict == "joint_root_cause"


def test_latent_fault_is_not_blamed():
    # F04 is injected but never exercised by this input, so it is not a cause of the failure
    dx = eng.diagnose(A, R2, M, ("TOY-F01", "TOY-F04"))
    assert dx.suspected_stages == ["tokenize"]


def test_invalid_reference_is_inconclusive():
    dx = eng.diagnose(A, R1, {"decision": "reject"}, ())
    assert dx.verdict == "inconclusive" and "Reference" in dx.evidence[0]


def test_budget_limits_experiments_and_reports_untested():
    dx = RootCauseEngine(ad, max_experiments=1).diagnose(A, R3, M, ("TOY-F04",))
    assert len(dx.experiments) <= 1
    assert dx.untested_stages


def test_baseline_is_fooled_where_engine_is_not():
    f = ad.run(A, R2, faults=("TOY-F01",))
    assert baseline_blame(f, ad.stage_names(A)) == "extract_skills"   # first empty output, wrong
    assert eng.diagnose(A, R2, M, ("TOY-F01",)).root_stage == "tokenize"


def test_evaluation_summary():
    res = evaluate(ad, eng, CASES)
    assert res["not_failing"] == 1                      # S3 does not fail
    lat = [r for r in res["rows"] if r["case"] == "L1-latent-decide"][0]
    assert not lat["engine_exact"]                      # truth lists the latent fault; engine correctly omits it
    others = [r for r in res["rows"] if r["case"] != "L1-latent-decide"]
    assert all(r["engine_exact"] for r in others)
    assert res["engine_exact_rate"] > res["baseline_exact_rate"]
    assert res["joint_detection_rate"] == 2/3


def test_storage_roundtrip():
    s = DiagnosisStore()
    dx = eng.diagnose(A, R3, M, ("TOY-F04",))
    i = s.save(dx, "run-1")
    assert s.get(i)["suspected_stages"] == ["decide"]
    assert s.list(A)[0]["verdict"] == "single_root_cause"
