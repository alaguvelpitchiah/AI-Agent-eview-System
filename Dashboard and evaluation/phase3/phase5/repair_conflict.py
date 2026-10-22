"""Repair Conflict Module (Phase 5 Module).

Analyzes pairwise and multi-repair conflicts to detect emergent regression traps:
- Repair A passes on its own.
- Repair B passes on its own.
- But combined Repair A + B causes regression or failure.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from phase4.conflict_analyzer import ConflictAnalyzer
from phase4.models import RepairPlan, ConflictReport


class RepairConflict(ConflictAnalyzer):
    """Alias & extension for ConflictAnalyzer in Phase 5."""

    def detect_conflicts(
        self,
        agent_id: str,
        plans: List[RepairPlan],
        targets: List[Any],
        regression: List[Any],
        faults: Optional[List[str]] = None,
    ) -> ConflictReport:
        """Evaluate pairs of repair plans for mutual regression or ordering dependency."""
        return self.analyze(agent_id, faults or [], targets, regression, plans)
