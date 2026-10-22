"""Interaction Reporter (Phase 4 Module).

Summarizes and visualizes fault interaction findings:
- Categorizes interactions: Synergistic (emergent failure), Cancelling (masking), Additive, or Benign.
- Reports status: Confirmed, Suspected, Inconclusive.
- Generates pairwise interaction matrix for dashboard rendering.
- Calculates testing budget utilization.
"""

from __future__ import annotations

from typing import Any, Dict, List
from pydantic import BaseModel, Field
from .combination_test_runner import CombinationResult, InteractionStatus


class InteractionReportSummary(BaseModel):
    total_combinations_tested: int = 0
    confirmed_synergies: int = 0
    cancelling_interactions: int = 0
    additive_failures: int = 0
    inconclusive_count: int = 0
    budget_used: int = 0
    budget_limit: int = 16
    pairwise_matrix: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    detailed_findings: List[Dict[str, Any]] = Field(default_factory=list)
    mitigation_priorities: List[str] = Field(default_factory=list)


class InteractionReporter:
    """Produces structured interaction reports for dashboard and evaluation exports."""

    @classmethod
    def generate_report(
        cls,
        results: List[CombinationResult],
        budget_limit: int = 16,
    ) -> InteractionReportSummary:
        summary = InteractionReportSummary(
            total_combinations_tested=len(results),
            budget_used=len(results),
            budget_limit=budget_limit,
        )

        matrix: Dict[str, Dict[str, str]] = {}
        findings: List[Dict[str, Any]] = []
        priorities: List[str] = []

        for r in results:
            if r.interaction_status == InteractionStatus.CONFIRMED and r.synergy_type == "synergistic":
                summary.confirmed_synergies += 1
                priorities.append(f"CRITICAL: Synergistic fault interaction between {' & '.join(r.fault_names)}")
            elif r.interaction_status == InteractionStatus.CONFIRMED and r.synergy_type == "cancelling":
                summary.cancelling_interactions += 1
            elif r.synergy_type == "additive":
                summary.additive_failures += 1
            elif r.interaction_status == InteractionStatus.INCONCLUSIVE:
                summary.inconclusive_count += 1

            if len(r.fault_names) == 2:
                f1, f2 = r.fault_names[0], r.fault_names[1]
                if f1 not in matrix:
                    matrix[f1] = {}
                if f2 not in matrix:
                    matrix[f2] = {}
                label = r.synergy_type or "benign"
                matrix[f1][f2] = label
                matrix[f2][f1] = label

            findings.append({
                "combo_id": r.combo_id,
                "faults": r.fault_names,
                "is_failed": r.is_failed,
                "status": r.interaction_status.value,
                "synergy_type": r.synergy_type,
                "latency_ms": r.latency_ms,
                "failure_category": r.failure_category,
            })

        summary.pairwise_matrix = matrix
        summary.detailed_findings = findings
        summary.mitigation_priorities = priorities or ["No severe synergistic fault interactions detected."]
        return summary
