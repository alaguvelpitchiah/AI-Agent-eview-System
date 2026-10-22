"""Optional FastAPI router: POST /api/agents/{agent_id}/diagnose, GET /api/diagnoses[/{id}]."""
from __future__ import annotations


def create_router(adapter, store, engine=None):
    from fastapi import APIRouter, HTTPException
    from .root_cause_engine import RootCauseEngine
    engine = engine or RootCauseEngine(adapter)
    r = APIRouter()

    @r.post("/api/agents/{agent_id}/diagnose")
    def diagnose(agent_id: str, body: dict):
        if "input" not in body or "expected" not in body:
            raise HTTPException(422, "body needs 'input' and 'expected'")
        dx = engine.diagnose(agent_id, body["input"], body["expected"], tuple(body.get("faults", ())))
        did = store.save(dx, body.get("run_ref", ""))
        return {"diagnosis_id": did, **dx.to_dict()}

    @r.get("/api/diagnoses")
    def list_(agent_id: str = None):
        return store.list(agent_id)

    @r.get("/api/diagnoses/{diagnosis_id}")
    def get(diagnosis_id: int):
        d = store.get(diagnosis_id)
        if d is None:
            raise HTTPException(404, "diagnosis not found")
        return d

    return r
