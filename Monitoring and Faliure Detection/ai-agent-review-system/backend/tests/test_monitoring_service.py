"""End-to-end Phase 2 pipeline: run -> trace -> evaluate -> classify -> store -> metrics."""
import pytest

from app.integration import AgentNotFoundError, TaskValidationError
from app.reviewer.fault_injector import FaultNotFoundError
from app.reviewer.outcome_evaluator import ExpectationSpecError

AGENTS = ["faq-chatbot", "calculator-agent", "recruitment-agent"]


@pytest.mark.parametrize("agent_id", AGENTS)
def test_healthy_agents_pass_their_whole_benchmark(monitoring, agent_id):
    summary = monitoring.run_benchmark(agent_id)
    assert summary["metrics"]["task_success_rate"] == 1.0, [c for c in summary["cases"] if c["verdict"] != "pass"]
    assert summary["metrics"]["failures_by_category"] == {}
    assert len(summary["cases"]) >= 8


@pytest.mark.parametrize("agent_id", AGENTS)
def test_every_known_fault_is_detected_by_the_benchmark(monitoring, agent_id):
    """A fault the benchmark cannot see would be useless as ground truth for diagnosis."""
    for fault in monitoring.faults.list_faults(agent_id):
        summary = monitoring.run_benchmark(agent_id, fault_id=fault.fault_id)
        assert summary["metrics"]["task_success_rate"] < 1.0, f"{fault.fault_id} is invisible to the benchmark"
        assert summary["metrics"]["failures_by_category"], fault.fault_id


def test_monitor_stores_run_evaluation_and_failure(monitoring, store):
    run = monitoring.monitor(
        "calculator-agent", {"question": "What is 2 plus 2?"},
        expected={"checks": [{"path": "result", "op": "equals", "value": 5}]}, metadata={"case_id": "x"},
    )
    assert run.evaluation.verdict == "fail" and run.failure.category == "incorrect_output"
    stored = store.get_run(run.record.execution_id)
    assert stored["evaluation"]["verdict"] == "fail" and stored["failure"]["failure_id"] == run.failure.failure_id
    assert stored["metadata"] == {"case_id": "x"} and len(stored["events"]) == 3


def test_tool_failure_is_classified_with_partial_trace(monitoring):
    run = monitoring.monitor("calculator-agent", {"question": "What is 5 divided by 0?"},
                             expected={"checks": [{"path": "result", "op": "exists"}]})
    assert run.evaluation.verdict == "error" and run.failure.category == "tool_failure"
    assert run.failure.first_error_event["name"] == "calculator" and run.failure.event_names == ["plan", "calculator"]


def test_run_without_expectation_is_stored_but_not_judged(monitoring, store):
    run = monitoring.monitor("faq-chatbot", {"question": "hello"})
    assert run.evaluation.verdict == "no_expectation" and run.failure is None
    assert store.get_run(run.record.execution_id)["evaluation"]["verdict"] == "no_expectation"


def test_fault_runs_are_tagged_and_ground_truth_is_recorded(monitoring, store):
    run = monitoring.monitor("faq-chatbot", {"question": "How do I reset my password?"}, fault_id="FAQ-F01",
                             expected={"checks": [{"path": "source_id", "op": "equals", "value": "F01"}]})
    assert run.failure.category == "incorrect_output"
    assert store.get_run(run.record.execution_id)["metadata"]["fault_component"] == "response_generation"


def test_caller_mistakes_raise_before_anything_runs(monitoring, store):
    with pytest.raises(ExpectationSpecError):
        monitoring.monitor("faq-chatbot", {"question": "hello"}, expected={"checks": [{"path": "x", "op": "bogus"}]})
    with pytest.raises(TaskValidationError):
        monitoring.monitor("faq-chatbot", {"question": "hello"}, fault_id="FAQ-F01", overrides={"config_overrides": {}})
    with pytest.raises(FaultNotFoundError):
        monitoring.monitor("faq-chatbot", {"question": "hello"}, fault_id="NOPE")
    with pytest.raises(AgentNotFoundError):
        monitoring.monitor("nope", {})
    with pytest.raises(TaskValidationError):
        monitoring.monitor("faq-chatbot", {})  # invalid input
    assert store.count_runs() == 0


def test_benchmark_options_and_guards(monitoring):
    subset = monitoring.run_benchmark("calculator-agent", case_ids=["M001", "M002"])
    assert [c["case_id"] for c in subset["cases"]] == ["M001", "M002"] and subset["metrics"]["runs"]["total"] == 2
    with pytest.raises(TaskValidationError):
        monitoring.run_benchmark("calculator-agent", case_ids=["M999"])
    with pytest.raises(FaultNotFoundError):
        monitoring.run_benchmark("calculator-agent", fault_id="NOPE")
    with pytest.raises(AgentNotFoundError):
        monitoring.run_benchmark("nope")


def test_benchmark_batches_are_separate_and_metrics_are_per_batch(monitoring, store):
    clean = monitoring.run_benchmark("calculator-agent")
    faulty = monitoring.run_benchmark("calculator-agent", fault_id="CAL-F03")
    assert clean["batch_id"] != faulty["batch_id"]
    assert clean["metrics"]["task_success_rate"] == 1.0 and faulty["metrics"]["task_success_rate"] < 0.5
    assert len(store.list_runs(batch_id=clean["batch_id"])) == len(clean["cases"])


def test_agent_version_is_recorded_per_run_so_configs_can_be_compared(monitoring, store):
    monitoring.monitor("faq-chatbot", {"question": "hello"}, expected={"checks": [{"path": "intent", "op": "equals", "value": "greeting"}]})
    monitoring.monitor("faq-chatbot", {"question": "hello"}, fault_id="FAQ-F02",
                       expected={"checks": [{"path": "intent", "op": "equals", "value": "greeting"}]})
    versions = {r["agent_version"] for r in store.list_runs(agent_id="faq-chatbot")}
    assert len(versions) == 2  # the fault changes the configuration, hence the version
