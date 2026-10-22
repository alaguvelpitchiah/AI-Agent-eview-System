"""Turn an executor result into a stored-ready trace record.

Records inputs, outputs, tool calls, errors and execution time, after removing
secrets and bounding the size of large payloads.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..integration.base_adapter import AgentResult
from .redaction import redact


@dataclass
class TraceRecord:
    execution_id: str
    agent_id: str
    agent_version: str
    status: str
    started_at: str
    duration_ms: float
    input: Dict[str, Any]
    output: Any
    events: List[Dict[str, Any]]
    usage: Dict[str, Any]
    error: Optional[Dict[str, str]]
    expected: Optional[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]]
    overrides: Optional[Dict[str, Any]]
    event_count: int = 0
    tool_call_count: int = 0
    error_events: List[Dict[str, Any]] = field(default_factory=list)
    truncated: bool = False
    batch_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TraceCollector:
    def __init__(self, max_payload_chars: int = 20_000, preview_chars: int = 500) -> None:
        self.max_payload_chars = max_payload_chars
        self.preview_chars = preview_chars

    def _bound(self, value: Any) -> Tuple[Any, bool]:
        """Replace an oversized payload with a short preview."""
        try:
            text = json.dumps(value, default=str)
        except (TypeError, ValueError):
            text = str(value)
        if len(text) <= self.max_payload_chars:
            return value, False
        return {"_truncated": True, "original_chars": len(text), "preview": text[: self.preview_chars]}, True

    def collect(self, result: AgentResult, batch_id: Optional[str] = None) -> TraceRecord:
        data = result.to_dict()
        truncated = False

        def clean(value: Any) -> Any:
            nonlocal truncated
            bounded, cut = self._bound(redact(value))
            truncated = truncated or cut
            return bounded

        events = []
        for event in data["events"]:
            events.append({**event, "input": clean(event.get("input")), "output": clean(event.get("output"))})

        return TraceRecord(
            execution_id=data["execution_id"],
            agent_id=data["agent_id"],
            agent_version=data["agent_version"],
            status=data["status"],
            started_at=data["started_at"],
            duration_ms=data["duration_ms"],
            input=clean(data["input"]),
            output=clean(data["output"]),
            events=events,
            usage=redact(data["usage"]),
            error=data["error"],
            expected=data["expected"],
            metadata=redact(data["metadata"]) if data["metadata"] else data["metadata"],
            overrides=data["overrides"],
            event_count=len(events),
            tool_call_count=sum(1 for e in events if e["kind"] == "tool_call"),
            error_events=[
                {"name": e["name"], "kind": e["kind"], "error": e["error"]} for e in events if e.get("error")
            ],
            truncated=truncated,
            batch_id=batch_id,
        )
