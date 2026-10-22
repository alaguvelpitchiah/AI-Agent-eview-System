"""SQLite storage for diagnoses."""
from __future__ import annotations
import json, sqlite3, time
from .models import Diagnosis


class DiagnosisStore:
    def __init__(self, path: str = ":memory:"):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("""CREATE TABLE IF NOT EXISTS diagnoses(
            id INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT, run_ref TEXT,
            created_at REAL, verdict TEXT, suspected_stages TEXT, confidence TEXT,
            experiment_count INTEGER, payload TEXT)""")
        self.db.commit()

    def save(self, dx: Diagnosis, run_ref: str = "") -> int:
        cur = self.db.execute(
            "INSERT INTO diagnoses(agent_id,run_ref,created_at,verdict,suspected_stages,confidence,experiment_count,payload)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (dx.agent_id, run_ref, time.time(), dx.verdict, json.dumps(dx.suspected_stages),
             dx.confidence, len(dx.experiments), json.dumps(dx.to_dict(), default=str)))
        self.db.commit()
        return cur.lastrowid

    def get(self, diagnosis_id: int):
        r = self.db.execute("SELECT payload FROM diagnoses WHERE id=?", (diagnosis_id,)).fetchone()
        return json.loads(r[0]) if r else None

    def list(self, agent_id: str = None, limit: int = 100):
        q, args = "SELECT id,agent_id,verdict,suspected_stages,confidence,experiment_count FROM diagnoses", []
        if agent_id:
            q += " WHERE agent_id=?"; args.append(agent_id)
        q += " ORDER BY id DESC LIMIT ?"; args.append(limit)
        return [dict(id=i, agent_id=a, verdict=v, suspected_stages=json.loads(s), confidence=c, experiments=n)
                for i, a, v, s, c, n in self.db.execute(q, args)]
