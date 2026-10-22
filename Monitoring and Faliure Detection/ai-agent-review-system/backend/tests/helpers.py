"""Builders for trace records and evaluations used by the Phase 2 tests."""
from app.reviewer.trace_collector import TraceRecord


def event(name, kind="stage", output=None, error=None, overridden=False, input=None):
    return {"kind": kind, "name": name, "input": input, "output": output, "duration_ms": 1.0,
            "overridden": overridden, "component_version": "v", "error": error, "metadata": {}}


def make_record(**kw) -> TraceRecord:
    events = kw.pop("events", [])
    base = dict(
        execution_id="e1", agent_id="a1", agent_version="1", status="success", started_at="2026-01-01T00:00:00+00:00",
        duration_ms=5.0, input={"q": 1}, output={"answer": "42", "n": 3}, events=events, usage={"latency_ms": 5.0},
        error=None, expected=None, metadata=None, overrides=None, event_count=len(events),
        tool_call_count=sum(1 for e in events if e["kind"] == "tool_call"),
        error_events=[{"name": e["name"], "kind": e["kind"], "error": e["error"]} for e in events if e.get("error")],
    )
    base.update(kw)
    return TraceRecord(**base)
