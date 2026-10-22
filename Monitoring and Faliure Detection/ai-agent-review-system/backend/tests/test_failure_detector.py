import pytest

from app.reviewer.failure_detector import CATEGORY_PRIORITY, FailureDetector
from app.reviewer.outcome_evaluator import OutcomeEvaluator
from helpers import event, make_record

detector, evaluator = FailureDetector(), OutcomeEvaluator()


def detect(record):
    return detector.detect(record, evaluator.evaluate(record))


def test_passing_and_unjudged_runs_produce_no_report():
    assert detect(make_record(expected={"checks": [{"path": "n", "op": "equals", "value": 3}]})) is None
    assert detect(make_record(expected=None)) is None


def test_incorrect_output():
    report = detect(make_record(expected={"checks": [{"path": "n", "op": "equals", "value": 99}]}))
    assert report.category == "incorrect_output" and report.severity == "major"
    assert report.failed_checks[0]["actual"] == 3 and "1 of 1 checks failed" in report.summary


def test_missing_field_is_incomplete_output():
    report = detect(make_record(expected={"checks": [{"path": "absent_field", "op": "equals", "value": 1}]}))
    assert report.category == "incomplete_output"


def test_completeness_category_check():
    report = detect(make_record(expected={"checks": [{"path": "answer", "op": "min_length", "value": 99, "category": "completeness"}]}))
    assert report.category == "incomplete_output"


def test_safety_violation_outranks_other_categories():
    report = detect(make_record(expected={"checks": [
        {"path": "n", "op": "equals", "value": 99},
        {"path": "answer", "op": "not_contains", "value": "42", "category": "safety"},
    ]}))
    assert report.category == "safety_violation" and report.severity == "critical"
    assert report.secondary_categories == ["incorrect_output"]


def test_explicit_check_severity_is_respected():
    report = detect(make_record(expected={"checks": [{"path": "n", "op": "equals", "value": 99, "severity": "minor"}]}))
    assert report.severity == "minor"


def test_execution_error():
    record = make_record(status="error", output=None, error={"type": "ValueError", "message": "bad"},
                         events=[event("parse", error="ValueError: bad")], expected={"checks": [{"path": "n", "op": "exists"}]})
    report = detect(record)
    assert report.category == "execution_error" and report.severity == "critical"
    assert report.first_error_event["name"] == "parse" and report.event_names == ["parse"]


def test_tool_failure_when_a_tool_call_errored():
    record = make_record(status="error", output=None, error={"type": "ToolError", "message": "x"},
                         events=[event("plan"), event("calc", kind="tool_call", error="ToolError: x")],
                         expected={"checks": [{"path": "n", "op": "exists"}]})
    assert detect(record).category == "tool_failure"


def test_timeout():
    record = make_record(status="error", output=None, error={"type": "Timeout", "message": "slow"},
                         expected={"checks": [{"path": "n", "op": "exists"}]})
    assert detect(record).category == "timeout"


def test_unexpected_success_and_wrong_error_type():
    assert detect(make_record(expected={"expect_error": "ToolError"})).category == "unexpected_success"
    wrong = make_record(status="error", output=None, error={"type": "Other", "message": "m"}, expected={"expect_error": "ToolError"})
    assert detect(wrong).category == "wrong_error_type"


def test_expected_error_that_happens_is_not_a_failure():
    record = make_record(status="error", output=None, error={"type": "ToolError", "message": "m"}, expected={"expect_error": "ToolError"})
    assert detect(record) is None


def test_slow_response_is_minor():
    report = detect(make_record(duration_ms=500, expected={"max_latency_ms": 10, "checks": [{"path": "n", "op": "exists"}]}))
    assert report.category == "slow_response" and report.severity == "minor"


def test_every_category_has_a_priority_and_default_severity():
    from app.reviewer.failure_detector import DEFAULT_SEVERITY
    assert set(CATEGORY_PRIORITY) == set(DEFAULT_SEVERITY)


def test_report_ids_are_unique_and_reports_serialise():
    rec = make_record(expected={"checks": [{"path": "n", "op": "equals", "value": 99}]})
    a, b = detect(rec), detect(rec)
    assert a.failure_id != b.failure_id and a.to_dict()["execution_id"] == "e1"
