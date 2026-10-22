"""Runs tasks through adapters and returns results in the standard format."""
from __future__ import annotations

import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .agent_registry import AgentRegistry
from .base_adapter import AgentResult
from .errors import TaskValidationError
from .input_validator import validate_task


class AgentExecutor:
    """Validates an input, runs it with a time limit, and never raises for agent failures.

    Raises only for caller mistakes (unknown agent, invalid input or overrides).
    Failures inside the agent become ``AgentResult(status="error")``, keeping
    any partial trace, so the failure detector can analyse them.

    Note: a timed-out run is reported as an error, but Python cannot forcibly
    stop the worker thread; it finishes in the background. Experiments must
    therefore be side-effect free (work on config copies, never live systems).
    """

    def __init__(
        self,
        registry: AgentRegistry,
        timeout_seconds: float = 30.0,
        max_task_bytes: int = 100_000,
        max_workers: int = 4,
    ) -> None:
        self.registry = registry
        self.timeout_seconds = timeout_seconds
        self.max_task_bytes = max_task_bytes
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="agent-run")

    def execute(
        self,
        agent_id: str,
        task_input: Dict[str, Any],
        overrides: Optional[Dict[str, Any]] = None,
        expected: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[float] = None,
    ) -> AgentResult:
        adapter = self.registry.get(agent_id)  # AgentNotFoundError
        info = adapter.info()
        cleaned = validate_task(task_input, info.input_schema, self.max_task_bytes)  # TaskValidationError
        adapter.validate_overrides(overrides)  # OverrideError
        for label, value in (("expected", expected), ("metadata", metadata)):
            if value is not None and not isinstance(value, dict):
                raise TaskValidationError([f"'{label}' must be an object"])

        limit = self.timeout_seconds if timeout_seconds is None else timeout_seconds
        started_at = datetime.now(timezone.utc).isoformat()
        t0 = time.perf_counter()
        base = dict(
            execution_id=uuid.uuid4().hex,
            agent_id=info.agent_id,
            started_at=started_at,
            input=cleaned,
            overrides=overrides or None,
            expected=expected,
            metadata=metadata,
        )

        def elapsed() -> float:
            return round((time.perf_counter() - t0) * 1000, 2)

        future = self._pool.submit(adapter.run, cleaned, overrides)
        try:
            out = future.result(timeout=limit)
        except FutureTimeout:
            future.cancel()
            return AgentResult(
                agent_version=info.version,
                status="error",
                duration_ms=elapsed(),
                error={"type": "Timeout", "message": f"Agent did not finish within {limit} seconds"},
                **base,
            )
        except Exception as exc:  # agent failure: record it, keep the partial trace
            return AgentResult(
                agent_version=info.version,
                status="error",
                duration_ms=elapsed(),
                events=list(getattr(exc, "events", [])),
                error={"type": getattr(exc, "error_type", type(exc).__name__), "message": str(exc)},
                **base,
            )

        duration = elapsed()
        return AgentResult(
            agent_version=out.agent_version or info.version,
            status="success",
            duration_ms=duration,
            output=out.output,
            events=out.events,
            usage={"latency_ms": duration, **out.usage},
            **base,
        )

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
