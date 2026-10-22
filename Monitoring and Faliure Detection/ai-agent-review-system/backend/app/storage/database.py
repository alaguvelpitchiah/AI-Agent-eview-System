"""SQLite access (standard library only). One short-lived connection per operation."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Union

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    execution_id    TEXT PRIMARY KEY,
    agent_id        TEXT NOT NULL,
    agent_version   TEXT NOT NULL,
    status          TEXT NOT NULL,
    started_at      TEXT NOT NULL,
    duration_ms     REAL NOT NULL,
    batch_id        TEXT,
    event_count     INTEGER NOT NULL DEFAULT 0,
    tool_call_count INTEGER NOT NULL DEFAULT 0,
    truncated       INTEGER NOT NULL DEFAULT 0,
    input_json      TEXT NOT NULL,
    output_json     TEXT,
    events_json     TEXT NOT NULL,
    usage_json      TEXT NOT NULL,
    error_json      TEXT,
    expected_json   TEXT,
    metadata_json   TEXT,
    overrides_json  TEXT
);
CREATE INDEX IF NOT EXISTS idx_runs_agent   ON runs (agent_id, started_at);
CREATE INDEX IF NOT EXISTS idx_runs_batch   ON runs (batch_id);

CREATE TABLE IF NOT EXISTS evaluations (
    execution_id TEXT PRIMARY KEY REFERENCES runs (execution_id) ON DELETE CASCADE,
    verdict      TEXT NOT NULL,
    score        REAL,
    message      TEXT,
    checks_json  TEXT NOT NULL,
    evaluated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS failures (
    failure_id    TEXT PRIMARY KEY,
    execution_id  TEXT NOT NULL UNIQUE REFERENCES runs (execution_id) ON DELETE CASCADE,
    agent_id      TEXT NOT NULL,
    agent_version TEXT NOT NULL,
    category      TEXT NOT NULL,
    severity      TEXT NOT NULL,
    summary       TEXT NOT NULL,
    report_json   TEXT NOT NULL,
    created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_failures_agent ON failures (agent_id, category);
"""


class Database:
    def __init__(self, path: Union[str, Path]) -> None:
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL")  # readers do not block the writer
            conn.executescript(SCHEMA)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
