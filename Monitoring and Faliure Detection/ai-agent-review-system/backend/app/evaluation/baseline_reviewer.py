"""Baseline reviewer: detect a failure and name a likely culprit with simple heuristics.

It never runs experiments, tests combinations of faults or checks fixes. It exists
so the full reviewer can be compared against what a developer would do by
reading a trace. Rules, in order:

1. the first step that recorded an error,
2. the first step whose output is empty,
3. the last step of the run (it produced the final answer).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

from ..reviewer.failure_detector import FailureReport
from ..reviewer.trace_collector import TraceRecord

_ACTIONS = {
    "safety_violation": "Add or tighten the safety rule in '{c}' and re-run the failing case.",
    "timeout": "Check why '{c}' is slow or stuck, then add a timeout or retry limit.",
    "tool_failure": "Inspect the arguments sent to '{c}' and handle its error cases.",
    "execution_error": "Fix the error raised in '{c}' and re-run the failing case.",
    "incorrect_output": "Review the logic or configuration of '{c}' and re-run the failing case.",
    "incomplete_output": "Make '{c}' return the missing information and re-run the failing case.",
    "wrong_error_type": "Check how '{c}' reports failures.",
    "unexpected_success": "Add the missing validation in '{c}'.",
    "slow_response": "Profile '{c}' and reduce its latency.",
}


@dataclass
class BaselineDiagnosis:
    failure_id: str
    method: str
    suspected_component: str
    rule: str
    rationale: str
    suggested_action: str
    confidence: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


class BaselineReviewer:
    def diagnose(self, record: TraceRecord, report: FailureReport) -> BaselineDiagnosis:
        component, rule, why = self._pick(record)
        action = _ACTIONS[report.category].format(c=component)
        return BaselineDiagnosis(report.failure_id, "baseline_heuristic", component, rule, why, action, "low")

    @staticmethod
    def _pick(record: TraceRecord):
        events = record.events
        if record.error_events:
            first = record.error_events[0]
            return first["name"], "first_error_event", f"'{first['name']}' recorded an error: {first['error']}"
        if not events:
            return "agent", "no_trace", "The agent exposed no steps, so the whole agent is the only candidate"
        for event in events:
            if not event.get("overridden") and _is_empty(event.get("output")):
                return event["name"], "first_empty_output", f"'{event['name']}' produced an empty output"
        last = events[-1]
        return last["name"], "last_stage", f"'{last['name']}' produced the final result"
