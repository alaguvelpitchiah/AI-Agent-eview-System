"""Regression Tester (Phase 5 Module).

Runs comprehensive regression testing:
- Executes known passing benchmark cases to ensure 0 regressions.
- Executes held-out test cases not seen during repair planning.
- Reports regression rate with precision and exact failing case IDs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from phase4.models import Repair


@dataclass
class RegressionReport:
    total_regression_cases: int = 0
    passed_cases: int = 0
    regressed_cases: int = 0
    heldout_total: int = 0
    heldout_passed: int = 0
    heldout_regressed: int = 0
    regressed_case_ids: List[str] = field(default_factory=list)
    clean: bool = True


class RegressionTester:
    """Executes regression and held-out test verification suites."""

    def __init__(self, adapter):
        self.adapter = adapter

    def run_regression_suite(
        self,
        agent_id: str,
        repairs: List[Repair],
        regression_cases: List[Any],
        heldout_cases: Optional[List[Any]] = None,
        faults: Optional[List[str]] = None,
    ) -> RegressionReport:
        report = RegressionReport(
            total_regression_cases=len(regression_cases),
            heldout_total=len(heldout_cases or []),
        )
        f_list = tuple(faults or ())
        rep_tuple = tuple(repairs)

        # 1. Baseline regression suite
        for case in regression_cases:
            run = self.adapter.run(agent_id, case.input, faults=f_list, repairs=rep_tuple)
            ok = run.status == "success" and self.adapter.judge(agent_id, run, case.expected)
            if ok:
                report.passed_cases += 1
            else:
                report.regressed_cases += 1
                report.regressed_case_ids.append(case.case_id)

        # 2. Heldout suite
        if heldout_cases:
            for case in heldout_cases:
                run = self.adapter.run(agent_id, case.input, faults=f_list, repairs=rep_tuple)
                ok = run.status == "success" and self.adapter.judge(agent_id, run, case.expected)
                if ok:
                    report.heldout_passed += 1
                else:
                    report.heldout_regressed += 1
                    report.regressed_case_ids.append(f"heldout:{case.case_id}")

        report.clean = (report.regressed_cases == 0 and report.heldout_regressed == 0)
        return report
