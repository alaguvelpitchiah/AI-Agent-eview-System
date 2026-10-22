"""Contract every adapter must satisfy. New adapters are checked automatically.

Add an agent to agents.yaml and, if it has benchmark cases under
data/benchmark_cases/<agent_id>/, these tests cover it with no extra code.
"""
import pytest

from app.integration import (
    OVERRIDE_CONFIG,
    OVERRIDE_STAGE,
    OVERRIDE_TOOL,
    OverrideError,
    TaskValidationError,
    validate_task,
)
from app.integration.case_loader import load_cases

TRACE_LEVELS = {"none", "io", "events"}


def agent_ids(registry_fixture):
    return [i.agent_id for i in registry_fixture.list_info()]


@pytest.fixture(scope="module", params=["faq-chatbot", "calculator-agent", "recruitment-agent"])
def agent_id(request, registry):
    if request.param not in registry:
        pytest.skip(f"{request.param} is not enabled")
    return request.param


def test_info_is_complete_and_consistent(registry, agent_id):
    info = registry.get(agent_id).info()
    assert info.agent_id == agent_id and info.name and info.agent_type and info.version
    assert info.capabilities.trace_level in TRACE_LEVELS
    caps = info.capabilities
    if caps.supports_stage_overrides:
        assert info.supported_stages
    if caps.supports_tool_overrides:
        assert info.supported_tools
    assert set(info.to_dict()["supported_overrides"]) <= {OVERRIDE_STAGE, OVERRIDE_TOOL, OVERRIDE_CONFIG}


def test_example_inputs_satisfy_the_schema(registry, agent_id):
    info = registry.get(agent_id).info()
    assert info.example_inputs, "every agent should ship at least one example input"
    for example in info.example_inputs:
        validate_task(example, info.input_schema)


def test_schema_rejects_empty_input(registry, executor, agent_id):
    if not registry.get(agent_id).info().input_schema["fields"]:
        pytest.skip("open schema")
    with pytest.raises(TaskValidationError):
        executor.execute(agent_id, {})


def test_benchmark_cases_run_and_follow_the_result_format(executor, settings, agent_id):
    cases = load_cases(settings.data_dir, agent_id)
    assert len(cases) >= 5, "each agent needs a benchmark of at least five cases"
    for case in cases:
        result = executor.execute(agent_id, case["input"], expected=case["expected"], metadata={"case_id": case["case_id"]})
        assert result.status in ("success", "error") and result.expected == case["expected"]
        if result.status == "success":
            assert result.output is not None and result.usage["latency_ms"] >= 0
        else:
            assert result.error["type"] == case["expected"].get("expect_error"), case["case_id"]
        for event in result.events:
            assert event.kind and event.name and event.duration_ms >= 0


def test_event_agents_report_events(registry, executor, agent_id):
    info = registry.get(agent_id).info()
    result = executor.execute(agent_id, info.example_inputs[0])
    if info.capabilities.trace_level == "events":
        assert result.events
    else:
        assert result.events == []


def test_deterministic_agents_repeat_exactly(registry, executor, agent_id):
    info = registry.get(agent_id).info()
    if not info.capabilities.deterministic:
        pytest.skip("not deterministic")
    first = executor.execute(agent_id, info.example_inputs[0])
    second = executor.execute(agent_id, info.example_inputs[0])
    assert first.output == second.output


def test_unsupported_overrides_are_rejected(registry, executor, agent_id):
    info = registry.get(agent_id).info()
    example = info.example_inputs[0]
    with pytest.raises(OverrideError):
        executor.execute(agent_id, example, overrides={"made_up_override": {}})
    with pytest.raises(OverrideError):
        executor.execute(agent_id, example, overrides={OVERRIDE_CONFIG: {"definitely.not.a.key": 1}})


def test_stage_override_marks_exactly_that_event(registry, executor, agent_id):
    info = registry.get(agent_id).info()
    if not info.capabilities.supports_stage_overrides:
        pytest.skip("no stage overrides")
    example = info.example_inputs[0]
    baseline = executor.execute(agent_id, example)
    stage = info.supported_stages[0]
    replacement = next(e.output for e in baseline.events if e.name == stage)  # same value: result must not change
    replaced = executor.execute(agent_id, example, overrides={OVERRIDE_STAGE: {stage: replacement}})
    assert replaced.status == "success" and replaced.output == baseline.output
    assert [e.name for e in replaced.events if e.overridden] == [stage]


def test_live_configuration_is_never_modified_by_overrides(registry, executor, agent_id):
    info = registry.get(agent_id).info()
    if not info.capabilities.supports_config_overrides:
        pytest.skip("no config overrides")
    before = registry.get(agent_id).info().version
    example = info.example_inputs[0]
    executor.execute(agent_id, example, overrides={OVERRIDE_CONFIG: {}})
    assert registry.get(agent_id).info().version == before
