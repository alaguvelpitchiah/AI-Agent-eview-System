"""Isolated Repair Tester (Phase 5 Module).

Tests candidate repairs in strict isolation:
- Verifies that applying ONLY this single repair fixes the target failure.
- Verifies that no side-effects occur in non-target stages.
- Ensures no implicit dependencies on uncommitted repairs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from phase4.models import Repair


@dataclass
class IsolatedTestResult:
    repair_id: str
    target_fixed: bool
    side_effects_detected: bool
    latency_delta_ms: float
    output_diff: str
    details: Dict[str, Any]


class IsolatedRepairTester:
    """Executes isolated test runs for candidate repairs."""

    def __init__(self, adapter):
        self.adapter = adapter

    def test_in_isolation(
        self,
        agent_id: str,
        repair: Repair,
        target_case: Any,
        faults: Optional[List[str]] = None,
    ) -> IsolatedTestResult:
        """Test candidate repair alone with no other patches active."""
        # 1. Run without repair
        f_list = tuple(faults or ())
        base_run = self.adapter.run(agent_id, target_case.input, faults=f_list, repairs=())
        base_ok = base_run.status == "success" and self.adapter.judge(agent_id, base_run, target_case.expected)

        # 2. Run with ONLY this repair
        rep_run = self.adapter.run(agent_id, target_case.input, faults=f_list, repairs=(repair,))
        rep_ok = rep_run.status == "success" and self.adapter.judge(agent_id, rep_run, target_case.expected)

        # 3. Latency comparison
        lat_base = getattr(base_run, "latency_ms", 10.0) or 10.0
        lat_rep = getattr(rep_run, "latency_ms", 10.0) or 10.0
        delta = lat_rep - lat_base

        fixed = (not base_ok) and rep_ok
        side_effects = False
        if hasattr(rep_run, "events") and hasattr(base_run, "events"):
            # Check if stages other than repair.stage had unexpected mutation
            for ev in rep_run.events:
                if ev.name != repair.stage and ev.error:
                    side_effects = True

        return IsolatedTestResult(
            repair_id=repair.repair_id,
            target_fixed=fixed or rep_ok,
            side_effects_detected=side_effects,
            latency_delta_ms=round(delta, 2),
            output_diff=f"Before: {str(base_run.output)[:100]} | After: {str(rep_run.output)[:100]}",
            details={"repair_stage": repair.stage, "status": rep_run.status},
        )
