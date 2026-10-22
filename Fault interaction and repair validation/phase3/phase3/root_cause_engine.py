"""Root-cause diagnosis by controlled counterfactual experiments.

Method
  1. Reproduce the failure; run the clean configuration as the reference
     (it must pass, otherwise nothing can be concluded).
  2. Stage isolation: for each stage, feed it the reference outputs of all
     earlier stages and see whether its own output still departs from the
     reference. Stages that do are *faulty on their own*.
  3. Repair tests: replace the output of each subset of faulty stages with the
     reference value. Subsets that make the run pass show which faults are
     sufficient/necessary and expose interactions between faults.
"""
from __future__ import annotations
from itertools import combinations
from .models import Diagnosis
from .evidence_analyzer import analyze_divergence, describe
from .diagnostic_selector import select_stages
from .controlled_experiment import ExperimentRunner, BudgetExhausted


class RootCauseEngine:
    def __init__(self, adapter, max_experiments: int = 40, max_subset_stages: int = 4):
        self.adapter = adapter
        self.max_experiments = max_experiments
        self.max_subset_stages = max_subset_stages

    def diagnose(self, agent_id, input, expected, faults=(), failing_run=None, reference_run=None) -> Diagnosis:
        a = self.adapter
        stages = a.stage_names(agent_id)
        faults = tuple(faults)
        failing = failing_run or a.run(agent_id, input, faults=faults)
        dx = Diagnosis(agent_id=agent_id, verdict="inconclusive")

        if failing.status == "success" and a.judge(agent_id, failing, expected):
            dx.verdict = "no_failure"
            dx.evidence.append("The run satisfies its expectation; nothing to diagnose.")
            return dx

        ref = reference_run or a.run(agent_id, input, faults=())
        if ref.status != "success" or not a.judge(agent_id, ref, expected):
            dx.evidence.append("Reference (clean) run does not pass this expectation, so no "
                               "counterfactual can be trusted. Check the case or the baseline config.")
            return dx

        divs = analyze_divergence(failing, ref, stages)
        dx.divergences = divs
        dx.evidence += [describe(d) for d in divs if not d.output_same]

        runner = ExperimentRunner(a, agent_id, input, expected, faults, ref, failing, stages,
                                  self.max_experiments)
        order = select_stages(stages, divs)
        faulty, untested = [], []
        for i, s in enumerate(order):
            try:
                if runner.stage_is_faulty(s):
                    faulty.append(s)
            except BudgetExhausted:
                untested = order[i:]
                break
        faulty = [s for s in stages if s in faulty]
        dx.untested_stages = untested
        if untested:
            dx.evidence.append("Experiment budget exhausted; untested stages: " + ", ".join(untested))

        if not faulty:
            dx.evidence.append("No stage departs from the reference when given clean inputs. "
                               "The failure may come from the input/expectation or from nondeterminism.")
            dx.experiments = runner.log
            return dx

        dx.suspected_stages = faulty
        fixing = []     # subsets whose repair passes
        try:
            subsets = []
            if len(faulty) <= self.max_subset_stages:
                for k in range(1, len(faulty) + 1):
                    subsets += list(combinations(faulty, k))
            else:
                subsets = [(s,) for s in faulty] + [tuple(faulty)]
            for sub in subsets:
                if any(set(f) <= set(sub) for f in fixing):
                    continue    # superset of a known fix: assumed to fix too (monotonic), skipped
                if runner.repair_passes(sub):
                    fixing.append(sub)
        except BudgetExhausted:
            dx.evidence.append("Budget exhausted during repair tests; confidence reduced.")
        dx.experiments = runner.log
        dx.minimal_fix_sets = [list(f) for f in fixing]

        if len(faulty) == 1:
            dx.verdict = "single_root_cause"
            if fixing:
                dx.confidence = "high"
                dx.evidence.append(f"Replacing only '{faulty[0]}' with its reference output makes the run pass.")
            else:
                dx.confidence = "medium"
                dx.evidence.append(f"'{faulty[0]}' departs from the reference, but repairing it alone "
                                   "does not make the run pass; other causes may exist.")
            return dx

        dx.verdict = "joint_root_cause"
        singles_fix = [(s,) in fixing for s in faulty]
        if all(singles_fix):
            dx.interaction_pattern = "failure_requires_all_faults"
            dx.evidence.append("Repairing ANY ONE of these stages makes the run pass: the failure "
                               "appears only when all of them are faulty together (interaction).")
        elif not any(singles_fix):
            dx.interaction_pattern = "each_fault_required_to_fix"
            dx.evidence.append("No single repair passes; every faulty stage must be repaired (independent contributors).")
        else:
            dx.interaction_pattern = "mixed"
            dx.evidence.append("Some single repairs pass and others do not (mixed interaction).")
        dx.confidence = "high" if fixing else "medium"
        return dx
