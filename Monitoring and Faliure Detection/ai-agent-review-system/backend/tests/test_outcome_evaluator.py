import pytest

from app.reviewer.outcome_evaluator import CheckResult, ExpectationSpecError, OutcomeEvaluator, resolve_path, validate_expected
from helpers import make_record

ev = OutcomeEvaluator()


def evaluate(expected, **kw):
    return ev.evaluate(make_record(expected=expected, **kw))


def one(check, output=None, **kw):
    out = {"answer": "The answer is 42", "n": 3, "tags": ["a", "b"], "none": None, "flag": True, "nested": {"x": [10, 20]}}
    out.update(output or {})
    return evaluate({"checks": [check]}, output=out, **kw)


@pytest.mark.parametrize(
    "check, passes",
    [
        ({"path": "n", "op": "equals", "value": 3}, True),
        ({"path": "n", "op": "equals", "value": 4}, False),
        ({"path": "flag", "op": "equals", "value": 1}, False),            # True must not equal 1
        ({"path": "n", "op": "equals", "value": True}, False),
        ({"path": "n", "op": "not_equals", "value": 4}, True),
        ({"path": "n", "op": "approx", "value": 3.0000001, "tolerance": 1e-3}, True),
        ({"path": "n", "op": "approx", "value": 3.5}, False),
        ({"path": "n", "op": "gt", "value": 2}, True),
        ({"path": "n", "op": "gte", "value": 3}, True),
        ({"path": "n", "op": "lt", "value": 3}, False),
        ({"path": "n", "op": "lte", "value": 3}, True),
        ({"path": "n", "op": "between", "value": [1, 5]}, True),
        ({"path": "n", "op": "between", "value": [4, 5]}, False),
        ({"path": "flag", "op": "gt", "value": 0}, False),                # booleans are not numbers
        ({"path": "answer", "op": "contains", "value": "ANSWER"}, True),
        ({"path": "answer", "op": "contains", "value": "ANSWER", "case_sensitive": True}, False),
        ({"path": "tags", "op": "contains", "value": "a"}, True),
        ({"path": "answer", "op": "not_contains", "value": "secret"}, True),
        ({"path": "answer", "op": "regex", "value": r"\d{2}"}, True),
        ({"path": "answer", "op": "regex", "value": r"^\d+$"}, False),
        ({"path": "n", "op": "in", "value": [1, 3]}, True),
        ({"path": "n", "op": "not_in", "value": [1, 3]}, False),
        ({"path": "none", "op": "is_null"}, True),
        ({"path": "n", "op": "not_null"}, True),
        ({"path": "n", "op": "exists"}, True),
        ({"path": "tags", "op": "type_is", "value": "list"}, True),
        ({"path": "n", "op": "type_is", "value": "number"}, True),
        ({"path": "flag", "op": "type_is", "value": "int"}, False),
        ({"path": "tags", "op": "min_length", "value": 2}, True),
        ({"path": "answer", "op": "max_length", "value": 3}, False),
        ({"path": "nested.x.1", "op": "equals", "value": 20}, True),
    ],
)
def test_operators(check, passes):
    assert one(check).checks[0].passed is passes


@pytest.mark.parametrize("op, passes", [("not_equals", True), ("not_contains", True), ("not_in", True), ("absent", True),
                                         ("equals", False), ("exists", False), ("is_null", False), ("not_null", False), ("gte", False)])
def test_missing_path_behaviour(op, passes):
    result = one({"path": "no.such.field", "op": op, "value": 1})
    check = result.checks[0]
    assert check.passed is passes and check.missing is (not passes)


def test_absent_fails_when_present():
    assert one({"path": "n", "op": "absent"}).checks[0].passed is False


def test_checks_can_read_usage_events_and_error():
    record = make_record(
        usage={"latency_ms": 5.0, "tokens": 90}, events=[{"kind": "stage", "name": "s", "output": 1, "error": None}],
        expected={"checks": [
            {"source": "usage", "path": "tokens", "op": "lte", "value": 100},
            {"source": "events", "path": "0.name", "op": "equals", "value": "s"},
        ]},
    )
    assert ev.evaluate(record).verdict == "pass"


