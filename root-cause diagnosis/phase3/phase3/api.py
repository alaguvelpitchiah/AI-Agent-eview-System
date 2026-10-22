"""FastAPI router and server for Root-Cause Diagnosis API (Phase 3).

Endpoints:
- POST /api/agents/{agent_id}/diagnose
- GET  /api/diagnoses
- GET  /api/diagnoses/{diagnosis_id}
- GET  /api/health
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure phase3 root is in sys.path regardless of execution method
_CUR = Path(__file__).resolve().parent
_PHASE3_ROOT = _CUR.parent

for _p in [str(_PHASE3_ROOT), str(_CUR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _ensure_venv_packages():
    """Auto-detect project .venv site-packages if not already in sys.path."""
    try:
        import fastapi  # noqa: F401
        return
    except ImportError:
        pass

    search_dirs = [
        _PHASE3_ROOT / ".venv",
        _CUR / ".venv",
        _PHASE3_ROOT.parent / "Monitoring and Faliure Detection" / "ai-agent-review-system" / "backend" / ".venv",
        _PHASE3_ROOT.parent / "Integration " / "ai-agent-review-system" / "backend" / ".venv",
    ]
    for d in search_dirs:
        if d.exists():
            sp = list(d.glob("lib/python*/site-packages"))
            if sp and sp[0].exists():
                sys.path.insert(0, str(sp[0]))
                break


_ensure_venv_packages()

# Allow both module imports (phase3.api) and standalone script execution (python api.py)
if not __package__:
    __package__ = "phase3"
    from phase3.root_cause_engine import RootCauseEngine
    from phase3.toy_agent import ToyAdapter
    from phase3.storage import DiagnosisStore
else:
    from .root_cause_engine import RootCauseEngine
    from .toy_agent import ToyAdapter
    from .storage import DiagnosisStore


def create_router(adapter, store, engine=None):
    from fastapi import APIRouter, HTTPException

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


def create_app(adapter=None, store=None, engine=None):
    from fastapi import FastAPI

    adapter = adapter or ToyAdapter()
    store = store or DiagnosisStore()

    app = FastAPI(
        title="AI Agent Root-Cause Diagnosis API (Phase 3)",
        version="0.3.0",
        description="Root-cause diagnosis and failure analysis API for AI agents",
    )
    app.include_router(create_router(adapter, store, engine))

    @app.get("/")
    def index():
        return {
            "service": "AI Agent Root-Cause Diagnosis API",
            "phase": "Phase 3",
            "docs": "/docs",
            "endpoints": [
                "POST /api/agents/{agent_id}/diagnose",
                "GET  /api/diagnoses",
                "GET  /api/diagnoses/{diagnosis_id}",
                "GET  /api/health",
            ],
        }

    @app.get("/api/health")
    def health():
        return {"status": "ok", "service": "root-cause-diagnosis"}

    return app


try:
    app = create_app()
except ImportError:
    app = None


def _free_port(port: int):
    """Safely release port if occupied by a previous process to prevent [Errno 98]."""
    import os
    import subprocess
    import time

    try:
        current_pid = os.getpid()
        out = subprocess.check_output(["lsof", "-ti", f":{port}"], text=True).strip()
        if out:
            pids = [int(p) for p in out.split() if int(p) != current_pid]
            if pids:
                print(f"-> Port {port} is held by PID(s) {pids}. Freeing port...")
                for pid in pids:
                    try:
                        os.kill(pid, 15)
                    except OSError:
                        pass
                time.sleep(0.4)
                try:
                    recheck = subprocess.check_output(["lsof", "-ti", f":{port}"], text=True).strip()
                    for pid in [int(p) for p in recheck.split() if int(p) != current_pid]:
                        try:
                            os.kill(pid, 9)
                        except OSError:
                            pass
                    time.sleep(0.2)
                except Exception:
                    pass
    except Exception:
        pass


def main():
    import uvicorn

    host = "0.0.0.0"
    port = 8001

    # Automatically free port if held by previous runs
    _free_port(port)

    print("=" * 60)
    print("AI Agent Root-Cause Diagnosis API Server")
    print(f"Active Port: {port}")
    print(f"Base URL:    http://127.0.0.1:{port}")
    print(f"API Docs:    http://127.0.0.1:{port}/docs")
    print("=" * 60)

    global app
    if app is None:
        app = create_app()
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
