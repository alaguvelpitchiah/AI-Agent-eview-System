import pytest

from app.reviewer.performance_metrics import compute_metrics, percentile


def row(verdict="pass", status="success", ms=10.0, cat=None, sev=None, events=3, tools=1, usage=None):
    return {"verdict": verdict, "status": status, "duration_ms": ms, "failure_category": cat, "severity": sev,
            "event_count": events, "tool_call_count": tools, "usage": usage or {"latency_ms": ms}}


def test_percentile():
    assert percentile([5], 95) == 5
    assert percentile([1, 2, 3, 4], 50) == 2.5
    assert percentile([10, 20, 30, 40, 50], 95) == pytest.approx(48.0)
    assert percentile([4, 1, 3, 2], 0) == 1 and percentile([4, 1, 3, 2], 100) == 4


def test_empty_input_is_safe():
    m = compute_metrics([])
    assert m["runs"]["total"] == 0 and m["task_success_rate"] is None and m["latency_ms"] is None
    assert m["events"]["mean_per_run"] is None and m["usage_totals"] == {}


def test_rates_and_counts():
    rows = [row(), row(), row("fail", cat="incorrect_output", sev="major"),
            row("error", "error", cat="timeout", sev="critical"), row("no_expectation")]
    m = compute_metrics(rows)
    assert m["runs"] == {"total": 5, "evaluated": 4, "passed": 2, "failed": 1, "unexpected_errors": 1,
                         "no_expectation": 1, "run_errors": 1, "timeouts": 1}
    assert m["task_success_rate"] == 0.5 and m["run_error_rate"] == 0.2 and m["timeout_rate"] == 0.2
    assert m["failures_by_category"] == {"incorrect_output": 1, "timeout": 1}
    assert m["failures_by_severity"] == {"major": 1, "critical": 1}


def test_expected_error_that_passes_counts_as_run_error_but_not_failure():
    m = compute_metrics([row("pass", "error")])
    assert m["task_success_rate"] == 1.0 and m["run_error_rate"] == 1.0


def test_latency_events_and_usage():
    rows = [row(ms=10, events=2, tools=1, usage={"latency_ms": 10, "tokens": 5, "cost": 0.5}),
            row(ms=30, events=4, tools=3, usage={"latency_ms": 30, "tokens": 15, "cost": 0.25, "model": "x", "ok": True})]
    m = compute_metrics(rows)
    assert m["latency_ms"] == {"mean": 20.0, "median": 20.0, "p95": 29.0, "min": 10.0, "max": 30.0}
    assert m["events"] == {"mean_per_run": 3.0, "tool_calls_total": 4}
    assert m["usage_totals"] == {"tokens": 20.0, "cost": 0.75}  # strings, booleans and latency are not summed
