"""The reference target agent: resume parsing -> job retrieval -> candidate ranking.

The agent is deterministic and each stage is a pure function, so the reviewer
can replay a run with one stage's output replaced (a counterfactual test) or
with a modified configuration (fault injection and repair testing).
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .candidate_ranker import rank_candidates
from .job_matcher import retrieve_jobs
from .resume_parser import parse_resume
from .settings import apply_overrides, config_version, load_config, load_jobs

STAGES = ("resume_parser", "job_retrieval", "candidate_ranking")


class RecruitmentAgent:
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        jobs: Optional[List[Dict[str, Any]]] = None,
        jobs_path: Optional[Path] = None,
    ) -> None:
        self.config = config if config is not None else load_config()
        if jobs is None:
            if jobs_path is None:
                raise ValueError("Provide either 'jobs' or 'jobs_path'")
            jobs = load_jobs(jobs_path)
        self.jobs = jobs
        self.jobs_by_id = {job["id"]: job for job in jobs}

    @property
    def version(self) -> str:
        return config_version(self.config)

    def run(
        self,
        resume_text: str,
        target_job_id: Optional[str] = None,
        stage_overrides: Optional[Dict[str, Any]] = None,
        config_overrides: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Run the pipeline. Returns (output, stage_events).

        stage_overrides: {stage_name: replacement_output}. The stage is skipped
            and its replacement is used instead (counterfactual testing).
        config_overrides: changes applied to a *copy* of the configuration.
        """
        stage_overrides = stage_overrides or {}
        unknown = set(stage_overrides) - set(STAGES)
        if unknown:
            raise ValueError(f"Unknown stages: {sorted(unknown)}")
        if target_job_id is not None and target_job_id not in self.jobs_by_id:
            raise ValueError(f"Unknown target_job_id '{target_job_id}'")

        config = apply_overrides(self.config, config_overrides)
        version = config_version(config)
        events: List[Dict[str, Any]] = []

        def stage(name: str, summary: Dict[str, Any], compute: Callable[[], Any]) -> Any:
            start = time.perf_counter()
            overridden = name in stage_overrides
            output = stage_overrides[name] if overridden else compute()
            events.append(
                {
                    "stage": name,
                    "input_summary": summary,
                    "output": output,
                    "duration_ms": round((time.perf_counter() - start) * 1000, 3),
                    "overridden": overridden,
                    "component_version": version,
                }
            )
            return output

        profile = stage(
            "resume_parser",
            {"resume_chars": len(resume_text)},
            lambda: parse_resume(resume_text, config),
        )
        retrieved = stage(
            "job_retrieval",
            {"skills_count": len(profile["skills"]), "jobs_considered": len(self.jobs)},
            lambda: retrieve_jobs(profile, self.jobs, config),
        )
        ranked = stage(
            "candidate_ranking",
            {"retrieved_count": len(retrieved)},
            lambda: rank_candidates(profile, retrieved, self.jobs_by_id, config),
        )

        top = ranked[0] if ranked else None
        target = None
        if target_job_id is not None:
            entry = next((r for r in ranked if r["job_id"] == target_job_id), None)
            target = {
                "job_id": target_job_id,
                "retrieved": any(r["job_id"] == target_job_id for r in retrieved),
                "match_score": entry["match_score"] if entry else 0.0,
                "rank": entry["rank"] if entry else None,
            }

        match_score = target["match_score"] if target else (top["match_score"] if top else None)
        output = {
            "candidate_profile": profile,
            "retrieved_jobs": retrieved,
            "ranked_jobs": ranked,
            "top_recommendation": (
                {"job_id": top["job_id"], "title": top["title"], "match_score": top["match_score"]} if top else None
            ),
            "target_job": target,
            "match_score": match_score,
            "config_version": version,
        }
        return output, events
