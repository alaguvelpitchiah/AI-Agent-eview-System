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


def create_app(adapter=None, store=None):
    from fastapi import FastAPI
    from .toy_agent import ToyAdapter
    from .storage import DiagnosisStore
    adapter = adapter or ToyAdapter()
    store = store or DiagnosisStore()
    app = FastAPI(title="Phase 3: Root-Cause Diagnosis API")
    app.include_router(create_router(adapter, store))

    @app.get("/api/health")
    def health():
        return {"status": "ok", "phase": 3, "service": "root-cause-diagnosis"}

    return app


if __name__ == "__main__":
    import os, uvicorn
    port = int(os.environ.get("PORT", 8001))
    print(f"Starting Phase 3 API on port {port}...")
    uvicorn.run(create_app(), host="0.0.0.0", port=port)

