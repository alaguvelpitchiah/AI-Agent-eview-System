"""Compares a failing run with a known-good reference run, stage by stage."""
from __future__ import annotations
import math
from .models import RunRecord, StageDivergence


def values_equal(a, b, tol: float = 1e-9) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b or a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=tol, abs_tol=tol)
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(values_equal(a[k], b[k], tol) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(values_equal(x, y, tol) for x, y in zip(a, b))
    return a == b


def analyze_divergence(failing: RunRecord, reference: RunRecord, stages: list) -> list:
    out = []
    for s in stages:
        f, r = failing.event(s), reference.event(s)
        if f is None or r is None:
            out.append(StageDivergence(s, present=f is not None, input_same=False, output_same=False))
            continue
        out.append(StageDivergence(
            s, present=True,
            input_same=values_equal(f.input, r.input),
            output_same=values_equal(f.output, r.output) and f.error is None))
    return out


def describe(d: StageDivergence) -> str:
    if not d.present:
        return f"{d.stage}: never ran in the failing run"
    if d.output_same:
        return f"{d.stage}: output matches reference"
    if d.input_same:
        return f"{d.stage}: output differs although its input matches the reference (local origin)"
    return f"{d.stage}: output differs, but its input already differed (possible propagation)"
