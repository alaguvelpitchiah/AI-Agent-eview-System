"""Adapter for the optional recruitment example agent."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from ...config import Settings
from ...integration.base_adapter import (
    OVERRIDE_CONFIG,
    OVERRIDE_STAGE,
    TRACE_EVENTS,
    AdapterOutput,
    AgentCapabilities,
    AgentInfo,
    BaseAgentAdapter,
    TraceEvent,
)
from .recruitment_agent import STAGES, RecruitmentAgent
from .settings import apply_overrides

_STAGE_SHAPES = {"resume_parser": dict, "job_retrieval": list, "candidate_ranking": list}
_PROFILE_KEYS = {"headline", "skills", "years_experience", "education_level", "education_label"}

_EXAMPLE_RESUME = (
    "Backend Python Developer\n4 years of experience building REST APIs.\n"
    "Skills: Python, SQL, REST API, Docker\nBachelor of Engineering in Computer Science"
)


class RecruitmentAdapter(BaseAgentAdapter):
    AGENT_ID = "recruitment-agent"

    def __init__(self, jobs_path: Path, agent: Optional[RecruitmentAgent] = None) -> None:
        self.agent = agent or RecruitmentAgent(jobs_path=jobs_path)

    def info(self) -> AgentInfo:
        return AgentInfo(
            agent_id=self.AGENT_ID,
            name="Recruitment Agent (example)",
            agent_type="recruitment",
            version=self.agent.version,
            description="Parses a resume, retrieves matching jobs and ranks them with a 0-100 match score.",
            input_schema={
                "fields": {
                    "resume_text": {"type": "str", "required": True, "min_length": 20, "max_length": 20000},
                    "target_job_id": {"type": "str", "required": False, "choices": sorted(self.agent.jobs_by_id)},
                },
                "allow_extra": False,
            },
            capabilities=AgentCapabilities(
                trace_level=TRACE_EVENTS,
                supports_stage_overrides=True,
                supports_config_overrides=True,
                deterministic=True,
            ),
            supported_stages=list(STAGES),
            example_inputs=[{"resume_text": _EXAMPLE_RESUME, "target_job_id": "J001"}],
        )

    def extra_override_errors(self, overrides: Dict[str, Any]) -> List[str]:
        errors: List[str] = []
        for name, value in (overrides.get(OVERRIDE_STAGE) or {}).items():
            if not isinstance(value, _STAGE_SHAPES[name]):
                errors.append(f"Override for '{name}' must be a {_STAGE_SHAPES[name].__name__}")
            elif name == "resume_parser" and not _PROFILE_KEYS <= set(value):
                errors.append(f"Parser override must contain {sorted(_PROFILE_KEYS)}")
        if overrides.get(OVERRIDE_CONFIG):
            try:
                apply_overrides(self.agent.config, overrides[OVERRIDE_CONFIG])
            except ValueError as exc:
                errors.append(str(exc))
        return errors

    def run(self, task_input: Dict[str, Any], overrides: Optional[Dict[str, Any]] = None) -> AdapterOutput:
        overrides = overrides or {}
        output, events = self.agent.run(
            resume_text=task_input["resume_text"],
            target_job_id=task_input.get("target_job_id"),
            stage_overrides=overrides.get(OVERRIDE_STAGE),
            config_overrides=overrides.get(OVERRIDE_CONFIG),
        )
        trace = [
            TraceEvent(
                kind="stage",
                name=e["stage"],
                input=e["input_summary"],
                output=e["output"],
                duration_ms=e["duration_ms"],
                overridden=e["overridden"],
                component_version=e["component_version"],
            )
            for e in events
        ]
        return AdapterOutput(output=output, events=trace, agent_version=output["config_version"])


def create_adapter(settings: Settings, **options: Any) -> RecruitmentAdapter:
    """Factory referenced from agents.yaml."""
    jobs_path = options.get("jobs_path") or settings.data_dir / "example_agents" / "recruitment" / "jobs.json"
    return RecruitmentAdapter(jobs_path=Path(jobs_path))
