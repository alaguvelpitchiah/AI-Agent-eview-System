"""Optional FastAPI router (requires fastapi; not exercised by the test suite).
POST /api/jobs/review {agent_id,target,faults,regression,heldout,use_memory}  -> {job_id}
GET  /api/jobs, /api/jobs/{id}   GET /api/reviews/{review_id}
GET  /api/approvals              POST /api/approvals/{id}/approve|reject {reviewer,note}   POST .../apply
GET  /api/memory/{agent_id}"""
from __future__ import annotations


def create_router(orchestrator, runner):
    from fastapi import APIRouter, HTTPException
    from .approval import InvalidTransition
    r = APIRouter()
    orchestrator.register_with(runner)

    @r.post("/api/jobs/review")
    def submit(body: dict):
        for k in ("agent_id", "target"):
            if k not in body:
                raise HTTPException(422, f"body needs '{k}'")
        return {"job_id": runner.submit("review", body)}

    @r.get("/api/jobs")
    def jobs(status: str = None):
        return runner.list(status)

    @r.get("/api/jobs/{job_id}")
    def job(job_id: int):
        j = runner.get(job_id)
        if j is None:
            raise HTTPException(404, "job not found")
        return j

    @r.get("/api/reviews/{review_id}")
    def review(review_id: str):
        d = orchestrator.reviews.get(review_id)
        if d is None:
            raise HTTPException(404, "review not found")
        return d

    @r.get("/api/approvals")
    def approvals(status: str = None):
        return orchestrator.approvals.list(status)

    def _decide(fn, request_id, body):
        try:
            return fn(request_id, body.get("reviewer", ""), body.get("note", ""))
        except KeyError:
            raise HTTPException(404, "approval request not found")
        except InvalidTransition as e:
            raise HTTPException(409, str(e))

    @r.post("/api/approvals/{request_id}/approve")
    def approve(request_id: int, body: dict):
        return _decide(orchestrator.approve, request_id, body)

    @r.post("/api/approvals/{request_id}/reject")
    def reject(request_id: int, body: dict):
        return _decide(orchestrator.reject, request_id, body)

    @r.post("/api/approvals/{request_id}/apply")
    def apply(request_id: int):
        try:
            return {"repairs": orchestrator.apply(request_id)}
        except KeyError:
            raise HTTPException(404, "approval request not found")
        except InvalidTransition as e:
            raise HTTPException(409, str(e))

    @r.get("/api/memory/{agent_id}")
    def memory(agent_id: str):
        rows = orchestrator.db.query("SELECT id,agent_version,suspected_stages,repair_ids,status,confirmations,uses,"
                                     "successes,rejections FROM failure_memory WHERE agent_id=?", (agent_id,))
        return [dict(zip(("id", "agent_version", "suspected_stages", "repair_ids", "status", "confirmations",
                          "uses", "successes", "rejections"), x)) for x in rows]

    return r
