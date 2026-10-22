"""Validation Gate (Phase 5 Module).

Enforces the 8 Hard Gates and evaluates candidate repairs.
Returns strictly one of three outcomes:
- PASS: All 8 hard gates satisfied with high confidence.
- FAIL: Confirmed failure or regression in any gate.
- UNCERTAIN: Inconclusive counterfactual data or marginal confidence threshold.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .gates import GateRunner, GateConfig, GateReport, GateResult


class GateOutcome(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNCERTAIN = "UNCERTAIN"


class ValidationGateSummary(BaseModel):
    outcome: GateOutcome
    confidence: float
    passed_all_gates: bool
    passed_gates: List[str] = Field(default_factory=list)
    failed_gates: List[str] = Field(default_factory=list)
    gate_details: List[Dict[str, Any]] = Field(default_factory=list)
    runs_executed: int = 0
    decision_reason: str


class ValidationGate:
    """Evaluates candidate repairs against all 8 hard gates and computes three-state outcome."""

    def __init__(self, adapter, config: Optional[GateConfig] = None):
        self.runner = GateRunner(adapter, config or GateConfig())

    def evaluate_repair(
        self,
        agent_id: str,
        faults: List[str],
        targets: List[Any],
        regression: List[Any],
        heldout: List[Any],
        diagnosis: Any,
        repairs: List[Any],
    ) -> ValidationGateSummary:
        """Run all hard gates and map results to PASS, FAIL, or UNCERTAIN."""
        raw_report: GateReport = self.runner.evaluate(
            agent_id, faults, targets, regression, heldout, diagnosis, repairs
        )

        passed_names = [r.name for r in raw_report.results if r.passed]
        failed_names = [r.name for r in raw_report.results if not r.passed]
        gate_details = [
            {"gate": r.name, "passed": r.passed, "detail": r.detail}
            for r in raw_report.results
        ]

        # Calculate confidence score
        total_gates = len(raw_report.results)
        conf = (len(passed_names) / total_gates) if total_gates > 0 else 0.0

        # Assess outcome
        if raw_report.passed:
            outcome = GateOutcome.PASS
            reason = "All 8 Hard Gates verified cleanly. Zero regressions detected."
        else:
            # Check if failure is due to low diagnosis confidence / inconclusive data
            diag_failed = "diagnosis_confirmed" in failed_names
            stability_failed = "stable" in failed_names

            if diag_failed or (len(failed_names) == 1 and stability_failed):
                outcome = GateOutcome.UNCERTAIN
                reason = "Inconclusive evidence or marginal diagnosis confidence. Abstained from auto-approval."
            else:
                outcome = GateOutcome.FAIL
                reason = f"Hard gate failure: Failed gates: {', '.join(failed_names)}"

        return ValidationGateSummary(
            outcome=outcome,
            confidence=round(conf, 3),
            passed_all_gates=raw_report.passed,
            passed_gates=passed_names,
            failed_gates=failed_names,
            gate_details=gate_details,
            runs_executed=raw_report.runs,
            decision_reason=reason,
        )
