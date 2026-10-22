"""Generic adapters (Python callable, HTTP) and the agents.yaml loader."""
import json
from dataclasses import replace

import httpx
import pytest

from app.config import get_settings
from app.integration import (
    AdapterConfigError,
    AdapterOutput,
    AgentCapabilities,
    AgentExecutor,
    AgentInfo,
    AgentRegistry,
    CallableAgentAdapter,
    DuplicateAgentError,
    HttpAgentAdapter,
    load_registry,
)
from app.integration.adapters.http_adapter import expand_env, get_path


def info(**kw):
    base = dict(agent_id="py-agent", name="Py", agent_type="coding", version="1", description="",
                input_schema={"fields": {"code": {"type": "str", "required": True}}})
    base.update(kw)
    return AgentInfo(**base)


# ---- callable adapter ------------------------------------------------------------

def test_callable_adapter_wraps_plain_function():
    adapter = CallableAgentAdapter(info(), lambda task, ov: {"length": len(task["code"])})
    registry = AgentRegistry()
    registry.register(adapter)
    result = AgentExecutor(registry).execute("py-agent", {"code": "print(1)"})
    assert result.status == "success" and result.output == {"length": 8} and result.agent_version == "1"


def test_callable_adapter_accepts_adapter_output_with_usage():
    fn = lambda task, ov: AdapterOutput(output="ok", usage={"tokens": 3})
    result = AgentExecutor(_reg(CallableAgentAdapter(info(), fn))).execute("py-agent", {"code": "x"})
    assert result.usage["tokens"] == 3


def test_callable_adapter_function_errors_are_recorded():
    def fn(task, ov):
        raise ZeroDivisionError("nope")

    result = AgentExecutor(_reg(CallableAgentAdapter(info(), fn))).execute("py-agent", {"code": "x"})
    assert result.status == "error" and result.error["type"] == "ZeroDivisionError"


def _reg(adapter):
    registry = AgentRegistry()
    registry.register(adapter)
    return registry


# ---- HTTP adapter ----------------------------------------------------------------

def make_http(handler, **kw):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return HttpAgentAdapter(agent_id="web", name="Web", url="https://agent.test/run", client=client, **kw)


def test_http_adapter_maps_output_events_and_usage():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={
            "result": {"answer": "hi"},
            "trace": [{"kind": "tool_call", "name": "search", "input": {"q": 1}, "output": "x", "duration_ms": 5}, "junk"],
            "usage": {"tokens": 42},
        })

    adapter = make_http(handler, headers={"Authorization": "Bearer t"}, output_path="result",
                        events_path="trace", usage_path="usage", agent_type="research")
    result = AgentExecutor(_reg(adapter)).execute("web", {"question": "q"})
    assert seen["body"] == {"input": {"question": "q"}} and seen["auth"] == "Bearer t"
    assert result.output == {"answer": "hi"} and result.usage["tokens"] == 42
    assert [(e.kind, e.name, e.duration_ms) for e in result.events] == [("tool_call", "search", 5.0)]
    assert adapter.info().capabilities.trace_level == "events"


def test_http_adapter_raw_mode_and_default_io_trace():
    seen = {}
    adapter = make_http(lambda r: (seen.update(body=json.loads(r.content)), httpx.Response(200, json={"a": 1}))[1], send_as="raw")
    result = AgentExecutor(_reg(adapter)).execute("web", {"x": 1})
    assert seen["body"] == {"x": 1} and result.output == {"a": 1}
    assert adapter.info().capabilities.trace_level == "io"


@pytest.mark.parametrize(
    "response, error_type",
    [
        (httpx.Response(500, text="server exploded"), "HTTPError"),
        (httpx.Response(200, text="not json"), "InvalidResponse"),
        (httpx.Response(200, json={"other": 1}), "InvalidResponse"),  # output_path missing
    ],
)
def test_http_adapter_failures_become_error_results(response, error_type):
    adapter = make_http(lambda r: response, output_path="result")
    result = AgentExecutor(_reg(adapter)).execute("web", {"q": 1})
    assert result.status == "error" and result.error["type"] == error_type