def test_verdict_and_score():
    result = evaluate({"checks": [{"path": "n", "op": "equals", "value": 3}, {"path": "n", "op": "equals", "value": 9}]})
    assert result.verdict == "fail" and result.score == 0.5 and result.message == "1 of 2 checks failed"
    assert evaluate({"checks": [{"path": "n", "op": "equals", "value": 3}]}).verdict == "pass"


def test_no_expectation_cases():
    assert evaluate(None).verdict == "no_expectation"
    assert evaluate({}).verdict == "no_expectation"
    assert evaluate({"checks": []}).verdict == "no_expectation"


def test_unexpected_run_error_is_verdict_error():
    result = evaluate({"checks": [{"path": "n", "op": "equals", "value": 3}]}, status="error", output=None,
                      error={"type": "ToolError", "message": "boom"})
    assert result.verdict == "error" and result.score == 0.0 and "ToolError" in result.checks[0].message


@pytest.mark.parametrize("expect, err_type, verdict", [("ToolError", "ToolError", "pass"), (True, "Anything", "pass"),
                                                        ("ToolError", "Timeout", "fail")])
def test_expected_errors(expect, err_type, verdict):
    result = evaluate({"expect_error": expect}, status="error", output=None, error={"type": err_type, "message": "m"})
    assert result.verdict == verdict
    if verdict == "fail":
        assert result.checks[0].category == "wrong_error_type"


def test_expected_error_but_run_succeeded():
    result = evaluate({"expect_error": "ToolError"})
    assert result.verdict == "fail" and result.checks[0].category == "unexpected_success"


def test_latency_expectation():
    assert evaluate({"max_latency_ms": 10, "checks": [{"path": "n", "op": "gte", "value": 0}]}, duration_ms=5).verdict == "pass"
    slow = evaluate({"max_latency_ms": 10, "checks": [{"path": "n", "op": "gte", "value": 0}]}, duration_ms=50)
    assert slow.verdict == "fail" and slow.checks[-1].category == "performance"


def test_safety_checks_default_to_critical():
    result = one({"path": "answer", "op": "not_contains", "value": "42", "category": "safety"})
    assert result.checks[0].severity == "critical" and result.checks[0].category == "safety"


def test_custom_evaluator_is_pluggable():
    evaluator = OutcomeEvaluator()
    evaluator.register_custom("positive_n", lambda rec, exp: [CheckResult(
        "n_positive", "n", "output", "gt", 0, rec.output["n"], rec.output["n"] > 0, "n must be positive")])
    assert evaluator.evaluate(make_record(expected={"custom": "positive_n"})).verdict == "pass"
    with pytest.raises(ExpectationSpecError):
        ev.evaluate(make_record(expected={"custom": "positive_n"}))  # unknown to the default evaluator


@pytest.mark.parametrize(
    "expected",
    [
        {"checks": "nope"}, {"checks": [{"path": "n", "op": "bogus"}]}, {"checks": [{"path": "n", "op": "equals"}]},
        {"checks": [{"op": "is_null"}]}, {"checks": [{"path": "n", "op": "regex", "value": "("}]},
        {"checks": [{"path": "n", "op": "between", "value": [1]}]}, {"checks": [{"path": "n", "op": "type_is", "value": "dog"}]},
        {"checks": [{"path": "n", "op": "exists", "category": "vibes"}]}, {"checks": [{"path": "n", "op": "exists", "severity": "huge"}]},
        {"checks": [{"path": "n", "op": "exists", "source": "elsewhere"}]}, {"unknown_key": 1}, {"max_latency_ms": -1},
        {"expect_error": 5}, "not a dict",
    ],
)
def test_malformed_specs_are_rejected(expected):
    with pytest.raises(ExpectationSpecError):
        validate_expected(expected)


def test_resolve_path_edges():
    assert resolve_path({"a": [1, 2]}, "a.1") == 2
    assert resolve_path({"a": 1}, "") == {"a": 1}
    assert resolve_path({"a": [1]}, "a.5") is not None  # sentinel, not an exception
