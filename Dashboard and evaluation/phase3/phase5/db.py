"""One SQLite connection shared (thread-safely) by jobs, approvals, memory and reviews."""
from __future__ import annotations
import sqlite3, threading


class Database:
    def __init__(self, path: str = ":memory:"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.lock = threading.RLock()

    def execute(self, sql, args=()):
        with self.lock:
            cur = self.conn.execute(sql, args)
            self.conn.commit()
            return cur

    def query(self, sql, args=()):
        with self.lock:
            return self.conn.execute(sql, args).fetchall()
