from __future__ import annotations
from dataclasses import dataclass, field, asdict


@dataclass
class Repair:
    repair_id: str
    stage: str
    description: str
    patch: dict = field(default_factory=dict)     # config change the adapter applies


@dataclass
class Candidate:
    repair: Repair
    role: str          # "root_cause" (on a diagnosed stage) | "downstream_compensation"


@dataclass
class ValidationResult:
    repair_ids: tuple
    target_failures: list = field(default_factory=list)
    regression_failures: list = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.target_failures and not self.regression_failures


@dataclass
class Conflict:
    repair_a: str
    repair_b: str
    kind: str          # "interaction" | "overlapping_write" | "order_dependent"
    failed_cases: list
    detail: str


@dataclass
class Interaction:
    factors: list
    kind: str          # "synergistic" (fail only together) | "cancelling" (together they pass)
    detail: str


@dataclass
class InteractionReport:
    factors: list
    outcomes: list = field(default_factory=list)    # [{"present": [...], "fails": bool}]
    pairs: list = field(default_factory=list)       # [{"pair": [a,b], "interacts": bool, "kind": str|None}]
    interactions: list = field(default_factory=list)
    summary: str = "none"
    runs: int = 0
    note: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class RepairPlan:
    agent_id: str
    status: str                                     # "validated_fix" | "no_validated_fix"
    selected: list = field(default_factory=list)
    rationale: list = field(default_factory=list)
    candidates: list = field(default_factory=list)  # per-repair single validation summary
    conflicts: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    validations_used: int = 0

    def to_dict(self):
        return asdict(self)
