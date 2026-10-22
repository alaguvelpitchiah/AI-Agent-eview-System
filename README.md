# AI Agent Review and Performance Improvement System

A state-of-the-art **Full-Stack Web Application and Automated Evaluation System** engineered to test, monitor, diagnose, and continuously improve **any AI agent product** (chatbots, tool-using calculators, recruitment workflows, coding agents, research assistants, and custom HTTP/Python services).

The system autonomously runs agent tasks, monitors step-by-step execution traces with secret redaction, evaluates outcomes against strict expectation rules, detects failures across standardized categories, performs scientific root-cause diagnosis (RCA), analyzes fault interactions ($2^k$ factorial), generates candidate repairs, validates fixes across regression suites using **8 Hard Gates**, and supports human-in-the-loop review approvals.

---

## 🌟 System Architecture Overview

```
                                  +---------------------------------------------+
                                  |            ANY AI AGENT PRODUCT             |
                                  |  (Python Callable, Class, or HTTP Endpoint)  |
                                  +---------------------------------------------+
                                                         |
                                                         v
               =====================================================================================
               PHASE 1: AGENT INTEGRATION CORE (BaseAgentAdapter & Registry)
               =====================================================================================
               * Standard Input / Output / Event Tracing Schema
               * Config, Tool, and Stage Overrides (Sandbox Isolation)
               * Auto-discovered via agents.yaml
                                                         |
                                                         v
               =====================================================================================
               PHASE 2: LIVE MONITORING & FAILURE DETECTION (SQLite Store & Evaluator)
               =====================================================================================
               * TraceCollector (Step-level timing, status, inputs, outputs)
               * Secret Redaction & Payload Bound Controls
               * OutcomeEvaluator: 18 path operators (equals, approx, regex, contains, etc.)
               * FailureDetector: Categories (incorrect_output, safety, tool_error, latency_spike)
                                                         |
                                                         v
               =====================================================================================
               PHASE 3: SCIENTIFIC ROOT-CAUSE DIAGNOSIS (RCA Engine)
               =====================================================================================
               * Controlled Counterfactual Experiments across pipeline stages
               * 100% Exact Match Root Cause Attribution (vs 26% Heuristic Baseline)
                                                         |
                                                         v
               =====================================================================================
               PHASE 4: FAULT INTERACTION ANALYSIS & REPAIR VALIDATION
               =====================================================================================
               * 2^k Factorial Experiments (Synergistic vs Cancelling interactions)
               * Automated Repair Generation (Root-cause & Downstream compensating)
               * Conflict Analyzer (Detects emergent regression traps: A passes, B passes, A+B fails)
                                                         |
                                                         v
               =====================================================================================
               PHASE 5: ORCHESTRATION, 8 HARD GATES & HUMAN-IN-THE-LOOP
               =====================================================================================
               * 8 Mandatory Hard Gates:
                 1. Diagnosis Confirmed        2. Target Fixed               3. No Regression (Clean)
                 4. Held-out No Regression     5. Root-Cause Coverage        6. No Compensating Hacks
                 7. Pairwise Safe              8. Stability Verification
               * Failure Memory Cache: Jaccard symptom similarity >= 0.85 with automated re-validation
               * Named Reviewer Approval Queue & Audit Trail
                                                         |
                                                         v
               =====================================================================================
               PHASE 6: UNIFIED FULL-STACK DASHBOARDS & EVALUATION BENCHMARK
               =====================================================================================
               * Unified Glassmorphic Dark-Mode Web App (Port 8004): Live Agent Testing, RCA & Gates
               * Streamlit Benchmark Dashboard (Port 8501): Wilson 95% CIs & Statistical Sign Tests
```

---

## 🚀 Quick Start & One-Click Execution

### 1. Master Control Scripts (Root Workspace)
You can launch, inspect, and stop all components with single bash commands:

```bash
# Start all 6 Full-Stack & Microservice subsystems
./start_all.sh

# Check real-time service health, listening ports, and databases
./status.sh

# Stop all background servers cleanly
./stop_all.sh
```

### 2. Active Web Interfaces & Microservice Ports

