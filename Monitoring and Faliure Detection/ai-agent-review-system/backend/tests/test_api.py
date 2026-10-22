import pytest


def test_health_and_listing(client):
    assert client.get("/api/health").json() == {"status": "ok", "agents_registered": 3}
    agents = {a["agent_id"]: a for a in client.get("/api/agents").json()}
    assert set(agents) == {"faq-chatbot", "calculator-agent", "recruitment-agent"}
    assert agents["calculator-agent"]["supported_tools"] == ["calculator"]
    assert agents["calculator-agent"]["capabilities"]["supports_tool_overrides"] is True
    assert set(agents["recruitment-agent"]["supported_overrides"]) == {"stage_overrides", "config_overrides"}
    assert client.get("/api/agents/faq-chatbot").json()["agent_type"] == "chatbot"


def test_unknown_agent_is_404_everywhere(client):
    assert client.get("/api/agents/nope").status_code == 404
    assert client.get("/api/agents/nope/cases").status_code == 404
    assert client.post("/api/agents/nope/run", json={"input": {}}).status_code == 404


def test_cases_endpoint(client):
    cases = client.get("/api/agents/calculator-agent/cases").json()
    assert len(cases) >= 5 and {"case_id", "input", "expected"} <= set(cases[0])


@pytest.mark.parametrize(
    "agent_id", ["faq-chatbot", "calculator-agent", "recruitment-agent"]
)
def test_run_example_input_for_every_agent(client, agent_id):
    example = client.get(f"/api/agents/{agent_id}").json()["example_inputs"][0]
    response = client.post(f"/api/agents/{agent_id}/run", json={"input": example, "metadata": {"source": "test"}})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success" and data["events"] and data["metadata"] == {"source": "test"}
    assert data["usage"]["latency_ms"] >= 0


def test_agent_failure_is_a_200_with_error_result(client):
    response = client.post("/api/agents/calculator-agent/run", json={"input": {"question": "What is 5 divided by 0?"}})
    data = response.json()
    assert response.status_code == 200 and data["status"] == "error"
    assert data["error"]["type"] == "ToolError" and len(data["events"]) == 2


def test_invalid_input_is_422_with_error_list(client):
    response = client.post("/api/agents/faq-chatbot/run", json={"input": {"question": "x"}})
    assert response.status_code == 422 and response.json()["detail"]["errors"]
    assert client.post("/api/agents/faq-chatbot/run", json={}).status_code == 422  # missing 'input'


def test_invalid_overrides_are_422(client):
    body = {"input": {"question": "How do I reset my password?"}, "overrides": {"bogus": 1}}
    assert client.post("/api/agents/faq-chatbot/run", json=body).status_code == 422


def test_expected_is_stored_with_the_result(client):
    body = {"input": {"question": "hello"}, "expected": {"intent": "greeting"}}
    assert client.post("/api/agents/faq-chatbot/run", json=body).json()["expected"] == {"intent": "greeting"}
