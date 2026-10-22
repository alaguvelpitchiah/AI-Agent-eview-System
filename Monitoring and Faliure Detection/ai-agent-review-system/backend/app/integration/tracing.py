"""Helper for in-process agents to record trace events and honour overrides."""
from __future__ import annotations

import time
from typing import Any, Callable, List, Optional

from .base_adapter import TraceEvent

MISSING = object()  # "no override given" (None is a legitimate override value)


class EventRecorder:
    """Runs steps, times them, records one TraceEvent each, supports replacement.

    If a step raises, its event (with the error) is recorded before the
    exception propagates, so the trace explains where the run failed.
    """

    def __init__(self, version: Optional[str] = None) -> None:
        self.version = version
        self.events: List[TraceEvent] = []

    def step(
        self,
        name: str,
        compute: Callable[[], Any],
        *,
        kind: str = "stage",
        input: Any = None,
        override: Any = MISSING,
    ) -> Any:
        start = time.perf_counter()
        overridden = override is not MISSING
        try:
            output = override if overridden else compute()
        except Exception as exc:
            self._add(kind, name, input, None, start, False, f"{type(exc).__name__}: {exc}")
            raise
        self._add(kind, name, input, output, start, overridden, None)
        return output

    def _add(self, kind, name, input, output, start, overridden, error) -> None:
        self.events.append(
            TraceEvent(
                kind=kind,
                name=name,
                input=input,
                output=output,
                duration_ms=round((time.perf_counter() - start) * 1000, 3),
                overridden=overridden,
                component_version=self.version,
                error=error,
            )
        )
