"""Agent-independent tests of validation, registry, executor and capability checks."""
import time

import pytest

from app.integration import (
    OVERRIDE_CONFIG,
    OVERRIDE_STAGE,
    AdapterOutput,
    AgentCapabilities,
    AgentExecutor,
    AgentInfo,
    AgentNotFoundError,
    AgentRegistry,
    AgentRunError,
    BaseAgentAdapter,
    DuplicateAgentError,
    EventRecorder,
    OverrideError,
    TaskValidationError,
    TraceEvent,
    validate_task,
)
from app.integration.config_utils import apply_overrides, config_version
from app.integration.tracing import MISSING


class FakeAdapter(BaseAgentAdapter):
    def __init__(self, agent_id="fake", mode="ok", capabilities=None):
        self._id, self.mode = agent_id, mode
        self._caps = capabilities or AgentCapabilities()

    def info(self):
        return AgentInfo(
            agent_id=self._id, name="Fake", agent_type="test", version="0.0.1", description="",
            input_schema={"fields": {"text": {"type": "str", "required": True, "min_length": 1}}},
            capabilities=self._caps, supported_stages=["s1", "s2"],
        )

    def run(self, task_input, overrides=None):
        if self.mode == "raise":
            raise RuntimeError("boom")
        if self.mode == "raise_with_trace":
            raise AgentRunError("tool failed", events=[TraceEvent(kind="tool_call", name="t", error="x")], error_type="ToolError")
        if self.mode == "slow":
            time.sleep(0.4)
        return AdapterOutput(output={"echo": task_input["text"]}, agent_version="0.0.1", usage={"tokens": 7})


def make_executor(mode="ok", timeout=5.0, capabilities=None):
    registry = AgentRegistry()
    registry.register(FakeAdapter("fake", mode, capabilities))
    return AgentExecutor(registry, timeout_seconds=timeout)


# ---- validator -----------------------------------------------------------------

SCHEMA = {
    "fields": {
        "name": {"type": "str", "required": True, "min_length": 2, "max_length": 5},
        "age": {"type": "int", "min": 0, "max": 120},
        "kind": {"type": "str", "choices": ["a", "b"]},
        "mode": {"type": "str", "default": "fast"},
        "blob": {"type": "any"},
    }
}


def test_validator_accepts_and_cleans():
    assert validate_task({"name": "  Bob ", "age": 30, "blob": [1]}, SCHEMA) == {
        "name": "Bob", "age": 30, "mode": "fast", "blob": [1],
    }


@pytest.mark.parametrize(
    "task",
    [{}, {"name": "B"}, {"name": "Bobbbbb"}, {"name": "Bob", "age": "30"}, {"name": "Bob", "age": True},
     {"name": "Bob", "age": 500}, {"name": "Bob", "kind": "z"}, {"name": "Bob", "extra": 1}],
)
def test_validator_rejects_bad_tasks(task):
    with pytest.raises(TaskValidationError):
        validate_task(task, SCHEMA)


def test_validator_rejects_non_dict_and_oversized():
    with pytest.raises(TaskValidationError):
        validate_task(["x"], SCHEMA)
    with pytest.raises(TaskValidationError):
        validate_task({"name": "Bob", "pad": "x" * 200}, {**SCHEMA, "allow_extra": True}, max_bytes=100)


def test_open_schema_passes_unknown_fields_through():
    task = {"anything": {"goes": 1}, "n": 2}
    assert validate_task(task, {"fields": {}, "allow_extra": True}) == task


# ---- registry ------------------------------------------------------------------

def test_registry_lifecycle_and_errors():
    registry = AgentRegistry()
    registry.register(FakeAdapter("a"))
    registry.register(FakeAdapter("b"))
    assert len(registry) == 2 and "a" in registry
    assert {i.agent_id for i in registry.list_info()} == {"a", "b"}
    with pytest.raises(DuplicateAgentError):
        registry.register(FakeAdapter("a"))
    registry.unregister("a")
    with pytest.raises(AgentNotFoundError):
        registry.get("a")
    with pytest.raises(AgentNotFoundError):
        registry.unregister("a")


