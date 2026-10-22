"""Audit Logger (Phase 6 Module).

Provides an immutable audit trail for governance and compliance:
- Logs all review runs, test executions, and failure discoveries.
- Logs human approval sign-offs and rejections with reviewer name, comments, and timestamps.
- Records target AI configuration changes and credential updates.
- Persists audit logs to SQLite and in-memory caches.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AuditEntry(BaseModel):
    entry_id: str = Field(default_factory=lambda: f"audit-{uuid.uuid4().hex[:10]}")
    timestamp: float = Field(default_factory=time.time)
    action: str = Field(..., description="Action name, e.g., 'repair.approved', 'test.executed', 'agent.registered'")
    actor: str = Field(default="system", description="Reviewer name, email, or system process")
    target_id: Optional[str] = Field(default=None, description="Agent ID, Run ID, or Repair ID")
    details: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    status: str = Field(default="success")


class AuditLogger:
    """Persistent audit logger backed by SQLite."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        self._memory_logs: List[AuditEntry] = []
        if self.db_path:
            self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    entry_id TEXT PRIMARY KEY,
                    timestamp REAL,
                    action TEXT,
                    actor TEXT,
                    target_id TEXT,
                    details_json TEXT,
                    ip_address TEXT,
                    status TEXT
                )
            """)
            conn.commit()

    def log(
        self,
        action: str,
        actor: str = "system",
        target_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        status: str = "success",
    ) -> AuditEntry:
        """Create and store an audit log entry."""
        entry = AuditEntry(
            action=action,
            actor=actor,
            target_id=target_id,
            details=details or {},
            ip_address=ip_address,
            status=status,
        )
        self._memory_logs.append(entry)

        if self.db_path:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        """
                        INSERT INTO audit_logs 
                        (entry_id, timestamp, action, actor, target_id, details_json, ip_address, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            entry.entry_id,
                            entry.timestamp,
                            entry.action,
                            entry.actor,
                            entry.target_id,
                            json.dumps(entry.details),
                            entry.ip_address,
                            entry.status,
                        ),
                    )
                    conn.commit()
            except Exception:
                pass

        return entry

    def list_logs(self, limit: int = 100, action_filter: Optional[str] = None) -> List[AuditEntry]:
        """Fetch audit log entries in reverse chronological order."""
        if self.db_path:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    if action_filter:
                        cursor.execute(
                            "SELECT entry_id, timestamp, action, actor, target_id, details_json, ip_address, status "
                            "FROM audit_logs WHERE action = ? ORDER BY timestamp DESC LIMIT ?",
                            (action_filter, limit),
                        )
                    else:
                        cursor.execute(
                            "SELECT entry_id, timestamp, action, actor, target_id, details_json, ip_address, status "
                            "FROM audit_logs ORDER BY timestamp DESC LIMIT ?",
                            (limit,),
                        )
                    rows = cursor.fetchall()
                    return [
                        AuditEntry(
                            entry_id=r[0],
                            timestamp=r[1],
                            action=r[2],
                            actor=r[3],
                            target_id=r[4],
                            details=json.loads(r[5] or "{}"),
                            ip_address=r[6],
                            status=r[7],
                        )
                        for r in rows
                    ]
            except Exception:
                pass

        # In-memory fallback
        logs = list(reversed(self._memory_logs))
        if action_filter:
            logs = [e for e in logs if e.action == action_filter]
        return logs[:limit]