| Component | Port | Description | URL / Docs |
|---|---|---|---|
| **Unified Full-Stack Web App** | **`8004`** | **Primary Interactive Web Application**: Agent Testing Sandbox, Live RCA Explorer, 8 Hard Gates, Approvals Queue & Benchmark Reports | [http://127.0.0.1:8004/](http://127.0.0.1:8004/)<br>Docs: [/docs](http://127.0.0.1:8004/docs) |
| **Streamlit Visual Dashboard** | **`8501`** | **Evaluation & Benchmark Dashboard**: Statistical Wilson 95% CIs, Group Slices, Significance Sign Tests | [http://127.0.0.1:8501](http://127.0.0.1:8501) |
| **AI Agent Monitoring API** | **`8000`** | **Phases 1 & 2 Service**: Target Agent execution, live monitoring, synthetic fault injection & trace recording | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) |
| **Root-Cause Diagnosis (RCA)** | **`8001`** | **Phase 3 Microservice**: Counterfactual stage experimentation engine | [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs) |
| **Repair & Conflict Validation** | **`8002`** | **Phase 4 Microservice**: $2^k$ Factorial interaction & repair search | [http://127.0.0.1:8002/docs](http://127.0.0.1:8002/docs) |
| **Orchestration & Hard Gates** | **`8003`** | **Phase 5 Microservice**: End-to-end review orchestrator & approval workflow | [http://127.0.0.1:8003/docs](http://127.0.0.1:8003/docs) |

---

## 🧪 Verified Test Suite (312 Tests Passing)

The entire codebase is verified by an extensive automated test suite covering all phases:

```bash
# Phase 1 & 2 Integration & Monitoring Backend (245 Tests)
cd "Monitoring and Faliure Detection/ai-agent-review-system/backend"
pytest
# Result: 245 passed in 96.79s (100% pass rate)

# Phases 3, 4, 5, 6 Evaluation & Orchestration (67 Tests)
cd "Dashboard and evaluation"
pytest phase3/tests
# Result: 67 passed in 22.37s (100% pass rate)

# Total: 312 Passed / 0 Failed
```

---

## 🤖 Connecting Any AI Agent Product

The review system is completely **agent-agnostic**. Any AI Agent can be integrated in minutes using one of two methods:

### Method A: Connect a Remote Agent over HTTP (Microservice / Cloud API)
In `agents.yaml`, add:
```yaml
agents:
  - type: http
    agent_id: my-custom-agent
    name: Production Customer Support Agent
    agent_type: chatbot
    version: "2.1.0"
    url: "https://agent-api.internal.com/v1/run"
    headers:
      Authorization: "Bearer ${AGENT_API_KEY}"
    timeout_seconds: 30
    input_schema:
      fields:
        query: {type: str, required: true, min_length: 2}
    output_path: result.answer
    events_path: trace.events
    usage_path: usage
```

### Method B: Connect an In-Process Python Agent
Implement `BaseAgentAdapter` or use `CallableAgentAdapter`:
```python
from app.integration.base_adapter import BaseAgentAdapter, AgentRunResult

class MyAgentAdapter(BaseAgentAdapter):
    def run(self, task_input, overrides=None, **kwargs):
        # Your agent logic, tool calls, and LLM completions
        response = my_llm_agent(task_input["query"])
        return AgentRunResult(
            output={"answer": response},
            trace_events=[...],
            status="success"
        )
```
Register the factory in `agents.yaml`:
```yaml
agents:
  - type: factory
    factory: "my_package.adapter:create_adapter"
```

---

## 🔍 How Failures & Errors Are Evaluated

The system supports a declarative **Expected Outcome Block** that works uniformly across every AI agent:

```json
{
  "checks": [
    {"path": "answer", "op": "contains", "value": "confirmation number"},
    {"path": "answer", "op": "not_contains", "value": "internal_key", "category": "safety", "severity": "critical"},
    {"path": "match_score", "op": "gte", "value": 85, "severity": "minor"}
  ],
  "max_latency_ms": 2500,
  "expect_error": null
}
```

### Supported Path Operators
* **Equality & Numerical**: `equals`, `not_equals`, `approx`, `gt`, `gte`, `lt`, `lte`, `between`
* **Text & Pattern**: `contains`, `not_contains`, `regex`, `in`, `not_in`
* **Structure & Typing**: `type_is`, `min_length`, `max_length`, `is_null`, `not_null`, `exists`, `absent`

### Failure Categories
1. `incorrect_output`: Output violated functional correctness checks.
2. `incomplete_output`: Required structured attributes or sections missing.
3. `safety_violation`: PII leakage, prompt jailbreak, or sensitive token disclosure.
4. `tool_error`: Simulated or actual failure in downstream agent tools.
5. `latency_spike`: Agent exceeded maximum allowable response budget.

---

## 🛡️ The 8 Mandatory Hard Gates

Before any suggested repair or performance improvement is submitted for human approval, it **must pass all 8 Hard Gates** without exception:

| Gate | Validation Rule |
|---|---|
| **1. Diagnosis Confirmed** | Isolates the faulty stage using controlled counterfactual tests; cannot be inconclusive. |
| **2. Target Fixed** | The candidate repair set successfully converts the failing target scenario to a pass. |
| **3. No Regression (Clean)** | Zero regressions across all pre-existing passing cases in the regression test suite. |
| **4. Held-out No Regression** | Zero regressions on held-out test scenarios not seen during repair planning. |
| **5. Root-Cause Coverage** | Every confirmed faulty stage has an explicit, targeted patch. |
| **6. No Compensating Hacks** | Prevents applying downstream compensating fixes that mask underlying root causes. |
| **7. Pairwise Safe** | Verifies multi-stage repairs in isolation and combination to detect emergent conflict traps. |
| **8. Stability Verification** | Re-runs the repaired agent to confirm non-flaky, deterministic execution. |

---

## 📈 Benchmark Results: Pipeline vs. Heuristic Baseline

Evaluated across 39 benchmark scenarios covering single faults, held-out faults, conflict traps, double synergistic faults, and independent decoys:

| Metric | Our Pipeline | Heuristic Baseline | Absolute Lift |
|---|---|---|---|
| **1. Root-Cause Exact Match** | **100% [0.91 - 1.00]** | 26% [0.15 - 0.41] | **+74%** 🚀 |
| **2. Blame Precision** | **100% [0.91 - 1.00]** | 26% [0.15 - 0.41] | **+74%** 🚀 |
| **3. Correct Fix Rate** | **92% - 100%** | 33% [0.20 - 0.49] | **+67%** 🚀 |
| **4. Regression Rate** | **0.00% [0.00 - 0.09]** | 63% [0.47 - 0.76] | **-63% Safer** 🛡️ |
| **5. Conflict Trap Recall** | **100% [0.61 - 1.00]** | 0% [0.00 - 0.39] | **100% Traps Caught** 🎯 |
| **6. Unsafe Deployment Rate** | **0.00% [0.00 - 0.09]** | 67% [0.51 - 0.79] | **Zero Unsafe Fixes** 🛡️ |

---

## 📂 Repository Structure

```
├── Dashboard and evaluation/               # Unified Server (Port 8004) & Streamlit (Port 8501)
│   ├── server.py                          # Unified Full-Stack FastAPI Server
│   ├── run_server.sh                      # Standalone runner for Port 8004
│   └── phase3/                            # Core Evaluation Engine (Phases 3, 4, 5, 6)
│       ├── phase3/                        # Root-Cause Diagnosis algorithms
│       ├── phase4/                        # 2^k Factorial & Repair Planning
│       ├── phase5/                        # 8 Hard Gates, Orchestrator, Jobs & Approvals
│       ├── phase6/                        # Benchmark Runner, Streamlit Dashboard & Report
│       └── phase6_results/                # Benchmark JSON, HTML & Markdown reports
├── Monitoring and Faliure Detection/       # Agent Integration & Monitoring Backend (Port 8000)
│   └── ai-agent-review-system/
│       ├── backend/                       # FastAPI Monitoring Service, Storage & Adapters
│       │   ├── app/integration/           # Universal BaseAgentAdapter & Registry
│       │   ├── app/reviewer/              # TraceCollector, OutcomeEvaluator, FailureDetector
│       │   ├── app/target_agents/         # Built-in Agents (Calculator, FAQ Chatbot, Recruitment)
│       │   └── agents.yaml                # Pluggable Agent Configurations
│       └── data/                          # Benchmark Cases & Synthetic Fault Scenarios
├── root-cause diagnosis/                  # Standalone RCA Microservice (Port 8001)
├── Fault interaction and repair validation/ # Standalone Repair Planning Microservice (Port 8002)
├── Repairs, conflicts, validation, orchestration/ # Standalone Phase 5 Microservice (Port 8003)
├── start_all.sh                           # Master runner script for all services
├── status.sh                              # Real-time health and port monitor
└── stop_all.sh                            # Graceful shutdown script
```
