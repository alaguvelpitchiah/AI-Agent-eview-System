import json

from app.integration.base_adapter import AgentResult, TraceEvent
from app.reviewer.redaction import REDACTED, redact
from app.reviewer.trace_collector import TraceCollector


def make_result(**kw):
    base = dict(execution_id="x1", agent_id="a", agent_version="1", status="success", started_at="t", duration_ms=3.0,
                input={"q": "hi"}, output={"answer": "ok"}, usage={"latency_ms": 3.0})
    base.update(kw)
    return AgentResult(**base)


def test_collects_derived_fields():
    events = [TraceEvent("stage", "plan", output=1), TraceEvent("tool_call", "calc", output=2),
              TraceEvent("tool_call", "search", error="ToolError: x")]
    rec = TraceCollector().collect(make_result(events=events), batch_id="b1")
    assert (rec.event_count, rec.tool_call_count, rec.batch_id) == (3, 2, "b1")
    assert rec.error_events == [{"name": "search", "kind": "tool_call", "error": "ToolError: x"}]
    assert rec.events[0]["name"] == "plan" and rec.truncated is False


def test_secrets_are_redacted_everywhere():
    result = make_result(
        input={"query": "hi", "api_key": "sk-abcdefghijklmnopqrstuvwxyz"},
        output={"headers": {"Authorization": "Bearer abcdefghijkl"}, "note": "use sk-abcdefghijklmnopqrstuv now"},
        events=[TraceEvent("stage", "s", input={"password": "hunter2"}, output={"token": "t"})],
        metadata={"secret": "x", "case": "c1"},
    )
    text = json.dumps(TraceCollector().collect(result).to_dict())
    for leaked in ("hunter2", "abcdefghijkl", "sk-abcdefghijklmnopqrstuv"):
        assert leaked not in text
    assert REDACTED in text and "c1" in text


def test_redact_does_not_mutate_and_keeps_normal_values():
    original = {"password": "p", "keep": [1, {"token": "t", "ok": "fine"}]}
    assert redact(original) == {"password": REDACTED, "keep": [1, {"token": REDACTED, "ok": "fine"}]}
    assert original["password"] == "p"


def test_oversized_payloads_are_truncated_and_flagged():
    collector = TraceCollector(max_payload_chars=100, preview_chars=20)
    rec = collector.collect(make_result(output={"blob": "x" * 5000}, events=[TraceEvent("stage", "s", output="y" * 5000)]))
    assert rec.truncated is True
    assert rec.output["_truncated"] is True and len(rec.output["preview"]) == 20
    assert rec.events[0]["output"]["_truncated"] is True
    assert rec.input == {"q": "hi"}  # small payloads are untouched


def test_error_results_are_collected():
    rec = TraceCollector().collect(make_result(status="error", output=None, error={"type": "Timeout", "message": "m"}))
    assert rec.status == "error" and rec.output is None and rec.error["type"] == "Timeout"
