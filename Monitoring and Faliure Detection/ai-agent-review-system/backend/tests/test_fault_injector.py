import json
from pathlib import Path

import pytest

from app.integration import AgentNotFoundError
from app.reviewer.fault_injector import FaultConfigError, FaultInjector, FaultNotFoundError

AGENTS = ["faq-chatbot", "calculator-agent", "recruitment-agent"]


@pytest.fixture(scope="module")
def injector(settings, registry):
    return FaultInjector(settings.data_dir, registry)


@pytest.mark.parametrize("agent_id", AGENTS)
def test_every_agent_ships_validated_faults_with_known_components(injector, registry, agent_id):
    faults = injector.list_faults(agent_id)
    assert len(faults) >= 4
    stages = set(registry.get(agent_id).info().supported_stages) | set(registry.get(agent_id).info().supported_tools)
    for fault in faults:
        assert fault.component and fault.overrides
        assert fault.component in stages  # the ground-truth component is a real step or tool of the agent


def test_unknown_agent_and_fault(injector):
    with pytest.raises(AgentNotFoundError):
        injector.list_faults("nope")
    with pytest.raises(FaultNotFoundError):
        injector.get_fault("faq-chatbot", "FAQ-F99")


def test_agent_without_fault_file_has_no_faults(settings, registry, tmp_path):
    assert FaultInjector(tmp_path, registry).list_faults("faq-chatbot") == []


def write_faults(tmp_path, faults, agent="faq-chatbot"):
    folder = tmp_path / "fault_scenarios" / agent
    folder.mkdir(parents=True)
    (folder / "faults.json").write_text(json.dumps({"agent_id": agent, "faults": faults}))


GOOD = {"fault_id": "X1", "name": "n", "component": "retrieval", "overrides": {"config_overrides": {"retrieval.top_k": 0}}}


@pytest.mark.parametrize(
    "fault",
    [
        {k: v for k, v in GOOD.items() if k != "component"},                                           # missing field
        {**GOOD, "overrides": {"config_overrides": {"no.such.key": 1}}},                                # unknown config key
        {**GOOD, "overrides": {"stage_overrides": {"retrieval": "not a list"}}},                        # wrong shape
        {**GOOD, "overrides": {"tool_overrides": {"calculator": 1}}},                                   # unsupported override group
    ],
)
def test_malformed_or_unsupported_faults_are_rejected(registry, tmp_path, fault):
    write_faults(tmp_path, [fault])
    with pytest.raises(FaultConfigError):
        FaultInjector(tmp_path, registry).list_faults("faq-chatbot")


def test_duplicate_fault_ids_and_invalid_json_are_rejected(registry, tmp_path):
    write_faults(tmp_path, [GOOD, GOOD])
    with pytest.raises(FaultConfigError):
        FaultInjector(tmp_path, registry).list_faults("faq-chatbot")
    (tmp_path / "fault_scenarios" / "faq-chatbot" / "faults.json").write_text("{not json")
    with pytest.raises(FaultConfigError):
        FaultInjector(tmp_path, registry).list_faults("faq-chatbot")


def test_run_with_fault_tags_the_result(injector, executor):
    result = injector.run_with_fault(executor, "calculator-agent", {"question": "What is 2 plus 2?"}, "CAL-F03", metadata={"case_id": "c"})
    assert result.output["result"] == 0
    assert result.metadata == {"case_id": "c", "fault_id": "CAL-F03", "fault_component": "calculator"}
