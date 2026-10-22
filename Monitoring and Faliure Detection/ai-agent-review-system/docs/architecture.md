# Architecture: Phase 1, Agent Integration Layer

The reviewer core never imports an agent. It talks to every agent through `BaseAgentAdapter`.

```
Any AI agent  ->  Adapter  ->  AgentRegistry  ->  AgentExecutor  ->  standard AgentResult
(chatbot, coding,   (factory or     (agents.yaml)      (validate, time limit,      (output, trace events,
 research, data,     HTTP config)                       partial trace on failure)    usage, expected, metadata)
 recruitment, custom)
```

## Ways to connect an agent

| Agent | How | Reviewer visibility |
|---|---|---|
| Runs in this process (Python) | Write an adapter, or wrap a function with `CallableAgentAdapter`; list it in `agents.yaml` as `type: factory` | Full: stage, tool and config overrides if declared |
| Exposes an HTTP endpoint | `type: http` entry in `agents.yaml` | Black box: input, output, latency; events if the response contains them |

Agents are registered only from `agents.yaml`, never from an API request, so callers cannot make the server contact arbitrary URLs.

## Capabilities drive the experiments

Each adapter declares `AgentCapabilities`: trace level (`none`, `io`, `events`) and whether it supports stage, tool and config overrides.
Later phases choose diagnostic experiments from these, so a black-box agent gets input-level tests and an instrumented agent also gets counterfactual stage replay.

## Standard formats

* Input: validated against the adapter's `input_schema`.
* Result: `AgentResult` with output, `events` (kind, name, input, output, duration, overridden, error), `usage`, `expected`, `metadata`, and an `error` block. Agent failures are results, not exceptions, and keep the partial trace.
* Benchmark cases: `data/benchmark_cases/<agent_id>/cases.json` with `case_id`, `input`, `expected`, `tags`.
