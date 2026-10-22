import pytest

from app.evaluation.baseline_reviewer import BaselineReviewer
from app.reviewer.failure_detector import FailureDetector
from app.reviewer.outcome_evaluator import OutcomeEvaluator
from helpers import event, make_record

reviewer = BaselineReviewer()
FAIL = {"checks": [{"path": "n", "op": "equals", "value": 99}]}


def diagnose(**kw):
    record = make_record(**kw)
    report = FailureDetector().detect(record, OutcomeEvaluator().evaluate(record))
    return reviewer.diagnose(record, report)


def test_blames_the_first_error_event():
    d = diagnose(status="error", output=None, error={"type": "ToolError", "message": "x"}, expected={"checks": [{"path": "n", "op": "exists"}]},
                 events=[event("plan", output={"a": 1}), event("calc", kind="tool_call", error="ToolError: x")])
    assert (d.suspected_component, d.rule) == ("calc", "first_error_event")
    assert "calc" in d.suggested_action and d.confidence == "low" and d.method == "baseline_heuristic"


def test_blames_the_first_empty_output_when_no_error():
    d = diagnose(expected=FAIL, events=[event("intent", output="question"), event("retrieval", output=[]), event("respond", output={"a": 1})])
    assert (d.suspected_component, d.rule) == ("retrieval", "first_empty_output")


def test_overridden_steps_are_not_blamed_for_emptiness():
    d = diagnose(expected=FAIL, events=[event("plan", output=None, overridden=True), event("respond", output={"a": 1})])
    assert (d.suspected_component, d.rule) == ("respond", "last_stage")


def test_falls_back_to_the_last_stage():
    d = diagnose(expected=FAIL, events=[event("a", output=1), event("b", output=2)])
    assert (d.suspected_component, d.rule) == ("b", "last_stage")


def test_agents_without_a_trace_get_the_whole_agent():
    d = diagnose(expected=FAIL, events=[])
    assert (d.suspected_component, d.rule) == ("agent", "no_trace")


@pytest.mark.parametrize("category_expected", [{"expect_error": "ToolError"}, FAIL, {"max_latency_ms": 1, "checks": [{"path": "n", "op": "exists"}]}])
def test_every_failure_category_yields_an_action(category_expected):
    assert diagnose(expected=category_expected, duration_ms=50, events=[event("s", output=1)]).suggested_action
