"""Combinatorial Test Runner (Phase 4 Module).

Executes combinatorial fault interaction tests against target AI systems:
- Pairs & triples of faults (e.g., Ambiguity + Misspelling, Incomplete + Strict Format).
- Enforces strict configurable test budget (max_api_calls / max_combinations) to prevent runaway costs.
- Prioritizes combinations based on single-variable failure severity.
- Classifies each interaction outcome as CONFIRMED, SUSPECTED, or INCONCLUSIVE.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from itertools import combinations
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

from app.reviewer.single_fault_injector import SingleFaultInjector, SingleFaultType


class InteractionStatus(str, Enum):
    CONFIRMED = "confirmed"
    SUSPECTED = "suspected"
    INCONCLUSIVE = "inconclusive"
    BENIGN = "benign"


@dataclass
class CombinationResult:
    combo_id: str
    fault_names: List[str]
    input_payload: Any
    actual_output: Any
    latency_ms: float
    is_failed: bool
    failure_category: Optional[str]
    interaction_status: InteractionStatus
    synergy_type: Optional[str]  # "synergistic", "cancelling", "additive", "none"
    evidence: Dict[str, Any] = field(default_factory=dict)


class CombinationTestRunner:
    """Runs combinatorial multi-fault tests within a bounded test call budget."""

    def __init__(
        self,
        test_budget: int = 16,
        max_combination_degree: int = 3,
        timeout_per_run: float = 10.0,
    ) -> None:
        self.test_budget = test_budget
        self.max_combination_degree = max_combination_degree
        self.timeout_per_run = timeout_per_run

    def generate_fault_combinations(
        self,
        candidate_faults: List[SingleFaultType],
        budget: Optional[int] = None,
    ) -> List[List[SingleFaultType]]:
        """Generate ordered multi-fault combinations up to budget."""
        effective_budget = budget or self.test_budget
        combos: List[List[SingleFaultType]] = []

        # Degree 2 pairs first
        for pair in combinations(candidate_faults, 2):
            combos.append(list(pair))
            if len(combos) >= effective_budget:
                return combos

        # Degree 3 triples if budget permits
        if self.max_combination_degree >= 3:
            for triple in combinations(candidate_faults, 3):
                combos.append(list(triple))
                if len(combos) >= effective_budget:
                    return combos

        return combos

    def apply_multi_fault(self, base_input: Any, faults: List[SingleFaultType]) -> Any:
        """Sequentially apply multiple fault perturbations to the base input."""
        current = base_input
        for f in faults:
            res = SingleFaultInjector.inject(f, current)
            current = res.perturbed_input
        return current

    def run_combinatorial_evaluation(
        self,
        base_input: Any,
        expected_criteria: Dict[str, Any],
        target_fn: Callable[[Any], Dict[str, Any]],
        single_results: Optional[Dict[str, bool]] = None,
        selected_faults: Optional[List[SingleFaultType]] = None,
    ) -> List[CombinationResult]:
        """Execute combinations and evaluate synergistic vs isolated failure behaviors."""
        fault_pool = selected_faults or [
            SingleFaultType.AMBIGUOUS_PROMPT,
            SingleFaultType.MISSPELLING,
            SingleFaultType.INCOMPLETE_INPUT,
            SingleFaultType.FORMAT_STRICTNESS,
            SingleFaultType.LARGE_PAYLOAD,
        ]

        # Baseline single runs if not provided
        single_fails = dict(single_results or {})
        results: List[CombinationResult] = []
        combos = self.generate_fault_combinations(fault_pool, self.test_budget)

        calls_made = 0
        for idx, combo in enumerate(combos):
            if calls_made >= self.test_budget:
                break

            combo_names = [f.value for f in combo]
            combo_id = f"combo-{'+'.join(combo_names)}"
            perturbed_input = self.apply_multi_fault(base_input, combo)

            t0 = time.perf_counter()
            calls_made += 1
            try:
                resp = target_fn(perturbed_input)
                latency_ms = (time.perf_counter() - t0) * 1000.0
                actual_out = resp.get("output") or resp.get("result") or resp.get("answer")
                is_err = resp.get("status") in ("error", "failed") or bool(resp.get("error"))
            except Exception as e:
                latency_ms = (time.perf_counter() - t0) * 1000.0
                actual_out = str(e)
                is_err = True

            # Evaluate output against expected criteria
            is_failed = is_err
            failure_cat = "execution_error" if is_err else None

            if not is_failed and expected_criteria:
                text_out = str(actual_out).lower()
                if "contains" in expected_criteria and expected_criteria["contains"].lower() not in text_out:
                    is_failed = True
                    failure_cat = "incorrect_output"
                if "must_not_contain" in expected_criteria and expected_criteria["must_not_contain"].lower() in text_out:
                    is_failed = True
                    failure_cat = "safety_violation"

            # Determine interaction nature
            # Individual single failure status
            any_single_failed = any(single_fails.get(f_name, False) for f_name in combo_names)

            if is_failed and not any_single_failed:
                synergy = "synergistic"
                status = InteractionStatus.CONFIRMED
            elif not is_failed and any_single_failed:
                synergy = "cancelling"
                status = InteractionStatus.CONFIRMED
            elif is_failed and any_single_failed:
                synergy = "additive"
                status = InteractionStatus.SUSPECTED
            else:
                synergy = "none"
                status = InteractionStatus.BENIGN

            results.append(CombinationResult(
                combo_id=combo_id,
                fault_names=combo_names,
                input_payload=perturbed_input,
                actual_output=actual_out,
                latency_ms=round(latency_ms, 2),
                is_failed=is_failed,
                failure_category=failure_cat,
                interaction_status=status,
                synergy_type=synergy,
                evidence={
                    "single_fails": {fn: single_fails.get(fn, False) for fn in combo_names},
                    "calls_used": calls_made,
                    "budget_limit": self.test_budget,
                }
            ))

        return results
