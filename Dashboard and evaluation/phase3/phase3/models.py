"""Shared data types for Phase 3 (root-cause diagnosis)."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class StageEvent:
    name: str
    input: dict
    output: Any = None
    error: Optional[str] = None
    overridden: bool = False


@dataclass
class RunRecord:
    status: str                      # "success" | "error"
    output: Any = None
    events: list = field(default_factory=list)   # list[StageEvent]
    error: Optional[str] = None

    def event(self, name: str) -> Optional[StageEvent]:
        for e in self.events:
            if e.name == name:
                return e
        return None


@dataclass
class Experiment:
    experiment_id: int
    kind: str          # "stage_isolation" | "repair"
    target: tuple      # stage names involved
    outcome: bool      # isolation: stage is faulty. repair: run passed after repair.
    detail: str = ""


@dataclass
class StageDivergence:
    stage: str
    present: bool
    input_same: bool
    output_same: bool

    @property
    def local_origin(self) -> bool:
        """Same input as the reference, different output."""
        return self.present and self.input_same and not self.output_same


@dataclass
class Diagnosis:
    agent_id: str
    verdict: str       # single_root_cause | joint_root_cause | inconclusive | no_failure
    suspected_stages: list = field(default_factory=list)
    confidence: str = "none"          # none | low | medium | high
    interaction_pattern: Optional[str] = None
    minimal_fix_sets: list = field(default_factory=list)
    evidence: list = field(default_factory=list)
    divergences: list = field(default_factory=list)
    experiments: list = field(default_factory=list)
    untested_stages: list = field(default_factory=list)

    @property
    def root_stage(self) -> Optional[str]:
        return self.suspected_stages[0] if self.verdict == "single_root_cause" else None

    def to_dict(self) -> dict:
        return asdict(self)
