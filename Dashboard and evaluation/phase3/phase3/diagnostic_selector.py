"""Chooses which stages to test first when the experiment budget is limited."""
from __future__ import annotations


def select_stages(stages: list, divergences: list) -> list:
    """Stages whose output diverged in the failing run go first (pipeline order),
    then the rest. A faulty stage can be masked, so the rest are still tested
    when budget allows."""
    div = {d.stage: d for d in divergences}
    first = [s for s in stages if s in div and not div[s].output_same]
    rest = [s for s in stages if s not in first]
    return first + rest