# ---- executor ------------------------------------------------------------------

def test_executor_success_returns_standard_result():
    result = make_executor().execute("fake", {"text": "hi"}, expected={"echo": "hi"}, metadata={"case": "c1"})
    assert result.status == "success" and result.output == {"echo": "hi"}
    assert result.expected == {"echo": "hi"} and result.metadata == {"case": "c1"}
    assert result.usage["tokens"] == 7 and result.usage["latency_ms"] >= 0
    assert result.input == {"text": "hi"} and result.execution_id and result.started_at


def test_executor_records_failure_without_raising():
    result = make_executor("raise").execute("fake", {"text": "hi"})
    assert result.status == "error" and result.output is None
    assert result.error == {"type": "RuntimeError", "message": "boom"}


def test_executor_keeps_partial_trace_on_agent_run_error():
    result = make_executor("raise_with_trace").execute("fake", {"text": "hi"})
    assert result.error["type"] == "ToolError"
    assert [e.name for e in result.events] == ["t"] and result.events[0].error == "x"


def test_executor_times_out():
    result = make_executor("slow", timeout=0.05).execute("fake", {"text": "hi"})
    assert result.status == "error" and result.error["type"] == "Timeout"


def test_executor_raises_for_caller_mistakes():
    executor = make_executor()
    with pytest.raises(AgentNotFoundError):
        executor.execute("nope", {"text": "hi"})
    with pytest.raises(TaskValidationError):
        executor.execute("fake", {})
    with pytest.raises(TaskValidationError):
        executor.execute("fake", {"text": "hi"}, expected="not a dict")


def test_unique_execution_ids():
    executor = make_executor()
    assert len({executor.execute("fake", {"text": "hi"}).execution_id for _ in range(5)}) == 5


# ---- capability-driven override validation ---------------------------------------------

def test_agent_without_capabilities_rejects_all_overrides():
    with pytest.raises(OverrideError):
        make_executor().execute("fake", {"text": "hi"}, overrides={OVERRIDE_STAGE: {"s1": 1}})


def test_agent_with_stage_capability_checks_stage_names():
    caps = AgentCapabilities(supports_stage_overrides=True)
    executor = make_executor(capabilities=caps)
    executor.execute("fake", {"text": "hi"}, overrides={OVERRIDE_STAGE: {"s1": 1}})
    with pytest.raises(OverrideError):
        executor.execute("fake", {"text": "hi"}, overrides={OVERRIDE_STAGE: {"missing": 1}})
    with pytest.raises(OverrideError):  # config overrides not declared
        executor.execute("fake", {"text": "hi"}, overrides={OVERRIDE_CONFIG: {"a": 1}})
    with pytest.raises(OverrideError):
        executor.execute("fake", {"text": "hi"}, overrides=["not", "a", "dict"])


# ---- tracing helper and config utilities --------------------------------------------------

def test_event_recorder_times_overrides_and_records_errors():
    rec = EventRecorder(version="v1")
    assert rec.step("a", lambda: 1, input={"x": 1}) == 1
    assert rec.step("b", lambda: 2, override=None) is None  # None is a valid override
    assert [(e.name, e.overridden, e.output) for e in rec.events] == [("a", False, 1), ("b", True, None)]
    with pytest.raises(ValueError):
        rec.step("c", lambda: (_ for _ in ()).throw(ValueError("bad")), kind="tool_call")
    assert rec.events[-1].error == "ValueError: bad" and rec.events[-1].kind == "tool_call"
    assert MISSING is not None


def test_config_overrides_are_copies_and_strict():
    base = {"version": "1", "a": {"b": 1, "c": 2}, "open": {}}
    changed = apply_overrides(base, {"a.b": 5, "open": {"new_key": 1}}, open_sections=("open",))
    assert changed["a"]["b"] == 5 and base["a"]["b"] == 1 and changed["open"]["new_key"] == 1
    with pytest.raises(ValueError):
        apply_overrides(base, {"a.zzz": 1})
    assert config_version(base) != config_version(changed)
