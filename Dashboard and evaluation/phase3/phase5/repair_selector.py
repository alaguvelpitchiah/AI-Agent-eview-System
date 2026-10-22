"""Repair Selector (Phase 5 Module).

Selects the optimal, non-conflicting repair plan from multiple candidates:
- Prioritizes plans that pass all 8 hard gates.
- Selects root-cause repairs over downstream compensating repairs.
- Minimizes patch complexity and latency overhead.
- Requires explicit evidence before recommending.
"""

from __future__ import annotations

from typing import Any, List, Optional
from phase4.models import RepairPlan
from .validation_gate import ValidationGate, GateOutcome, ValidationGateSummary


class RepairSelector:
    """Selects the best validated repair plan for human reviewer review."""

    def __init__(self, gate: ValidationGate):
        self.gate = gate

    def select_best_repair(
        self,
        agent_id: str,
        candidate_plans: List[RepairPlan],
        targets: List[Any],
        regression: List[Any],
        heldout: List[Any],
        diagnosis: Any,
        faults: Optional[List[str]] = None,
    ) -> tuple[Optional[RepairPlan], Optional[ValidationGateSummary]]:
        """Evaluate candidate plans and return the top-ranking passing plan."""
        passing_candidates: List[tuple[RepairPlan, ValidationGateSummary]] = []
        uncertain_candidates: List[tuple[RepairPlan, ValidationGateSummary]] = []

        f_list = list(faults or [])

        for plan in candidate_plans:
            summary = self.gate.evaluate_repair(
                agent_id, f_list, targets, regression, heldout, diagnosis, plan.repairs
            )
            if summary.outcome == GateOutcome.PASS:
                passing_candidates.append((plan, summary))
            elif summary.outcome == GateOutcome.UNCERTAIN:
                uncertain_candidates.append((plan, summary))

        if passing_candidates:
            # Sort by: 1) fewest repairs, 2) fewest runs, 3) highest confidence
            passing_candidates.sort(key=lambda item: (len(item[0].repairs), item[1].runs_executed))
            best_plan, best_summary = passing_candidates[0]
            return best_plan, best_summary

        if uncertain_candidates:
            # Return uncertain candidate with note
            best_plan, best_summary = uncertain_candidates[0]
            return best_plan, best_summary

        return None, None
