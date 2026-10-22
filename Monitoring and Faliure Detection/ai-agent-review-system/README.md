# AI Agent Review System: Phases 1 and 2 (Integration, Monitoring and Failure Detection)

A reviewer that can connect to **any** AI agent (chatbot, coding, research, data analysis,
recruitment, tool-using, custom), run its tasks, and return results and traces in one standard format.
The reviewer core is agent-independent. The three agents included are examples,
and recruitment is just one of them.

All example data is synthetic.

## Run (Linux Mint / Ubuntu)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

pytest                                  # 245 tests
python scripts/run_phase1_demo.py       # runs every benchmark case of every agent
python scripts/run_phase2_demo.py       # healthy vs. each injected fault, with metrics
uvicorn app.main:app --reload           # API docs at http://127.0.0.1:8000/docs
```

```bash
curl http://127.0.0.1:8000/api/agents
curl -X POST http://127.0.0.1:8000/api/agents/calculator-agent/run \
  -H "Content-Type: application/json" \
  -d '{"input": {"question": "What is 12 plus 30 times 2?"}}'
```

## Connecting your own agent

1. **Python agent**: implement `BaseAgentAdapter` (or wrap a function with `CallableAgentAdapter`), add a
   `create_adapter(settings)` factory, and list it in `backend/agents.yaml` as `type: factory`.
2. **HTTP agent**: add a `type: http` entry to `backend/agents.yaml` (see the commented example).
3. Add benchmark cases in `data/benchmark_cases/<agent_id>/cases.json`.
   The contract tests in `tests/test_adapter_contract.py` then check the new agent automatically.

## Layout

| Part | Location |
|---|---|
| Integration core | `backend/app/integration/` (base_adapter, agent_registry, agent_executor, input_validator, adapter_loader, tracing, config_utils, case_loader, errors) |
| Generic adapters | `backend/app/integration/adapters/` (HTTP, Python callable) |
| Example agents | `backend/app/target_agents/` (faq_chatbot, calculator_agent, recruitment) |
| Agent list | `backend/agents.yaml` |
| API | `backend/app/main.py`, `backend/app/api/` |
| Benchmarks | `data/benchmark_cases/<agent_id>/cases.json` |
| Phase 2 modules | `backend/app/reviewer/`, `storage/`, `services/`, `evaluation/` |
| Faults | `data/fault_scenarios/<agent_id>/faults.json` |
| Design notes | `docs/architecture.md` |

## What later phases build on

* **Capabilities** (`AgentCapabilities`): declare trace level and supported overrides. Phase 3 and 4 choose experiments from them.
* **Overrides**: `stage_overrides` (replace a stage's output), `tool_overrides` (mock a tool result) and `config_overrides` (change a copy of the configuration).
  Unknown keys are rejected, and the live configuration is never modified.
* **Trace events**: every run records steps with kind, input, output, duration and errors. A failed run keeps the partial trace.
* **`expected` and `metadata`** travel with each result for the outcome evaluator (Phase 2).

## Phase 2: monitoring and failure detection

```
run (Phase 1) -> TraceCollector -> OutcomeEvaluator -> FailureDetector -> TraceStore (SQLite) -> metrics
                  redact + bound     expected vs actual   category + severity
```

| Part | File |
|---|---|
| Trace record, secret redaction, payload limits | `reviewer/trace_collector.py`, `reviewer/redaction.py` |
| Expected-vs-actual evaluation for any agent | `reviewer/outcome_evaluator.py` |
| Failure categories and severity | `reviewer/failure_detector.py` |
| Success rate, latency, events, usage | `reviewer/performance_metrics.py` |
| Single known faults (ground truth for later phases) | `reviewer/fault_injector.py`, `data/fault_scenarios/<agent_id>/faults.json` |
| Baseline reviewer (heuristics only) | `evaluation/baseline_reviewer.py` |
| SQLite persistence | `storage/database.py`, `storage/trace_store.py` |
| Orchestration | `services/monitoring_service.py`, `api/routes/monitoring.py` |

### The expected block (the same for every agent type)

```json
{
  "checks": [
    {"path": "result", "op": "equals", "value": 72},
    {"path": "answer", "op": "not_contains", "value": "password", "category": "safety"},
    {"path": "match_score", "op": "gte", "value": 90, "severity": "minor"}
  ],
  "expect_error": "ToolError",
  "max_latency_ms": 2000,
  "custom": "name_of_a_registered_evaluator"
}
```

Operators: `equals, not_equals, approx, gt, gte, lt, lte, between, contains, not_contains, regex, in, not_in,
type_is, min_length, max_length, is_null, not_null, exists, absent`.
`path` is dotted (list indices allowed) and reads from `source`: `output` (default), `usage`, `events` or `error`.
Check `category` is `correctness` (default), `completeness` or `safety`. `severity` is `minor`, `major` or `critical`.
Malformed expectations are rejected before anything runs (HTTP 422).

### Verdicts and failure categories

Verdicts: `pass`, `fail`, `error` (the run failed unexpectedly), `no_expectation`.
Failure categories, highest priority first: `safety_violation`, `timeout`, `tool_failure`, `execution_error`,
`incorrect_output`, `incomplete_output`, `wrong_error_type`, `unexpected_success`, `slow_response`.

### Endpoints

| Endpoint | Purpose |
|---|---|
| `POST /api/agents/{id}/monitor` | Run, evaluate, classify and store one input (optional `fault_id`) |
| `POST /api/agents/{id}/benchmark` | Run all (or selected) benchmark cases, optionally under a fault; returns metrics |
| `GET /api/agents/{id}/faults` | Known faults for the agent |
| `GET /api/runs`, `GET /api/runs/{execution_id}` | Stored runs with evaluation and failure |
| `GET /api/failures`, `GET /api/failures/{id}` | Failure reports |
| `GET /api/failures/{id}/baseline` | What the baseline reviewer would conclude |
| `GET /api/metrics` | Metrics, filterable by agent, version or batch |

### Phase 2 limits

* Resource usage is latency, event counts and whatever the agent reports in `usage` (tokens, cost). CPU and memory are not measured.
* Benchmarks run synchronously (at most 200 cases per request). Background jobs arrive with the Phase 5 orchestrator.
* The baseline reviewer is deliberately simple. It is the comparison point for Phases 3 to 5, not a tuned competitor.
* A fault only counts as ground truth if the benchmark can see it. A test enforces this for every shipped fault.

## Known limits

* A timed-out run is reported as an error, but its worker thread finishes in the background. Experiments must stay side-effect free.
* Black-box (HTTP) agents support input-level tests only. Stage-level counterfactuals need an agent that exposes stages.
* No real LLM agent is bundled. The examples are deterministic so experiments are reproducible. A chatbot or research agent backed by an LLM connects through the HTTP adapter or a Python adapter.
