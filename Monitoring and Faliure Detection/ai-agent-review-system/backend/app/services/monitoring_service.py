"""Runs an agent, then records, evaluates and classifies the run (Phase 2 pipeline)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..integration.agent_executor import AgentExecutor
from ..integration.base_adapter import AgentResult
from ..integration.case_loader import load_cases
from ..integration.errors import TaskValidationError
from ..reviewer.failure_detector import FailureDetector, FailureReport
from ..reviewer.fault_injector import FaultInjector
from ..reviewer.outcome_evaluator import OutcomeEvaluation, OutcomeEvaluator
from ..reviewer.performance_metrics import compute_metrics
from ..reviewer.trace_collector import TraceCollector, TraceRecord
from ..storage.trace_store import TraceStore

MAX_BENCHMARK_CASES = 200


@dataclass
class MonitoredRun:
    result: AgentResult
    record: TraceRecord
    evaluation: OutcomeEvaluation
    failure: Optional[FailureReport]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.record.execution_id,
            "agent_id": self.record.agent_id,
            "agent_version": self.record.agent_version,
            "status": self.record.status,
            "duration_ms": self.record.duration_ms,
            "event_count": self.record.event_count,
            "verdict": self.evaluation.verdict,
            "score": self.evaluation.score,
            "message": self.evaluation.message,
            "checks": [c.to_dict() for c in self.evaluation.checks],
            "failure": self.failure.to_dict() if self.failure else None,
            "batch_id": self.record.batch_id,
        }


class MonitoringService:
    def __init__(
        self,
        executor: AgentExecutor,
        store: TraceStore,
        data_dir,
        collector: Optional[TraceCollector] = None,
        evaluator: Optional[OutcomeEvaluator] = None,
        detector: Optional[FailureDetector] = None,
        faults: Optional[FaultInjector] = None,
    ) -> None:
        self.executor = executor
        self.store = store
        self.data_dir = data_dir
        self.collector = collector or TraceCollector()
        self.evaluator = evaluator or OutcomeEvaluator()
        self.detector = detector or FailureDetector()
        self.faults = faults or FaultInjector(data_dir, executor.registry)

    def monitor(
        self,
        agent_id: str,
        task_input: Dict[str, Any],
        *,
        expected: Optional[Dict[str, Any]] = None,
        overrides: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        fault_id: Optional[str] = None,
        batch_id: Optional[str] = None,
    ) -> MonitoredRun:
        self.evaluator.validate(expected)  # a bad expectation is the caller's mistake: fail before running
        if fault_id is not None:
            if overrides:
                raise TaskValidationError(["Use either 'fault_id' or 'overrides', not both"])
            result = self.faults.run_with_fault(self.executor, agent_id, task_input, fault_id, expected, metadata)
        else:
            result = self.executor.execute(agent_id, task_input, overrides=overrides, expected=expected, metadata=metadata)

        record = self.collector.collect(result, batch_id=batch_id)
        evaluation = self.evaluator.evaluate(record)
        failure = self.detector.detect(record, evaluation)
        self.store.save_monitored(record, evaluation, failure)
        return MonitoredRun(result, record, evaluation, failure)

    def run_benchmark(
        self,
        agent_id: str,
        fault_id: Optional[str] = None,
        case_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        self.executor.registry.get(agent_id)  # AgentNotFoundError
        cases = load_cases(self.data_dir, agent_id)
        if case_ids is not None:
            known = {c["case_id"] for c in cases}
            unknown = [c for c in case_ids if c not in known]
            if unknown:
                raise TaskValidationError([f"Unknown case ids: {unknown}"])
            cases = [c for c in cases if c["case_id"] in set(case_ids)]
        if not cases:
            raise TaskValidationError([f"No benchmark cases found for agent '{agent_id}'"])
        if len(cases) > MAX_BENCHMARK_CASES:
            raise TaskValidationError([f"At most {MAX_BENCHMARK_CASES} cases can run at once"])
        if fault_id is not None:
            self.faults.get_fault(agent_id, fault_id)  # fail early on unknown faults
        for case in cases:
            self.evaluator.validate(case["expected"])

        batch_id = uuid.uuid4().hex
        rows = []
        for case in cases:
            run = self.monitor(
                agent_id, case["input"], expected=case["expected"], fault_id=fault_id, batch_id=batch_id,
                metadata={"case_id": case["case_id"], "tags": case.get("tags", [])},
            )
            rows.append({
                "case_id": case["case_id"],
                "execution_id": run.record.execution_id,
                "verdict": run.evaluation.verdict,
                "failure_category": run.failure.category if run.failure else None,
            })
        return {
            "batch_id": batch_id,
            "agent_id": agent_id,
            "fault_id": fault_id,
            "cases": rows,
            "metrics": compute_metrics(self.store.metric_rows(batch_id=batch_id)),
        }
