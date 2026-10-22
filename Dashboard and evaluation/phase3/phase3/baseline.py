"""Simple trace-only reviewer (same rules as the Phase 2 baseline): first error,
then first empty output, then last stage. Used as the comparison point."""
from __future__ import annotations


def _empty(v) -> bool:
    return v is None or v == "" or v == [] or v == {}


def baseline_blame(failing, stages: list) -> str:
    for e in failing.events:
        if e.error:
            return e.name
    for e in failing.events:
        if _empty(e.output):
            return e.name
    return stages[-1]
