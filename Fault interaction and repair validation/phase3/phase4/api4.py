"""Optional FastAPI router. Body: {"target": {case_id,input,expected}, "regression": [...], "faults": [...]}."""
from __future__ import annotations


def create_router(adapter, store):
    from fastapi import APIRouter, HTTPException
    from phase3.evaluation import Case
    from phase3.root_cause_engine import RootCauseEngine
    from .interaction_analyzer import InteractionAnalyzer
    from .repair_planner import RepairPlanner
    r = APIRouter()

    @r.post("/api/agents/{agent_id}/repair-plan")
    def repair_plan(agent_id: str, body: dict):
        if "target" not in body:
            raise HTTPException(422, "body needs 'target'")
        mk = lambda d: Case(d["case_id"], agent_id, d["input"], d["expected"])
        t, faults = mk(body["target"]), tuple(body.get("faults", ()))
        dx = RootCauseEngine(adapter).diagnose(agent_id, t.input, t.expected, faults)
        rep = InteractionAnalyzer(adapter).analyze(agent_id, t.input, t.expected, faults, dx.suspected_stages)
        plan = RepairPlanner(adapter).plan(agent_id, dx, [t], [mk(c) for c in body.get("regression", [])], faults)
        pid = store.save(plan, rep)
        return {"plan_id": pid, "diagnosis": dx.to_dict(), "interaction": rep.to_dict(), "plan": plan.to_dict()}

    @r.get("/api/repair-plans")
    def list_(agent_id: str = None):
        return store.list(agent_id)

    @r.get("/api/repair-plans/{plan_id}")
    def get(plan_id: int):
        d = store.get(plan_id)
        if d is None:
            raise HTTPException(404, "plan not found")
        return d

    return r


def create_app(adapter=None, store=None):
    from fastapi import FastAPI
    from .toy_repairs import ToyRepairAdapter
    from .storage4 import PlanStore
    adapter = adapter or ToyRepairAdapter()
    store = store or PlanStore()
    app = FastAPI(title="Phase 4: Fault Interaction & Repair Validation API")
    app.include_router(create_router(adapter, store))

    @app.get("/api/health")
    def health():
        return {"status": "ok", "phase": 4, "service": "repair-validation"}

    return app


if __name__ == "__main__":
    import os, uvicorn
    port = int(os.environ.get("PORT", 8002))
    print(f"Starting Phase 4 API on port {port}...")
    uvicorn.run(create_app(), host="0.0.0.0", port=port)

