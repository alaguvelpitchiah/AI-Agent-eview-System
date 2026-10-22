"""Task success, latency, event and usage metrics over a set of monitored runs."""
from __future__ import annotations

import math
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional


def percentile(values: List[float], p: float) -> float:
    """Linear-interpolated percentile (p between 0 and 100) of a non-empty list."""
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * p / 100.0
    low, high = math.floor(rank), math.ceil(rank)
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)


def _round(value: Optional[float]) -> Optional[float]:
    return None if value is None else round(value, 4)


def compute_metrics(rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Each row: status, duration_ms, verdict, failure_category, severity, event_count,
    tool_call_count and usage (as returned by TraceStore.metric_rows)."""
    rows = list(rows)
    total = len(rows)
    evaluated = [r for r in rows if r.get("verdict") in ("pass", "fail", "error")]
    passed = sum(1 for r in evaluated if r["verdict"] == "pass")
    failed = sum(1 for r in evaluated if r["verdict"] == "fail")
    errored = sum(1 for r in evaluated if r["verdict"] == "error")
    run_errors = sum(1 for r in rows if r["status"] == "error")
    timeouts = sum(1 for r in rows if r.get("failure_category") == "timeout")

    latencies = [float(r["duration_ms"]) for r in rows]
    latency = (
        {
            "mean": _round(sum(latencies) / total),
            "median": _round(percentile(latencies, 50)),
            "p95": _round(percentile(latencies, 95)),
            "min": _round(min(latencies)),
            "max": _round(max(latencies)),
        }
        if latencies
        else None
    )

    usage_totals: Dict[str, float] = {}
    for r in rows:
        for key, value in (r.get("usage") or {}).items():
            if key != "latency_ms" and isinstance(value, (int, float)) and not isinstance(value, bool):
                usage_totals[key] = usage_totals.get(key, 0) + value

    return {
        "runs": {
            "total": total,
            "evaluated": len(evaluated),
            "passed": passed,
            "failed": failed,
            "unexpected_errors": errored,
            "no_expectation": total - len(evaluated),
            "run_errors": run_errors,
            "timeouts": timeouts,
        },
        "task_success_rate": _round(passed / len(evaluated)) if evaluated else None,
        "run_error_rate": _round(run_errors / total) if total else None,
        "timeout_rate": _round(timeouts / total) if total else None,
        "latency_ms": latency,
        "events": {
            "mean_per_run": _round(sum(r["event_count"] for r in rows) / total) if total else None,
            "tool_calls_total": sum(r["tool_call_count"] for r in rows),
        },
        "usage_totals": {k: _round(v) for k, v in usage_totals.items()},
        "failures_by_category": dict(Counter(r["failure_category"] for r in rows if r.get("failure_category"))),
        "failures_by_severity": dict(Counter(r["severity"] for r in rows if r.get("severity"))),
    }
