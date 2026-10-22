# AI Agent Review System - Phases 3 and 4
Run: `python -m phase3.demo`, `python -m phase4.demo4`, `pytest -q` (tests/).

## Phase 3 - root-cause diagnosis (phase3/)
root_cause_engine, diagnostic_selector, controlled_experiment, evidence_analyzer, baseline, evaluation, storage, api.

## Phase 4 - interaction discovery, repair generation, validation, conflict testing (phase4/)
- interaction_analyzer.py : 2^k factorial over diagnosed faulty stages (synergistic / cancelling / none)
- repair_generator.py     : candidates from a diagnosis (root-cause + downstream compensating); RepairProposer hook for an LLM
- validation.py           : a repair set must fix the target and break no currently-passing case
- conflict_analyzer.py    : A passes, B passes, A+B fails (also same-setting overwrite order checks)
- repair_planner.py       : generate -> validate -> conflicts -> search sets -> select, or "no_validated_fix"
- baseline4.py, evaluation4.py, storage4.py, api4.py, toy_repairs.py, demo4.py

## Wiring to your real system
Implement AgentAdapter (phase3/adapters.py) plus, for Phase 4:
  run(..., repairs=())        apply Repair.patch after faults
  candidate_repairs(agent_id, stage) -> list[Repair]
  true_repair(agent_id, fault_id)    (evaluation only)
Template: phase3/phase2_adapter.py (unfilled: Phase 2 code was not available).

## Limits
- Needs deterministic, replayable stages and a passing clean reference.
- Validation is only as strong as the regression suite: a compensating repair that no test exercises will pass.
- Factorial design is capped at 4 factors; repair-set search at 3 repairs, one per stage.
- Toy-agent results show the machinery works; they are not evidence for the research claim.

## Phase 5 - orchestrator, hard gates, approval, memory, background jobs (phase5/)
Run: `python -m phase5.demo5`. Tests: tests/test_phase5.py.
- orchestrator.py : monitor -> memory -> diagnose -> interaction -> plan -> HARD GATES -> approval request
                    outcomes: no_failure | inconclusive | no_validated_fix | approval_pending (nothing auto-applies)
- gates.py        : 8 mandatory gates, all must pass, no weighted score (diagnosis_confirmed, target_fixed, no_regression,
                    heldout_no_regression, root_cause_coverage, no_compensating, pair_safe, stable)
- approval.py     : pending -> approved -> applied | rejected; a named reviewer is required
- memory.py       : failure memory; same agent+version, Jaccard symptom similarity >= 0.85, then re-validated before reuse
- jobs.py         : SQLite job queue, worker threads, retries, cancel (queued only), progress events
- evaluation5.py  : gate effectiveness; memory ablation (off / validated / blind)
- api5.py         : FastAPI router (not exercised by tests; fastapi was not installed)
Extra adapter method: get_repair(agent_id, repair_id); optional agent_version(agent_id).

Limits: gates are only as strong as the regression and held-out cases; running jobs cannot be killed; memory similarity
uses coarse symptom features (stage empty/ok/error, decision values), so lookalikes are expected and handled by re-validation.
