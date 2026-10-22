"""FastAPI application entry point.

Run from the backend folder:  uvicorn app.main:app --reload
Interactive API docs:         http://127.0.0.1:8000/docs
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.routes import agents, monitoring
from .config import Settings, get_settings
from .reviewer.fault_injector import FaultConfigError, FaultNotFoundError
from .services.monitoring_service import MonitoringService
from .storage import Database, RecordNotFoundError, TraceStore
from .integration import (
    AgentExecutor,
    AgentNotFoundError,
    AgentRegistry,
    TaskValidationError,
    build_default_registry,
)


def create_app(settings: Optional[Settings] = None, registry: Optional[AgentRegistry] = None) -> FastAPI:
    settings = settings or get_settings()
    registry = registry or build_default_registry(settings)
    executor = AgentExecutor(
        registry,
        timeout_seconds=settings.execution_timeout_seconds,
        max_task_bytes=settings.max_task_bytes,
    )

    store = TraceStore(Database(settings.database_path))
    monitoring_service = MonitoringService(executor, store, settings.data_dir)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield
        executor.shutdown()

    app = FastAPI(title="AI Agent Review System", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.registry = registry
    app.state.executor = executor
    app.state.store = store
    app.state.monitoring = monitoring_service

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.exception_handler(AgentNotFoundError)
    async def _not_found(_request: Request, exc: AgentNotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(TaskValidationError)
    async def _invalid(_request: Request, exc: TaskValidationError):
        return JSONResponse(status_code=422, content={"detail": {"errors": exc.errors}})

    @app.exception_handler(RecordNotFoundError)
    async def _record_missing(_request: Request, exc: RecordNotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(FaultNotFoundError)
    async def _fault_missing(_request: Request, exc: FaultNotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(FaultConfigError)
    async def _fault_config(_request: Request, exc: FaultConfigError):
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    @app.get("/api/health")
    def health():
        return {"status": "ok", "agents_registered": len(registry)}

    app.include_router(agents.router)
    app.include_router(monitoring.router)
    return app


app = create_app()
