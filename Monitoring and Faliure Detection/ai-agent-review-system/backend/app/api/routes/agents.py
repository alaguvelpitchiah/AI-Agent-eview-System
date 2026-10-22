"""Endpoints for listing agents, browsing their benchmark cases and running inputs."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Request

from ...integration.case_loader import load_cases
from ..schemas import AgentInfoResponse, BenchmarkCase, RunRequest, RunResponse

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("", response_model=List[AgentInfoResponse])
def list_agents(request: Request):
    return [info.to_dict() for info in request.app.state.registry.list_info()]


@router.get("/{agent_id}", response_model=AgentInfoResponse)
def get_agent(agent_id: str, request: Request):
    return request.app.state.registry.get(agent_id).info().to_dict()


@router.get("/{agent_id}/cases", response_model=List[BenchmarkCase])
def list_cases(agent_id: str, request: Request):
    request.app.state.registry.get(agent_id)  # 404 for unknown agents
    return load_cases(request.app.state.settings.data_dir, agent_id)


@router.post("/{agent_id}/run", response_model=RunResponse)
def run_agent(agent_id: str, body: RunRequest, request: Request):
    result = request.app.state.executor.execute(
        agent_id, body.input, overrides=body.overrides, expected=body.expected, metadata=body.metadata
    )
    return result.to_dict()