def test_http_adapter_connection_error():
    def handler(request):
        raise httpx.ConnectError("refused")

    result = AgentExecutor(_reg(make_http(handler))).execute("web", {"q": 1})
    assert result.error["type"] == "ConnectionError"


def test_http_adapter_rejects_overrides():
    from app.integration import OverrideError

    adapter = make_http(lambda r: httpx.Response(200, json={}))
    with pytest.raises(OverrideError):
        AgentExecutor(_reg(adapter)).execute("web", {"q": 1}, overrides={"config_overrides": {"a": 1}})


@pytest.mark.parametrize("kwargs", [{"url": "ftp://x"}, {"method": "DELETE"}, {"send_as": "xml"}])
def test_http_adapter_validates_configuration(kwargs):
    params = dict(agent_id="w", name="W", url="https://x.test")
    params.update(kwargs)
    with pytest.raises(AdapterConfigError):
        HttpAgentAdapter(**params)


def test_env_expansion_and_paths(monkeypatch):
    monkeypatch.setenv("MY_TOKEN", "abc")
    assert expand_env("Bearer ${MY_TOKEN}") == "Bearer abc"
    with pytest.raises(AdapterConfigError):
        expand_env("${DEFINITELY_NOT_SET_12345}")
    assert get_path({"a": [{"b": 7}]}, "a.0.b") == 7
    assert get_path({"a": 1}, "") == {"a": 1}
    with pytest.raises(KeyError):
        get_path({"a": 1}, "a.b")


# ---- agents.yaml loader ------------------------------------------------------------

def settings_with(tmp_path, yaml_text):
    path = tmp_path / "agents.yaml"
    path.write_text(yaml_text)
    return replace(get_settings(), agents_config_path=path)


def test_default_config_registers_example_agents(registry):
    ids = {i.agent_id for i in registry.list_info()}
    assert ids == {"faq-chatbot", "calculator-agent", "recruitment-agent"}


def test_recruitment_can_be_removed_without_code_changes(tmp_path):
    cfg = """
agents:
  - type: factory
    factory: "app.target_agents.faq_chatbot.faq_adapter:create_adapter"
  - type: factory
    enabled: false
    factory: "app.target_agents.recruitment.recruitment_adapter:create_adapter"
"""
    reg = load_registry(settings_with(tmp_path, cfg))
    assert [i.agent_id for i in reg.list_info()] == ["faq-chatbot"]


def test_loader_builds_http_agent_from_config(tmp_path):
    cfg = """
agents:
  - type: http
    agent_id: remote
    name: Remote
    agent_type: research
    url: "https://agent.test/run"
    output_path: result
"""
    reg = load_registry(settings_with(tmp_path, cfg))
    assert reg.get("remote").info().agent_type == "research"


@pytest.mark.parametrize(
    "cfg",
    [
        "agents: nope",
        "agents:\n  - just a string",
        "agents:\n  - type: mystery",
        "agents:\n  - type: factory\n    factory: 'not a ref'",
        "agents:\n  - type: factory\n    factory: 'app.missing.module:create'",
        "agents:\n  - type: factory\n    factory: 'app.config:get_settings'",  # returns Settings, not an adapter
        "agents:\n  - type: http\n    agent_id: x\n    name: X",                 # url missing
        "agents:\n  - type: http\n    agent_id: x\n    name: X\n    url: https://a.test\n    bogus: 1",
    ],
)
def test_loader_rejects_bad_entries(tmp_path, cfg):
    with pytest.raises(AdapterConfigError):
        load_registry(settings_with(tmp_path, cfg))


def test_loader_rejects_duplicates_and_missing_file(tmp_path):
    entry = '  - type: factory\n    factory: "app.target_agents.faq_chatbot.faq_adapter:create_adapter"\n'
    with pytest.raises(DuplicateAgentError):
        load_registry(settings_with(tmp_path, "agents:\n" + entry + entry))
    with pytest.raises(AdapterConfigError):
        load_registry(replace(get_settings(), agents_config_path=tmp_path / "missing.yaml"))
