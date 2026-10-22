"""Human-approval queue. A fix can only be applied after a named reviewer approves it.
pending -> approved -> applied, or pending -> rejected. Anything else is refused."""
from __future__ import annotations
import json, time
from .db import Database


class InvalidTransition(ValueError):
    pass


class ApprovalQueue:
    def __init__(self, db: Database):
        self.db = db
        db.execute("""CREATE TABLE IF NOT EXISTS approvals(id INTEGER PRIMARY KEY AUTOINCREMENT, review_id TEXT,
            agent_id TEXT, status TEXT, payload TEXT, reviewer TEXT, note TEXT, created_at REAL, decided_at REAL,
            applied_at REAL)""")

    def create(self, review_id: str, agent_id: str, payload: dict) -> int:
        return self.db.execute("INSERT INTO approvals(review_id,agent_id,status,payload,created_at) VALUES (?,?,?,?,?)",
                               (review_id, agent_id, "pending", json.dumps(payload), time.time())).lastrowid

    def get(self, request_id: int):
        r = self.db.query("SELECT id,review_id,agent_id,status,payload,reviewer,note,created_at,decided_at,applied_at "
                          "FROM approvals WHERE id=?", (request_id,))
        if not r:
            return None
        i, rv, ag, st, p, who, note, c, d, ap = r[0]
        return dict(id=i, review_id=rv, agent_id=ag, status=st, payload=json.loads(p), reviewer=who, note=note,
                    created_at=c, decided_at=d, applied_at=ap)

    def list(self, status: str = None):
        rows = self.db.query("SELECT id FROM approvals" + (" WHERE status=?" if status else "") + " ORDER BY id",
                             (status,) if status else ())
        return [self.get(r[0]) for r in rows]

    def _move(self, request_id, allowed_from, to, reviewer=None, note="", col="decided_at"):
        req = self.get(request_id)
        if req is None:
            raise KeyError(f"approval request {request_id} not found")
        if req["status"] != allowed_from:
            raise InvalidTransition(f"cannot go {req['status']} -> {to} (needs {allowed_from})")
        if reviewer is not None and not reviewer.strip():
            raise InvalidTransition("a named reviewer is required")
        if reviewer is not None:
            self.db.execute(f"UPDATE approvals SET status=?, reviewer=?, note=?, {col}=? WHERE id=?",
                            (to, reviewer, note, time.time(), request_id))
        else:
            self.db.execute(f"UPDATE approvals SET status=?, {col}=? WHERE id=?", (to, time.time(), request_id))
        return self.get(request_id)

    def approve(self, request_id, reviewer, note=""):
        return self._move(request_id, "pending", "approved", reviewer, note)

    def reject(self, request_id, reviewer, note=""):
        return self._move(request_id, "pending", "rejected", reviewer, note)

    def apply(self, request_id):
        """Marks an approved request applied and returns the repairs to deploy (deployment itself is the caller's)."""
        return self._move(request_id, "approved", "applied", col="applied_at")["payload"]["repairs"]
