import pytest


def test_monitor_endpoint_returns_verdict_and_failure(client):
    body = {"input": {"question": "What is 2 plus 2?"}, "expected": {"checks": [{"path": "result", "op": "equals", "value": 5}]}}
    data = client.post("/api/agents/calculator-agent/monitor", json=body).json()
    assert data["verdict"] == "fail" and data["failure"]["category"] == "incorrect_output"
    assert client.get(f"/api/runs/{data['execution_id']}").json()["evaluation"]["verdict"] == "fail"
    assert client.get(f"/api/failures/{data['failure']['failure_id']}").json()["agent_id"] == "calculator-agent"


def test_monitor_with_fault(client):
    body = {"input": {"question": "What is 12 plus 30 times 2?"}, "fault_id": "CAL-F02",
            "expected": {"checks": [{"path": "result", "op": "equals", "value": 72}]}}
    data = client.post("/api/agents/calculator-agent/monitor", json=body).json()
    assert data["verdict"] == "fail" and data["checks"][0]["actual"] == 44


def test_benchmark_endpoint_and_metrics(client):
    clean = client.post("/api/agents/faq-chatbot/benchmark", json={}).json()
    assert clean["metrics"]["task_success_rate"] == 1.0
    faulty = client.post("/api/agents/faq-chatbot/benchmark", json={"fault_id": "FAQ-F03"}).json()
    assert faulty["metrics"]["task_success_rate"] < 0.2
    by_batch = client.get("/api/metrics", params={"batch_id": faulty["batch_id"]}).json()
    assert by_batch["runs"]["total"] == len(faulty["cases"])
    assert client.get("/api/metrics", params={"agent_id": "faq-chatbot"}).json()["runs"]["total"] >= 2 * len(clean["cases"])


def test_benchmark_body_is_optional(client):
    assert client.post("/api/agents/calculator-agent/benchmark").status_code == 200


def test_listings_and_filters(client):
    client.post("/api/agents/faq-chatbot/benchmark", json={"fault_id": "FAQ-F01"})
    runs = client.get("/api/runs", params={"agent_id": "faq-chatbot", "verdict": "fail", "limit": 5}).json()
    assert 0 < len(runs) <= 5 and all(r["verdict"] == "fail" for r in runs)
    failures = client.get("/api/failures", params={"category": "incorrect_output"}).json()
    assert failures and all(f["category"] == "incorrect_output" for f in failures)
    assert client.get("/api/runs", params={"limit": 0}).status_code == 422
    assert client.get("/api/runs", params={"limit": 501}).status_code == 422
    assert client.get("/api/runs", params={"offset": -1}).status_code == 422


def test_faults_endpoint(client):
    faults = client.get("/api/agents/recruitment-agent/faults").json()
    assert {"REC-F01", "REC-F05"} <= {f["fault_id"] for f in faults}
    assert client.get("/api/agents/nope/faults").status_code == 404


def test_baseline_diagnosis_endpoint(client):
    body = {"input": {"question": "What is 5 divided by 0?"}, "expected": {"checks": [{"path": "result", "op": "exists"}]}}
    failure_id = client.post("/api/agents/calculator-agent/monitor", json=body).json()["failure"]["failure_id"]
    diagnosis = client.get(f"/api/failures/{failure_id}/baseline").json()
    assert diagnosis["suspected_component"] == "calculator" and diagnosis["rule"] == "first_error_event"


@pytest.mark.parametrize(
    "path, method, body, status",
    [
        ("/api/runs/nope", "get", None, 404),
        ("/api/failures/nope", "get", None, 404),
        ("/api/failures/nope/baseline", "get", None, 404),
        ("/api/agents/nope/monitor", "post", {"input": {}}, 404),
        ("/api/agents/nope/benchmark", "post", {}, 404),
        ("/api/agents/faq-chatbot/monitor", "post", {"input": {"question": "hello"}, "fault_id": "NOPE"}, 404),
        ("/api/agents/faq-chatbot/benchmark", "post", {"fault_id": "NOPE"}, 404),
        ("/api/agents/faq-chatbot/benchmark", "post", {"case_ids": ["Z"]}, 422),
        ("/api/agents/faq-chatbot/monitor", "post", {"input": {"question": "x"}}, 422),
        ("/api/agents/faq-chatbot/monitor", "post", {"input": {"question": "hello"}, "expected": {"checks": [{"path": "a", "op": "bogus"}]}}, 422),
        ("/api/agents/faq-chatbot/monitor", "post", {"input": {"question": "hello"}, "fault_id": "FAQ-F01", "overrides": {"config_overrides": {}}}, 422),
    ],
)
def test_error_responses(client, path, method, body, status):
    response = getattr(client, method)(path, **({"json": body} if body is not None else {}))
    assert response.status_code == status
