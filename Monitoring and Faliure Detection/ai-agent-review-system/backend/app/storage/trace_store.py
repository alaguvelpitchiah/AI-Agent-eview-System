"""Persistence of runs, evaluations and failure reports."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from ..reviewer.failure_detector import FailureReport
from ..reviewer.outcome_evaluator import OutcomeEvaluation
from ..reviewer.trace_collector import TraceRecord
from .database import Database

MAX_PAGE = 500


class RecordNotFoundError(Exception):
    def __init__(self, kind: str, key: str):
        super().__init__(f"{kind} '{key}' was not found")
        self.kind, self.key = kind, key


def _dumps(value: Any) -> Optional[str]:
    return None if value is None else json.dumps(value, default=str)


def _loads(text: Optional[str]) -> Any:
    return None if text is None else json.loads(text)


class TraceStore:
    def __init__(self, db: Database) -> None:
        self.db = db

    # ---- writes ---------------------------------------------------------------------------
    def save_monitored(
        self, record: TraceRecord, evaluation: OutcomeEvaluation, failure: Optional[FailureReport]
    ) -> None:
        """Store a run, its evaluation and (if any) its failure report in one transaction."""
        with self.db.connection() as conn:
            conn.execute(
                """INSERT INTO runs (execution_id, agent_id, agent_version, status, started_at, duration_ms,
                       batch_id, event_count, tool_call_count, truncated, input_json, output_json, events_json,
                       usage_json, error_json, expected_json, metadata_json, overrides_json)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    record.execution_id, record.agent_id, record.agent_version, record.status, record.started_at,
                    record.duration_ms, record.batch_id, record.event_count, record.tool_call_count,
                    int(record.truncated), _dumps(record.input), _dumps(record.output), _dumps(record.events),
                    _dumps(record.usage), _dumps(record.error), _dumps(record.expected), _dumps(record.metadata),
                    _dumps(record.overrides),
                ),
            )
            conn.execute(
                "INSERT INTO evaluations (execution_id, verdict, score, message, checks_json, evaluated_at) VALUES (?,?,?,?,?,?)",
                (
                    evaluation.execution_id, evaluation.verdict, evaluation.score, evaluation.message,
                    _dumps([c.to_dict() for c in evaluation.checks]), evaluation.evaluated_at,
                ),
            )
            if failure is not None:
                conn.execute(
                    """INSERT INTO failures (failure_id, execution_id, agent_id, agent_version, category, severity,
                           summary, report_json, created_at) VALUES (?,?,?,?,?,?,?,?,?)""",
                    (
                        failure.failure_id, failure.execution_id, failure.agent_id, failure.agent_version,
                        failure.category, failure.severity, failure.summary, _dumps(failure.to_dict()),
                        failure.created_at,
                    ),
                )

    # ---- reads ----------------------------------------------------------------------------
    def get_run(self, execution_id: str) -> Dict[str, Any]:
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM runs WHERE execution_id = ?", (execution_id,)).fetchone()
            if row is None:
                raise RecordNotFoundError("Run", execution_id)
            ev = conn.execute("SELECT * FROM evaluations WHERE execution_id = ?", (execution_id,)).fetchone()
            fl = conn.execute("SELECT report_json FROM failures WHERE execution_id = ?", (execution_id,)).fetchone()
        return {
            "execution_id": row["execution_id"],
            "agent_id": row["agent_id"],
            "agent_version": row["agent_version"],
            "status": row["status"],
            "started_at": row["started_at"],
            "duration_ms": row["duration_ms"],
            "batch_id": row["batch_id"],
            "event_count": row["event_count"],
            "tool_call_count": row["tool_call_count"],
            "truncated": bool(row["truncated"]),
            "input": _loads(row["input_json"]),
            "output": _loads(row["output_json"]),
            "events": _loads(row["events_json"]),
            "usage": _loads(row["usage_json"]),
            "error": _loads(row["error_json"]),
            "expected": _loads(row["expected_json"]),
            "metadata": _loads(row["metadata_json"]),
            "overrides": _loads(row["overrides_json"]),
            "evaluation": None
            if ev is None
            else {
                "verdict": ev["verdict"], "score": ev["score"], "message": ev["message"],
                "checks": _loads(ev["checks_json"]), "evaluated_at": ev["evaluated_at"],
            },
            "failure": _loads(fl["report_json"]) if fl else None,
        }

    @staticmethod
    def _filters(agent_id, status, verdict, batch_id, agent_version=None):
        clauses, params = [], []
        for column, value in (
            ("r.agent_id", agent_id), ("r.status", status), ("e.verdict", verdict),
            ("r.batch_id", batch_id), ("r.agent_version", agent_version),
        ):
            if value is not None:
                clauses.append(f"{column} = ?")
                params.append(value)
        return (" WHERE " + " AND ".join(clauses)) if clauses else "", params

    _RUN_SELECT = """
        SELECT r.execution_id, r.agent_id, r.agent_version, r.status, r.started_at, r.duration_ms, r.batch_id,
               r.event_count, r.tool_call_count, r.usage_json, e.verdict, e.score,
               f.failure_id, f.category AS failure_category, f.severity
        FROM runs r
        LEFT JOIN evaluations e ON e.execution_id = r.execution_id
        LEFT JOIN failures f ON f.execution_id = r.execution_id"""

    def list_runs(
        self, agent_id=None, status=None, verdict=None, batch_id=None, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        where, params = self._filters(agent_id, status, verdict, batch_id)
        limit = max(1, min(int(limit), MAX_PAGE))
        with self.db.connection() as conn:
            rows = conn.execute(
                f"{self._RUN_SELECT}{where} ORDER BY r.started_at DESC, r.rowid DESC LIMIT ? OFFSET ?",
                params + [limit, max(0, int(offset))],
            ).fetchall()
        return [self._summary(r) for r in rows]

    def metric_rows(self, agent_id=None, agent_version=None, batch_id=None) -> List[Dict[str, Any]]:
        where, params = self._filters(agent_id, None, None, batch_id, agent_version)
        with self.db.connection() as conn:
            rows = conn.execute(f"{self._RUN_SELECT}{where}", params).fetchall()
        return [self._summary(r) for r in rows]

    @staticmethod
    def _summary(row) -> Dict[str, Any]:
        data = dict(row)
        data["usage"] = _loads(data.pop("usage_json"))
        return data

    def get_failure(self, failure_id: str) -> Dict[str, Any]:
        with self.db.connection() as conn:
            row = conn.execute("SELECT report_json FROM failures WHERE failure_id = ?", (failure_id,)).fetchone()
        if row is None:
            raise RecordNotFoundError("Failure", failure_id)
        return _loads(row["report_json"])

    def list_failures(
        self, agent_id=None, category=None, severity=None, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        clauses, params = [], []
        for column, value in (("agent_id", agent_id), ("category", category), ("severity", severity)):
            if value is not None:
                clauses.append(f"{column} = ?")
                params.append(value)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        limit = max(1, min(int(limit), MAX_PAGE))
        with self.db.connection() as conn:
            rows = conn.execute(
                f"""SELECT failure_id, execution_id, agent_id, agent_version, category, severity, summary, created_at
                    FROM failures{where} ORDER BY created_at DESC, rowid DESC LIMIT ? OFFSET ?""",
                params + [limit, max(0, int(offset))],
            ).fetchall()
        return [dict(r) for r in rows]

    def count_runs(self) -> int:
        with self.db.connection() as conn:
            return conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
