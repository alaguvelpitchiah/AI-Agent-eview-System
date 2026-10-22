"""Endpoints for monitored runs, failures, metrics, faults and benchmarks."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from ...evaluation.baseline_reviewer import BaselineReviewer
from ...reviewer.failure_detector import FailureReport
from ...reviewer.performance_metrics import compute_metrics
from ...reviewer.trace_collector import TraceRecord

router = APIRouter(prefix="/api", tags=["monitoring"])
_baseline = BaselineReviewer()


class MonitorRequest(BaseModel):
    input: Dict[str, Any]
    expected: Optional[Dict[str, Any]] = None
    overrides: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    fault_id: Optional[str] = Field(default=None, description="Run with a known injected fault")


class BenchmarkRequest(BaseModel):
    fault_id: Optional[str] = None
    case_ids: Optional[List[str]] = None


@router.post("/agents/{agent_id}/monitor")
def monitor_run(agent_id: str, body: MonitorRequest, request: Request):
    run = request.app.state.monitoring.monitor(
        agent_id, body.input, expected=body.expected, overrides=body.overrides,
        metadata=body.metadata, fault_id=body.fault_id,
    )
    return run.to_dict()


@router.post("/agents/{agent_id}/benchmark")
def run_benchmark(agent_id: str, request: Request, body: BenchmarkRequest = BenchmarkRequest()):
    return request.app.state.monitoring.run_benchmark(agent_id, fault_id=body.fault_id, case_ids=body.case_ids)


@router.get("/agents/{agent_id}/faults")
def list_faults(agent_id: str, request: Request):
    return [f.to_dict() for f in request.app.state.monitoring.faults.list_faults(agent_id)]


@router.get("/runs")
def list_runs(
    request: Request,
    agent_id: Optional[str] = None,
    status: Optional[str] = None,
    verdict: Optional[str] = None,
    batch_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return request.app.state.store.list_runs(agent_id, status, verdict, batch_id, limit, offset)


@router.get("/runs/{execution_id}")
def get_run(execution_id: str, request: Request):
    return request.app.state.store.get_run(execution_id)


@router.get("/failures")
def list_failures(
    request: Request,
    agent_id: Optional[str] = None,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return request.app.state.store.list_failures(agent_id, category, severity, limit, offset)


@router.get("/failures/{failure_id}")
def get_failure(failure_id: str, request: Request):
    return request.app.state.store.get_failure(failure_id)


@router.get("/failures/{failure_id}/baseline")
def baseline_diagnosis(failure_id: str, request: Request):
    store = request.app.state.store
    report = store.get_failure(failure_id)
    run = store.get_run(report["execution_id"])
    record = TraceRecord(
        execution_id=run["execution_id"], agent_id=run["agent_id"], agent_version=run["agent_version"],
        status=run["status"], started_at=run["started_at"], duration_ms=run["duration_ms"], input=run["input"],
        output=run["output"], events=run["events"], usage=run["usage"], error=run["error"],
        expected=run["expected"], metadata=run["metadata"], overrides=run["overrides"],
        event_count=run["event_count"], tool_call_count=run["tool_call_count"],
        error_events=[{"name": e["name"], "kind": e["kind"], "error": e["error"]} for e in run["events"] if e.get("error")],
    )
    return _baseline.diagnose(record, FailureReport(**report)).to_dict()


@router.get("/metrics")
def metrics(
    request: Request,
    agent_id: Optional[str] = None,
    agent_version: Optional[str] = None,
    batch_id: Optional[str] = None,
):
    return compute_metrics(request.app.state.store.metric_rows(agent_id, agent_version, batch_id))
