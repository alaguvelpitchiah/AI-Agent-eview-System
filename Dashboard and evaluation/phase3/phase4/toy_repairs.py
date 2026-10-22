"""Toy adapter with a repair catalog, including two compensating 'distractor' repairs."""
from __future__ import annotations
from phase3.toy_agent import ToyAdapter
from .models import Repair

CATALOG = {
    "tokenize": [Repair("RP1", "tokenize", "remove the token limit", {"max_tokens": None})],
    "extract_skills": [Repair("RP2", "extract_skills", "stop dropping skills", {"drop": []})],
    "score": [Repair("RP3", "score", "use the correct denominator", {"denom_extra": 0})],
    "decide": [Repair("RP4", "decide", "threshold 0.5 (original)", {"threshold": 0.5}),
               Repair("RP5", "decide", "lower threshold to 0.3 (compensates for low scores)", {"threshold": 0.3}),
               Repair("RP6", "decide", "raise threshold to 0.6", {"threshold": 0.6})],
}
TRUE_REPAIR = {"TOY-F01": "RP1", "TOY-F02": "RP2", "TOY-F03": "RP3", "TOY-F04": "RP4"}


class ToyRepairAdapter(ToyAdapter):
    def candidate_repairs(self, agent_id, stage):
        return list(CATALOG.get(stage, []))

    def true_repair(self, agent_id, fault_id):
        return TRUE_REPAIR[fault_id]

    def get_repair(self, agent_id, repair_id):
        for rs in CATALOG.values():
            for r in rs:
                if r.repair_id == repair_id:
                    return r
        raise KeyError(repair_id)

    def agent_version(self, agent_id):
        return "1.0.0"
