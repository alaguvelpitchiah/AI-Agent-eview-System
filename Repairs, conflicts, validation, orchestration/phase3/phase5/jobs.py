"""Background job runner: SQLite-backed queue, worker threads, retries, cancellation, progress.
Handlers are called as fn(payload: dict, ctx: JobContext) and must return a JSON-able dict.
Limit: a running job cannot be killed (no preemptive timeout); cancel works on queued jobs only."""
from __future__ import annotations
import json, threading, time, traceback
from .db import Database


class JobContext:
    def __init__(self, runner, job_id):
        self.runner, self.job_id, self._events = runner, job_id, []

    def progress(self, message: str):
        self._events.append(message)
        self.runner.db.execute("UPDATE jobs SET progress=? WHERE id=?", (json.dumps(self._events), self.job_id))


class JobRunner:
    def __init__(self, db: Database, max_retries: int = 1):
        self.db, self.max_retries = db, max_retries
        self.handlers, self._threads, self._stop = {}, [], threading.Event()
        db.execute("""CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT,
            payload TEXT, status TEXT, attempts INTEGER DEFAULT 0, max_retries INTEGER, result TEXT,
            error TEXT, progress TEXT DEFAULT '[]', created_at REAL, started_at REAL, finished_at REAL)""")

    def register(self, job_type: str, fn):
        self.handlers[job_type] = fn

    def submit(self, job_type: str, payload: dict, max_retries: int = None) -> int:
        if job_type not in self.handlers:
            raise ValueError(f"unknown job type: {job_type}")
        mr = self.max_retries if max_retries is None else max_retries
        return self.db.execute("INSERT INTO jobs(type,payload,status,max_retries,created_at) VALUES (?,?,?,?,?)",
                               (job_type, json.dumps(payload), "queued", mr, time.time())).lastrowid

    def get(self, job_id: int):
        r = self.db.query("SELECT id,type,status,attempts,max_retries,result,error,progress,created_at,started_at,finished_at "
                          "FROM jobs WHERE id=?", (job_id,))
        if not r:
            return None
        i, t, st, at, mr, res, err, prog, c, s, f = r[0]
        return dict(id=i, type=t, status=st, attempts=at, max_retries=mr, result=json.loads(res) if res else None,
                    error=err, progress=json.loads(prog), created_at=c, started_at=s, finished_at=f)

    def list(self, status: str = None):
        rows = self.db.query("SELECT id FROM jobs" + (" WHERE status=?" if status else "") + " ORDER BY id",
                             (status,) if status else ())
        return [self.get(r[0]) for r in rows]

    def cancel(self, job_id: int) -> bool:
        return self.db.execute("UPDATE jobs SET status='cancelled', finished_at=? WHERE id=? AND status='queued'",
                               (time.time(), job_id)).rowcount == 1

    def _claim(self):
        with self.db.lock:
            r = self.db.query("SELECT id,type,payload FROM jobs WHERE status='queued' ORDER BY id LIMIT 1")
            if not r:
                return None
            jid, jtype, payload = r[0]
            self.db.execute("UPDATE jobs SET status='running', attempts=attempts+1, started_at=? WHERE id=?",
                            (time.time(), jid))
            return jid, jtype, json.loads(payload)

    def run_one(self) -> bool:
        claimed = self._claim()
        if not claimed:
            return False
        jid, jtype, payload = claimed
        try:
            result = self.handlers[jtype](payload, JobContext(self, jid))
            self.db.execute("UPDATE jobs SET status='succeeded', result=?, error=NULL, finished_at=? WHERE id=?",
                            (json.dumps(result, default=str), time.time(), jid))
        except Exception as e:                                            # noqa: BLE001
            err = f"{type(e).__name__}: {e}"
            job = self.get(jid)
            if job["attempts"] <= job["max_retries"]:
                self.db.execute("UPDATE jobs SET status='queued', error=? WHERE id=?", (err, jid))
            else:
                self.db.execute("UPDATE jobs SET status='failed', error=?, finished_at=? WHERE id=?",
                                (err + "\n" + traceback.format_exc(limit=3), time.time(), jid))
        return True

    def run_pending(self) -> int:
        n = 0
        while self.run_one():
            n += 1
        return n

    def start(self, workers: int = 2):
        self._stop.clear()
        for _ in range(workers):
            t = threading.Thread(target=self._loop, daemon=True)
            t.start()
            self._threads.append(t)

    def _loop(self):
        while not self._stop.is_set():
            if not self.run_one():
                self._stop.wait(0.02)

    def stop(self):
        self._stop.set()
        for t in self._threads:
            t.join(timeout=2)
        self._threads = []

    def wait(self, job_id: int, timeout: float = 10.0):
        end = time.time() + timeout
        while time.time() < end:
            j = self.get(job_id)
            if j["status"] in ("succeeded", "failed", "cancelled"):
                return j
            time.sleep(0.02)
        raise TimeoutError(f"job {job_id} did not finish in {timeout}s")
