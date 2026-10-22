"""Turn a failed evaluation into a categorised failure report."""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .outcome_evaluator import CheckResult, OutcomeEvaluation
from .trace_collector import TraceRecord

# Categories, highest priority first.
CATEGORY_PRIORITY = [
    "safety_violation", "timeout", "tool_failure", "execution_error", "incorrect_output",
    "incomplete_output", "wrong_error_type", "unexpected_success", "slow_response",
]
DEFAULT_SEVERITY = {
    "safety_violation": "critical", "timeout": "critical", "tool_failure": "critical",
    "execution_error": "critical", "incorrect_output": "major", "incomplete_output": "major",
    "wrong_error_type": "major", "unexpected_success": "major", "slow_response": "minor",
}
_RANK = {"minor": 0, "major": 1, "critical": 2}


@dataclass
class FailureReport:
    failure_id: str
    execution_id: str
    agent_id: str
    agent_version: str
    category: str
    secondary_categories: List[str]
    severity: str
    summary: str
    failed_checks: List[Dict[str, Any]]
    error: Optional[Dict[str, str]]
    first_error_event: Optional[Dict[str, Any]]
    event_names: List[str]
    expected: Optional[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]]
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _check_category(check: CheckResult) -> str:
    if check.category == "safety":
        return "safety_violation"
    if check.category in ("wrong_error_type", "unexpected_success"):
        return check.category
    if check.category == "performance":
        return "slow_response"
    if check.category == "execution":
        return "execution_error"
    if check.category == "completeness" or check.missing:
        return "incomplete_output"
    return "incorrect_output"


class FailureDetector:
    def detect(self, record: TraceRecord, evaluation: OutcomeEvaluation) -> Optional[FailureReport]:
        if evaluation.verdict in ("pass", "no_expectation"):
            return None

        failed = [c for c in evaluation.checks if not c.passed]
        first_error = record.error_events[0] if record.error_events else None
        categories: List[str] = []

        if evaluation.verdict == "error":
            err_type = (record.error or {}).get("type")
            if err_type == "Timeout":
                categories.append("timeout")
            elif first_error and first_error["kind"] == "tool_call":
                categories.append("tool_failure")
            else:
                categories.append("execution_error")
        else:
            categories = [_check_category(c) for c in failed]

        ordered = sorted(set(categories), key=CATEGORY_PRIORITY.index)
        primary, secondary = ordered[0], ordered[1:]

        severities = [
            c.severity if c.category in ("correctness", "completeness", "safety") else DEFAULT_SEVERITY[_check_category(c)]
            for c in failed
        ]
        severity = max(severities, key=_RANK.__getitem__) if severities else DEFAULT_SEVERITY[primary]
        if evaluation.verdict == "error":
            severity = DEFAULT_SEVERITY[primary]

        return FailureReport(
            failure_id=uuid.uuid4().hex,
            execution_id=record.execution_id,
            agent_id=record.agent_id,
            agent_version=record.agent_version,
            category=primary,
            secondary_categories=secondary,
            severity=severity,
            summary=self._summary(record, evaluation, failed),
            failed_checks=[c.to_dict() for c in failed],
            error=record.error,
            first_error_event=first_error,
            event_names=[e["name"] for e in record.events],
            expected=record.expected,
            metadata=record.metadata,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def _summary(record: TraceRecord, evaluation: OutcomeEvaluation, failed: List[CheckResult]) -> str:
        if evaluation.verdict == "error":
            err = record.error or {}
            return f"Run failed with {err.get('type', 'error')}: {err.get('message', '')}"
        parts = [f"{c.name} ({c.message})" for c in failed[:3]]
        more = f" and {len(failed) - 3} more" if len(failed) > 3 else ""
        return f"{len(failed)} of {len(evaluation.checks)} checks failed: " + "; ".join(parts) + more
