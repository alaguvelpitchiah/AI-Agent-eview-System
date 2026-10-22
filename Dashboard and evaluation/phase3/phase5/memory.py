"""Context-aware failure memory. A past fix is only a *suggestion*: it is retrieved when agent id and
version match and the symptom similarity is high, and the orchestrator must still re-validate it."""
from __future__ import annotations
import json, time
from .db import Database
from phase3.baseline import _empty


def symptom_features(agent_id, case, run) -> set:
    """Input-independent symptom description of a failing run."""
    f = {f"agent:{agent_id}", f"status:{run.status}", f"events:{len(run.events)}"}
    for e in run.events:
        f.add(f"stage:{e.name}:" + ("error" if e.error else "empty" if _empty(e.output) else "ok"))
    if isinstance(run.output, dict):
        f |= {f"out:{k}={v}" for k, v in run.output.items() if isinstance(v, str)}
    if isinstance(case.expected, dict):
        f |= {f"exp:{k}={v}" for k, v in case.expected.items() if isinstance(v, str)}
    return f


def jaccard(a, b) -> float:
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if (a | b) else 0.0


class FailureMemory:
    def __init__(self, db: Database):
        self.db = db
        db.execute("""CREATE TABLE IF NOT EXISTS failure_memory(id INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT,
            agent_version TEXT, features TEXT, suspected_stages TEXT, repair_ids TEXT, status TEXT,
            confirmations INTEGER DEFAULT 1, uses INTEGER DEFAULT 0, successes INTEGER DEFAULT 0,
            rejections INTEGER DEFAULT 0, source_review TEXT, created_at REAL)""")

    def record(self, agent_id, version, features, stages, repair_ids, status="approved", source_review="") -> int:
        feats, st, rp = json.dumps(sorted(features)), json.dumps(list(stages)), json.dumps(list(repair_ids))
        ex = self.db.query("SELECT id FROM failure_memory WHERE agent_id=? AND agent_version=? AND features=? "
                           "AND suspected_stages=? AND repair_ids=? AND status=?",
                           (agent_id, version, feats, st, rp, status))
        if ex:
            self.db.execute("UPDATE failure_memory SET confirmations=confirmations+1 WHERE id=?", (ex[0][0],))
            return ex[0][0]
        return self.db.execute("INSERT INTO failure_memory(agent_id,agent_version,features,suspected_stages,repair_ids,"
                               "status,source_review,created_at) VALUES (?,?,?,?,?,?,?,?)",
                               (agent_id, version, feats, st, rp, status, source_review, time.time())).lastrowid

    def _row(self, r):
        return dict(id=r[0], agent_id=r[1], agent_version=r[2], features=set(json.loads(r[3])),
                    suspected_stages=json.loads(r[4]), repair_ids=json.loads(r[5]), status=r[6],
                    confirmations=r[7], uses=r[8], successes=r[9], rejections=r[10])

    def get(self, memory_id):
        r = self.db.query("SELECT id,agent_id,agent_version,features,suspected_stages,repair_ids,status,confirmations,"
                          "uses,successes,rejections FROM failure_memory WHERE id=?", (memory_id,))
        return self._row(r[0]) if r else None

    def lookup(self, agent_id, version, features, min_similarity=0.85, limit=3):
        rows = self.db.query("SELECT id,agent_id,agent_version,features,suspected_stages,repair_ids,status,confirmations,"
                             "uses,successes,rejections FROM failure_memory WHERE agent_id=? AND agent_version=? "
                             "AND status='approved'", (agent_id, version))
        hits = []
        for r in rows:
            rec = self._row(r)
            if rec["rejections"] > rec["successes"]:
                continue                                  # humans rejected it more often than they accepted it
            sim = jaccard(features, rec["features"])
            if sim >= min_similarity:
                hits.append(dict(record=rec, similarity=round(sim, 4)))
        hits.sort(key=lambda h: (-h["similarity"], -h["record"]["confirmations"], h["record"]["id"]))
        return hits[:limit]

    def mark_reuse(self, memory_id, success: bool):
        self.db.execute("UPDATE failure_memory SET uses=uses+1, " + ("successes=successes+1" if success else "rejections=rejections+1")
                        + " WHERE id=?", (memory_id,))
