"""Request and response models for the REST API."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    input: Dict[str, Any] = Field(..., description="Input matching the agent's input schema")
    overrides: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional stage, tool or config overrides (for experiments)"
    )
    expected: Optional[Dict[str, Any]] = Field(
        default=None, description="Expected outcome, kept with the result for evaluation"
    )
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Free-form labels, e.g. a case id")


class AgentInfoResponse(BaseModel):
    agent_id: str
    name: str
    agent_type: str
    version: str
    description: str
    input_schema: Dict[str, Any]
    capabilities: Dict[str, Any]
    supported_stages: List[str]
    supported_tools: List[str]
    supported_overrides: List[str]
    example_inputs: List[Dict[str, Any]]


class RunResponse(BaseModel):
    execution_id: str
    agent_id: str
    agent_version: str
    status: str
    started_at: str
    duration_ms: float
    input: Dict[str, Any]
    overrides: Optional[Dict[str, Any]] = None
    expected: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    output: Any = None
    events: List[Dict[str, Any]] = []
    usage: Dict[str, Any] = {}
    error: Optional[Dict[str, str]] = None


class BenchmarkCase(BaseModel):
    case_id: str
    input: Dict[str, Any]
    expected: Dict[str, Any]
    tags: List[str] = []
